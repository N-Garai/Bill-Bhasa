"""Sequential pipeline runner — one scan at a time (the RAM promise).

Stages: received -> cleaning -> reading -> thinking -> speaking -> done.
Timings are recorded honestly and shown in the app.
"""
from __future__ import annotations

import asyncio
import time

from sqlalchemy.orm import Session

from .. import config
from ..models import Document
from . import anomaly as anomaly_stage
from . import llm as llm_stage
from . import ocr as ocr_stage
from . import tts as tts_stage
from . import vision as vision_stage
from .preprocess import load_and_prepare

_lock = asyncio.Lock()


async def run_scan(doc_id: str, raw_image: bytes, lang: str, session_factory,
                 family_code: str = "default") -> None:
    async with _lock:  # never overlap heavy stages on 512MB
        timings: dict = {}
        t_all = time.perf_counter()
        phase = "starting"
        try:
            phase = "cleaning"
            _set(doc_id, session_factory, status="cleaning")
            t0 = time.perf_counter()
            prep = await asyncio.to_thread(
                load_and_prepare, raw_image, config.MAX_IMAGE_PX)
            if len(prep) == 3:
                prepared, gray_retry, small_jpg = prep
            else:  # tolerate an older image build
                prepared, small_jpg = prep
                gray_retry = None
            timings["cleaning"] = round(time.perf_counter() - t0, 2)
            phase = "reading"
            _set(doc_id, session_factory, status="reading")

            t0 = time.perf_counter()
            ocr_text, conf = await asyncio.to_thread(
                ocr_stage.run_ocr, prepared, gray_retry, lang)
            timings["reading"] = round(time.perf_counter() - t0, 2)
            _save(doc_id, session_factory, image_bytes=small_jpg,
                  ocr_text=ocr_text, ocr_confidence=conf, status="thinking")

            past = _past_amounts(doc_id, session_factory, family_code, limit=6)
            hint = anomaly_stage.build_history_hint(past, lang)

            phase = "thinking"
            t0 = time.perf_counter()
            vis = None
            if len(ocr_text.strip()) < config.VISION_MIN_CHARS:
                if vision_stage.available():
                    # On-box eyes failed — borrow Gemma's (photo only, free API).
                    vis = await asyncio.to_thread(
                        vision_stage.explain_image, small_jpg, lang)
                    if vis is None:
                        timings["vision_error"] = vision_stage.last_error or "failed"
                else:
                    timings["vision"] = "no-key"
            if vis is not None:
                explanation, transcript = vis
                if transcript:
                    ocr_text, conf = transcript, max(conf, 85.0)
                timings["thinking"] = round(time.perf_counter() - t0, 2)
                timings["vision"] = True
            else:
                explanation, _provider = await asyncio.to_thread(
                    llm_stage.explain, ocr_text, hint, lang)
                timings["thinking"] = round(time.perf_counter() - t0, 2)
            timings["ocr_chars"] = len(ocr_text.strip())

            # Anomaly compares against same-type history once type is known.
            past_typed = _past_amounts(doc_id, session_factory, family_code, limit=6,
                                       doc_type=explanation.get("doc_type"))
            flag = anomaly_stage.detect(past_typed or past,
                                        _as_float(explanation.get("amount")), lang)
            if flag:
                explanation["unusual_hi"] = flag
            phase = "speaking"
            _set(doc_id, session_factory, status="speaking")

            t0 = time.perf_counter()
            # Speech input: native-script twin when the helper built one,
            # else the display text; anomaly appended in native script too.
            speech = str(explanation.get("speech_text") or (
                str(explanation.get("summary_hi", "")) + " " +
                " ".join(explanation.get("key_points_hi", [])[:3]))).strip()
            if explanation.get("unusual_hi"):
                flag_native = anomaly_stage.detect(
                    past_typed or past,
                    _as_float(explanation.get("amount")), lang, native=True)
                speech += " " + str(flag_native or explanation["unusual_hi"])
            audio = await asyncio.to_thread(tts_stage.synthesize, speech, lang)
            timings["speaking"] = round(time.perf_counter() - t0, 2)

            timings["total"] = round(time.perf_counter() - t_all, 2)
            _save(doc_id, session_factory,
                  doc_type=str(explanation.get("doc_type", "unknown")),
                  explanation=explanation, anomaly=explanation.get("unusual_hi"),
                  amount=_as_float(explanation.get("amount")),
                  currency=str(explanation.get("currency", "INR") or "INR"),
                  language=lang or config.DEFAULT_LANG,
                  audio_ogg=audio, status="done", stage_timings=timings,
                  ocr_text=ocr_text, ocr_confidence=conf)
        except Exception as exc:  # honest failure, friendly message downstream
            timings["failed_at"] = phase
            _save(doc_id, session_factory, status="error",
                  stage_timings={**timings, "total": round(time.perf_counter() - t_all, 2),
                                 "error": str(exc)[:300]})


def _session(session_factory) -> Session:
    return session_factory()


def _set(doc_id: str, session_factory, status: str) -> None:
    s = _session(session_factory)
    try:
        doc = s.get(Document, doc_id)
        if doc:
            doc.status = status
            s.commit()
    finally:
        s.close()


def _save(doc_id: str, session_factory, **fields) -> None:
    s = _session(session_factory)
    try:
        doc = s.get(Document, doc_id)
        if doc:
            for k, v in fields.items():
                setattr(doc, k, v)
            s.commit()
    finally:
        s.close()


def _past_amounts(doc_id: str, session_factory, family_code: str = "default",
                  limit: int = 6, doc_type: str | None = None) -> list[float]:
    s = _session(session_factory)
    try:
        q = (s.query(Document.amount)
             .filter(Document.id != doc_id,
                     Document.family_code == family_code,
                     Document.amount.is_not(None),
                     Document.status == "done")
             .order_by(Document.created_at.desc()))
        if doc_type and doc_type != "unknown":
            q = q.filter(Document.doc_type == doc_type)
        rows = q.limit(limit).all()
        return [float(r[0]) for r in rows if r[0] is not None]
    finally:
        s.close()


def _as_float(v) -> float | None:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None
