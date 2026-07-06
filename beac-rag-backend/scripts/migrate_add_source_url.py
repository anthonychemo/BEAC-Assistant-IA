"""Ajoute la colonne source_url a la table documents si elle n'existe pas."""
from src.database.connection import session_scope
from sqlalchemy import text

with session_scope() as s:
    s.execute(text("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS source_url TEXT;
    """))
    s.commit()
    print("Colonne source_url ajoutee avec succes.")
