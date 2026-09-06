"""Renseigne `documents.source_url` a partir du CSV produit par le scraper.

`data_pipeline/Scrapping/scraping/beac_pdfs_export.csv` (colonnes `chemin_relatif`,
`lien`, ...) est le mapping produit par le scraper entre chaque fichier PDF et son
URL source reelle sur beac.int. Ce script fait correspondre `documents.filename`
au nom de fichier (basename de `chemin_relatif`) et met a jour `source_url` en
consequence (uniquement pour les lignes ou il est actuellement vide, et sans
jamais toucher au reste du schema).

Usage : python -m scripts.backfill_source_urls [--csv CHEMIN] [--dry-run]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.database.connection import session_scope
from src.database.schema import Document
from src.utils.logger import logger

# beac-rag-backend/scripts/ -> beac-rag-backend/ -> racine du repo -> data_pipeline/Scrapping/
_DEFAULT_CSV = (
    Path(__file__).resolve().parents[2]
    / "data_pipeline" / "Scrapping" / "scraping" / "beac_pdfs_export.csv"
)


def load_links(csv_path: Path) -> dict[str, str]:
    """basename(chemin_relatif) -> lien, dernier gagne en cas de doublon."""
    links: dict[str, str] = {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            rel = (row.get("chemin_relatif") or "").strip()
            lien = (row.get("lien") or "").strip()
            if not rel or not lien:
                continue
            links[Path(rel).name] = lien
    return links


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill documents.source_url depuis le CSV du scraper")
    parser.add_argument("--csv", type=Path, default=_DEFAULT_CSV, help="Chemin vers beac_pdfs_export.csv")
    parser.add_argument("--dry-run", action="store_true", help="N'ecrit rien, affiche seulement le resultat attendu")
    args = parser.parse_args()

    if not args.csv.exists():
        logger.error(f"Fichier introuvable : {args.csv}")
        return

    links = load_links(args.csv)
    logger.info(f"{len(links)} correspondances nom_fichier -> lien chargees depuis {args.csv}")

    updated = 0
    already_set = 0
    unmatched = 0

    with session_scope() as session:
        rows = session.query(Document).filter(Document.file_type == "pdf").all()
        for doc in rows:
            if doc.source_url:
                already_set += 1
                continue
            lien = links.get(doc.filename)
            if not lien:
                unmatched += 1
                continue
            updated += 1
            if not args.dry_run:
                doc.source_url = lien
        if args.dry_run:
            session.rollback()

    logger.info(
        f"{'(dry-run) ' if args.dry_run else ''}"
        f"{updated} documents mis a jour, {already_set} deja renseignes, {unmatched} sans correspondance."
    )


if __name__ == "__main__":
    main()
