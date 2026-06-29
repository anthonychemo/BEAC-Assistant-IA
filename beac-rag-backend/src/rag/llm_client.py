"""Client LLM via Ollama (Llama 3.1 local).

Garde le modèle en RAM (keep_alive) pour réduire la latence en démo live.
Supporte la génération simple et en streaming.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Iterator

import ollama
from ollama import ResponseError

from src.config import CONFIG, settings
from src.utils.logger import logger

_LLM = CONFIG.get("llm", {})
_MODEL = _LLM.get("model", settings.llm_model)
_TEMPERATURE = float(_LLM.get("temperature", 0.1))
_NUM_CTX = int(_LLM.get("num_ctx", 4096))
_MAX_TOKENS = int(_LLM.get("max_tokens", 1024))
_KEEP_ALIVE = _LLM.get("keep_alive", "1h")
_FAST_MODEL = _LLM.get("fast_model", None)

# Nombre de tentatives en cas d'erreur transitoire (connexion Ollama)
_MAX_RETRIES = 2
_RETRY_DELAY = 1.0  # secondes


class LLMClient:
    def __init__(self) -> None:
        self.client = ollama.Client(host=settings.ollama_host)
        self.model = _MODEL
        self._options = {
            "temperature": _TEMPERATURE,
            "num_ctx": _NUM_CTX,
            "num_predict": _MAX_TOKENS,
        }

    # ------------------------------------------------------------------
    # Warmup
    # ------------------------------------------------------------------

    def warmup(self) -> None:
        try:
            self.client.generate(
                model=self.model,
                prompt="Bonjour",
                keep_alive=_KEEP_ALIVE,   # "30m" — maintient le modèle chargé
                options={"num_predict": 1},
            )
            # Préchauffer aussi le fast_model s'il est configuré
            if _FAST_MODEL:
                self.client.generate(
                    model=_FAST_MODEL,
                    prompt="Bonjour",
                    keep_alive=_KEEP_ALIVE,
                    options={"num_predict": 1},
                )
            logger.info("LLM(s) préchauffé(s) : %s", self.model)
        except Exception as exc:
            logger.error("Échec warmup : %s", exc)

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

    def _chat_with_retry(self, **kwargs) -> dict:
        """Appel client.chat avec retry sur erreur transitoire."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                return self.client.chat(**kwargs)
            except ResponseError as exc:
                # Erreur Ollama non-récupérable (ex: modèle introuvable)
                logger.error("Erreur Ollama [%s] : %s", exc.status_code, exc.error)
                raise
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "Tentative %d/%d échouée : %s — retry dans %.1fs",
                        attempt + 1, _MAX_RETRIES, exc, _RETRY_DELAY,
                    )
                    time.sleep(_RETRY_DELAY)
        raise RuntimeError(
            f"Échec après {_MAX_RETRIES + 1} tentatives : {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def generate(self, prompt: str, system: str | None = None,
                 fast: bool = False) -> str:
        model = (_FAST_MODEL if fast and _FAST_MODEL else self.model)
        messages = self._build_messages(prompt, system)
        response = self._chat_with_retry(
            model=model,
            messages=messages,
            options=self._options,
            keep_alive=_KEEP_ALIVE,
        )
        return response["message"]["content"].strip()

    def stream(self, prompt: str, system: str | None = None) -> Iterator[str]:
        """Génère une réponse token par token (streaming)."""
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
        except ResponseError as exc:
            logger.error("Erreur Ollama streaming [%s] : %s", exc.status_code, exc.error)
            raise
        except Exception as exc:
            logger.error("Erreur inattendue en streaming : %s", exc)
            raise
    
    def unload(self) -> None:
        """Décharge le modèle de la RAM (utile pendant l'ingestion longue)."""
        try:
            self.client.generate(
                model=self.model,
                prompt="",
                keep_alive=0,   # 0 = décharge immédiate
                options={"num_predict": 0},
            )
            logger.info("LLM déchargé de la RAM.")
        except Exception as exc:
            logger.warning(f"Échec déchargement LLM : {exc}")


@lru_cache
def get_llm() -> LLMClient:
    """Retourne le singleton LLMClient (instancié une seule fois)."""
    return LLMClient()