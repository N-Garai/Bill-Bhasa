# DEV post draft (fill after handover — maps 1:1 to the submission template)

> Keep this file as your writing checklist; publish the final post on DEV
> with the required tags.

## What I Built
BillBhasha for **my mother (62, Hindi-first, low vision)**: she photographs
any bill/parcha/raseed and hears it explained in warm spoken Hindi, with a
gentle warning when an amount jumps vs. her own history. [Her verbatim quote
 + reaction clip go HERE — first paragraph.]

## Demo
- Live link: https://billbhasha.onrender.com (first visit ~40s wake-up)
- 90-sec GIF: scan → spoken Hindi → ₹120 spike flag

## Code
- Repo: <github link> · stack: FastAPI + Tesseract + SmolLM2-360M (GGUF,
  Apache-2.0) + Piper Hindi voice + Neon; frontend vanilla + GSAP + Three.js

## How I Built It
Open AI at the core three ways: open-weight model (SmolLM2-360M, swappable to
Qwen2.5-0.5B via `LLM_MODEL`), open harness (llama.cpp + FastAPI), local
inference inside our own container. Subprocess isolation + sequential lock =
full pipeline under 512MB (table + soak numbers here). Model-swap clip +
offline `docker compose` note.

## Why Does Open Innovation Matter?
Her prescriptions never touch a closed server; runs with the cable pulled
(SQLite profile); swap models/voices via env vars; $0/month receipt
(Render $0 + Neon $0 + weights $0). What failed: Phi-3 OOM, EasyOCR eviction,
Render Postgres 30-day trap → Neon.

## Prize Categories
Best Use of Render (one free web service hosts app + AI runtime).
