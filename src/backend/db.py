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


def get_session():
    return SessionLocal()
