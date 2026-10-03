"""Runner failure path: errors land with stage + message, never hang."""
import asyncio
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="billbhasha-runner-")
os.environ["DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/runner.db"
os.environ["LLM_PROVIDER"] = "heuristic"

from src.backend.db import SessionLocal, init_db  # noqa: E402
from src.backend.models import Document  # noqa: E402
from src.backend.pipeline import runner  # noqa: E402

init_db()


def test_pipeline_error_records_stage_and_message():
    s = SessionLocal()
    s.add(Document(id="boom", status="received"))
    s.commit()
    s.close()
    asyncio.run(runner.run_scan("boom", b"garbage-bytes-not-an-image", "en", SessionLocal))
    s = SessionLocal()
    doc = s.get(Document, "boom")
    assert doc.status == "error"
    assert doc.stage_timings.get("failed_at") == "cleaning"
    assert doc.stage_timings.get("error")
    s.close()
