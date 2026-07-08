"""Client LLM via OpenRouter (Gemma gratuit avec fallback).

3 retries sur le modele principal (gemma), puis 3 retries sur le fallback.
Si les deux echouent, retourne un message d'indisponibilite propre a l'utilisateur.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Iterator

from openai import APIConnectionError, APIError, OpenAI, RateLimitError

from src.config import CONFIG, settings
from src.utils.logger import logger

_LLM = CONFIG.get("llm", {})
_MODEL = _LLM.get("model", settings.llm_model)
_FAST_MODEL = _LLM.get("fast_model", None)
_FALLBACK_MODEL = _LLM.get("fallback_model") or None
_TEMPERATURE = float(_LLM.get("temperature", 0.1))
_MAX_TOKENS = int(_LLM.get("max_tokens", 1024))

_MAX_RETRIES = 3
_RETRY_DELAY = 3.0  # secondes, doublee a chaque tentative

_UNAVAILABLE_MSG = (
    "Je suis temporairement indisponible en raison d'une forte demande. "
    "Veuillez reessayer dans quelques instants ou consulter le site officiel : "
    "https://www.beac.int"
)


class LLMClient:
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
        )
        self.model = _MODEL
        self._options = {
            "temperature": _TEMPERATURE,
            "max_tokens": _MAX_TOKENS,
        }

    def warmup(self) -> None:
        if not settings.openrouter_api_key:
            logger.error("OPENROUTER_API_KEY manquante dans .env")
            return
        logger.info("LLM OpenRouter : {} — pas de prechauffage necessaire.", self.model)

    def unload(self) -> None:
        pass

    def _build_messages(self, prompt: str, system: str | None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _attempt(self, model: str, messages: list[dict[str, str]], **options):
        """Un modele donne avec _MAX_RETRIES tentatives en cas de rate limit."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self.client.chat.completions.create(
                    model=model, messages=messages, **options
                )
            except RateLimitError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_DELAY * (2 ** attempt)
                    logger.warning(
                        "Rate limit OpenRouter [{}] (tentative {}/{}) — retry dans {:.1f}s",
                        model, attempt + 1, _MAX_RETRIES, delay,
                    )
                    time.sleep(delay)
            except APIConnectionError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    time.sleep(_RETRY_DELAY)
            except APIError as exc:
                logger.error("Erreur OpenRouter [{}] : {}", getattr(exc, "status_code", "?"), exc)
                raise
        raise RuntimeError(f"Echec apres {_MAX_RETRIES + 1} tentatives sur '{model}' : {last_exc}")

    def _chat_with_retry(self, model: str, messages: list[dict[str, str]], **options):
        """Modele principal → fallback → message d'indisponibilite."""
        try:
            return self._attempt(model, messages, **options)
        except RuntimeError:
            if _FALLBACK_MODEL and _FALLBACK_MODEL != model:
                logger.warning(
                    "Modele '{}' indisponible — bascule sur '{}'", model, _FALLBACK_MODEL,
                )
                try:
                    return self._attempt(_FALLBACK_MODEL, messages, **options)
                except RuntimeError:
                    logger.error("Fallback '{}' aussi indisponible.", _FALLBACK_MODEL)
            raise RuntimeError("LLM_UNAVAILABLE")

    def generate(self, prompt: str, system: str | None = None, fast: bool = False) -> str:
        model = (_FAST_MODEL if fast and _FAST_MODEL else self.model)
        messages = self._build_messages(prompt, system)
        try:
            response = self._chat_with_retry(model=model, messages=messages, **self._options)
            return response.choices[0].message.content.strip()
        except RuntimeError as exc:
            if "LLM_UNAVAILABLE" in str(exc):
                return _UNAVAILABLE_MSG
            raise

    def stream(self, prompt: str, system: str | None = None) -> Iterator[str]:
        messages = self._build_messages(prompt, system)
        try:
            stream = self._chat_with_retry(
                model=self.model, messages=messages, stream=True, **self._options,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except RuntimeError as exc:
            if "LLM_UNAVAILABLE" in str(exc):
                yield _UNAVAILABLE_MSG
                return
            logger.error("Erreur streaming : {}", exc)
            raise
        except APIError as exc:
            logger.error("Erreur OpenRouter streaming : {}", exc)
            raise


@lru_cache
def get_llm() -> LLMClient:
    return LLMClient()
