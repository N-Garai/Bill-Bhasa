"""Database engine + session helpers.

SQLite locally (zero setup), Postgres (Neon) when DATABASE_URL points
there. SQLAlchemy sync engine is enough for a single-worker free-tier
service — keeps the dependency tree tiny.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # Postgres / Neon needs SSL + small pool for the free tier.
    return {"pool_size": 2, "max_overflow": 2, "pool_pre_ping": True,
            "connect_args": {"sslmode": "require", "connect_timeout": 10}}


class Base(DeclarativeBase):
    pass


engine = create_engine(config.DATABASE_URL, **_engine_kwargs(config.DATABASE_URL))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """Lightweight additive migration for DBs created by older versions."""
    from sqlalchemy import inspect, text

    try:
        insp = inspect(engine)
        if "documents" in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns("documents")}
            if "family_code" not in cols:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN family_code VARCHAR(24) DEFAULT 'default'"))
    except Exception:
        pass  # fresh create_all above already covers new installs


def get_session():
    return SessionLocal()
