"""Renseigne `documents.r2_key` en reliant chaque document au fichier present dans R2.

Tous les documents de la base actuelle ont ete ingeres sans `r2_key` (ingestion
historique, avant le passage au pipeline base sur R2) : le bouton "Consulter"
de la bibliotheque et les liens de sources du chat ne peuvent donc pas ouvrir
le fichier original (endpoint `/documents/{id}/view`).

Ce script liste les objets du bucket R2 et fait correspondre `documents.filename`
au nom de fichier (basename) de chaque objet, puis renseigne `r2_key` pour les
documents ainsi retrouves (uniquement si `r2_key` est actuellement vide, et sans
toucher au reste du schema). Les documents dont le fichier n'est plus/pas present
dans le bucket restent inchanges (ils retombent sur `source_url` puis sur la page
d'accueil beac.int, voir `/documents/{id}/view`).

Usage : python -m scripts.backfill_r2_keys [--dry-run]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from src.database.connection import session_scope
from src.database.schema import Document
from src.ingestion.r2_client import _client
from src.config import settings
from src.utils.logger import logger


def load_bucket_keys_by_basename() -> dict[str, list[str]]:
    """Liste tous les objets R2 et les regroupe par nom de fichier (basename)."""
    client = _client()
    bucket = settings.r2_bucket_name
    by_basename: dict[str, list[str]] = defaultdict(list)
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            by_basename[Path(obj["Key"]).name].append(obj["Key"])
    return by_basename


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill documents.r2_key depuis le contenu du bucket R2")
    parser.add_argument("--dry-run", action="store_true", help="N'ecrit rien, affiche seulement le resultat attendu")
    args = parser.parse_args()

    by_basename = load_bucket_keys_by_basename()
    logger.info(f"{len(by_basename)} noms de fichiers uniques trouves dans le bucket R2")

    updated = 0
    already_set = 0
    unmatched = 0
    ambiguous = 0
    duplicate_rows = 0
    # `r2_key` est unique en base : si plusieurs lignes `documents` partagent le
    # meme `filename` (doublons d'une ingestion historique), une seule peut
    # recevoir la cle - les autres restent en attente (source_url en repli).
    claimed: set[str] = set()

    with session_scope() as session:
        rows = session.query(Document).all()

        # Passe 1 : reserver les cles deja assignees a un AUTRE document, quel
        # que soit l'ordre de renvoi de la requete (sinon un document sans
        # r2_key peut etre traite avant celui qui la detient deja et retenter
        # la meme valeur -> violation de l'unicite en base).
        for doc in rows:
            if doc.r2_key:
                already_set += 1
                claimed.add(doc.r2_key)

        # Passe 2 : assigner les cles disponibles aux documents restants.
        for doc in rows:
            if doc.r2_key:
                continue
            keys = by_basename.get(doc.filename)
            if not keys:
                unmatched += 1
                continue
            if len(keys) > 1:
                # Plusieurs objets portent le meme nom de fichier (dossiers differents) :
                # pas de moyen fiable de departager, on ignore plutot que de deviner.
                ambiguous += 1
                continue
            key = keys[0]
            if key in claimed:
                duplicate_rows += 1
                continue
            claimed.add(key)
            updated += 1
            if not args.dry_run:
                doc.r2_key = key
        if args.dry_run:
            session.rollback()

    logger.info(
        f"{'(dry-run) ' if args.dry_run else ''}"
        f"{updated} documents mis a jour, {already_set} deja renseignes, "
        f"{unmatched} sans fichier correspondant dans R2, {ambiguous} ambigus (ignores), "
        f"{duplicate_rows} doublons en base pour un meme fichier (ignores)."
    )


if __name__ == "__main__":
    main()
