"""Renseigne `documents.source_url` a partir de `beac_data/beac_pdfs_liens.xlsx`.

Les documents ingeres localement (metadata avec `relative_path`, sans `r2_key`)
n'ont pas de `source_url` : le bouton "Consulter" de la bibliotheque retombe
alors sur la page d'accueil generique de beac.int au lieu du document precis.

`beac_data/beac_pdfs_liens.xlsx` (colonnes `nom_pdf`, `lien`, `statut`) est le
mapping produit par le scraper entre chaque nom de fichier PDF et son URL
source reelle sur beac.int. Ce script fait correspondre `documents.filename`
a `nom_pdf` et met a jour `source_url` en consequence (uniquement pour les
lignes ou il est actuellement vide, et sans jamais toucher au reste du schema).

Usage : python -m scripts.backfill_source_urls [--xlsx CHEMIN] [--dry-run]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.database.connection import session_scope
from src.database.schema import Document
from src.utils.logger import logger

# beac-rag-backend/scripts/ -> beac-rag-backend/ -> racine du repo -> beac_data/
_DEFAULT_XLSX = Path(__file__).resolve().parents[2] / "beac_data" / "beac_pdfs_liens.xlsx"


def load_links(xlsx_path: Path) -> dict[str, str]:
    df = pd.read_excel(xlsx_path)
    # dropna : ignore les lignes sans lien exploitable
    df = df.dropna(subset=["nom_pdf", "lien"])
    return dict(zip(df["nom_pdf"], df["lien"]))


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill documents.source_url depuis beac_pdfs_liens.xlsx")
    parser.add_argument("--xlsx", type=Path, default=_DEFAULT_XLSX, help="Chemin vers beac_pdfs_liens.xlsx")
    parser.add_argument("--dry-run", action="store_true", help="N'ecrit rien, affiche seulement le resultat attendu")
    args = parser.parse_args()

    if not args.xlsx.exists():
        logger.error(f"Fichier introuvable : {args.xlsx}")
        return

    links = load_links(args.xlsx)
    logger.info(f"{len(links)} correspondances nom_pdf -> lien chargees depuis {args.xlsx}")

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
