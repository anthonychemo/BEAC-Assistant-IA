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


@dataclass
class RoutedQuery:
    query_type: QueryType
    country: str | None = None
    year: int | None = None
    filters: dict = field(default_factory=dict)


def classify_query(question: str) -> RoutedQuery:
    low = question.lower()
    has_data_kw = any(kw in low for kw in _DATA_KEYWORDS)

    country = detect_country(question)
    year = detect_year(question)

    # Heuristique de classification
    if has_data_kw and (country or year):
        qtype = QueryType.HYBRID
    elif has_data_kw:
        qtype = QueryType.SQL
    else:
        qtype = QueryType.VECTOR

    filters: dict = {}
    if country:
        filters["country"] = country
    if year:
        filters["year"] = year

    return RoutedQuery(query_type=qtype, country=country, year=year, filters=filters)
