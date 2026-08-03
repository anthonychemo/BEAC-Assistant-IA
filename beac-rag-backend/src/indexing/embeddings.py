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
# Nombre de threads intra-op : par defaut os.cpu_count(), surchargeable via
# OMP_NUM_THREADS si os.cpu_count() sous-estime le nombre de coeurs logiques
# (observe sur certaines configs Windows).
torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", os.cpu_count() or 8)))
torch.set_num_interop_threads(2)   # threads pour les ops parallèles inter-opérations


from functools import lru_cache
from typing import Sequence

from sentence_transformers import SentenceTransformer

from src.config import CONFIG, settings
from src.utils.logger import logger

_EMB = CONFIG.get("embeddings", {})
_MODEL_NAME = _EMB.get("model", settings.embedding_model)
_BATCH_SIZE = int(_EMB.get("batch_size", 16))
_NORMALIZE = bool(_EMB.get("normalize", True))

# BGE-M3 recommande un prefixe pour les requetes de recherche
_QUERY_PREFIX = ""  # bge-m3 ne necessite pas de prefixe contrairement a e5


class Embedder:
    def __init__(self) -> None:
        logger.info(f"Chargement du modele d'embedding : {_MODEL_NAME} (device={settings.embedding_device})")
        self.model = SentenceTransformer(
            _MODEL_NAME,
            device=settings.embedding_device,
            local_files_only=True,
        )
        self.dimension = self.model.get_sentence_embedding_dimension()

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

    @lru_cache(maxsize=1024)
    def _embed_query_cached(self, normalized_text: str) -> tuple[float, ...]:
        vector = self.model.encode(
            _QUERY_PREFIX + normalized_text,
            normalize_embeddings=_NORMALIZE,
            convert_to_numpy=True,
        )
        return tuple(vector.tolist())

    def embed_query(self, text: str) -> list[float]:
        # Questions identiques (mêmes recherches repétées, frappe/effacement
        # dans la barre de recherche bibliothèque) réutilisent l'embedding
        # déjà calculé au lieu de refaire une inférence CPU à chaque appel.
        normalized = " ".join(text.strip().lower().split())
        return list(self._embed_query_cached(normalized))


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()
