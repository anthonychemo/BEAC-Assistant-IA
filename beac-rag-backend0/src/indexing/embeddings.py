"""Generation d'embeddings avec BGE-M3 (multilingue, CPU-friendly).

Le modele est charge une seule fois (singleton) pour economiser la RAM.
BGE-M3 produit des vecteurs de dimension 1024, adaptes au FR/EN/ES.
"""
from __future__ import annotations

import os

# Mode offline HuggingFace : on utilise le modele en cache local sans requete.
# reseau. Evite les retries de plusieurs heures quand la machine est hors ligne.
# Surchargez en exportant HF_HUB_OFFLINE=0 si vous devez (re)telecharger un modele.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch

# Desactive les gradients (inutile en inference) et maximise les threads CPU.
torch.set_grad_enabled(False)
torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", 6)))
torch.set_num_interop_threads(2)


from functools import lru_cache
from typing import Sequence

from sentence_transformers import SentenceTransformer

from src.config import CONFIG, settings
from src.utils.logger import logger

_EMB = CONFIG.get("embeddings", {})
_MODEL_NAME = _EMB.get("model", settings.embedding_model)
_BATCH_SIZE = int(_EMB.get("batch_size", 16))
_NORMALIZE = bool(_EMB.get("normalize", True))

_QUERY_PREFIX = ""

# Singleton global — charge une seule fois pour tout le processus
_EMBEDDER_INSTANCE: "Embedder | None" = None


class Embedder:
    def __init__(self) -> None:
        logger.info(f"Chargement du modele d'embedding : {_MODEL_NAME} (device={settings.embedding_device})")
        self.model = SentenceTransformer(
            _MODEL_NAME,
            device=settings.embedding_device,
            local_files_only=True,
        )
        self.dimension = self.model.get_embedding_dimension()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            list(texts),
            batch_size=_BATCH_SIZE,
            normalize_embeddings=_NORMALIZE,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = self.model.encode(
            _QUERY_PREFIX + text,
            normalize_embeddings=_NORMALIZE,
            convert_to_numpy=True,
        )
        return vector.tolist()


def get_embedder() -> Embedder:
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        _EMBEDDER_INSTANCE = Embedder()
    return _EMBEDDER_INSTANCE
