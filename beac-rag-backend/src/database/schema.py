"""Modeles SQLAlchemy du pipeline BEAC RAG.

Trois tables principales :
- `documents`  : un enregistrement par fichier source (PDF/Excel).
- `chunks`     : morceaux de texte + embedding vectoriel (pgvector).
- `statistics` : donnees chiffrees extraites des Excel (pour requetes SQL).
"""
from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.config import CONFIG

EMBED_DIM = int(CONFIG.get("embeddings", {}).get("dimension", 1024))


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Chemin relatif du fichier source (unique)
    source_path: Mapped[str] = mapped_column(Text, unique=True, index=True)
    filename: Mapped[str] = mapped_column(Text)
    file_type: Mapped[str] = mapped_column(String(16))  # pdf | xls | xlsx
    # Categorie BEAC (ex: "Politique monetaire", "Publications")
    category: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pays CEMAC detecte (Cameroun, Gabon, ...)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Annee/date detectee dans le document
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # Methode d'extraction : "native" | "ocr" | "excel"
    extraction_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doc_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
    # Metadonnees denormalisees pour filtrer rapidement au retrieval
    chunk_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="chunks")


class Statistic(Base):
    """Donnees tabulaires Excel normalisees en format long.

    Une ligne = (indicateur, pays, periode) -> valeur.
    Permet des requetes SQL precises pour les questions chiffrees.
    """

    __tablename__ = "statistics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    indicator: Mapped[str] = mapped_column(Text, index=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    period: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    raw_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(Text, nullable=True)


# Index composites utiles
Index("ix_statistics_indicator_country_year", Statistic.indicator, Statistic.country, Statistic.year)
