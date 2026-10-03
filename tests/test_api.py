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


def _wait_done(c, doc_id, code=None):
    headers = {"X-Family-Code": code} if code else {}
    for _ in range(40):
        st = c.get(f"/api/scan/{doc_id}/status", headers=headers).json()
        if st["stage"] in ("done", "error"):
            return st
        time.sleep(0.25)
    raise AssertionError("scan never finished")


def test_family_spaces_are_isolated():
    with _client() as c:
        code_a = c.post("/api/family/ensure", json={}).json()["code"]
        code_b = c.post("/api/family/ensure", json={}).json()["code"]
        assert code_a != code_b

        def scan_as(code, text):
            r = c.post("/api/scan-text", json={"text": text},
                       headers={"X-Family-Code": code})
            assert r.status_code == 200, r.text
            return r.json()["id"]

        id_a = scan_as(code_a, "POWER BILL\nTotal Rs. 700")
        _wait_done(c, id_a, code_a)

        ha = c.get("/api/history", headers={"X-Family-Code": code_a}).json()
        hb = c.get("/api/history", headers={"X-Family-Code": code_b}).json()
        assert any(h["id"] == id_a for h in ha)
        assert not any(h["id"] == id_a for h in hb)

        # cross-family read by id is hidden
        r = c.get(f"/api/scan/{id_a}", headers={"X-Family-Code": code_b})
        assert r.status_code == 404


def test_family_pin_locks_space():
    with _client() as c:
        code = c.post("/api/family/ensure", json={}).json()["code"]
        r = c.post("/api/family/pin",
                   json={"code": code, "pin": "", "new_pin": "4821"})
        assert r.status_code == 200, r.text
        locked = c.get("/api/history", headers={"X-Family-Code": code})
        assert locked.status_code == 401
        open_ = c.get("/api/history",
                      headers={"X-Family-Code": code, "X-Family-Pin": "4821"})
        assert open_.status_code == 200
