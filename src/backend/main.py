"""BillBhasha API — one service serves the app + the AI pipeline.

Free-tier rules enforced: 6MB upload cap, single sequential pipeline,
stateless container (all persistence in SQLite locally / Neon in prod).
"""
from __future__ import annotations

import uuid
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import config
from .db import SessionLocal, init_db
from .models import Document
from .pipeline import runner
from .pipeline import tts as tts_stage
from .schemas import HistoryItem, ScanCreated, ScanResult, ScanStatus, SpeakIn

HERE = Path(__file__).resolve().parent
FRONTEND_DIR = HERE.parent / "frontend"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="BillBhasha", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- helpers ---------------------------------------------------------------
def _db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


def _need_pin(x_family_pin: str | None = Header(default=None, alias="X-Family-Pin")) -> None:
    if config.FAMILY_PIN and x_family_pin != config.FAMILY_PIN:
        raise HTTPException(status_code=401, detail="Parivar PIN galat hai")


def _doc_to_result(doc: Document) -> ScanResult:
    exp = doc.explanation or {}
    summary = str(exp.get("summary_hi", "")) if isinstance(exp, dict) else ""
    return ScanResult(
        id=doc.id,
        doc_type=doc.doc_type or "unknown",
        explanation=exp if isinstance(exp, dict) else {},
        anomaly=doc.anomaly,
        amount=doc.amount,
        currency=doc.currency or "INR",
        language=doc.language or "hi",
        has_audio=bool(doc.audio_ogg),
        created_at=doc.created_at.isoformat() if doc.created_at else None,
    )


# --- health / meta ---------------------------------------------------------
@app.get("/api/health")
def health():
    return {"ok": True, "app": config.APP_NAME}


@app.get("/api/ready")
def ready():
    """Friendly readiness for the PWA wake-up splash (cold starts)."""
    return {"ready": True, "message": "Namaste! Main taiyaar hoon."}


# --- scan flow -------------------------------------------------------------
@app.post("/api/scan", response_model=ScanCreated)
async def create_scan(background: BackgroundTasks,
                      image: UploadFile = File(...),
                      lang: str = Form(default="hi")):
    data = await image.read()
    limit = int(config.MAX_UPLOAD_MB * 1024 * 1024)
    if len(data) > limit:
        raise HTTPException(status_code=413, detail="Photo bahut badi hai (6MB tak).")
    if not (image.content_type or "").startswith(("image/",)):
        # Allow octet-stream from some phones, but reject obvious non-images.
        if image.content_type not in (None, "", "application/octet-stream"):
            raise HTTPException(status_code=415, detail="Kripya photo (JPG/PNG) bhejein.")
    doc_id = str(uuid.uuid4())
    s = SessionLocal()
    try:
        s.add(Document(id=doc_id, language=(lang or "hi")[:8], status="received"))
        s.commit()
    finally:
        s.close()
    background.add_task(runner.run_scan, doc_id, data, (lang or "hi")[:8], SessionLocal)
    return ScanCreated(id=doc_id)


@app.post("/api/scan-text", response_model=ScanCreated)
async def create_scan_text(background: BackgroundTasks, payload: dict):
    """Typed/pasted text path — works even with zero OCR on the box."""
    text = str(payload.get("text", ""))[:3000]
    lang = str(payload.get("lang", "hi"))[:8] or "hi"
    if not text.strip():
        raise HTTPException(status_code=400, detail="Kuch likhiye ya photo bhejiye.")
    doc_id = str(uuid.uuid4())
    s = SessionLocal()
    try:
        s.add(Document(id=doc_id, ocr_text=text, ocr_confidence=100.0,
                       language=lang, status="thinking"))
        s.commit()
    finally:
        s.close()

    async def _text_only():
        from .pipeline import anomaly as anomaly_stage
        from .pipeline import llm as llm_stage

        past: list[float] = []
        ss = SessionLocal()
        try:
            rows = (ss.query(Document.amount)
                    .filter(Document.amount.is_not(None), Document.status == "done")
                    .order_by(Document.created_at.desc()).limit(6).all())
            past = [float(r[0]) for r in rows if r[0] is not None]
        finally:
            ss.close()
        explanation, _ = await __import__("asyncio").to_thread(
            llm_stage.explain, text, anomaly_stage.build_history_hint(past, lang), lang)
        flag = anomaly_stage.detect(past, llm_stage._find_amount(text), lang)
        if flag:
            explanation["unusual_hi"] = flag
        audio = await __import__("asyncio").to_thread(
            tts_stage.synthesize,
            explanation.get("summary_hi", "") + " " +
            " ".join(explanation.get("key_points_hi", [])[:3]))
        ss = SessionLocal()
        try:
            doc = ss.get(Document, doc_id)
            if doc:
                doc.doc_type = str(explanation.get("doc_type", "unknown"))
                doc.explanation = explanation
                doc.anomaly = explanation.get("unusual_hi")
                try:
                    doc.amount = float(explanation["amount"]) if explanation.get("amount") is not None else None
                except (TypeError, ValueError):
                    doc.amount = None
                doc.audio_ogg = audio
                doc.status = "done"
                doc.stage_timings = {"mode": "text"}
                ss.commit()
        finally:
            ss.close()

    background.add_task(_text_only)
    return ScanCreated(id=doc_id)


@app.get("/api/scan/{doc_id}/status", response_model=ScanStatus)
def scan_status(doc_id: str, db=Depends(_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Nahi mila")
    return ScanStatus(id=doc.id, stage=doc.status or "received",
                      timings=doc.stage_timings or {})


@app.get("/api/scan/{doc_id}", response_model=ScanResult)
def scan_result(doc_id: str, db=Depends(_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Nahi mila")
    if doc.status == "error":
        raise HTTPException(status_code=500,
                            detail="Maaf kijiye, padhne mein dikkat aayi. Dobara koshish kijiye.")
    return _doc_to_result(doc)


@app.get("/api/scan/{doc_id}/audio")
def scan_audio(doc_id: str, db=Depends(_db)):
    doc = db.get(Document, doc_id)
    if not doc or not doc.audio_ogg:
        raise HTTPException(status_code=404, detail="Audio taiyaar nahi hai")
    return Response(content=bytes(doc.audio_ogg), media_type="audio/ogg",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.delete("/api/scan/{doc_id}")
def delete_scan(doc_id: str, db=Depends(_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Nahi mila")
    db.delete(doc)
    db.commit()
    return {"deleted": True}


# --- family views (PIN-gated only when FAMILY_PIN is set) ------------------
@app.get("/api/history", response_model=list[HistoryItem])
def history(limit: int = 30, db=Depends(_db), _pin: None = Depends(_need_pin)):
    limit = max(1, min(limit, 100))
    docs = (db.query(Document).filter(Document.status == "done")
            .order_by(Document.created_at.desc()).limit(limit).all())
    out: list[HistoryItem] = []
    for d in docs:
        exp = d.explanation or {}
        summary = str(exp.get("summary_hi", ""))[:140] if isinstance(exp, dict) else ""
        out.append(HistoryItem(id=d.id, doc_type=d.doc_type or "unknown",
                               amount=d.amount, anomaly=d.anomaly,
                               created_at=d.created_at.isoformat() if d.created_at else None,
                               summary=summary))
    return out


@app.get("/api/trends")
def trends(db=Depends(_db), _pin: None = Depends(_need_pin)):
    docs = (db.query(Document).filter(Document.status == "done",
                                      Document.amount.is_not(None))
            .order_by(Document.created_at.asc()).limit(500).all())
    by_month: dict[str, float] = {}
    by_type: dict[str, float] = {}
    for d in docs:
        key = d.created_at.strftime("%Y-%m") if d.created_at else "unknown"
        by_month[key] = round(by_month.get(key, 0) + float(d.amount or 0), 2)
        by_type[d.doc_type or "unknown"] = round(
            by_type.get(d.doc_type or "unknown", 0) + float(d.amount or 0), 2)
    return {"monthly": [{"month": k, "total": v} for k, v in sorted(by_month.items())],
            "by_type": by_type, "count": len(docs)}


@app.post("/api/speak")
async def speak(payload: SpeakIn):
    audio = await __import__("asyncio").to_thread(tts_stage.synthesize, payload.text)
    if not audio:
        # Browser will speak it instead — tell the app politely.
        return JSONResponse({"fallback": "browser", "message": "Browser awaaz mein suniye"}, status_code=200)
    return Response(content=audio, media_type="audio/ogg")


# --- frontend (single service serves the PWA) ------------------------------
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR)), name="assets")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/manifest.webmanifest")
    def manifest():
        p = FRONTEND_DIR / "manifest.webmanifest"
        return Response(content=p.read_bytes(), media_type="application/manifest+json")

    @app.get("/sw.js")
    def sw():
        p = FRONTEND_DIR / "sw.js"
        return Response(content=p.read_bytes(), media_type="application/javascript")
