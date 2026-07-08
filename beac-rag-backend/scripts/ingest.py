"""Lance l'ingestion des donnees BEAC depuis le bucket Cloudflare R2.

Exemples :
  python -m scripts.ingest                 # tous les objets du bucket R2
  python -m scripts.ingest --only excel     # uniquement les Excel
  python -m scripts.ingest --only pdf --limit 10
"""
from __future__ import annotations

import argparse

from src.ingestion.pipeline import ingest_from_r2
from src.utils.logger import logger

from src.rag.llm_client import get_llm
get_llm().unload()   # libérer ~5 Go pendant l'ingestion OCR

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion BEAC RAG")
    parser.add_argument("--only", choices=["pdf", "excel"], default=None, help="Filtrer un type")
    parser.add_argument("--limit", type=int, default=None, help="Nb max d'objets")
    args = parser.parse_args()

    stats = ingest_from_r2(limit=args.limit, only=args.only)
    logger.info(f"Resultat : {stats}")


if __name__ == "__main__":
    main()
