"""Schemas Pydantic de l'API (contrat avec le frontend)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Question de l'utilisateur")
    provider: str = Field(default="ollama", description="ollama | openrouter")
    model_key: str = Field(default="gemma-4-26b", description="Cle du modele OpenRouter")


class SourceItem(BaseModel):
    source: str
    category: str | None = None
    year: int | None = None
    score: float | None = None
    source_url: str | None = None
    image_paths: list[str] | None = None


class QueryResponse(BaseModel):
    answer: str
    query_type: str
    sources: list[SourceItem] = []
    sql: str | None = None
    provider: str | None = None
    model_key: str | None = None


class HealthResponse(BaseModel):
    status: str
    documents: int
    chunks: int
    statistics: int
    llm_model: str
    embedding_model: str
