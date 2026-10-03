"""Neon/Postgres + SQLite compatible tables."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    family_code: Mapped[str] = mapped_column(String(24), default="default", index=True)
    doc_type: Mapped[str] = mapped_column(String(64), default="unknown")
    image_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)
    anomaly: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    language: Mapped[str] = mapped_column(String(8), default="hi")
    audio_ogg: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="received")
    stage_timings: Mapped[dict] = mapped_column(JSON, default=dict)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class Family(Base):
    """One private space per visitor/family: own history, own PIN.

    Visitors who never set anything share the open "default" space only if
    they never received a personal code — the app assigns one per browser,
    so strangers are isolated by default. Relatives join by entering the
    same code (+ PIN if the owner set one).
    """

    __tablename__ = "families"

    code: Mapped[str] = mapped_column(String(24), primary_key=True)
    pin_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pin_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
