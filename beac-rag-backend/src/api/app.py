"""API FastAPI du chatbot BEAC RAG.

Endpoints :
- GET  /health                    : etat du systeme + comptes
- POST /query                     : question -> reponse complete (JSON)
- POST /query/stream              : question -> reponse en streaming (texte brut,
                                     1re ligne = JSON meta, puis tokens concatenes)
- GET  /documents                 : liste paginee/recherchable des documents indexes
- GET  /metadata                  : categories / pays / annees / modeles disponibles
- POST /cache/clear               : vide le cache reponses (proteg par X-Admin-Token)
- GET  /images/{doc}/{filename}   : sert une image extraite d'un PDF
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, or_

from src.api.models import (
    FeedbackRequest,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceItem,
)
from src.config import CONFIG, settings
from src.database.connection import session_scope
from src.database.schema import Chunk, Document, Feedback, Statistic
from src.database.vector_store import similarity_search
from src.indexing.embeddings import get_embedder
from src.rag.cache import get_cache
from src.rag.engine import answer_question, build_context, sources_from_items
from src.rag.llm_client import MODEL_CHOICES, get_llm, resolve_model
from src.rag.prompts import META_RESPONSE, SYSTEM_PROMPT, build_rag_prompt
from src.rag.query_router import QueryType, classify_query
from src.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Prechauffe le LLM au demarrage de l'API (latence reduite en demo)
    logger.info("Demarrage de l'API BEAC RAG, prechauffage du LLM...")
    try:
        get_llm().warmup()
    except Exception as exc:
        logger.warning(f"Warmup LLM ignore : {exc}")
    yield
    logger.info("Arret de l'API BEAC RAG.")


app = FastAPI(
    title="BEAC RAG API",
    description="API du chatbot RAG sur les donnees de la BEAC",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS restreint aux origines listees dans CORS_ALLOW_ORIGINS (.env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    """Protege les routes d'administration via un jeton partage (header X-Admin-Token)."""
    if not settings.admin_api_token:
        raise HTTPException(status_code=503, detail="Route d'administration desactivee (ADMIN_API_TOKEN non configure)")
    if x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="Jeton d'administration invalide")


@app.post("/cache/clear", dependencies=[Depends(_require_admin)])
def clear_cache():
    get_cache().invalidate()
    return {"status": "cache vidé"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    with session_scope() as session:
        n_docs = session.query(func.count(Document.id)).scalar() or 0
        n_chunks = session.query(func.count(Chunk.id)).scalar() or 0
        n_stats = session.query(func.count(Statistic.id)).scalar() or 0
        n_positive = session.query(func.count(Feedback.id)).filter(Feedback.is_positive.is_(True)).scalar() or 0
        n_negative = session.query(func.count(Feedback.id)).filter(Feedback.is_positive.is_(False)).scalar() or 0
    n_feedback_total = n_positive + n_negative
    satisfaction = (n_positive / n_feedback_total * 100) if n_feedback_total > 0 else None
    return HealthResponse(
        status="ok",
        documents=n_docs,
        chunks=n_chunks,
        statistics=n_stats,
        llm_model=CONFIG.get("llm", {}).get("model", settings.llm_model),
        embedding_model=CONFIG.get("embeddings", {}).get("model", settings.embedding_model),
        feedback_positive=n_positive,
        feedback_negative=n_negative,
        feedback_satisfaction=round(satisfaction, 1) if satisfaction is not None else None,
    )


@app.post("/feedback", status_code=201)
def submit_feedback(req: FeedbackRequest) -> dict:
    """Enregistre un retour utilisateur (pouce haut/bas) sur une reponse du chat."""
    with session_scope() as session:
        session.add(Feedback(
            question=req.question,
            is_positive=req.is_positive,
            query_type=req.query_type,
            model_key=req.model_key,
        ))
    return {"status": "ok"}


# Messages affiches a l'utilisateur en cas d'echec du LLM (ex: quota OpenRouter
# epuise) : jamais de details techniques (code HTTP, fournisseur, user_id...),
# qui n'ont aucun sens pour un utilisateur final et sont deja journalises via
# logger.exception ci-dessous pour le diagnostic.
_FRIENDLY_ERROR = (
    "Le service est momentanément surchargé en raison d'une forte affluence. "
    "Merci de réessayer votre question dans quelques instants."
)
_FRIENDLY_ERROR_MIDSTREAM = (
    "\n\nDésolé, la réponse a été interrompue en raison d'une forte affluence "
    "sur le service. Merci de réessayer votre question."
)


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    try:
        result = answer_question(req.question, model_key=req.model_key, document_id=req.document_id)
    except Exception:
        logger.exception("Erreur lors du traitement de la question")
        raise HTTPException(status_code=500, detail=_FRIENDLY_ERROR)
    return QueryResponse(
        answer=result.answer,
        query_type=result.query_type,
        sources=[SourceItem(**s) for s in result.sources],
        sql=result.sql,
    )


@app.post("/query/stream")
def query_stream(req: QueryRequest) -> StreamingResponse:
    def token_generator():
        meta_sent = False
        token_sent = False
        try:
            # Une question ciblee sur un document precis (bouton "Analyser IA")
            # n'est jamais une question meta, quels que soient les mots employes.
            exploratory = False
            if req.document_id is None:
                routed = classify_query(req.question)
                if routed.query_type == QueryType.META:
                    meta = {"type": "meta", "query_type": QueryType.META.value, "sources": [], "sql": None}
                    yield json.dumps(meta, ensure_ascii=False) + "\n"
                    yield META_RESPONSE
                    return
                exploratory = routed.exploratory

            # 1. Envoyer d'abord les métadonnées en JSON (avant les tokens)
            context, vector_items, sql_used, qtype = build_context(req.question, document_id=req.document_id)
            meta = {
                "type": "meta",
                "query_type": qtype,
                # Dedupliquee par nom de fichier (un meme document contribue souvent
                # plusieurs chunks) : sans ca, une seule source apparaissait
                # plusieurs fois dans la liste affichee au lieu d'une seule fois.
                "sources": sources_from_items(vector_items),
                "sql": sql_used,
            }
            yield json.dumps(meta, ensure_ascii=False) + "\n"
            meta_sent = True

            # 2. Streamer les tokens ensuite
            prompt = build_rag_prompt(req.question, context, exploratory=exploratory)
            model = resolve_model(req.model_key)
            for token in get_llm().stream(prompt, system=SYSTEM_PROMPT, model=model):
                token_sent = True
                yield token

        except Exception:
            logger.exception("Erreur streaming")
            if not meta_sent:
                # Rien n'a encore ete envoye : on peut renvoyer un meta "erreur"
                # explicite, que le frontend peut styliser differemment.
                error_meta = {
                    "type": "meta", "query_type": "error", "sources": [], "sql": None, "error": True,
                }
                yield json.dumps(error_meta, ensure_ascii=False) + "\n"
                yield _FRIENDLY_ERROR
            elif not token_sent:
                yield _FRIENDLY_ERROR
            else:
                yield _FRIENDLY_ERROR_MIDSTREAM

    return StreamingResponse(token_generator(), media_type="text/plain; charset=utf-8")

@app.get("/metadata")
def metadata() -> dict:
    """Valeurs distinctes pour alimenter les filtres de l'interface, et modeles LLM disponibles."""
    with session_scope() as session:
        categories = [r[0] for r in session.query(Document.category).distinct() if r[0]]
        countries = [r[0] for r in session.query(Document.country).distinct() if r[0]]
        years = sorted([r[0] for r in session.query(Document.year).distinct() if r[0]])
    return {
        "categories": sorted(categories),
        "countries": sorted(countries),
        "years": years,
        "models": [{"key": k, "label": v} for k, v in MODEL_CHOICES.items()],
    }


_SEMANTIC_FALLBACK_POOL = 200   # chunks candidats (indexes HNSW) avant agregation par document
_SEMANTIC_MIN_SIMILARITY = 0.35


def _semantic_document_fallback(
    session,
    search: str,
    doc_type: str | None,
    country: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Document], int]:
    """Repli quand la recherche textuelle (ILIKE) ne trouve aucun document.

    Cherche par sens plutot que par correspondance exacte : embedde la requete
    et reutilise l'index vectoriel HNSW deja en place pour le chat RAG, puis
    remonte les chunks les plus proches a leur document parent (meilleur score
    par document, les chunks etant deja tries par similarite decroissante).
    """
    filters: dict[str, Any] = {}
    if doc_type and doc_type != "Tous":
        filters["category"] = doc_type
    if country and country != "Tous":
        filters["country"] = country

    query_vec = get_embedder().embed_query(search)
    candidates = similarity_search(
        query_embedding=query_vec,
        top_k=_SEMANTIC_FALLBACK_POOL,
        filters=filters or None,
        min_similarity=_SEMANTIC_MIN_SIMILARITY,
    )

    ordered_doc_ids: list[int] = []
    seen: set[int] = set()
    for c in candidates:
        if c.document_id not in seen:
            seen.add(c.document_id)
            ordered_doc_ids.append(c.document_id)

    total = len(ordered_doc_ids)
    page_ids = ordered_doc_ids[offset : offset + limit]
    if not page_ids:
        return [], total

    docs_by_id = {d.id: d for d in session.query(Document).filter(Document.id.in_(page_ids)).all()}
    rows = [docs_by_id[i] for i in page_ids if i in docs_by_id]
    return rows, total


@app.get("/documents")
def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    doc_type: str | None = None,
    country: str | None = None,
    sort: str = Query("recent", pattern="^(recent|oldest)$"),
) -> dict:
    """Liste paginee/recherchable des documents indexes (bibliotheque du frontend)."""
    search_mode = "exact"
    with session_scope() as session:
        q = session.query(Document)
        if doc_type and doc_type != "Tous":
            q = q.filter(Document.category == doc_type)
        if country and country != "Tous":
            q = q.filter(Document.country == country)
        if search:
            like = f"%{search}%"
            conditions = [
                Document.filename.ilike(like),
                Document.subcategory.ilike(like),
                Document.category.ilike(like),
                Document.country.ilike(like),
            ]
            if search.strip().isdigit():
                conditions.append(Document.year == int(search.strip()))
            q = q.filter(or_(*conditions))
        total = q.count()

        if total == 0 and search and len(search.strip()) >= 3:
            search_mode = "semantic"
            rows, total = _semantic_document_fallback(session, search, doc_type, country, limit, offset)
        else:
            # Tri par date reelle du document (date_publication puis annee), les
            # documents sans date connue sont relegues en fin de liste quel que
            # soit le sens de tri ; created_at (date d'indexation) sert de dernier
            # departage.
            if sort == "oldest":
                q = q.order_by(
                    Document.date_publication.asc().nullslast(),
                    Document.year.asc().nullslast(),
                    Document.created_at.asc(),
                )
            else:
                q = q.order_by(
                    Document.date_publication.desc().nullslast(),
                    Document.year.desc().nullslast(),
                    Document.created_at.desc(),
                )
            rows = (
                q.offset(offset)
                .limit(limit)
                .all()
            )

        documents = [
            {
                "id": str(d.id),
                "title": d.filename,
                "type": d.category or "Non classe",
                "fileType": d.file_type.upper(),
                "date": d.date_publication,
                "description": d.subcategory,
                "country": d.country,
                "year": d.year,
                "url": d.source_url or "https://www.beac.int",
            }
            for d in rows
        ]
    return {"documents": documents, "total": total, "searchMode": search_mode}


# --- Endpoint images ---
_IMAGE_DIR_CFG = CONFIG.get("ingestion", {}).get("image_extract_dir")
if _IMAGE_DIR_CFG:
    _IMAGE_DIR = Path(_IMAGE_DIR_CFG)
    if not _IMAGE_DIR.is_absolute():
        _IMAGE_DIR = (Path(__file__).resolve().parents[2] / _IMAGE_DIR).resolve()
else:
    _IMAGE_DIR = None


@app.get("/images/{doc_name}/{filename}")
def get_image(doc_name: str, filename: str) -> FileResponse:
    """Sert une image extraite d'un PDF graphique."""
    if not _IMAGE_DIR:
        raise HTTPException(status_code=404, detail="Image serving disabled")
    img_path = _IMAGE_DIR / doc_name / filename
    # Securite : s'assurer que le fichier est bien dans le repertoire images
    try:
        img_path.resolve().relative_to(_IMAGE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(img_path)
