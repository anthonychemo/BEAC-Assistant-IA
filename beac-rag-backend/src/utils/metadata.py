"""Detection de metadonnees (pays, annee, categorie) a partir du chemin et du texte."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

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


def extract_metadata_from_path(file_path: Path, raw_root: Path) -> dict[str, Any]:
    """Deduit categorie/sous-categorie/pays/annee depuis l'arborescence du fichier.

    Structure attendue : <raw_root>/<categorie>/<sous-categorie>/.../fichier
    """
    try:
        rel = file_path.relative_to(raw_root)
    except ValueError:
        rel = Path(file_path.name)

    parts = rel.parts
    category = parts[0] if len(parts) > 1 else None
    subcategory = parts[1] if len(parts) > 2 else None

    # Recherche pays/annee dans le chemin complet + nom de fichier
    search_space = " ".join(parts)
    country = detect_country(search_space)
    year = detect_year(search_space)

    return {
        "category": category,
        "subcategory": subcategory,
        "country": country,
        "year": year,
        "relative_path": str(rel).replace("\\", "/"),
    }
