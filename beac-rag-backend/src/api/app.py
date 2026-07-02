"""API FastAPI du chatbot BEAC RAG."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, or_

from src.api.models import HealthResponse, QueryRequest, QueryResponse, SourceItem
from src.config import CONFIG, settings
from src.database.connection import session_scope
from src.database.schema import Chunk, Document, Statistic
from src.rag.engine import answer_question, stream_answer, _build_context
from src.rag.llm_client import get_llm
from src.rag.prompts import SYSTEM_PROMPT, build_rag_prompt
from src.utils.logger import logger
from src.rag.cache import get_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mapping type frontend -> mots-cles dans la colonne category de la BD
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "Rapports":       ["rapport", "annual", "annuel"],
    "Bulletins":      ["bulletin", "statistique", "stat"],
    "Working Papers": ["working", "etude", "research"],
    "Communiques":    ["communique", "presse", "note"],
    "Reglementation": ["reglement", "directive", "loi", "convention", "statut"],
}
# Mapping avec accents pour la correspondance frontend
_TYPE_ALIAS: dict[str, str] = {
    "Communiques":    "Communiques",
    "Reglementation": "Reglementation",
}


def _map_type(doc: Document) -> str:
    cat = (doc.category or "").lower()
    if any(k in cat for k in ["rapport", "annual", "annuel"]):
        return "Rapports"
    if any(k in cat for k in ["bulletin", "statistique", "stat"]):
        return "Bulletins"
    if any(k in cat for k in ["working", "etude", "research"]):
        return "Working Papers"
    if any(k in cat for k in ["communique", "presse", "note"]):
        return "Communiques"
    if any(k in cat for k in ["reglement", "directive", "loi", "convention", "statut"]):
        return "Reglementation"
    return "Rapports"


def _map_section(doc: Document) -> str:
    cat = (doc.category or "").lower()
    sub = (doc.subcategory or "").lower()
    combined = cat + " " + sub
    if any(k in combined for k in ["monetaire", "politique", "taux", "reserve"]):
        return "Politique Monetaire"
    if any(k in combined for k in ["statistique", "stat", "donnees", "bulletin"]):
        return "Etudes Statistiques"
    return "Stabilite Financiere"


@app.get("/documents")
def get_documents(
    limit: int = 5000,
    offset: int = 0,
    doc_type: str | None = None,
    year: int | None = None,
    search: str | None = None,
) -> dict:
    """Liste paginee des documents pour la bibliotheque frontend."""
    with session_scope() as session:
        q = session.query(Document)

        # Filtre par type (mapping frontend -> mots-cles BD)
        if doc_type and doc_type in _TYPE_KEYWORDS:
            kws = _TYPE_KEYWORDS[doc_type]
            q = q.filter(or_(*[Document.category.ilike(f"%{kw}%") for kw in kws]))

        if year:
            q = q.filter(Document.year == year)

        # Recherche textuelle sur filename, category et subcategory
        if search:
            q = q.filter(
                or_(
                    Document.filename.ilike(f"%{search}%"),
                    Document.category.ilike(f"%{search}%"),
                    Document.subcategory.ilike(f"%{search}%"),
                )
            )

        total = q.count()
        docs = q.order_by(
            Document.year.desc().nullslast(),
            Document.id.desc()
        ).offset(offset).limit(limit).all()

    result = []
    for doc in docs:
        size = ""
        if doc.char_count:
            kb = doc.char_count / 1000
            size = f"{kb:.0f} KB" if kb < 1000 else f"{kb/1000:.1f} MB"
        title = doc.filename or (doc.source_path.split("/")[-1] if doc.source_path else "Document")
        title = title.rsplit(".", 1)[0].replace("_", " ")
        result.append({
            "id": str(doc.id),
            "title": title,
            "type": _map_type(doc),
            "fileType": (doc.file_type or "pdf").upper(),
            "fileSize": size or "-",
            "date": str(doc.year) if doc.year else "-",
            "description": (doc.category or "Document BEAC") + (f" - {doc.subcategory}" if doc.subcategory else ""),
            "section": _map_section(doc),
            "url": f"/api/files/{doc.source_path}" if doc.file_type in ("pdf", "PDF") else "#",
            "source_path": doc.source_path,
            "country": doc.country,
        })
    return {"total": total, "documents": result}


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
            prompt = build_rag_prompt(req.question, context)
            for token in get_llm().stream(prompt, system=SYSTEM_PROMPT):
                yield token
        except Exception as exc:
            logger.exception("Erreur streaming")
            yield f"\n[Erreur: {exc}]"

    return StreamingResponse(token_generator(), media_type="text/plain; charset=utf-8")


@app.post("/cache/clear")
def clear_cache():
    get_cache().invalidate()
    return {"status": "cache vide"}


@app.get("/metadata")
def metadata() -> dict:
    with session_scope() as session:
        categories = [r[0] for r in session.query(Document.category).distinct() if r[0]]
        countries = [r[0] for r in session.query(Document.country).distinct() if r[0]]
        years = sorted([r[0] for r in session.query(Document.year).distinct() if r[0]])
    return {"categories": sorted(categories), "countries": sorted(countries), "years": years}


# --- Endpoint fichiers PDF source ---
_RAW_DATA_DIR = settings.raw_data_path


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
    if not _IMAGE_DIR:
        raise HTTPException(status_code=404, detail="Image serving disabled")
    img_path = _IMAGE_DIR / doc_name / filename
    try:
        img_path.resolve().relative_to(_IMAGE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path")
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(img_path)
