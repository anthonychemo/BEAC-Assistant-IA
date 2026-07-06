"""Clients LLM : Ollama (local) et OpenRouter (cloud).

Le client actif est choisi par requete via le parametre `provider`.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Iterator

import httpx
import ollama
from ollama import ResponseError

from src.config import CONFIG, settings
from src.utils.logger import logger

_LLM = CONFIG.get("llm", {})
_MODEL = _LLM.get("model", settings.llm_model)
_TEMPERATURE = float(_LLM.get("temperature", 0.1))
_NUM_CTX = int(_LLM.get("num_ctx", 3072))
_MAX_TOKENS = int(_LLM.get("max_tokens", 512))
_NUM_THREAD = int(_LLM.get("num_thread", 8))
_KEEP_ALIVE = _LLM.get("keep_alive", "2h")

_MAX_RETRIES = 2
_RETRY_DELAY = 1.0

# Modeles OpenRouter disponibles
OPENROUTER_MODELS = {
    "gemma-4-26b": "google/gemma-4-26b-a4b-it:free",
    "llama-3.1-8b": "meta-llama/llama-3.1-8b-instruct:free",
    "mistral-7b": "mistralai/mistral-7b-instruct:free",
    "qwen-2.5-7b": "qwen/qwen-2.5-7b-instruct:free",
}

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _get_openrouter_key() -> str:
    import os
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[3] / ".env")
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY non definie dans .env")
    return key


class OllamaClient:
    """Client LLM local via Ollama."""

    def __init__(self) -> None:
        self.client = ollama.Client(host=settings.ollama_host)
        self.model = _MODEL
        self._options = {
            "temperature": _TEMPERATURE,
            "num_ctx": _NUM_CTX,
            "num_predict": _MAX_TOKENS,
            "num_thread": _NUM_THREAD,
        }

    def warmup(self) -> None:
        try:
            self.client.generate(
                model=self.model,
                prompt="Bonjour",
                keep_alive=_KEEP_ALIVE,
                options={"num_predict": 1},
            )
            logger.info("Ollama prechauffé : %s", self.model)
        except Exception as exc:
            logger.error("Echec warmup Ollama : %s", exc)

    def _build_messages(self, prompt: str, system: str | None) -> list[dict]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _chat_with_retry(self, **kwargs) -> dict:
        last_exc = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self.client.chat(**kwargs)
            except ResponseError as exc:
                logger.error("Erreur Ollama [%s] : %s", exc.status_code, exc.error)
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY)
        raise RuntimeError(f"Echec apres {_MAX_RETRIES + 1} tentatives : {last_exc}") from last_exc

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        messages = self._build_messages(prompt, system)
        response = self._chat_with_retry(
            model=self.model,
            messages=messages,
            options=self._options,
            keep_alive=_KEEP_ALIVE,
        )
        return response["message"]["content"].strip()

    def stream(self, prompt: str, system: str | None = None, **kwargs) -> Iterator[str]:
        messages = self._build_messages(prompt, system)
        try:
            for chunk in self.client.chat(
                model=self.model,
                messages=messages,
                options=self._options,
                keep_alive=_KEEP_ALIVE,
                stream=True,
            ):
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
        except Exception as exc:
            logger.error("Erreur streaming Ollama : %s", exc)
            raise

    def unload(self) -> None:
        try:
            self.client.generate(model=self.model, prompt="", keep_alive=0, options={"num_predict": 0})
        except Exception as exc:
            logger.warning("Echec dechargement LLM : %s", exc)


class OpenRouterClient:
    """Client LLM cloud via OpenRouter (compatible OpenAI)."""

    def __init__(self, model_key: str = "gemma-4-26b") -> None:
        self.model = OPENROUTER_MODELS.get(model_key, OPENROUTER_MODELS["gemma-4-26b"])
        self.api_key = _get_openrouter_key()
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "BEAC Assistant",
        }

    def _build_messages(self, prompt: str, system: str | None) -> list[dict]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def generate(self, prompt: str, system: str | None = None, **kwargs) -> str:
        messages = self._build_messages(prompt, system)
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
                logger.error("Reponse OpenRouter inattendue : %s", data)
                raise RuntimeError(f"OpenRouter error: {data.get('error', data)}")
            return data["choices"][0]["message"]["content"].strip()

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
                        import json
                        try:
                            chunk = json.loads(line[6:])
                            token = chunk["choices"][0].get("delta", {}).get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue

    def warmup(self) -> None:
        pass  # pas de warmup necessaire pour l'API cloud

    def unload(self) -> None:
        pass


def get_llm(provider: str = "ollama", model_key: str = "gemma-4-26b"):
    """Retourne le client LLM selon le provider choisi."""
    if provider == "openrouter":
        return OpenRouterClient(model_key=model_key)
    return OllamaClient()


# Singleton Ollama pour le warmup au demarrage
_ollama_singleton: OllamaClient | None = None


def get_default_llm() -> OllamaClient:
    global _ollama_singleton
    if _ollama_singleton is None:
        _ollama_singleton = OllamaClient()
    return _ollama_singleton
