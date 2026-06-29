"""Connexion PostgreSQL via SQLAlchemy (pool reduit pour economiser la RAM)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings

engine = create_engine(
    settings.database_url,
    pool_size=3,
    max_overflow=2,
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
