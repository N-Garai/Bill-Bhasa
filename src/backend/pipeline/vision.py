"""Second pair of eyes — Gemma 3 multimodal via Google AI Studio free API.

Used ONLY when on-box OCR comes back weak (too short/garbled) and a
GEMMA_API_KEY is set. We send the downscaled photo (never the original),
Gemma reads the layout like a person would (tables, totals, dates), and
returns our exact JSON contract plus a figures transcript we persist as
ocr_text so the no-invented-numbers guardrail still holds.

Key from https://aistudio.google.com (free tier, no card). Model id via
GEMMA_VISION_MODEL, default gemma-3-4b-it.
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


def _request_text(model: str, instruction: str, b64: str) -> tuple[str | None, str | None]:
    """One generateContent call. Returns (text, halt):

    text   — all text parts joined (models split replies across parts), or None
    halt   — None on success, 'stop' (don't retry) or 'next' (try next model id)
    """
    global last_error
    payload = json.dumps({
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        "contents": [{
            "parts": [
                {"text": instruction},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
            ],
        }],
    }).encode()
    url = GEN_URL.format(model=model, key=config.GEMMA_API_KEY)
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
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
        b64 = base64.b64encode(jpeg_bytes).decode()
        instruction = (
            _pick(lang)
            + "\n\nYou are given a PHOTO of the paper (not OCR text). "
              "Read it directly, including tables and totals. First write one line: "
              "FIGURES: <comma-separated numbers and dates you actually see>. "
              "Then the JSON object, nothing else."
        )
        models = [config.GEMMA_VISION_MODEL] + [
            m for m in VERIFIED_MODELS if m != config.GEMMA_VISION_MODEL]
        for model in models:
            transcript = ""
            for attempt in (instruction, instruction + STRICT_TAIL):
                text, halt = _request_text(model, attempt, b64)
                if halt == "stop":
                    return None
                if halt == "next":
                    break  # answer was unusable/blocked — next attempt or model
                parsed = _extract_json(text)
                if isinstance(parsed, dict):
                    transcript = _figures_line(text)
                    guarded = _guard_numbers(parsed, transcript or json.dumps(parsed))
                    return guarded, transcript
            # It answered, just not in JSON — try the next verified model id.
            last_error = f"no-json:{model}"
        return None
    except Exception:
        last_error = "request-failed"
        return None
