"""Client LLM via OpenRouter (Gemma et autres modeles cloud gratuits)."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

import httpx

from src.config import CONFIG, settings
from src.utils.logger import logger

_LLM = CONFIG.get("llm", {})
_TEMPERATURE = float(_LLM.get("temperature", 0.1))
_MAX_TOKENS = int(_LLM.get("max_tokens", 512))

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Modeles disponibles via OpenRouter
OPENROUTER_MODELS: dict[str, str] = {
    "gemma-4-26b":   "google/gemma-4-26b-a4b-it:free",
    "llama-3.1-8b":  "meta-llama/llama-3.1-8b-instruct:free",
    "mistral-7b":    "mistralai/mistral-7b-instruct:free",
    "qwen-2.5-7b":   "qwen/qwen-2.5-7b-instruct:free",
}

DEFAULT_MODEL_KEY = "gemma-4-26b"


def _get_api_key() -> str:
    import os
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY non definie dans .env")
    return key


class LLMClient:
    """Client OpenRouter — interface unique pour tous les modeles cloud."""

    def __init__(self, model_key: str = DEFAULT_MODEL_KEY) -> None:
        self.model_key = model_key
        self.model = OPENROUTER_MODELS.get(model_key, OPENROUTER_MODELS[DEFAULT_MODEL_KEY])
        self._api_key = _get_api_key()
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "X-Title": "BEAC Assistant",
        }
        logger.info(f"LLMClient initialise : {self.model}")

    def _build_messages(self, prompt: str, system: str | None) -> list[dict]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def warmup(self) -> None:
        """Pas de warmup necessaire pour l'API cloud."""
        logger.info("OpenRouter pret (pas de warmup necessaire).")

    def unload(self) -> None:
        pass

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        messages = self._build_messages(prompt, system)
        for attempt in range(2):
            try:
                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers=self._headers,
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": _TEMPERATURE,
                            "max_tokens": _MAX_TOKENS,
                            "stream": False,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()
                    if "choices" not in data:
                        err = data.get("error", data)
                        logger.error("Reponse OpenRouter inattendue : %s", err)
                        if attempt == 0:
                            # Retry avec un modele de secours
                            logger.warning("Retry avec llama-3.1-8b...")
                            self.model = OPENROUTER_MODELS["llama-3.1-8b"]
                            continue
                        raise RuntimeError(f"OpenRouter error: {err}")
                    return data["choices"][0]["message"]["content"].strip()
            except httpx.TimeoutException:
                if attempt == 0:
                    logger.warning("Timeout, retry...")
                    continue
                raise
        raise RuntimeError("Echec apres 2 tentatives")

    def stream(self, prompt: str, system: str | None = None, **kwargs) -> Iterator[str]:
        messages = self._build_messages(prompt, system)
        with httpx.Client(timeout=120) as client:
            with client.stream(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=self._headers,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": _TEMPERATURE,
                    "max_tokens": _MAX_TOKENS,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            token = chunk["choices"][0].get("delta", {}).get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue


def get_llm(provider: str = "openrouter", model_key: str = DEFAULT_MODEL_KEY) -> LLMClient:
    """Retourne un LLMClient OpenRouter avec le modele choisi."""
    return LLMClient(model_key=model_key)


def get_default_llm() -> LLMClient:
    """Singleton LLMClient avec le modele par defaut (Gemma)."""
    return LLMClient(model_key=DEFAULT_MODEL_KEY)
