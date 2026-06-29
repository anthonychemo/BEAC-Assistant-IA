"""Operations vectorielles sur pgvector (insertion + recherche de similarite)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import text

from src.config import CONFIG
from src.database.connection import engine, session_scope
from src.database.schema import Base, Chunk

_VS = CONFIG.get("vector_store", {})
_DISTANCE = _VS.get("distance", "cosine")
# Operateur pgvector selon la distance choisie
_OPS = {"cosine": "<=>", "l2": "<->", "ip": "<#>"}
_DISTANCE_OP = _OPS.get(_DISTANCE, "<=>")
_HNSW_OPCLASS = {
    "cosine": "vector_cosine_ops",
    "l2": "vector_l2_ops",
    "ip": "vector_ip_ops",
}.get(_DISTANCE, "vector_cosine_ops")


@dataclass
class RetrievedChunk:
    chunk_id: int
    document_id: int
    content: str
    score: float
    metadata: dict[str, Any]


def create_schema() -> None:
    """Cree les extensions, tables et l'index HNSW."""
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    Base.metadata.create_all(engine)
    _create_vector_index()


def _create_vector_index() -> None:
    index_type = _VS.get("index_type", "hnsw")
    m = int(_VS.get("hnsw_m", 16))
    ef = int(_VS.get("hnsw_ef_construction", 64))
    with engine.begin() as conn:
        if index_type == "hnsw":
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS ix_chunks_embedding_hnsw "
                    f"ON chunks USING hnsw (embedding {_HNSW_OPCLASS}) "
                    f"WITH (m = {m}, ef_construction = {ef})"
                )
            )
        else:
            conn.execute(
                text(
                    f"CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivf "
                    f"ON chunks USING ivfflat (embedding {_HNSW_OPCLASS}) "
                    f"WITH (lists = 100)"
                )
            )


def build_chunk_objects(
    document_id: int,
    contents: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    token_counts: Sequence[int] | None = None,
    metadatas: Sequence[dict] | None = None,
) -> list[Chunk]:
    """Construit (sans insertion) les objets Chunk pour un document."""
    token_counts = token_counts or [None] * len(contents)
    metadatas = metadatas or [None] * len(contents)
    return [
        Chunk(
            document_id=document_id,
            chunk_index=i,
            content=content,
            token_count=token_counts[i],
            embedding=list(embeddings[i]),
            chunk_metadata=metadatas[i],
        )
        for i, content in enumerate(contents)
    ]


def insert_chunks(
    document_id: int,
    contents: Sequence[str],
    embeddings: Sequence[Sequence[float]],
    token_counts: Sequence[int] | None = None,
    metadatas: Sequence[dict] | None = None,
) -> int:
    """Insere un lot de chunks pour un document (transaction dediee)."""
    with session_scope() as session:
        session.execute(text("SET hnsw.ef_search = 40"))   # défaut=40, peut descendre à 20
        for row in session.execute(sql, params):
            objs = build_chunk_objects(
                document_id, contents, embeddings, token_counts, metadatas
            )
            session.add_all(objs)
    return len(objs)


def similarity_search(
    query_embedding: Sequence[float],
    top_k: int = 6,
    filters: dict[str, Any] | None = None,
    min_similarity: float | None = None,
) -> list[RetrievedChunk]:
    """Recherche les chunks les plus proches.

    `filters` filtre sur les metadonnees du document jointes (category, country, year).
    """
    embedding_literal = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"

    where_clauses: list[str] = []
    params: dict[str, Any] = {"top_k": top_k}
    if filters:
        for key in ("category", "country", "year"):
            if filters.get(key) is not None:
                where_clauses.append(f"d.{key} = :{key}")
                params[key] = filters[key]
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # score = 1 - distance cosine (plus grand = plus pertinent)
    sql = text(
        f"""
        SELECT c.id, c.document_id, c.content, c.chunk_metadata,
               1 - (c.embedding {_DISTANCE_OP} '{embedding_literal}') AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        {where_sql}
        ORDER BY c.embedding {_DISTANCE_OP} '{embedding_literal}'
        LIMIT :top_k
        """
    )

    results: list[RetrievedChunk] = []
    with session_scope() as session:
        for row in session.execute(sql, params):
            score = float(row.score)
            if min_similarity is not None and score < min_similarity:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=row.id,
                    document_id=row.document_id,
                    content=row.content,
                    score=score,
                    metadata=row.chunk_metadata or {},
                )
            )
    return results
