"""Second pair of eyes — Gemma 4 multimodal via Google AI Studio free API.

Used ONLY when on-box OCR comes back weak (too short/garbled) and a
GEMMA_API_KEY is set. We send the downscaled photo (never the original),
Gemma reads the layout like a person would (tables, totals, dates), and
returns our exact JSON contract — schema-locked via responseSchema so the
reply is always parseable — plus a "figures" transcript we persist as
ocr_text so the no-invented-numbers guardrail still holds. A free local
math audit (subtotal + tax == total) triggers one targeted re-read if the
model's own numbers don't add up.

Key from https://aistudio.google.com (free tier, no card). Model id via
GEMMA_VISION_MODEL, default gemma-4-26b-a4b-it (verified served on the
generateContent endpoint; gemma-4-31b-it is the failover).
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from .. import config
from ..prompts import _pick
from .llm import _extract_json, _guard_numbers

GEN_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "{model}:generateContent?key={key}")

# Model IDs verified as served on the generateContent endpoint
# (ai.google.dev/gemma/docs/core/gemma_on_gemini_api). On a 404 we retry
# with the next verified ID before giving up — IDs rot, answers shouldn't.
VERIFIED_MODELS = ("gemma-4-26b-a4b-it", "gemma-4-31b-it")

# Schema-locked JSON contract for Gemma 4. responseSchema + responseMimeType
# force the model to return parseable JSON with the exact fields we need.
_VISION_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_type": {"type": "string", "enum": [
            "electricity_bill", "water_bill", "gas_bill", "phone_bill",
            "medical_prescription", "medicine_strip", "receipt", "unknown"]},
        "summary_hi": {"type": "string"},
        "key_points_hi": {"type": "array", "items": {"type": "string"}},
        "unusual_hi": {"type": ["string", "null"]},
        "action_hi": {"type": "string"},
        "disclaimer_hi": {"type": ["string", "null"]},
        "amount": {"type": ["number", "null"]},
        "currency": {"type": "string"},
        "date": {"type": ["string", "null"]},
        "figures": {"type": "string"},
        "subtotal": {"type": ["number", "null"]},
        "gst_amount": {"type": ["number", "null"]},
    },
    "required": ["doc_type", "summary_hi", "key_points_hi", "action_hi",
                 "currency", "figures"],
}

# Short machine-readable reason for the last failure (never contains the key).
last_error: str = ""


def available() -> bool:
    return bool(config.GEMMA_API_KEY)


# Asked again with the strictest framing if the first answer has no JSON.
STRICT_TAIL = ("\n\nOne more time: reply with ONLY the raw JSON object. "
               "No FIGURES line, no prose, no code fences.")


def _figures_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip().upper().startswith("FIGURES:"):
            return line.split(":", 1)[1].strip()[:500]
    return ""


def _arithmetic_problem(parsed: dict) -> str:
    subtotal = parsed.get("subtotal")
    gst = parsed.get("gst_amount")
    total = parsed.get("amount")
    if subtotal is None or gst is None or total is None:
        return ""
    try:
        expected = round(float(subtotal) + float(gst), 2)
        actual = round(float(total), 2)
        if abs(expected - actual) > 0.02:
            return (f"The numbers don't add up: {expected} (subtotal {subtotal} + "
                    f"gst/tax {gst}) != total {actual}. Please re-read the paper "
                    f"carefully and correct subtotal, tax/gst, and total.")
    except (TypeError, ValueError):
        pass
    return ""


def _request_text(model: str, instruction: str, b64: str) -> tuple[str | None, str | None]:
    """One generateContent call. Returns (text, halt):

    text   — all text parts joined (models split replies across parts), or None
    halt   — None on success, 'stop' (don't retry) or 'next' (try next model id)
    """
    global last_error
    payload_str = json.dumps({
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        "contents": [{
            "parts": [
                {"text": instruction},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            ],
        }],
        "responseMimeType": "application/json",
        "responseSchema": _VISION_SCHEMA,
    })
    payload = payload_str.encode()
    url = GEN_URL.format(model=model, key=config.GEMMA_API_KEY)
    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # 400 = bad key, 404 = unknown model id, 429 = free-tier limit
        last_error = f"http-{e.code}:{model}"
        return None, ("next" if e.code == 404 else "stop")
    except TimeoutError:
        last_error = "timeout"
        return None, "stop"
    except Exception:
        last_error = "request-failed"
        return None, "stop"
    try:
        parts = body["candidates"][0]["content"]["parts"]
    except Exception:
        last_error = f"blocked-or-empty:{model}"
        return None, "next"
    text = "".join(str(p.get("text", "")) for p in parts
                   if isinstance(p, dict) and p.get("text"))
    if not text.strip():
        last_error = f"empty-response:{model}"
        return None, "next"
    return text, None


def explain_image(jpeg_bytes: bytes, lang: str = "hi") -> tuple[dict, str] | None:
    """Return (explanation-json, figures-transcript) or None. Never raises."""
    global last_error
    last_error = ""
    if not jpeg_bytes:
        last_error = "empty-image"
        return None
    if not available():
        last_error = "no-key"
        return None
    try:
        lang = (lang or "hi")[:2]
        name = {"bn": "Bangla", "hi": "Hindi", "en": "English"}.get(lang, "Hindi")
        b64 = base64.b64encode(jpeg_bytes).decode()
        instruction = (
            _pick(lang)
            + "\n\nYou are given a PHOTO of the paper (not OCR text). Read it like a person "
              "would: EVERY line item, quantity, unit price, amount, subtotal, tax, total, "
              "date, name and reference number — do not skip anything, including tables. "
              f"Reply with ONLY a JSON object, ALL text fields in {name}, "
              f"'figures' filled with every number/date you actually see."
        )
        models = [config.GEMMA_VISION_MODEL] + [
            m for m in VERIFIED_MODELS if m != config.GEMMA_VISION_MODEL]
        for model in models:
            # First attempt
            text, halt = _request_text(model, instruction, b64)
            if halt == "stop":
                return None
            if halt == "next":
                break
            parsed = _extract_json(text)
            if isinstance(parsed, dict):
                figures = str(parsed.get("figures", ""))[:500]
                guarded = _guard_numbers(parsed, figures or json.dumps(parsed))
                problem = _arithmetic_problem(guarded)
                if problem:
                    text2, halt2 = _request_text(
                        model, instruction + "\n\n" + problem, b64)
                    if halt2 == "stop":
                        return None
                    if halt2 != "next":
                        parsed2 = _extract_json(text2)
                        if isinstance(parsed2, dict):
                            figures2 = str(parsed2.get("figures", ""))[:500]
                            guarded2 = _guard_numbers(parsed2, figures2 or json.dumps(parsed2))
                            if not _arithmetic_problem(guarded2):
                                return guarded2, figures2
                return guarded, figures
            # Strict retry on same model
            text, halt = _request_text(model, instruction + STRICT_TAIL, b64)
            if halt == "stop":
                return None
            if halt == "next":
                break
            parsed = _extract_json(text)
            if isinstance(parsed, dict):
                figures = str(parsed.get("figures", ""))[:500]
                guarded = _guard_numbers(parsed, figures or json.dumps(parsed))
                problem = _arithmetic_problem(guarded)
                if problem:
                    text2, halt2 = _request_text(
                        model, instruction + "\n\n" + problem, b64)
                    if halt2 == "stop":
                        return None
                    if halt2 != "next":
                        parsed2 = _extract_json(text2)
                        if isinstance(parsed2, dict):
                            figures2 = str(parsed2.get("figures", ""))[:500]
                            guarded2 = _guard_numbers(parsed2, figures2 or json.dumps(parsed2))
                            if not _arithmetic_problem(guarded2):
                                return guarded2, figures2
                return guarded, figures
            last_error = f"no-json:{model}"
        return None
    except Exception:
        last_error = "request-failed"
        return None
