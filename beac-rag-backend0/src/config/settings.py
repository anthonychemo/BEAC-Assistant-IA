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

    # PostgreSQL
    postgres_user: str = "beac"
    postgres_password: str = "beac_password"
    postgres_db: str = "beac_rag"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Données
    raw_data_dir: str = "../beac_data"

    # Ollama
    ollama_host: str = "http://localhost:11434"
    llm_model: str = "llama3.1:8b-instruct-q4_K_M"

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
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def raw_data_path(self) -> Path:
        p = Path(self.raw_data_dir)
        if not p.is_absolute():
            p = (ROOT_DIR / p).resolve()
        return p


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
