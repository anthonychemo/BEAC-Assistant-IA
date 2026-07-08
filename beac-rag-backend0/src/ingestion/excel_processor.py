"""Parsing des fichiers Excel BEAC.

Produit deux sorties par fichier :
1. `text_blocks` : representation textuelle (markdown) de chaque feuille,
   destinee au RAG vectoriel (questions narratives sur les donnees).
2. `statistics`  : lignes normalisees (indicateur, periode, valeur) destinees
   a la table SQL `statistics` pour les requetes chiffrees precises.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.logger import logger
from src.utils.metadata import detect_country, detect_year


@dataclass
class StatRow:
    indicator: str
    period: str | None
    year: int | None
    value: float | None
    country: str | None = None
    unit: str | None = None
    raw_label: str | None = None
    source_sheet: str | None = None


@dataclass
class ExcelParseResult:
    text_blocks: list[str] = field(default_factory=list)
    statistics: list[StatRow] = field(default_factory=list)
    sheet_count: int = 0


def _read_excel(path: Path) -> dict[str, pd.DataFrame]:
    """Lit toutes les feuilles. .xls -> xlrd, .xlsx -> openpyxl."""
    engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    try:
        return pd.read_excel(path, sheet_name=None, header=None, engine=engine)
    except Exception as exc:
        logger.error(f"Lecture Excel echouee {path.name}: {exc}")
        return {}


def _df_to_markdown(df: pd.DataFrame, sheet_name: str, max_rows: int = 40) -> str:
    """Convertit une feuille en markdown lisible (tronque si trop grande)."""
    clean = df.dropna(how="all").dropna(axis=1, how="all")
    if clean.empty:
        return ""
    truncated = clean.head(max_rows)
    lines = [f"### Feuille : {sheet_name}"]
    for _, row in truncated.iterrows():
        cells = [str(c).replace("\x00", " ").replace("\x07", " ") for c in row.tolist() if pd.notna(c)]
        if cells:
            lines.append(" | ".join(cells))
    if len(clean) > max_rows:
        lines.append(f"... ({len(clean) - max_rows} lignes supplementaires)")
    return "\n".join(lines)


def _looks_like_period(label: str) -> bool:
    """Detecte si une etiquette de colonne ressemble a une periode (annee/mois)."""
    label = str(label).strip()
    if detect_year(label):
        return True
    months = ["janv", "fevr", "mars", "avril", "mai", "juin", "juil",
              "aout", "sept", "oct", "nov", "dec", "trim", "t1", "t2", "t3", "t4"]
    low = label.lower()
    return any(m in low for m in months)


def _extract_statistics(
    df: pd.DataFrame, sheet_name: str, file_country: str | None
) -> list[StatRow]:
    """Extraction best-effort de series chiffrees au format long.

    Heuristique : la 1ere colonne = libelle d'indicateur, les colonnes suivantes
    dont l'entete ressemble a une periode = valeurs temporelles.
    """
    clean = df.dropna(how="all").dropna(axis=1, how="all").reset_index(drop=True)
    if clean.shape[0] < 2 or clean.shape[1] < 2:
        return []

    # On cherche la ligne d'entete : celle qui contient le plus de "periodes"
    header_idx = None
    for i in range(min(8, len(clean))):
        row_vals = clean.iloc[i].tolist()
        period_count = sum(1 for v in row_vals if pd.notna(v) and _looks_like_period(v))
        if period_count >= 2:
            header_idx = i
            break
    if header_idx is None:
        return []

    header = clean.iloc[header_idx].tolist()
    period_cols = {
        j: str(header[j]).strip()
        for j in range(1, len(header))
        if pd.notna(header[j]) and _looks_like_period(header[j])
    }
    if not period_cols:
        return []

    rows: list[StatRow] = []
    for i in range(header_idx + 1, len(clean)):
        label = clean.iloc[i, 0]
        if pd.isna(label):
            continue
        indicator = str(label).strip()
        if not indicator or len(indicator) > 200:
            continue
        row_country = detect_country(indicator) or file_country
        for j, period in period_cols.items():
            if j >= clean.shape[1]:
                continue
            raw_val = clean.iloc[i, j]
            value = _to_float(raw_val)
            if value is None:
                continue
            rows.append(
                StatRow(
                    indicator=indicator,
                    period=period,
                    year=detect_year(period),
                    value=value,
                    country=row_country,
                    raw_label=f"{indicator} | {period}",
                    source_sheet=sheet_name,
                )
            )
    return rows


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(" ", "").replace("\u00a0", "")
    s = s.replace(",", ".")
    # gere les parentheses pour negatifs et les %
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()%")
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return None


def parse_excel(path: str | Path) -> ExcelParseResult:
    path = Path(path)
    sheets = _read_excel(path)
    if not sheets:
        return ExcelParseResult()

    file_country = detect_country(path.stem)
    result = ExcelParseResult(sheet_count=len(sheets))
    for sheet_name, df in sheets.items():
        md = _df_to_markdown(df, sheet_name)
        if md:
            result.text_blocks.append(md)
        result.statistics.extend(_extract_statistics(df, sheet_name, file_country))
    return result
