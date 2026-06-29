"""Lance l'ingestion des donnees BEAC.

Exemples :
  python -m scripts.ingest                 # tout le dossier RAW_DATA_DIR
  python -m scripts.ingest --only excel     # uniquement les Excel
  python -m scripts.ingest --only pdf --limit 10
  python -m scripts.ingest --path "C:/chemin/dossier"
"""
from __future__ import annotations

import argparse
from pathlib import Path

from src.ingestion.pipeline import ingest_directory
from src.utils.logger import logger

from src.rag.llm_client import get_llm
get_llm().unload()   # libérer ~5 Go pendant l'ingestion OCR

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion BEAC RAG")
    parser.add_argument("--path", type=str, default=None, help="Dossier source (defaut: .env RAW_DATA_DIR)")
    parser.add_argument("--only", choices=["pdf", "excel"], default=None, help="Filtrer un type")
    parser.add_argument("--limit", type=int, default=None, help="Nb max de fichiers")
    args = parser.parse_args()

    root = Path(args.path) if args.path else None
    stats = ingest_directory(root=root, limit=args.limit, only=args.only)
    logger.info(f"Resultat : {stats}")


if __name__ == "__main__":
    main()
