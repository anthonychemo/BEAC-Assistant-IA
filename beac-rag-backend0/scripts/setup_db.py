"""Initialise la base : extensions, tables et index vectoriel.

Usage : python -m scripts.setup_db
"""
from __future__ import annotations

from src.database.vector_store import create_schema
from src.utils.logger import logger


def main() -> None:
    logger.info("Creation du schema (extensions, tables, index HNSW)...")
    create_schema()
    logger.info("Schema pret.")


if __name__ == "__main__":
    main()
