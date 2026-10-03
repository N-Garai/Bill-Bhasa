"""Pydantic response shapes — keeps the API contract stable."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ScanCreated(BaseModel):
    id: str
    status: str = "received"


class ScanStatus(BaseModel):
    id: str
    stage: str
    timings: dict = Field(default_factory=dict)


class ScanResult(BaseModel):
    id: str
    doc_type: str = "unknown"
    explanation: dict = Field(default_factory=dict)
    anomaly: Optional[str] = None
    amount: Optional[float] = None
    currency: str = "INR"
    language: str = "hi"
    has_audio: bool = False
    created_at: Any = None
    ocr_confidence: float = 0.0
    ocr_preview: str = ""  # first ~280 chars of what OCR/vision read
    stage_timings: dict = Field(default_factory=dict)  # incl. vision/vision_error


class HistoryItem(BaseModel):
    id: str
    doc_type: str
    amount: Optional[float] = None
    anomaly: Optional[str] = None
    created_at: Any = None
    summary: str = ""


class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=1200)
    lang: str = "hi"
