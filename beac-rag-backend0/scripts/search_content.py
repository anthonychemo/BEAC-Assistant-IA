"""Cherche un mot-cle dans les chunks indexes."""
from src.database.connection import session_scope
from src.database.schema import Chunk, Document
from sqlalchemy import or_

keywords = ["gouverneur", "Mahamat", "Gouverneur", "direction generale"]

with session_scope() as s:
    for kw in keywords:
        results = (
            s.query(Chunk.content, Document.filename)
            .join(Document, Chunk.document_id == Document.id)
            .filter(Chunk.content.ilike(f"%{kw}%"))
            .limit(3)
            .all()
        )
        print(f"\n--- Recherche: '{kw}' ({len(results)} resultats) ---")
        for content, fname in results:
            idx = content.lower().find(kw.lower())
            extract = content[max(0, idx-50):idx+150]
            print(f"  [{fname}] ...{extract}...")
