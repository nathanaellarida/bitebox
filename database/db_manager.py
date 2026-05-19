"""Database connection manager and initialization."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import DB_PATH
from database.models import Base

_engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables, apply additive migrations, then run seed data on first run."""
    Base.metadata.create_all(_engine)
    _apply_additive_migrations()
    from database.seed_data import run_seed
    run_seed()


def _apply_additive_migrations() -> None:
    """SQLite-safe migrations that add new columns without breaking existing data."""
    from sqlalchemy import text
    additions = [
        ("customers", "password_hash", "VARCHAR(255)"),
        ("customers", "is_active", "BOOLEAN DEFAULT 1"),
        ("customers", "street", "VARCHAR(200)"),
        ("customers", "city", "VARCHAR(100)"),
        ("customers", "province", "VARCHAR(100)"),
        ("customers", "postal_code", "VARCHAR(20)"),
        ("customers", "landmark", "VARCHAR(200)"),
    ]
    with _engine.begin() as conn:
        for table, col, ddl in additions:
            existing = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            cols = {row[1] for row in existing}
            if col not in cols:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Session:
    """Return a raw session (caller must close)."""
    return _SessionLocal()
