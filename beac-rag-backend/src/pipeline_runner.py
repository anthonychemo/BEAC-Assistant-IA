"""Orchestration du pipeline complet declenchable depuis le bouton "Demarrer
le pipeline" du dashboard admin : scraping du site BEAC -> upload des PDF
vers R2 -> liaison des documents existants a leur fichier -> ingestion des
documents reellement nouveaux (chunking + embeddings + insertion DB).

Chaque etape est un sous-processus independant (le scraper vit dans un projet
et un venv separes, data_pipeline/Scrapping) ; l'etat d'avancement est suivi
en memoire - suffisant pour un usage mono-utilisateur (pas de file d'attente).
"""
from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import func

from src.database.connection import session_scope
from src.database.schema import Document
from src.utils.logger import logger

_BACKEND_DIR = Path(__file__).resolve().parents[1]  # beac-rag-backend/
_REPO_ROOT = _BACKEND_DIR.parent
_SCRAPER_DIR = _REPO_ROOT / "data_pipeline" / "Scrapping"
_SCRAPER_PYTHON = _SCRAPER_DIR / ".venv" / "Scripts" / "python.exe"
_BACKEND_PYTHON = _BACKEND_DIR / ".venv" / "Scripts" / "python.exe"

STAGE_LABELS = {
    "scraping": "Scraping du site BEAC",
    "upload_r2": "Upload des documents vers R2",
    "liaison_r2": "Liaison des documents existants",
    "liaison_sources": "Liaison des liens source",
    "ingestion": "Ingestion des nouveaux documents",
    "termine": "Termine",
}


@dataclass
class _PipelineState:
    status: str = "idle"  # idle | running | done | error
    stage: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    new_documents: int = 0
    error: str | None = None
    log_tail: list[str] = field(default_factory=list)


_state = _PipelineState()
_lock = threading.Lock()


def get_status() -> dict:
    with _lock:
        return {
            "status": _state.status,
            "stage": _state.stage,
            "stage_label": STAGE_LABELS.get(_state.stage or "", _state.stage),
            "started_at": _state.started_at,
            "finished_at": _state.finished_at,
            "new_documents": _state.new_documents,
            "error": _state.error,
            "log_tail": list(_state.log_tail[-20:]),
        }


def _set(**kwargs) -> None:
    with _lock:
        for k, v in kwargs.items():
            setattr(_state, k, v)


def _append_log(line: str) -> None:
    with _lock:
        _state.log_tail.append(line)
        del _state.log_tail[:-200]


def _run_step(cmd: list[str], cwd: Path, stage: str) -> None:
    _set(stage=stage)
    _append_log(f"--- {STAGE_LABELS.get(stage, stage)} ---")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        _append_log(line.rstrip())
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"Etape '{STAGE_LABELS.get(stage, stage)}' echouee (code {code})")


def _count_documents() -> int:
    with session_scope() as session:
        return session.query(func.count(Document.id)).scalar() or 0


def _run_pipeline_thread() -> None:
    started_count = _count_documents()
    try:
        _set(status="running", started_at=time.time(), finished_at=None, error=None, new_documents=0)

        _run_step([str(_SCRAPER_PYTHON), "-u", "scraper.py"], _SCRAPER_DIR, "scraping")
        _run_step([str(_SCRAPER_PYTHON), "-u", "upload_to_r2.py"], _SCRAPER_DIR, "upload_r2")
        _run_step(
            [str(_BACKEND_PYTHON), "-u", "-m", "scripts.backfill_r2_keys"], _BACKEND_DIR, "liaison_r2"
        )
        _run_step(
            [str(_BACKEND_PYTHON), "-u", "-m", "scripts.backfill_source_urls"], _BACKEND_DIR, "liaison_sources"
        )
        _run_step([str(_BACKEND_PYTHON), "-u", "-m", "scripts.ingest"], _BACKEND_DIR, "ingestion")

        new_count = _count_documents() - started_count
        _set(status="done", stage="termine", finished_at=time.time(), new_documents=new_count)
        _append_log(f"Pipeline termine : {new_count} nouveaux documents indexes.")
    except Exception as exc:
        logger.exception("Pipeline echoue")
        _set(status="error", error=str(exc), finished_at=time.time())
        _append_log(f"ERREUR : {exc}")


def start_pipeline() -> bool:
    """Demarre le pipeline en arriere-plan. Retourne False s'il tourne deja."""
    with _lock:
        if _state.status == "running":
            return False
    thread = threading.Thread(target=_run_pipeline_thread, daemon=True)
    thread.start()
    return True
