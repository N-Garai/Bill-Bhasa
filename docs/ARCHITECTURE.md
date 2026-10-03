# Architecture — why this shape fits a 512MB free box

```
phone (PWA) ──HTTPS──▶ Render web service: FastAPI serves / + /api/*
                              │  sequential asyncio.Lock pipeline
                              ▼
   clean (Pillow+numpy) → read (Tesseract subprocess) → understand
        (local GGUF → hosted open-weight → built-in helper)
     → remember (pure-Python history compare) → speak (Piper subprocess
        or browser voice fallback) ──▶ SQLite locally / Neon in prod
```

## The three decisions that matter

1. **One service, one URL.** FastAPI serves the static PWA and the API.
   No CORS, no second service, no extra bill.
2. **Subprocess isolation = the RAM strategy.** Tesseract and Piper spawn per
   request and exit — the OS reclaims their memory automatically. Only the
   small helper + web server stay resident (~120MB), so the box never OOMs.
   When the optional 360M GGUF model is baked in, it stays memory-mapped and
   peak still sits under ~470MB.
3. **Graceful degradation everywhere.** Every AI stage has a fallback that
   keeps Amma unblocked: OCR missing → typed-text path; local model missing →
   hosted open-weight → built-in Hindi helper (always works offline); server
   voice missing → the phone speaks with its own Hindi voice. The app is
   *useful on day one* and gets smarter as free keys/models are added.

## Data model

`documents(id, created_at, doc_type, image_bytes, ocr_text, ocr_confidence,
explanation JSON, anomaly, amount, currency, language, audio_ogg, status,
stage_timings)` + `settings(key, value)`.

Images are downscaled JPEGs (~200KB), audio is OGG (~60–150KB) — a year of
family papers fits in a few MB on the free database.

## API

`POST /api/scan` · `POST /api/scan-text` · `GET /api/scan/{id}/status` ·
`GET /api/scan/{id}` · `GET /api/scan/{id}/audio` · `GET /api/history` ·
`GET /api/trends` · `POST /api/speak` · `DELETE /api/scan/{id}` ·
`GET /api/health` · `GET /api/ready`
