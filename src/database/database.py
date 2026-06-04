"""Database engine, session factory, and initialisation helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base

# Default DB file location (relative to project root).
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "smartphones.db"

_DATABASE_URL: str | None = None
_engine = None
SessionLocal: sessionmaker[Session] | None = None  # type: ignore[type-arg]


def _get_database_url() -> str:
    global _DATABASE_URL
    if _DATABASE_URL is not None:
        return _DATABASE_URL
    db_path = os.getenv("DATABASE_PATH", str(_DEFAULT_DB_PATH))
    _DATABASE_URL = f"sqlite:///{db_path}"
    return _DATABASE_URL


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    url = _get_database_url()
    # Ensure the parent directory exists.
    if url.startswith("sqlite:///"):
        db_file = Path(url.replace("sqlite:///", ""))
        db_file.parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(url, connect_args={"check_same_thread": False}, echo=False)
    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    global SessionLocal
    if SessionLocal is not None:
        return SessionLocal
    engine = _get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def init_db() -> None:
    """Create all tables (idempotent)."""
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    factory = _get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def reset_for_testing(database_url: str = "sqlite:///:memory:") -> None:
    """Reset engine/session for unit tests (in-memory DB)."""
    global _DATABASE_URL, _engine, SessionLocal
    _DATABASE_URL = database_url
    _engine = None
    SessionLocal = None
    init_db()


__all__ = ["get_db", "init_db", "SessionLocal", "reset_for_testing"]
