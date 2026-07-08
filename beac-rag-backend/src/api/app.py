"""API FastAPI du chatbot BEAC RAG.

Endpoints :
- GET  /health          : etat du systeme + comptes
- POST /query           : question -> reponse complete (JSON)
- POST /query/stream    : question -> reponse en streaming (text/event-stream)
- GET  /metadata        : categories / pays / annees disponibles (pour filtres UI)
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, or_
from src.api.models import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
    SourceItem,
)
from src.config import CONFIG, settings
from src.database.connection import session_scope
from src.database.schema import Chunk, Document, Statistic
from src.rag.cache import get_cache
from src.rag.engine import answer_question, build_context
from src.rag.llm_client import get_llm
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


@app.post("/query/stream")
def query_stream(req: QueryRequest) -> StreamingResponse:
    def token_generator():
        try:
            routed = classify_query(req.question)
            if routed.query_type == QueryType.META:
                meta = {"type": "meta", "query_type": QueryType.META.value, "sources": [], "sql": None}
                yield json.dumps(meta, ensure_ascii=False) + "\n"
                yield META_RESPONSE
                return

            # 1. Envoyer d'abord les métadonnées en JSON (avant les tokens)
            context, vector_items, sql_used, qtype = build_context(req.question)
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
            prompt = build_rag_prompt(req.question, context, exploratory=routed.exploratory)
            for token in get_llm().stream(prompt, system=SYSTEM_PROMPT):
                yield token

        except Exception as exc:
            logger.exception("Erreur streaming")
            yield "\nJe suis desole, une erreur est survenue lors du traitement de votre question. Veuillez reessayer ou consulter le site officiel : https://www.beac.int"

    return StreamingResponse(token_generator(), media_type="text/plain; charset=utf-8")

@app.get("/metadata")
def metadata() -> dict:
    with session_scope() as session:
        categories = [r[0] for r in session.query(Document.category).distinct() if r[0]]
        countries = [r[0] for r in session.query(Document.country).distinct() if r[0]]
        years = sorted([r[0] for r in session.query(Document.year).distinct() if r[0]])
    return {"categories": sorted(categories), "countries": sorted(countries), "years": years}


_TYPE_KEYWORDS: dict[str, list[str]] = {
    "Rapports":       ["rapport", "annual", "annuel"],
    "Bulletins":      ["bulletin", "statistique", "stat"],
    "Working Papers": ["working", "etude", "research"],
    "Communiques":    ["communique", "presse", "note"],
    "Reglementation": ["reglement", "directive", "loi", "convention", "statut"],
}


def _map_type(doc: Document) -> str:
    cat = (doc.category or "").lower()
    if any(k in cat for k in ["rapport", "annual", "annuel"]): return "Rapports"
    if any(k in cat for k in ["bulletin", "statistique", "stat"]): return "Bulletins"
    if any(k in cat for k in ["working", "etude", "research"]): return "Working Papers"
    if any(k in cat for k in ["communique", "presse", "note"]): return "Communiques"
    if any(k in cat for k in ["reglement", "directive", "loi", "convention", "statut"]): return "Reglementation"
    return "Rapports"


def _map_section(doc: Document) -> str:
    combined = (doc.category or "").lower() + " " + (doc.subcategory or "").lower()
    if any(k in combined for k in ["monetaire", "politique", "taux", "reserve"]): return "Politique Monetaire"
    if any(k in combined for k in ["statistique", "stat", "donnees", "bulletin"]): return "Etudes Statistiques"
    return "Stabilite Financiere"


@app.get("/documents")
def get_documents(
    limit: int = 5000, offset: int = 0,
    doc_type: str | None = None, year: int | None = None, search: str | None = None,
) -> dict:
    with session_scope() as session:
        q = session.query(Document)
        if doc_type and doc_type in _TYPE_KEYWORDS:
            kws = _TYPE_KEYWORDS[doc_type]
            q = q.filter(or_(*[Document.category.ilike(f"%{kw}%") for kw in kws]))
        if year:
            q = q.filter(Document.year == year)
        if search:
            q = q.filter(or_(
                Document.filename.ilike(f"%{search}%"),
                Document.category.ilike(f"%{search}%"),
            ))
        total = q.count()
        docs = q.order_by(Document.year.desc().nullslast(), Document.id.desc()).offset(offset).limit(limit).all()

    result = []
    for doc in docs:
        size = ""
        if doc.char_count:
            kb = doc.char_count / 1000
            size = f"{kb:.0f} KB" if kb < 1000 else f"{kb/1000:.1f} MB"
        title = doc.filename or (doc.r2_key.split("/")[-1] if doc.r2_key else "Document")
        title = title.rsplit(".", 1)[0].replace("_", " ")
        # URL : soit source_url (beac.int), soit lien vers le fichier via R2
        url = doc.source_url or "#"
        result.append({
            "id": str(doc.id), "title": title, "type": _map_type(doc),
            "fileType": (doc.file_type or "pdf").upper(), "fileSize": size or "-",
            "date": doc.date_publication or (str(doc.year) if doc.year else "-"),
            "description": (doc.category or "Document BEAC") + (f" - {doc.subcategory}" if doc.subcategory else ""),
            "section": _map_section(doc),
            "url": url,
            "source_path": doc.r2_key, "country": doc.country,
        })
    return {"total": total, "documents": result}


_RAW_DATA_DIR_CFG = CONFIG.get("ingestion", {}).get("raw_data_dir", "")
_RAW_DATA_DIR = Path(_RAW_DATA_DIR_CFG) if _RAW_DATA_DIR_CFG else Path(__file__).resolve().parents[3] / "data_pipeline" / "Scrapping" / "scraping" / "beac_data"


@app.get("/files/{file_path:path}")
def serve_file(file_path: str) -> FileResponse:
    target = (_RAW_DATA_DIR / file_path).resolve()
    try:
        target.relative_to(_RAW_DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Chemin invalide")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return FileResponse(target, media_type="application/pdf")


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
