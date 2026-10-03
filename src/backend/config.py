"""Central configuration — every behaviour swaps via env vars, no code edits.

Free-tier discipline lives here: single worker, upload caps, tiny LLM
context, subprocess-only heavy tools.
"""
from __future__ import annotations

import os
from pathlib import Path


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


# --- paths ---------------------------------------------------------------
# src/backend/config.py -> repo root is parents[2]
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
DATA_DIR = Path(_get("DATA_DIR", str(ROOT / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = DATA_DIR / "billbhasha.db"

# --- database ------------------------------------------------------------
# Local default: SQLite file. Production: set DATABASE_URL to Neon Postgres.
DATABASE_URL = _get("DATABASE_URL", f"sqlite:///{DB_FILE}")

# --- AI providers --------------------------------------------------------
# auto = local GGUF if present -> Groq if key set -> built-in helper.
LLM_PROVIDER = _get("LLM_PROVIDER", "auto").lower() or "auto"
LLM_MODEL = _get("LLM_MODEL", "/models/smollm2-360m-instruct-q4_k_m.gguf")
LLM_FALLBACK_MODEL = _get("LLM_FALLBACK_MODEL", "llama-3.3-70b-versatile")
N_CTX = int(_get("N_CTX", "1024") or 1024)
N_THREADS = int(_get("N_THREADS", "1") or 1)
GROQ_API_KEY = _get("GROQ_API_KEY", "")

# --- OCR -----------------------------------------------------------------
TESS_LANG = _get("TESS_LANG", "eng+hin")
TESS_CMD = _get("TESSERACT_CMD", "tesseract")

# --- Voice ---------------------------------------------------------------
PIPER_BIN = _get("PIPER_BIN", "piper")
PIPER_VOICE = _get("PIPER_VOICE", "/models/hi_IN-pratham-medium.onnx")
DEFAULT_LANG = _get("DEFAULT_LANG", "hi")

# --- App guardrails ------------------------------------------------------
FAMILY_PIN = _get("FAMILY_PIN", "")
MAX_UPLOAD_MB = float(_get("MAX_UPLOAD_MB", "6") or 6)
MAX_IMAGE_PX = int(_get("MAX_IMAGE_PX", "1280") or 1280)
WEB_CONCURRENCY = int(_get("WEB_CONCURRENCY", "1") or 1)

APP_NAME = "BillBhasha"
TAGLINE_HI = "Har kagaz, aapki bhasha mein."
