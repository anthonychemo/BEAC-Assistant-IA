"""Vide toutes les donnees de la BD (garde le schema et les index)."""
from src.database.connection import session_scope
from sqlalchemy import text

with session_scope() as s:
    s.execute(text("TRUNCATE TABLE chunks, statistics, documents RESTART IDENTITY CASCADE"))
    s.commit()
    print("Tables videes avec succes.")
