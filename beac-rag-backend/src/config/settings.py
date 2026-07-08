"""Chargement centralise de la configuration.

- Les secrets et chemins machine viennent de `.env` (voir `.env.example`).
- Les parametres fonctionnels viennent de `config/config.yaml`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Racine du projet (beac-rag-backend/)
ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"
ENV_PATH = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Variables d'environnement (.env)."""

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL (fallback si database_url_override n'est pas fourni)
    postgres_user: str = "beac"
    postgres_password: str = "beac_password"
    postgres_db: str = "beac_rag"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # Chaine de connexion complete (ex: Supabase, "Project Settings > Database").
    # Prioritaire sur postgres_user/password/host/port/db si renseignee.
    database_url_override: str | None = None

    # Stockage des documents (Cloudflare R2 - meme bucket que le scraper)
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

    # LLM (OpenRouter - modele gratuit, plus de dependance a Ollama/GPU local)
    openrouter_api_key: str = ""
    llm_model: str = "google/gemma-4-31b-it:free"

    # Embeddings
    embedding_model: str = "BAAI/bge-m3"
    embedding_device: str = "cpu"

    # OCR
    tesseract_cmd: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    poppler_path: str = r"C:\poppler\Library\bin"
    ocr_langs: str = "fra+eng+spa"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            url = self.database_url_override
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg://", 1)
            return url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
CONFIG: dict[str, Any] = _load_yaml(CONFIG_PATH)
