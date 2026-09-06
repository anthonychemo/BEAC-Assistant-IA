"""Moteur RAG hybride : orchestre routage, retrieval (vectoriel + SQL) et generation."""
from __future__ import annotations

from dataclasses import dataclass, field

from src.rag.cache import get_cache
from src.rag.llm_client import get_llm, resolve_model
from src.rag.prompts import META_RESPONSE, SYSTEM_PROMPT, build_rag_prompt
from src.rag.query_router import QueryType, classify_query
from src.rag.retriever import ContextItem, format_context, retrieve_context
from src.rag.sql_generator import format_sql_context, run_statistics_query
from src.utils.logger import logger


@dataclass
class RAGResponse:
    answer: str
    query_type: str
    sources: list[dict] = field(default_factory=list)
    sql: str | None = None
    context_used: str = ""


def build_context(
    question: str, document_id: int | None = None
) -> tuple[str, list[ContextItem], str | None, str]:
    """Route la question et assemble le contexte (recherche vectorielle et/ou SQL).

    `document_id` : quand fourni (ex: bouton "Analyser IA" sur un document precis
    de la bibliotheque), on court-circuite le routage SQL/exploratoire habituel —
    le document est deja identifie avec certitude, la recherche se limite a ses
    propres chunks plutot qu'a l'ensemble du corpus.
    """
    if document_id is not None:
        logger.info(f"Question ciblee sur le document #{document_id} (recherche restreinte)")
        vector_items = retrieve_context(question, top_k=10, filters={"document_id": document_id})
        context = format_context(vector_items)
        return context, vector_items, None, QueryType.VECTOR.value

    routed = classify_query(question)
    logger.info(f"Question routée : {routed.query_type} | exploratoire={routed.exploratory} | filtres={routed.filters}")

    context_parts: list[str] = []
    vector_items: list[ContextItem] = []
    sql_used: str | None = None

    if routed.query_type in (QueryType.SQL, QueryType.HYBRID):
        sql_result = run_statistics_query(question)
        sql_used = sql_result.sql
        context_parts.append(format_sql_context(sql_result))

    if routed.query_type in (QueryType.VECTOR, QueryType.HYBRID):
        # Plus de contexte pour les questions larges
        top_k = 12 if routed.exploratory else None
        vector_items = retrieve_context(question, top_k=top_k, filters=routed.filters)
        context_parts.append(format_context(vector_items))

    context = "\n\n".join(p for p in context_parts if p)
    return context, vector_items, sql_used, routed.query_type.value


def sources_from_items(items: list[ContextItem]) -> list[dict]:
    seen = set()
    sources = []
    for item in items:
        # Dédupliquer sur le nom de fichier seul, pas sur (source, year)
        key = item.source
        if key in seen:
            continue
        seen.add(key)
        sources.append({
            "source": item.source,
            "category": item.category,
            "year": item.year,
            "score": round(item.score, 3),
            "source_url": item.source_url or "https://www.beac.int",
            "url": f"/api/documents/{item.document_id}/view" if item.document_id else None,
            "image_paths": item.image_paths,
        })
    return sources


def answer_question(
    question: str, model_key: str | None = None, document_id: int | None = None
) -> RAGResponse:
    """Reponse complete (non-streaming) : meta -> reponse canned, sinon cache puis RAG."""
    # Une question ciblee sur un document precis n'est jamais une question meta
    # sur l'assistant lui-meme, quels que soient les mots employes ("explique-moi").
    exploratory = False
    if document_id is None:
        routed = classify_query(question)
        if routed.query_type == QueryType.META:
            return RAGResponse(
                answer=META_RESPONSE,
                query_type=QueryType.META.value,
                sources=[],
                sql=None,
                context_used="",
            )
        exploratory = routed.exploratory

    cache = get_cache()
    cached = cache.get(question, model_key)
    if cached is not None:
        logger.info("Réponse servie depuis le cache")
        return cached

    context, vector_items, sql_used, qtype = build_context(question, document_id=document_id)
    prompt = build_rag_prompt(question, context, exploratory=exploratory)
    use_fast = qtype == QueryType.SQL.value
    model = resolve_model(model_key)
    answer = get_llm().generate(prompt, system=SYSTEM_PROMPT, fast=use_fast, model=model)

    result = RAGResponse(
        answer=answer,
        query_type=qtype,
        sources=sources_from_items(vector_items),
        sql=sql_used,
        context_used=context,
    )
    cache.set(question, result, model_key)
    return result
