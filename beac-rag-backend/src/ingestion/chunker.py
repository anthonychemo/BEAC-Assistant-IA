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


# Motif frequent dans les organigrammes/annuaires extraits de PDF : une ligne
# "TITRE EN MAJUSCULES" suivie d'une ligne "Nom Personne". Ce format brut
# etiquette/valeur matche mal les questions en langage naturel ("qui est le
# gouverneur ?") lors de la recherche par similarite d'embeddings. On le
# reformate en phrase "Titre : Nom." pour ameliorer le score de similarite.
_TITLE_LINE_RE = re.compile(r"^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ][A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ '\-]{2,60}$")
_NAME_TOKEN_TITLECASE_RE = re.compile(r"^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ][a-zà-ÿ'\-]+$")
_NAME_TOKEN_UPPER_RE = re.compile(r"^[A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]{2,}$")


def _looks_like_name(line: str) -> bool:
    """Ex: 'Yvon SANA BANGUI' (prenom Titlecase + nom(s) en capitales)."""
    tokens = line.split()
    if not (1 <= len(tokens) <= 5):
        return False
    has_titlecase = False
    for tok in tokens:
        if _NAME_TOKEN_TITLECASE_RE.match(tok):
            has_titlecase = True
        elif not _NAME_TOKEN_UPPER_RE.match(tok):
            return False
    return has_titlecase


_ENTRY_LINE_RE = re.compile(r"^.+ : .+\.$")
# Nombre d'entrees 'Titre : Nom.' regroupees par chunk. Un annuaire/organigramme
# contient souvent des dizaines d'entrees a la suite ; les decouper par lots de
# 400 tokens (comme du texte narratif) noie chaque entree individuelle sous des
# dizaines d'autres, ce qui degrade fortement son score de similarite avec une
# question ciblee ("qui est le gouverneur ?"). On les regroupe donc par petits
# lots homogenes plutot que via le splitter recursif standard.
_ENTRY_GROUP_SIZE = 4


def _pair_titles_with_names(text: str) -> str:
    """Reformate les paires 'TITRE' / 'Nom' en phrases 'Titre : Nom.'."""
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if (
            _TITLE_LINE_RE.match(line)
            and len(line.split()) <= 6
            and _looks_like_name(next_line)
        ):
            # "de la BEAC" ameliore nettement le score de similarite avec des
            # questions qui nomment l'institution (verifie empiriquement : sans
            # cette mention, le score chute sous celui du texte brut non-reformate).
            out.append(f"{line.title()} de la BEAC : {next_line}.")
            i += 2
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def _split_standard(block: str) -> list[TextChunk]:
    """Decoupage recursif standard (paragraphes/phrases, ~chunk_size tokens)."""
    chunks: list[TextChunk] = []
    for piece in _SPLITTER.split_text(block):
        piece = piece.strip()
        if len(piece) >= _MIN_CHARS:
            chunks.append(TextChunk(content=piece, token_count=_count_tokens(piece)))
    return chunks


def _split_entry_group(lines: list[str]) -> list[TextChunk]:
    """Regroupe des lignes 'Titre : Nom.' consecutives par petits lots."""
    chunks: list[TextChunk] = []
    for start in range(0, len(lines), _ENTRY_GROUP_SIZE):
        piece = "\n".join(lines[start:start + _ENTRY_GROUP_SIZE]).strip()
        if len(piece) >= _MIN_CHARS:
            chunks.append(TextChunk(content=piece, token_count=_count_tokens(piece)))
    return chunks


def chunk_text(text: str) -> list[TextChunk]:
    """Decoupe un texte nettoye en chunks exploitables.

    Les lignes 'Titre : Nom.' consecutives (annuaires/organigrammes) sont
    regroupees a part par petits lots homogenes ; le reste du texte suit le
    decoupage recursif standard (paragraphes/phrases, ~chunk_size tokens).
    """
    text = _clean(text)
    text = _pair_titles_with_names(text)
    if not text:
        return []

    chunks: list[TextChunk] = []
    buffer: list[str] = []
    entry_group: list[str] = []

    def flush_buffer() -> None:
        if buffer:
            chunks.extend(_split_standard("\n".join(buffer)))
            buffer.clear()

    def flush_entries() -> None:
        if entry_group:
            chunks.extend(_split_entry_group(entry_group))
            entry_group.clear()

    for line in text.split("\n"):
        if _ENTRY_LINE_RE.match(line.strip()):
            flush_buffer()
            entry_group.append(line.strip())
        else:
            flush_entries()
            buffer.append(line)
    flush_buffer()
    flush_entries()
    return chunks
