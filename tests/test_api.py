"""API smoke: health, text-scan end-to-end, history, trends, delete."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="billbhasha-test-")
os.environ["DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["LLM_PROVIDER"] = "heuristic"
os.environ["FAMILY_PIN"] = ""

import time  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from src.backend.main import app  # noqa: E402


def _client():
    return TestClient(app)


def test_health():
    with _client() as c:
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.json()["ok"] is True


def test_text_scan_flow():
    with _client() as c:
        r = c.post("/api/scan-text", json={"text": "BIJLI BILL\nTotal Rs. 420\nDue 10-09-2026"})
        assert r.status_code == 200, r.text
        doc_id = r.json()["id"]
        for _ in range(40):
            st = c.get(f"/api/scan/{doc_id}/status").json()
            if st["stage"] in ("done", "error"):
                break
            time.sleep(0.25)
        assert st["stage"] == "done", st
        res = c.get(f"/api/scan/{doc_id}").json()
        assert res["amount"] == 420
        assert "bijli" in res["explanation"]["summary_hi"].lower() or "bill" in res["explanation"]["summary_hi"].lower()

        hist = c.get("/api/history").json()
        assert any(h["id"] == doc_id for h in hist)
        trends = c.get("/api/trends").json()
        assert trends["count"] >= 1

        d = c.delete(f"/api/scan/{doc_id}").json()
        assert d["deleted"] is True
