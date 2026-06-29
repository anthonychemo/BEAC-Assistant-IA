"""Cache en mémoire des réponses RAG (LRU, TTL configurable)."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from collections import OrderedDict

from src.config import CONFIG

_CACHE = CONFIG.get("cache", {})
_MAX_SIZE = int(_CACHE.get("max_size", 100))   # 100 questions max
_TTL = int(_CACHE.get("ttl_seconds", 3600))    # 1h par défaut


@dataclass
class CacheEntry:
    response: object
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > _TTL


class ResponseCache:
    def __init__(self) -> None:
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()

    def _key(self, question: str) -> str:
        return hashlib.sha256(question.strip().lower().encode()).hexdigest()

    def get(self, question: str):
        key = self._key(question)
        entry = self._store.get(key)
        if entry is None or entry.is_expired():
            if entry:
                del self._store[key]
            return None
        # LRU : remonter en tête
        self._store.move_to_end(key)
        return entry.response

    def set(self, question: str, response: object) -> None:
        key = self._key(question)
        if len(self._store) >= _MAX_SIZE:
            self._store.popitem(last=False)   # évince le plus ancien
        self._store[key] = CacheEntry(response=response)

    def invalidate(self) -> None:
        self._store.clear()


_cache = ResponseCache()


def get_cache() -> ResponseCache:
    return _cache