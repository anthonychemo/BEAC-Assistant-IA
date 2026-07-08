"""Routeur de requetes : determine si une question vise des donnees chiffrees
(table SQL `statistics`), du texte narratif (recherche vectorielle), ou les deux.

Approche legere par mots-cles (rapide, deterministe, pas d'appel LLM) avec
extraction de filtres (pays, annee) pour cibler le retrieval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from src.config import CONFIG
from src.utils.metadata import detect_country, detect_year

_DATA_KEYWORDS: list[str] = [k.lower() for k in CONFIG.get("router", {}).get("data_keywords", [])]


class QueryType(str, Enum):
    SQL = "sql"          # question purement chiffree
    VECTOR = "vector"    # question narrative
    HYBRID = "hybrid"    # un peu des deux
    META = "meta"          # nouveau : questions sur le système lui-même
    


# Phrases déclenchant une réponse méta (pas de recherche RAG)
_META_PATTERNS: list[str] = [
    "que sais-tu faire", "que peux-tu faire", "qui es-tu", "qui êtes-vous",
    "que sais tu faire", "c'est quoi ton rôle", "à quoi sers-tu",
    "comment tu marches", "comment fonctionnes-tu", "tes capacités",
    "que peux tu faire", "aide-moi", "comment t'utiliser",
    "quelles questions", "que peux-tu m'aider",
]


_EXPLORATORY_PATTERNS: list[str] = [
    "parle-moi de", "parle moi de", "que peux-tu me dire sur",
    "que peux tu me dire sur", "qu'est-ce que", "qu'est ce que",
    "explique-moi", "explique moi", "présente-moi", "présente moi",
    "dis-moi tout sur", "résume", "vue d'ensemble", "qui est",
]

_PERSON_KEYWORDS: list[str] = [
    "qui est", "qui sont", "gouverneur", "directeur", "président",
    "responsable", "chef", "nommé", "nomination", "poste",
]


@dataclass
class RoutedQuery:
    query_type: QueryType
    country: str | None = None
    year: int | None = None
    filters: dict = field(default_factory=dict)
    exploratory: bool = False 


def _is_meta_query(question: str) -> bool:
    low = question.lower().strip()
    return any(p in low for p in _META_PATTERNS)


def _is_exploratory_query(question: str) -> bool:
    low = question.lower().strip()
    return any(p in low for p in _EXPLORATORY_PATTERNS)


def _is_person_query(question: str) -> bool:
    low = question.lower().strip()
    return any(p in low for p in _PERSON_KEYWORDS)


def classify_query(question: str) -> RoutedQuery:
    if _is_meta_query(question):
        return RoutedQuery(query_type=QueryType.META)

    low = question.lower()
    has_data_kw = any(kw in low for kw in _DATA_KEYWORDS)
    is_exploratory = _is_exploratory_query(question)
    country = detect_country(question)
    year = detect_year(question)

    if has_data_kw and (country or year):
        qtype = QueryType.HYBRID
    elif has_data_kw:
        qtype = QueryType.SQL
    else:
        qtype = QueryType.VECTOR

    filters: dict = {}
    if country:
        filters["country"] = country
    is_person = _is_person_query(question)
    if year and not is_person and qtype in (QueryType.SQL, QueryType.HYBRID):
        filters["year"] = year

    return RoutedQuery(
        query_type=qtype,
        country=country,
        year=year,
        filters=filters,
        exploratory=is_exploratory,
    )