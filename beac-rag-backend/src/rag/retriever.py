"""Retrieval vectoriel : transforme une question en contexte documentaire."""
from __future__ import annotations

from dataclasses import dataclass

from src.config import CONFIG
from src.database.connection import session_scope
from src.database.schema import Document
from src.database.vector_store import RetrievedChunk, similarity_search
from src.indexing.embeddings import get_embedder

_RET = CONFIG.get("retrieval", {})
_TOP_K = int(_RET.get("top_k", 6))
_MIN_SIM = float(_RET.get("min_similarity", 0.3))


@dataclass
class ContextItem:
    content: str
    score: float
    source: str
    category: str | None
    year: int | None
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

    chunks: list[RetrievedChunk] = similarity_search(
        query_embedding=query_vec,
        top_k=top_k or _TOP_K,
        filters=filters,
        min_similarity=_MIN_SIM,
    )
    if not chunks:
        # Repli sans filtre si trop restrictif
        if filters:
            chunks = similarity_search(
                query_embedding=query_vec,
                top_k=top_k or _TOP_K,
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
        items.append(
            ContextItem(
                content=c.content,
                score=c.score,
                source=doc.filename if doc else f"doc#{c.document_id}",
                category=doc.category if doc else None,
                year=doc.year if doc else None,
                image_paths=meta.get("image_paths"),
            )
        )
    return items


def format_context(items: list[ContextItem]) -> str:
    """Formate les chunks en texte avec citation de source."""
    if not items:
        return "[Aucun document pertinent trouve.]"
    blocks = []
    for i, item in enumerate(items, 1):
        src = item.source
        if item.year:
            src += f", {item.year}"
        blocks.append(f"[Source {i} : {src}]\n{item.content}")
    return "\n\n".join(blocks)
