"""Client Cloudflare R2 (S3-compatible) pour l'ingestion.

Le scraper (projet separe) televerse les documents directement dans ce
bucket, avec une metadata objet (lien, module, section, nom_pdf,
date_publication, type_document) qui remplace l'ancien export CSV.

Les documents sont telecharges dans un fichier temporaire le temps de leur
traitement (extraction PDF/OCR ou parsing Excel, qui necessitent un vrai
chemin fichier), puis le fichier temporaire est supprime immediatement
apres usage - aucune persistance locale durable.
"""
from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path
from typing import Iterator
from urllib.parse import unquote

import boto3
from botocore.client import Config

from src.config import settings


def _client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def decode_metadata(raw_metadata: dict[str, str]) -> dict[str, str]:
    """Decode les valeurs de metadata S3 (percent-encodees par le scraper)."""
    return {k: unquote(v) for k, v in raw_metadata.items()}


def list_document_keys() -> list[dict[str, str | dict[str, str]]]:
    """Liste tous les objets du bucket avec leur metadata decodee.

    Retourne une liste de {"key": str, "metadata": dict}.
    """
    client = _client()
    bucket = settings.r2_bucket_name
    results: list[dict] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            head = client.head_object(Bucket=bucket, Key=key)
            results.append({"key": key, "metadata": decode_metadata(head.get("Metadata", {}))})
    return results


@contextlib.contextmanager
def download_to_tempfile(key: str) -> Iterator[Path]:
    """Telecharge un objet R2 vers un fichier temporaire, supprime a la sortie."""
    client = _client()
    suffix = Path(key).suffix
    fd, tmp_path_str = tempfile.mkstemp(suffix=suffix)
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "wb") as f:
            client.download_fileobj(settings.r2_bucket_name, key, f)
        yield tmp_path
    finally:
        tmp_path.unlink(missing_ok=True)
