"""Generation et execution securisee de requetes SQL sur la table `statistics`.

Le LLM propose une requete SELECT ; on la valide (lecture seule, mono-instruction)
avant execution. Garde-fous stricts car la requete est generee par un modele.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from src.config import CONFIG
from src.database.connection import session_scope
from src.rag.llm_client import get_llm
from src.rag.prompts import SQL_SYSTEM_PROMPT, build_sql_prompt
from src.utils.logger import logger

_MAX_ROWS = int(CONFIG.get("retrieval", {}).get("sql_max_rows", 50))

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy)\b",
    re.IGNORECASE,
)


@dataclass
class SQLResult:
    sql: str
    rows: list[dict[str, Any]]
    error: str | None = None


def _extract_sql(raw: str) -> str:
    """Nettoie la sortie du LLM pour isoler la requete SQL."""
    # Retire les blocs markdown ```sql ... ```
    raw = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).replace("```", "")
    raw = raw.strip().rstrip(";").strip()
    # Ne garde que la 1ere instruction
    if ";" in raw:
        raw = raw.split(";")[0].strip()
    return raw


def _is_safe(sql: str) -> bool:
    if not sql.lower().lstrip().startswith("select"):
        return False
    if _FORBIDDEN.search(sql):
        return False
    return True


def _ensure_limit(sql: str) -> str:
    if re.search(r"\blimit\b", sql, re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {_MAX_ROWS}"


def generate_sql(question: str) -> str:
    prompt = build_sql_prompt(question, _MAX_ROWS)
    raw = get_llm().generate(prompt, system=SQL_SYSTEM_PROMPT)
    return _extract_sql(raw)


def run_statistics_query(question: str) -> SQLResult:
    """Genere une requete SQL depuis la question, la valide et l'execute."""
    sql = generate_sql(question)

    if not _is_safe(sql):
        logger.warning(f"Requete SQL rejetee (non sure) : {sql}")
        return SQLResult(sql=sql, rows=[], error="Requete non autorisee (lecture seule).")

    sql = _ensure_limit(sql)
    try:
        with session_scope() as session:
            result = session.execute(text(sql))
            rows = [dict(r._mapping) for r in result]
        return SQLResult(sql=sql, rows=rows)
    except Exception as exc:
        logger.error(f"Execution SQL echouee : {exc}")
        return SQLResult(sql=sql, rows=[], error=str(exc))


def format_sql_context(result: SQLResult) -> str:
    """Formate les lignes SQL en texte injectable dans le prompt RAG."""
    if result.error:
        return f"[Donnees chiffrees indisponibles : {result.error}]"
    if not result.rows:
        return "[Aucune donnee chiffree trouvee pour cette question.]"
    lines = ["Donnees chiffrees (table statistiques BEAC) :"]
    for row in result.rows:
        parts = [f"{k}={v}" for k, v in row.items() if v is not None]
        lines.append("- " + ", ".join(parts))
    return "\n".join(lines)
