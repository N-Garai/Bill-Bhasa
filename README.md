# BillBhasha — *Har kagaz, aapki bhasha mein.* / *Protek kagaj, apnar bhashay.*

Photo kheenchiye, kagaz ko apni bhasha mein **suniye**. Bijli bill, parcha,
raseed — sab seedhe-saral shabdon mein, bade buttonon ke saath. **Hindi aur
Bangla**, dono mein.

Two experiences in one installable app:

- **🏠 Saral / Sohaj** — one giant camera button. Photo → spoken explanation.
  Made for low-vision, Hindi/Bangla-first hands. Zero menus.
- **📚 Parivar / Poribar** — history cards, monthly spend chart, gentle spike
  warnings ("yeh ₹120 zyada hai") for the family member who looks after things.

Privacy-first: your papers stay yours. One-tap delete really deletes.

---

## Why this exists — the novelty (why not just Google Lens?)

Anyone can point Google Lens at a bill and get a translation. That solves a
*different* problem. BillBhasha is built for a person Lens leaves behind —
a 62-year-old with weak eyesight, no English, and nobody home at 11 AM when
the bills arrive. The differences are the whole product:

| Google Lens / Translate | BillBhasha |
|---|---|
| Returns **text to read** — useless if you can't read small print | Returns a **voice that speaks**: photograph → warm spoken Hindi/Bangla, replayable line by line |
| Translates words literally ("payable within due date") | **Explains like family**: "kul ₹540 likha hai, aakhri taareekh 12 tarikh hai, ghabraiye mat" |
| Forgets everything after you close it | **Remembers your history** and warns: "yeh ₹120 zyada hai pichhle mahine se" — a sudden tariff jump, a duplicate charge, a changed dosage |
| Your medical + financial photos go to a stranger's cloud | **Privacy by architecture**: runs in your own container + your own database; optional on-box model works with the network cable pulled |
| One generic interface for everyone | **Two personas, one URL**: a zero-menu giant-button screen for her, a full diary dashboard for the family |
| Confident even when the photo is blurry | **Honest when unsure**: low-confidence reads get a gentle "dobara photo lijiye" instead of a wrong answer |
| May paraphrase dosages freely | **Medical guardrails**: never suggests doses, never invents a number (every figure is traced to the photo's text), every medical result carries a "doctor/pharmacist se poochhein" note |

In one line: Lens *translates the paper*; BillBhasha **looks after the person
holding it** — month after month, in her language, out loud.

---

## Run locally (5 minutes, free forever)

**You need:** Python 3.11+ and nothing else. No Docker, no database server,
no API keys, no credit card. Tesseract/Piper/model files are all *optional* —
the app boots with its built-in explainer + your browser's voice.

```powershell
# 1. enter the project
cd Bill-Bhasa

# 2. (recommended) isolated environment
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. install — ~1 minute, ~120MB resident
pip install -r requirements.txt

# 4. start
py -m uvicorn src.backend.main:app --port 8000
```

Open **http://localhost:8000** 🌼

> No camera needed to try it — use the *"likh kar bhejiye / likhe pathan"*
> box with a sample from [`data/samples/README.md`](data/samples/README.md).
> Switch **हिंदी / বাংলা** on the Saral card anytime; it sticks.

**Useful commands:**

```powershell
pytest -q                                            # 13 tests: anomaly, explainer contract (HI+BN), API smoke
py -m uvicorn src.backend.main:app --port 8000 --reload   # dev loop
```

**Environment setup (all optional, all free):**

| Variable | Default | What it does |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/billbhasha.db` | SQLite locally, zero setup. In production set to Neon Postgres so history survives restarts |
| `LLM_PROVIDER` | `auto` | `auto` → local GGUF if present → Groq if key set → built-in helper. Force `local`, `groq`, or `heuristic` |
| `LLM_MODEL` | `/models/smollm2-360m-instruct-q4_k_m.gguf` | Any GGUF file — swap models without touching code |
| `GROQ_API_KEY` | *(empty)* | Free Groq key → bigger open-weight answer when the on-box helper is unsure |
| `TESS_LANG` | `eng+hin` | OCR languages; `+ben` auto-added when Bangla is selected (needs `ben.traineddata`, baked into Docker) |
| `PIPER_VOICE` | `/models/hi_IN-pratham-medium.onnx` | Server Hindi voice; browsers fall back to their own Hindi/Bangla voice |
| `FAMILY_PIN` | *(empty)* | Locks Parivar history/trends behind a family PIN |
| `MAX_UPLOAD_MB` | `6` | Upload cap (free-tier RAM discipline) |
| `DEFAULT_LANG` | `hi` | `hi` or `bn` |

---

## Architecture & system design

```
                    ┌─────────────────────────────────────────────────┐
                    │  ONE free-tier container (512MB) · ONE url      │
 phone (PWA) ─HTTPS─│  FastAPI serves  /  +  /api/*                  │
 photo / text ─────▶│                                                 │
                    │   sequential asyncio.Lock pipeline (never overlap)
                    │   ┌───────────────────────────────────────────┐ │
                    │   │ 1. CLEAN  Pillow+numpy: gray, contrast,    │ │
                    │   │           threshold, upscale (~40MB peak)  │ │
                    │   │ 2. READ   Tesseract 5 subprocess eng/hin/  │ │
                    │   │           ben — exits after call (~80MB)  │ │
                    │   │ 3. THINK  local GGUF (mmap, resident) →    │ │
                    │   │    Groq open-weight → built-in HI/BN       │ │
                    │   │    helper (strict JSON contract)           │ │
                    │   │ 4. MEMORY pure-Python compare vs last N     │ │
                    │   │    same-type docs → gentle HI/BN warning   │ │
                    │   │ 5. SPEAK  Piper subprocess → OGG, or       │ │
                    │   │    phone's own Hindi/Bangla voice          │ │
                    │   └───────────────────────────────────────────┘ │
                    └──────────────────────┬──────────────────────────┘
                                           │ SQLAlchemy
                                           ▼
                              SQLite file (local) / Neon Postgres
                              (free, permanent) — docs, OCR text,
                              explanation JSON, OGG bytes, amounts
```

**Design decisions that matter:**

1. **One service, one URL.** FastAPI serves the PWA and the API — no CORS,
   no second service, no extra bill. `GET /` → app, `/api/*` → pipeline,
   `/api/health` → Render health check, `/api/ready` → PWA wake-up splash.
2. **Subprocess isolation = the RAM strategy.** Tesseract and Piper spawn per
   request and *exit* — the OS reclaims their memory automatically. Only the
   web server + tiny helper stay resident (~120MB). With the optional 360M
   GGUF memory-mapped, peak still sits under ~470MB of the 512MB budget.
3. **Sequential lock.** Heavy stages never overlap (`asyncio.Lock`), so peak
   RAM = base + one subprocess. Slow but safe on a 0.1-CPU box.
4. **Graceful degradation everywhere.** Every AI stage has a fallback that
   keeps the user unblocked: OCR missing → typed-text path; local model
   missing → hosted open-weight → built-in Hindi/Bangla helper (always works
   offline); server voice missing → the phone speaks. Useful on day one,
   smarter as free keys/models are added.
5. **Strict JSON contract.** One prompt → one JSON object (`doc_type`,
   `summary`, `key_points`, `unusual`, `action`, `disclaimer`, `amount`,
   `date`). Temperature 0.3, ≤350 tokens — small enough for a 360M CPU model.
   A code guardrail drops any amount not found in the OCR text.
6. **Stateless container.** All persistence lives in SQLite/Neon; images are
   downscaled JPEGs (~200KB), audio is OGG (~60–150KB). A year of family
   papers fits in a few MB.

**API:** `POST /api/scan` · `POST /api/scan-text` · `GET /api/scan/{id}/status`
· `GET /api/scan/{id}` · `GET /api/scan/{id}/audio` · `GET /api/history`
· `GET /api/trends` · `POST /api/speak` · `DELETE /api/scan/{id}` ·
`GET /api/health` · `GET /api/ready`

---

## Open-source tech stack (100% free, no credit card)

| Layer | Choice | Licence | Why |
|---|---|---|---|
| OCR | **Tesseract 5** + `eng`/`hin`/`ben` data | Apache-2.0 | EasyOCR/PaddleOCR need PyTorch (800MB+) — impossible on 512MB |
| LLM (on-box) | **SmolLM2-360M-Instruct GGUF Q4_K_M** | Apache-2.0 | Best quality-per-MB for short JSON tasks on CPU; swap via `LLM_MODEL` |
| LLM runtime | **llama-cpp-python** | MIT | CPU GGUF inference with mmap |
| LLM fallback | **Groq free tier → Llama-3.3-70B** (open weights) | free key | Same open-weight family, bigger; text-only, never the photo |
| TTS (server) | **Piper** (`hi_IN` voice) | MIT | Open, CPU-fast Hindi voice |
| TTS (fallback) | **Web Speech API** (browser) | built-in | Phone's own Hindi/Bangla voice — zero server cost |
| Image prep | **Pillow + numpy** | HPND/BSD | No OpenCV (~30MB saved) |
| Backend | **FastAPI + SQLAlchemy + uvicorn** | MIT | One process serves app + API |
| Database | **SQLite** (local) / **Neon Postgres** (prod) | free | Neon free never expires (unlike Render's 30-day Postgres) |
| Frontend | **Vanilla JS + GSAP + Three.js** (CDN) | MIT | No framework tax on a 0.1-CPU-served page; <400KB payload |
| Hosting | **Render free tier** (Blueprint `render.yaml`) | free | Single Docker web service |

---

## Deploy free (Render + Neon, $0)

1. Create a free Postgres at [neon.tech](https://neon.tech) → copy the
   connection string.
2. Push this folder to GitHub, then **New → Blueprint** on Render pointing at
   `render.yaml`, and paste `DATABASE_URL` when asked.
3. Open your `https://billbhasha.onrender.com` — first visit wakes up in
   ~30–60s (the app shows a friendly wake-up splash meanwhile).

## Project layout

```
Bill-Bhasa/
├── src/
│   ├── backend/        # FastAPI + pipeline (preprocess/ocr/llm/anomaly/tts/runner)
│   └── frontend/       # PWA: Saral+Sohaj / Parivar, GSAP + Three.js, Web Speech
├── docs/               # architecture, privacy, handover, post draft
├── data/samples/       # try-it texts (no real personal data)
├── scripts/            # optional model/voice downloader (docker build only)
├── tests/              # pytest: anomaly, explainer contract (HI+BN), API smoke
├── Dockerfile render.yaml requirements.txt requirements-ml.txt
└── README.md
```

## Safety notes

- Explains papers; never advises medicine doses.
- Numbers are never invented — every figure is traced to the photo's text.
- Delete means delete (row + image + audio removed).

Made with care for family 🤍 — Apache-2.0, see [LICENSE](LICENSE).
