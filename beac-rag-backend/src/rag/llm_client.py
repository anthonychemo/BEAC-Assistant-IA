"""Client LLM via OpenRouter (modele gratuit, ex: google/gemma-4-31b-it:free).

OpenRouter expose une API compatible OpenAI (chat/completions), donc le SDK
`openai` officiel est reutilise tel quel avec un `base_url` different. Plus de
dependance a Ollama ni a un GPU/RAM local : le modele tourne cote OpenRouter.

Le modele gratuit est rate-limite (~20 req/min, ~200 req/jour) car subventionne :
les erreurs 429 sont retentees avec backoff, puis si `fallback_model` est
configure (config.yaml), on bascule dessus avant d'abandonner.
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

# Le modele gratuit est rate-limite : on retente plus longtemps que pour un LLM local.
_MAX_RETRIES = 3
_RETRY_DELAY = 3.0  # secondes, doublee a chaque tentative

# Modeles selectionnables depuis le frontend (cle envoyee par le client ->
# modele OpenRouter reel). Seuls les modeles effectivement configures et
# testes (principal + secours) sont proposes, pour eviter d'exposer un choix
# qui echouerait silencieusement.
MODEL_CHOICES: dict[str, str] = {"primary": _MODEL}
if _FALLBACK_MODEL:
    MODEL_CHOICES["fallback"] = _FALLBACK_MODEL


def resolve_model(model_key: str | None) -> str:
    """Traduit une cle de modele cote client en identifiant OpenRouter reel.

    Cle inconnue ou absente -> modele principal (comportement par defaut).
    """
    return MODEL_CHOICES.get(model_key or "primary", _MODEL)


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

    # ------------------------------------------------------------------
    # Cycle de vie (no-op : API distante, rien a charger/decharger localement)
    # ------------------------------------------------------------------

    def warmup(self) -> None:
        if not settings.openrouter_api_key:
            logger.error("OPENROUTER_API_KEY manquante dans .env")
            return
        logger.info("LLM distant (OpenRouter) : {} — pas de préchauffage nécessaire.", self.model)

    def unload(self) -> None:
        logger.info("LLM distant (OpenRouter) : rien à décharger localement.")

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    def _build_messages(
        self, prompt: str, system: str | None
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _attempt(self, model: str, messages: list[dict[str, str]], **options):
        """Tente une completion sur un modele donne, avec retry (rate limit/connexion)."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self.client.chat.completions.create(model=model, messages=messages, **options)
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
        raise RuntimeError(
            f"Échec après {_MAX_RETRIES + 1} tentatives sur '{model}' : {last_exc}"
        ) from last_exc

    def _chat_with_retry(self, model: str, messages: list[dict[str, str]], **options):
        """Tente le modele demande ; bascule sur `fallback_model` (config.yaml) si
        tous les essais sur le modele principal echouent (rate limit/connexion)."""
        try:
            return self._attempt(model, messages, **options)
        except RuntimeError:
            if _FALLBACK_MODEL and _FALLBACK_MODEL != model:
                logger.warning(
                    "Modele '{}' indisponible — bascule sur le modele de secours '{}'",
                    model, _FALLBACK_MODEL,
                )
                return self._attempt(_FALLBACK_MODEL, messages, **options)
            raise

    # ------------------------------------------------------------------
    # API publique (signature identique a l'ancien client Ollama)
    # ------------------------------------------------------------------

    def generate(self, prompt: str, system: str | None = None,
                 fast: bool = False, model: str | None = None) -> str:
        model = model or (_FAST_MODEL if fast and _FAST_MODEL else self.model)
        messages = self._build_messages(prompt, system)
        response = self._chat_with_retry(model=model, messages=messages, **self._options)
        return response.choices[0].message.content.strip()

    def stream(self, prompt: str, system: str | None = None,
               model: str | None = None) -> Iterator[str]:
        """Génère une réponse token par token (streaming)."""
        messages = self._build_messages(prompt, system)
        try:
            stream = self._chat_with_retry(
                model=model or self.model, messages=messages, stream=True, **self._options,
            )
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except APIError as exc:
            logger.error("Erreur OpenRouter streaming : {}", exc)
            raise


@lru_cache
def get_llm() -> LLMClient:
    """Retourne le singleton LLMClient (instancié une seule fois)."""
    return LLMClient()
