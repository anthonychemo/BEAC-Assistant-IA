"""Moteur RAG hybride : orchestre routage, retrieval (vectoriel + SQL) et generation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from src.rag.llm_client import get_llm
from src.rag.prompts import SYSTEM_PROMPT, META_RESPONSE, build_rag_prompt
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
    routed = classify_query(question)
    logger.info(f"Question routee : {routed.query_type} | filtres={routed.filters}")

    context_parts: list[str] = []
    vector_items: list[ContextItem] = []
    sql_used: str | None = None

    if routed.query_type in (QueryType.SQL, QueryType.HYBRID):
        sql_result = run_statistics_query(question)
        sql_used = sql_result.sql
        context_parts.append(format_sql_context(sql_result))

    if routed.query_type in (QueryType.VECTOR, QueryType.HYBRID):
        top_k = 12 if getattr(routed, "exploratory", False) else None
        vector_items = retrieve_context(question, top_k=top_k, filters=routed.filters)
        context_parts.append(format_context(vector_items))

    context = "\n\n".join(p for p in context_parts if p)
    return context, vector_items, sql_used, routed.query_type.value


def _sources_from_items(items: list[ContextItem]) -> list[dict]:
    seen: set = set()
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


def answer_question(question: str, **kwargs) -> RAGResponse:
    """Reponse complete avec cache."""
    routed = classify_query(question)

    if hasattr(QueryType, "META") and routed.query_type == QueryType.META:
        return RAGResponse(answer=META_RESPONSE, query_type=QueryType.META.value, sources=[])

    cache = get_cache()
    cached = cache.get(question)
    if cached is not None:
        logger.info("Reponse servie depuis le cache")
        return cached

    context, vector_items, sql_used, qtype = _build_context(question)
    exploratory = getattr(routed, "exploratory", False)
    prompt = build_rag_prompt(question, context, exploratory=exploratory)
    answer = get_llm().generate(prompt, system=SYSTEM_PROMPT)

    result = RAGResponse(
        answer=answer,
        query_type=qtype,
        sources=_sources_from_items(vector_items),
        sql=sql_used,
        context_used=context,
    )
    cache.set(question, result)
    return result


def stream_answer(question: str, **kwargs) -> Iterator[str]:
    """Reponse en streaming."""
    context, _, _, _ = _build_context(question)
    prompt = build_rag_prompt(question, context)
    yield from get_llm().stream(prompt, system=SYSTEM_PROMPT)
