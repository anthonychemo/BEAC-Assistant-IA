"""Affiche un resume des documents indexes dans la BD."""
from src.database.connection import session_scope
from src.database.schema import Document
from sqlalchemy import func

with session_scope() as s:
    total = s.query(func.count(Document.id)).scalar()
    print(f"Total documents: {total}\n")

    cats = (
        s.query(Document.category, func.count(Document.id))
        .group_by(Document.category)
        .order_by(func.count(Document.id).desc())
        .all()
    )
    print("Par categorie:")
    for cat, count in cats:
        print(f"  {cat or '(aucune)'}: {count}")

    print("\nEchantillon (10 premiers):")
    docs = s.query(Document.filename, Document.category, Document.year).limit(10).all()
    for fname, cat, year in docs:
        print(f"  [{year}] {fname} — {cat}")
