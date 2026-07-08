"""Pre-charge le modele LLM en RAM (a lancer avant une demo live).

Usage : python -m scripts.warmup
"""
from __future__ import annotations

from src.rag.llm_client import get_llm
from src.utils.logger import logger


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-if-ingesting", action="store_true")
    args = parser.parse_args()
    if not args.skip_if_ingesting:
        logger.info("Préchauffage du LLM...")
        get_llm().warmup()
        logger.info("LLM prêt.")
    else:
        logger.info("Warmup ignoré (mode ingestion).")


if __name__ == "__main__":
    main()
