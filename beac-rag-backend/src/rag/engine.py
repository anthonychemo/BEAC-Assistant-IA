"""Moteur RAG hybride : orchestre routage, retrieval (vectoriel + SQL) et generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from src.rag.llm_client import get_llm
from src.rag.prompts import SYSTEM_PROMPT, build_rag_prompt
from src.rag.query_router import QueryType, classify_query
from src.rag.retriever import ContextItem, format_context, retrieve_context
from src.rag.sql_generator import format_sql_context, run_statistics_query
from src.utils.logger import logger
from src.rag.cache import get_cache

@dataclass
class RAGResponse:
    answer: str
    query_type: str
    sources: list[dict] = field(default_factory=list)
    sql: str | None = None
    context_used: str = ""


def _build_context(question: str) -> tuple[str, list[ContextItem], str | None, str]:
    """Construit le contexte selon le type de question. Retourne
    (contexte_texte, items_vectoriels, sql_execute, query_type)."""
    routed = classify_query(question)
    logger.info(f"Question routee : {routed.query_type} | filtres={routed.filters}")

    context_parts: list[str] = []
    vector_items: list[ContextItem] = []
    sql_used: str | None = None

    # Partie SQL (donnees chiffrees)
    if routed.query_type in (QueryType.SQL, QueryType.HYBRID):
        sql_result = run_statistics_query(question)
        sql_used = sql_result.sql
        context_parts.append(format_sql_context(sql_result))

    # Partie vectorielle (texte narratif)
    if routed.query_type in (QueryType.VECTOR, QueryType.HYBRID):
        vector_items = retrieve_context(question, filters=routed.filters)
        context_parts.append(format_context(vector_items))

    context = "\n\n".join(p for p in context_parts if p)
    return context, vector_items, sql_used, routed.query_type.value


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
            "image_paths": item.image_paths,
        })
    return sources


def answer_question(question: str) -> RAGResponse:
    """Reponse complete (non-streaming)."""
    context, vector_items, sql_used, qtype = _build_context(question)
    prompt = build_rag_prompt(question, context)
    answer = get_llm().generate(prompt, system=SYSTEM_PROMPT)
    return RAGResponse(
        answer=answer,
        query_type=qtype,
        sources=_sources_from_items(vector_items),
        sql=sql_used,
        context_used=context,
    )


def stream_answer(question: str) -> Iterator[str]:
    """Reponse en streaming (pour interface temps reel)."""
    context, _, _, _ = _build_context(question)
    prompt = build_rag_prompt(question, context)
    yield from get_llm().stream(prompt, system=SYSTEM_PROMPT)



def answer_question(question: str) -> RAGResponse:
    cache = get_cache()

    # Vérifier le cache d'abord
    cached = cache.get(question)
    if cached is not None:
        logger.info("Réponse servie depuis le cache")
        return cached

    # Pipeline normal
    context, vector_items, sql_used, qtype = _build_context(question)
    prompt = build_rag_prompt(question, context)
    answer = get_llm().generate(prompt, system=SYSTEM_PROMPT)

    result = RAGResponse(
        answer=answer,
        query_type=qtype,
        sources=_sources_from_items(vector_items),
        sql=sql_used,
        context_used=context,
    )

    use_fast = (qtype == QueryType.SQL.value)
    answer = get_llm().generate(prompt, system=SYSTEM_PROMPT, fast=use_fast)

    cache.set(question, result)
    return result
