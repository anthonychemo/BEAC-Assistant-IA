import re
from typing import List

# Paramètres par défaut pour le chunking
CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    words = normalize_whitespace(text).split(" ")
    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


if __name__ == "__main__":
    sample = "Ceci est un exemple de texte. " * 50
    chunks = chunk_text(sample)
    print(f"Nombre de chunks: {len(chunks)}")
    for idx, chunk in enumerate(chunks, start=1):
        print(f"--- chunk {idx} ---\n{chunk[:120]}\n")
