"""API FastAPI du chatbot BEAC RAG.

Endpoints :
- GET  /health          : etat du systeme + comptes
- POST /query           : question -> reponse complete (JSON)
- POST /query/stream    : question -> reponse en streaming (text/event-stream)
- GET  /metadata        : categories / pays / annees disponibles (pour filtres UI)
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func

from src.api.models import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceItem,
)
from src.config import CONFIG, settings
from src.database.connection import session_scope
from src.database.schema import Chunk, Document, Statistic
from src.rag.engine import answer_question, stream_answer
from src.rag.llm_client import get_llm
from src.utils.logger import logger
from src.rag.cache import get_cache


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

# CORS ouvert pour le dev frontend (a restreindre en production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/cache/clear")
def clear_cache():
    get_cache().invalidate()
    return {"status": "cache vidé"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    with session_scope() as session:
        n_docs = session.query(func.count(Document.id)).scalar() or 0
        n_chunks = session.query(func.count(Chunk.id)).scalar() or 0
        n_stats = session.query(func.count(Statistic.id)).scalar() or 0
    return HealthResponse(
        status="ok",
        documents=n_docs,
        chunks=n_chunks,
        statistics=n_stats,
        llm_model=CONFIG.get("llm", {}).get("model", settings.llm_model),
        embedding_model=CONFIG.get("embeddings", {}).get("model", settings.embedding_model),
    )


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    try:
        result = answer_question(req.question)
    except Exception as exc:
        logger.exception("Erreur lors du traitement de la question")
        raise HTTPException(status_code=500, detail=str(exc))
    return QueryResponse(
        answer=result.answer,
        query_type=result.query_type,
        sources=[SourceItem(**s) for s in result.sources],
        sql=result.sql,
    )


# src/api/app.py — améliorer query_stream
@app.post("/query/stream")
def query_stream(req: QueryRequest) -> StreamingResponse:
    def token_generator():
        try:
            # 1. Envoyer d'abord les métadonnées en JSON (avant les tokens)
            context, vector_items, sql_used, qtype = _build_context(req.question)
            meta = {
                "type": "meta",
                "query_type": qtype,
                "sources": [
                    {"source": i.source, "year": i.year, "score": round(i.score, 3)}
                    for i in vector_items
                ],
                "sql": sql_used,
            }
            yield json.dumps(meta, ensure_ascii=False) + "\n"

            # 2. Streamer les tokens ensuite
            prompt = build_rag_prompt(req.question, context)
            for token in get_llm().stream(prompt, system=SYSTEM_PROMPT):
                yield token

        except Exception as exc:
            logger.exception("Erreur streaming")
            yield f"\n[Erreur: {exc}]"

    return StreamingResponse(token_generator(), media_type="text/plain; charset=utf-8")

@app.get("/metadata")
def metadata() -> dict:
    """Valeurs distinctes pour alimenter les filtres de l'interface."""
    with session_scope() as session:
        categories = [r[0] for r in session.query(Document.category).distinct() if r[0]]
        countries = [r[0] for r in session.query(Document.country).distinct() if r[0]]
        years = sorted([r[0] for r in session.query(Document.year).distinct() if r[0]])
    return {"categories": sorted(categories), "countries": sorted(countries), "years": years}


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
