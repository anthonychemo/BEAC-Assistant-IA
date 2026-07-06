"""Retrieval vectoriel : transforme une question en contexte documentaire."""
from __future__ import annotations

from dataclasses import dataclass

from src.config import CONFIG
from src.database.connection import session_scope
from src.database.schema import Document
from src.database.vector_store import RetrievedChunk, similarity_search
from src.indexing.embeddings import get_embedder
from src.utils.logger import logger

_RET = CONFIG.get("retrieval", {})
_TOP_K = int(_RET.get("top_k", 6))
_MIN_SIM = float(_RET.get("min_similarity", 0.3))
_CONFIDENT_THRESHOLD = 0.55



@dataclass
class ContextItem:
    content: str
    score: float
    source: str
    category: str | None
    year: int | None
    source_url: str | None = None
    image_paths: list[str] | None = None
    


def _document_info(document_ids: list[int]) -> dict[int, Document]:
    if not document_ids:
        return {}
    with session_scope() as session:
        docs = session.query(Document).filter(Document.id.in_(document_ids)).all()
        return {d.id: d for d in docs}


def retrieve_context(
    question: str,
    top_k: int | None = None,
    filters: dict | None = None,
) -> list[ContextItem]:
    """Recherche les chunks pertinents et enrichit avec les infos document."""
    embedder = get_embedder()
    query_vec = embedder.embed_query(question)
    k = top_k or _TOP_K

    chunks: list[RetrievedChunk] = similarity_search(
        query_embedding=query_vec,
        top_k=k,
        filters=filters,
        min_similarity=_MIN_SIM,
    )

    # Fallback unique : si aucun resultat avec filtres, retenter sans
    if not chunks and filters:
        logger.info("Fallback : recherche sans filtres")
        chunks = similarity_search(
            query_embedding=query_vec,
            top_k=k,
            filters=None,
            min_similarity=_MIN_SIM,
        )

    if not chunks:
        return []

    docs = _document_info([c.document_id for c in chunks])
    items: list[ContextItem] = []
    for c in chunks:
        doc = docs.get(c.document_id)
        meta = c.metadata or {}
        items.append(ContextItem(
            content=c.content,
            score=c.score,
            source=doc.filename if doc else f"doc#{c.document_id}",
            category=doc.category if doc else None,
            year=doc.year if doc else None,
            image_paths=meta.get("image_paths"),
            source_url=doc.source_url if doc else None,
        ))
    return items


def format_context(items: list[ContextItem]) -> str:
    """Formate les chunks en texte avec citation de source — tronque si necessaire."""
    if not items:
        return "[Aucun document pertinent trouve.]"
    blocks = []
    total_chars = 0
    MAX_CHARS = 6000  # limite safe pour les modeles gratuits OpenRouter
    for i, item in enumerate(items, 1):
        src = item.source
        if item.year:
            src += f", {item.year}"
        block = f"[Source {i} : {src}]\n{item.content}"
        if total_chars + len(block) > MAX_CHARS:
            break
        blocks.append(block)
        total_chars += len(block)
    return "\n\n".join(blocks)

def _sources_from_items(items: list[ContextItem]) -> list[dict]:
    seen = set()
    sources = []
    for item in items:
        key = (item.source, item.year)
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "source": item.source,
            "category": item.category,
            "year": item.year,
            "score": round(item.score, 3),
            "source_url": item.source_url or "https://www.beac.int",
            "image_paths": item.image_paths,
        })
    return sources
