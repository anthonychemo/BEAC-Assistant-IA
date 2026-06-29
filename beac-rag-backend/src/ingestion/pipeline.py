"""Orchestrateur d'ingestion : parcourt les fichiers sources, extrait le texte
(PDF natif/OCR + Excel), decoupe en chunks, calcule les embeddings et insere
le tout dans PostgreSQL (documents + chunks + statistics).

Idempotent : un fichier deja ingere (meme source_path) est ignore.
Optimisations :
- Filtrage idempotent en bulk (1 requete DB pour tout le lot).
- Micro-batching : les fichiers sont groupes par lots ; les embeddings de tout
  le lot sont calcules en un seul appel au modele (meilleure saturation CPU).
"""
from __future__ import annotations

import gc

from dataclasses import dataclass, field
from pathlib import Path

from tqdm import tqdm

from src.config import CONFIG, settings
from src.database.connection import session_scope
from src.database.schema import Document, Statistic
from src.database.vector_store import build_chunk_objects
from src.indexing.embeddings import get_embedder
from src.ingestion.chunker import chunk_text
from src.ingestion.excel_processor import ExcelParseResult, parse_excel
from src.ingestion.pdf_processor import PdfExtractionResult, extract_pdf_text
from src.utils.logger import logger
from src.utils.metadata import extract_metadata_from_path

_ING = CONFIG.get("ingestion", {})
_PDF_EXT = set(_ING.get("pdf_extensions", [".pdf"]))
_EXCEL_EXT = set(_ING.get("excel_extensions", [".xls", ".xlsx"]))
_EMB_BATCH = int(CONFIG.get("embeddings", {}).get("batch_size", 16))
_FILE_BATCH = int(_ING.get("batch_size", 8))


@dataclass
class _FileWork:
    """Travail en cours pour un fichier au sein d'un lot (batch)."""
    file_path: Path
    meta: dict
    file_type: str
    pdf_result: PdfExtractionResult | None = None
    excel_result: ExcelParseResult | None = None
    contents: list[str] = field(default_factory=list)
    tokens: list[int] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)
    image_paths: list[str] = field(default_factory=list)


@dataclass
class IngestStats:
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    chunks: int = 0
    stat_rows: int = 0


def _already_ingested_bulk(session, paths: list[str]) -> set[str]:
    """Retourne l'ensemble des source_path deja presents en base."""
    if not paths:
        return set()
    rows = session.query(Document.source_path).filter(Document.source_path.in_(paths)).all()
    return {row[0] for row in rows}


def _create_document(session, file_path: Path, meta: dict, file_type: str,
                     method: str | None, page_count: int | None, char_count: int | None) -> int:
    doc = Document(
        source_path=meta["relative_path"],
        filename=file_path.name,
        file_type=file_type,
        category=meta.get("category"),
        subcategory=meta.get("subcategory"),
        country=meta.get("country"),
        year=meta.get("year"),
        extraction_method=method,
        page_count=page_count,
        char_count=char_count,
        doc_metadata=meta,
    )
    session.add(doc)
    session.flush()  # pour obtenir doc.id
    return doc.id


def _prepare_chunks(text_blocks: list[str]) -> tuple[list[str], list[int]]:
    """Decoupe les blocs de texte en chunks (sans aucune ecriture DB)."""
    contents: list[str] = []
    tokens: list[int] = []
    for block in text_blocks:
        for ch in chunk_text(block):
            contents.append(ch.content)
            tokens.append(ch.token_count)
    return contents, tokens


def _embed_chunks(contents: list[str]) -> list[list[float]]:
    """Calcule les embeddings par lots (sans ecriture DB)."""
    embedder = get_embedder()
    vectors: list[list[float]] = []
    for start in range(0, len(contents), _EMB_BATCH):
        batch = contents[start:start + _EMB_BATCH]
        vecs = embedder.embed_documents(batch)
        vectors.extend(vecs)
        del vecs   # libération immédiate des tenseurs intermédiaires
        gc.collect()   # force le GC après chaque batch
    return vectors


def _extract_all(file_batch: list[Path], metas: list[dict]) -> list[_FileWork]:
    """Extrait le texte de tous les fichiers d'un lot (tolerance aux erreurs)."""
    works: list[_FileWork] = []
    for fp, meta in zip(file_batch, metas):
        try:
            if fp.suffix.lower() in _PDF_EXT:
                result = extract_pdf_text(fp)
                if not result.text.strip():
                    logger.warning(f"Aucun texte extrait : {fp.name}")
                    continue
                works.append(_FileWork(
                    file_path=fp, meta=meta, file_type="pdf", pdf_result=result,
                    image_paths=result.image_paths,
                ))
            else:
                parsed = parse_excel(fp)
                if not parsed.text_blocks and not parsed.statistics:
                    logger.warning(f"Excel vide/illisible : {fp.name}")
                    continue
                works.append(_FileWork(
                    file_path=fp, meta=meta, file_type="excel", excel_result=parsed,
                ))
        except Exception as exc:
            logger.exception(f"Extraction echouee {fp.name}: {exc}")
    return works


def _prepare_batch(works: list[_FileWork], stats: IngestStats) -> list[_FileWork]:
    """Decoupe les textes en chunks pour chaque work ; filtre les vides."""
    prepared: list[_FileWork] = []
    for w in works:
        blocks = (
            [w.pdf_result.text] if w.file_type == "pdf"
            else (w.excel_result.text_blocks if w.excel_result else [])
        )
        contents, tokens = _prepare_chunks(blocks)
        if not contents:
            logger.warning(f"Aucun chunk exploitable : {w.file_path.name}")
            stats.failed += 1
            continue
        w.contents = contents
        w.tokens = tokens
        prepared.append(w)
    return prepared


def _insert_work(session, w: _FileWork) -> None:
    """Insertion atomique d'un fichier (document + stats + chunks)."""
    if w.file_type == "pdf" and w.pdf_result is not None:
        doc_id = _create_document(
            session, w.file_path, w.meta, w.file_type,
            w.pdf_result.method, w.pdf_result.page_count, w.pdf_result.char_count,
        )
    else:
        full_text = "\n".join(w.excel_result.text_blocks) if w.excel_result else ""
        doc_id = _create_document(
            session, w.file_path, w.meta, w.file_type,
            "excel", None, len(full_text),
        )
        if w.excel_result:
            for sr in w.excel_result.statistics:
                session.add(Statistic(
                    document_id=doc_id,
                    indicator=sr.indicator,
                    country=sr.country,
                    period=sr.period,
                    year=sr.year,
                    value=sr.value,
                    unit=sr.unit,
                    raw_label=sr.raw_label,
                    source_sheet=sr.source_sheet,
                ))
    chunk_metas = _build_chunk_metas(w)
    session.add_all(build_chunk_objects(
        doc_id, w.contents, w.vectors, w.tokens,
        chunk_metas,
    ))


def _build_chunk_metas(w: _FileWork) -> list[dict]:
    """Construit les metadatas pour chaque chunk ; injecte image_paths dans le premier."""
    base = {
        "category": w.meta.get("category"),
        "subcategory": w.meta.get("subcategory"),
        "country": w.meta.get("country"),
        "year": w.meta.get("year"),
        "source": w.meta.get("relative_path"),
    }
    metas = [base.copy() for _ in w.contents]
    if w.image_paths:
        metas[0]["image_paths"] = w.image_paths
    return metas


def _iter_files(root: Path) -> list[Path]:
    exts = _PDF_EXT | _EXCEL_EXT
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts]


def ingest_directory(root: Path | None = None, limit: int | None = None,
                     only: str | None = None) -> IngestStats:
    """Ingestion complete d'un dossier avec micro-batching pour la vitesse.

    `only` : 'pdf' ou 'excel' pour ne traiter qu'un type. `limit` : nb max de fichiers.
    """
    root = root or settings.raw_data_path
    if not root.exists():
        raise FileNotFoundError(f"Dossier source introuvable : {root}")

    files = _iter_files(root)
    if only == "pdf":
        files = [f for f in files if f.suffix.lower() in _PDF_EXT]
    elif only == "excel":
        files = [f for f in files if f.suffix.lower() in _EXCEL_EXT]
    if limit:
        files = files[:limit]

    # Pre-calcul des metadonnees
    all_metas = [extract_metadata_from_path(fp, root) for fp in files]

    # Idempotence en bulk : 1 requete pour tout le lot
    with session_scope() as session:
        existing = _already_ingested_bulk(session, [m["relative_path"] for m in all_metas])
    files = [fp for fp, meta in zip(files, all_metas) if meta["relative_path"] not in existing]
    metas = [meta for meta in all_metas if meta["relative_path"] not in existing]
    skipped_initial = len(all_metas) - len(files)

    logger.info(
        f"{len(files)} fichiers a traiter depuis {root} "
        f"({skipped_initial} deja presents en base)"
    )
    stats = IngestStats(skipped=skipped_initial)

    # Traitement par micro-lots : extraction + embeddings groupes
    for i in range(0, len(files), _FILE_BATCH):
        batch_files = files[i:i + _FILE_BATCH]
        batch_metas = metas[i:i + _FILE_BATCH]

        # 1. Extraction
        works = _extract_all(batch_files, batch_metas)

        # 2. Chunking
        works = _prepare_batch(works, stats)
        if not works:
            continue

        # 3. Embedding unique de tout le lot (meilleure saturation CPU/GPU)
        all_contents = []
        for w in works:
            all_contents.extend(w.contents)
        all_vectors = _embed_chunks(all_contents)

        # 4. Redistribution des vecteurs par fichier
        idx = 0
        for w in works:
            n = len(w.contents)
            w.vectors = all_vectors[idx:idx + n]
            idx += n

        # 5. Insertion atomique par fichier
        for w in works:
            try:
                with session_scope() as session:
                    _insert_work(session, w)
                stats.processed += 1
                stats.chunks += len(w.contents)
                if w.file_type == "excel" and w.excel_result:
                    stats.stat_rows += len(w.excel_result.statistics)
            except Exception as exc:
                logger.exception(f"Insertion echouee {w.file_path.name}: {exc}")
                stats.failed += 1

    logger.info(
        f"Ingestion terminee : {stats.processed} traites, {stats.skipped} ignores, "
        f"{stats.failed} echecs, {stats.chunks} chunks, {stats.stat_rows} stats."
    )
    return stats
