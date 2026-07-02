#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    import psycopg2
    from psycopg2.extras import Json
except ImportError:
    print(
        "Dependencies manquantes. Installez python-dotenv et psycopg2-binary :\n"
        "pip install python-dotenv psycopg2-binary"
    )
    sys.exit(1)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD", "postgres")
PGDATABASE = os.getenv("PGDATABASE", "beac_rag")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "BAAI/bge-m3")

from chunking import chunk_text

@dataclass
class DocumentChunk:
    source_path: str
    title: str
    section: str
    chunk_index: int
    content: str
    metadata: Dict[str, Any]


def extract_document_metadata(text_file: Path, root_dir: Path) -> Tuple[str, str, str]:
    rel_path = text_file.relative_to(root_dir)
    parts = rel_path.parts
    section = parts[0] if len(parts) > 1 else "Autres"
    title = text_file.stem
    return section, title, str(rel_path).replace("\\", "/")


def find_text_files(source_dir: Path) -> List[Path]:
    return sorted(source_dir.rglob("*.txt"))


def run_ollama_embed(text: str) -> List[float]:
    args = ["ollama", "embed", OLLAMA_EMBED_MODEL, "--text", text, "--json"]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Échec de la commande ollama embed : {result.stderr.strip() or result.stdout.strip()}"
        )
    output = result.stdout.strip()
    if not output:
        raise ValueError("Aucun vecteur reçu depuis ollama.")

    try:
        parsed = json.loads(output)
        if isinstance(parsed, dict):
            if "embedding" in parsed:
                return parsed["embedding"]
            if "vector" in parsed:
                return parsed["vector"]
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    floats = re.findall(r"-?\d+\.\d+(?:[eE][+-]?\d+)?", output)
    if not floats:
        raise ValueError(f"Impossible de parser l'embedding Ollama : {output[:200]}")
    return [float(x) for x in floats]


def create_connection():
    return psycopg2.connect(
        host=PGHOST,
        port=int(PGPORT),
        user=PGUSER,
        password=PGPASSWORD,
        database=PGDATABASE,
    )


def ensure_database_table(conn, vector_dim: int) -> None:
    with conn.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cursor.execute(
            "SELECT to_regclass('public.beac_documents');"
        )
        exists = cursor.fetchone()[0] is not None
        if not exists:
            cursor.execute(
                f"""
                CREATE TABLE beac_documents (
                    id SERIAL PRIMARY KEY,
                    source_path TEXT,
                    title TEXT,
                    section TEXT,
                    chunk_index INTEGER,
                    content TEXT,
                    metadata JSONB,
                    embedding vector({vector_dim}),
                    created_at TIMESTAMPTZ DEFAULT now()
                );
                CREATE INDEX IF NOT EXISTS idx_beac_documents_embedding ON beac_documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                """
            )
            conn.commit()
        else:
            cursor.execute(
                "SELECT data_type FROM information_schema.columns WHERE table_name='beac_documents' AND column_name='embedding';"
            )
            existing_type = cursor.fetchone()
            if existing_type and f"vector({vector_dim})" not in existing_type[0]:
                print(
                    f"Attention : la colonne embedding existe déjà avec le type {existing_type[0]}."
                    " Vérifiez que la dimension correspond à l'embed BAAI/bge-m3."
                )


def upsert_document_chunk(conn, chunk: DocumentChunk) -> None:
    with conn.cursor() as cursor:
        embedding_str = "[" + ",".join(str(float(x)) for x in chunk.metadata["embedding"]) + "]"
        cursor.execute(
            "INSERT INTO beac_documents (source_path, title, section, chunk_index, content, metadata, embedding) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s::vector);",
            (
                chunk.source_path,
                chunk.title,
                chunk.section,
                chunk.chunk_index,
                chunk.content,
                Json(chunk.metadata),
                embedding_str,
            ),
        )


def process_file(text_file: Path, root_dir: Path, conn) -> int:
    raw_text = text_file.read_text(encoding="utf-8", errors="ignore")
    section, title, source_path = extract_document_metadata(text_file, root_dir)
    chunks = chunk_text(raw_text)
    print(f"Processing {source_path} → {len(chunks)} chunks")

    for index, chunk_content in enumerate(chunks, start=1):
        embedding = run_ollama_embed(chunk_content)
        chunk = DocumentChunk(
            source_path=source_path,
            title=title,
            section=section,
            chunk_index=index,
            content=chunk_content,
            metadata={
                "source_path": source_path,
                "title": title,
                "section": section,
                "chunk_length": len(chunk_content.split()),
                "embedding": embedding,
            },
        )
        upsert_document_chunk(conn, chunk)
        conn.commit()
    return len(chunks)


def find_vector_dimension(sample_text: str) -> int:
    embedding = run_ollama_embed(sample_text)
    return len(embedding)


def main(args: argparse.Namespace) -> None:
    source_dir = Path(args.source_dir).expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"Répertoire introuvable : {source_dir}")

    files = find_text_files(source_dir)
    if not files:
        print(f"Aucun fichier texte trouvé dans {source_dir}")
        return

    print(f"Found {len(files)} text files in {source_dir}")

    sample_dim = find_vector_dimension(files[0].read_text(encoding="utf-8", errors="ignore")[:2000])
    print(f"Detected embedding dimension: {sample_dim}")

    conn = create_connection()
    ensure_database_table(conn, sample_dim)

    total_chunks = 0
    for text_file in files:
        total_chunks += process_file(text_file, source_dir, conn)

    conn.close()
    print(f"Import terminé : {total_chunks} chunks indexés dans PostgreSQL.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chunker, vectoriser et importer le corpus BEAC dans PostgreSQL + pgvector.")
    parser.add_argument(
        "--source-dir",
        default=Path(__file__).parent / "scraping" / "beac_text",
        help="Répertoire contenant les fichiers .txt à indexer.",
    )
    args = parser.parse_args()
    main(args)
