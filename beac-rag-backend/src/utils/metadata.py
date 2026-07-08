"""Detection de metadonnees (pays, annee) a partir du texte."""
from __future__ import annotations

import re

from unidecode import unidecode

# Pays de la zone CEMAC + variantes
_COUNTRY_PATTERNS: dict[str, list[str]] = {
    "Cameroun": ["cameroun", "cameroon"],
    "Congo": ["congo"],
    "Gabon": ["gabon"],
    "Tchad": ["tchad", "chad"],
    "Centrafrique": ["centrafrique", "rca", "centrafricaine", "central african"],
    "Guinee Equatoriale": ["guinee equatoriale", "guinea ecuatorial", "equatorial guinea"],
}

# Annee plausible (BEAC : ~1990 a 2030)
_YEAR_RE = re.compile(r"\b(19[9]\d|20[0-3]\d)\b")


def _norm(text: str) -> str:
    return unidecode(text).lower()


def detect_country(text: str) -> str | None:
    """Detecte un pays CEMAC dans une chaine."""
    norm = _norm(text)
    for country, patterns in _COUNTRY_PATTERNS.items():
        if any(p in norm for p in patterns):
            return country
    return None


def detect_year(text: str) -> int | None:
    """Retourne la derniere annee plausible trouvee (souvent la plus pertinente)."""
    matches = _YEAR_RE.findall(text)
    if not matches:
        return None
    return int(matches[-1])