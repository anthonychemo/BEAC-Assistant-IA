"""Import manuel d'un document unique depuis le dashboard admin (bouton
"Importer un document") : upload vers R2 puis extraction + chunking +
embeddings + insertion en base, en arriere-plan (meme pattern de suivi que
`pipeline_runner.py`) pour que la reponse HTTP soit immediate et que le
document devienne interrogeable dans le chat des que le statut passe a "done".
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from src.ingestion.pipeline import ingest_single_upload
from src.ingestion.r2_client import upload_file
from src.utils.logger import logger

_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@dataclass
class _UploadState:
    status: str = "processing"  # processing | done | error
    filename: str = ""
    document_id: int | None = None
    chunks: int = 0
    error: str | None = None


_uploads: dict[str, _UploadState] = {}
_lock = threading.Lock()


def _process(upload_id: str, tmp_path: Path, r2_key: str, meta: dict) -> None:
    state = _uploads[upload_id]
    try:
        content_type = _CONTENT_TYPES.get(tmp_path.suffix.lower(), "application/octet-stream")
        upload_file(tmp_path, r2_key, content_type, meta)
        doc_id, n_chunks = ingest_single_upload(tmp_path, r2_key, meta)
        with _lock:
            state.status = "done"
            state.document_id = doc_id
            state.chunks = n_chunks
    except Exception as exc:
        logger.exception(f"Import manuel echoue ({state.filename})")
        with _lock:
            state.status = "error"
            state.error = str(exc)
    finally:
        tmp_path.unlink(missing_ok=True)


def start_upload(tmp_path: Path, filename: str, category: str | None) -> str:
    """Demarre le traitement en arriere-plan, retourne l'id a interroger."""
    upload_id = uuid.uuid4().hex[:12]
    safe_name = Path(filename).name
    r2_key = f"imports_manuels/{upload_id}_{safe_name}"
    meta = {
        "module": category or "Import manuel",
        "section": "Import manuel",
        "nom_pdf": safe_name,
        "date_publication": date.today().isoformat(),
        "type_document": "document",
    }
    state = _UploadState(filename=safe_name)
    with _lock:
        _uploads[upload_id] = state
    thread = threading.Thread(target=_process, args=(upload_id, tmp_path, r2_key, meta), daemon=True)
    thread.start()
    return upload_id


def get_status(upload_id: str) -> dict | None:
    with _lock:
        state = _uploads.get(upload_id)
        if not state:
            return None
        return {
            "status": state.status,
            "filename": state.filename,
            "document_id": state.document_id,
            "chunks": state.chunks,
            "error": state.error,
        }
