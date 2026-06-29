"""Segmentation du texte en chunks pour le RAG.

Utilise un decoupage recursif (paragraphes -> phrases) avec chevauchement,
en mesurant la taille en tokens (tiktoken) pour rester compatible avec la
fenetre de contexte du LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import CONFIG

_CHUNK = CONFIG.get("chunking", {})
_CHUNK_SIZE = int(_CHUNK.get("chunk_size", 800))
_CHUNK_OVERLAP = int(_CHUNK.get("chunk_overlap", 120))
_MIN_CHARS = int(_CHUNK.get("min_chunk_chars", 50))

_ENCODER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


_SPLITTER = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=_CHUNK_SIZE,
    chunk_overlap=_CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


@dataclass
class TextChunk:
    content: str
    token_count: int


def _clean(text: str) -> str:
    # Normalise les espaces et supprime les lignes vides multiples
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str) -> list[TextChunk]:
    """Decoupe un texte nettoye en chunks exploitables."""
    text = _clean(text)
    if not text:
        return []

    pieces = _SPLITTER.split_text(text)
    chunks: list[TextChunk] = []
    for piece in pieces:
        piece = piece.strip()
        if len(piece) < _MIN_CHARS:
            continue
        chunks.append(TextChunk(content=piece, token_count=_count_tokens(piece)))
    return chunks
