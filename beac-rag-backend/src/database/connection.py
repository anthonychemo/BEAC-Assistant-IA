"""Connexion PostgreSQL via SQLAlchemy (pool volontairement modeste pour economiser la RAM)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

engine = create_engine(
    settings.database_url,
    # Releve de 3/2 a 5/5 : la recherche vectorielle (chat + bibliotheque)
    # peut desormais s'executer en concurrence sans saturer le pool, chaque
    # connexion restant tres legere en RAM par rapport au modele d'embedding.
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Session:
    """Retourne une session (a fermer manuellement)."""
    return SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Session transactionnelle: commit auto, rollback si erreur."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
