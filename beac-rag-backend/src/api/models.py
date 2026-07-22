"""Schemas Pydantic de l'API (contrat avec le frontend)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    # "model_key" commence par "model_", namespace reserve par Pydantic (model_config,
    # model_fields, ...) ; on desactive cette protection pour ce champ metier.
    model_config = ConfigDict(protected_namespaces=())

    question: str = Field(..., min_length=2, max_length=2000, description="Question de l'utilisateur")
    model_key: str | None = Field(
        None, description="Cle de modele optionnelle ('primary' ou 'fallback', voir GET /metadata)"
    )
    document_id: int | None = Field(
        None,
        description="Quand fourni (bouton 'Analyser IA' sur un document de la bibliotheque), "
        "restreint la recherche aux chunks de ce document precis au lieu de tout le corpus.",
    )


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


class HealthResponse(BaseModel):
    status: str
    documents: int
    chunks: int
    statistics: int
    llm_model: str
    embedding_model: str
    feedback_positive: int = 0
    feedback_negative: int = 0
    # None tant qu'aucun retour n'a ete soumis (evite d'afficher un faux 0%/100%)
    feedback_satisfaction: float | None = None


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    question: str = Field(..., min_length=1, max_length=2000)
    is_positive: bool
    query_type: str | None = None
    model_key: str | None = None
