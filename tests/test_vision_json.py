"""Vision JSON handling: multi-part replies, model failover, truncated JSON."""
import json as _json

from src.backend import config
from src.backend.pipeline import llm, vision


class _Resp:
    def __init__(self, body):
        self._body = _json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._body


def _body(*parts_text):
    return {"candidates": [{"content": {"parts": [
        {"text": t} for t in parts_text]}}]}


def _fake_urlopen(monkeypatch, bodies):
    calls = []

    def _urlopen(req, timeout=None):
        model = req.full_url.split("/models/")[1].split(":")[0]
        calls.append(model)
        body = bodies.pop(0)
        if isinstance(body, Exception):
            raise body
        return _Resp(body)

    monkeypatch.setattr(vision.urllib.request, "urlopen", _urlopen)
    return calls


def _on(monkeypatch):
    monkeypatch.setattr(config, "GEMMA_API_KEY", "test-key")


def test_vision_joins_split_text_parts(monkeypatch):
    _on(monkeypatch)
    bodies = [_body("FIGURES: TOTAL 13,715.52, 28/04/2019\n",
                    '{"doc_type": "receipt", "amount": 13715.52, '
                    '"currency": "INR", "figures": "13,715.52, 28/04/2019"}')]
    _fake_urlopen(monkeypatch, bodies)
    out, transcript = vision.explain_image(b"\xff\xd8fakejpeg", "en")
    assert out is not None and out["doc_type"] == "receipt"
    assert out["amount"] == 13715.52
    assert "13,715.52" in transcript


def test_vision_retries_strict_prompt_then_next_model(monkeypatch):
    _on(monkeypatch)
    bodies = [
        _body("Here is what I read... but no JSON at all."),
        _body("Sorry, I mean it: {not json}"),
        _body("FIGURES: 540\n", '{"doc_type": "electricity_bill", "amount": 540, '
                                 '"currency": "INR", "figures": "540"}'),
    ]
    calls = _fake_urlopen(monkeypatch, bodies)
    out, _ = vision.explain_image(b"\xff\xd8fakejpeg", "en")
    assert out is not None and out["amount"] == 540
    assert len(calls) == 3  # two attempts on first model, then second model


def test_vision_bad_key_stops_not_spins(monkeypatch):
    import urllib.error

    _on(monkeypatch)
    bodies = [urllib.error.HTTPError("u", 400, "bad key", None, None)]
    calls = _fake_urlopen(monkeypatch, bodies)
    assert vision.explain_image(b"\xff\xd8fakejpeg") is None
    assert len(calls) == 1
    assert "http-400" in vision.last_error


def test_extract_json_salvages_truncated_object():
    cut = 'FIGURES: 540\n{"doc_type": "electricity_bill", "amount": 54'
    out = llm._extract_json(cut)
    assert out is not None
    assert out["doc_type"] == "electricity_bill"
    assert out["amount"] == 54
    assert llm._extract_json("no braces here") is None


def test_extract_json_still_prefers_complete_span():
    blob = '{"doc_type": "receipt", "amount": 13715.52}'
    assert llm._extract_json(blob) == {"doc_type": "receipt", "amount": 13715.52}


# --- arithmetic audit -------------------------------------------------------
class TestArithmeticProblem:
    def test_no_issue(self):
        assert vision._arithmetic_problem(
            {"amount": 118, "subtotal": 100, "gst_amount": 18}) == ""

    def test_mismatch(self):
        result = vision._arithmetic_problem(
            {"amount": 150, "subtotal": 100, "gst_amount": 18})
        assert "don't add up" in result
        assert "118" in result
        assert "150" in result

    def test_missing_fields(self):
        assert vision._arithmetic_problem({"amount": 118}) == ""
        assert vision._arithmetic_problem({}) == ""

    def test_non_numeric(self):
        assert vision._arithmetic_problem(
            {"amount": "x", "subtotal": 100, "gst_amount": 18}) == ""


# --- schema + conditional re-read -------------------------------------------
def test_vision_payload_includes_schema(monkeypatch):
    _on(monkeypatch)
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["payload"] = _json.loads(req.data.decode())
        return _Resp({"candidates": [{"content": {"parts": [
            {"text": '{"doc_type": "receipt", "summary_hi": "x", '
                     '"key_points_hi": [], "action_hi": "x", '
                     '"currency": "INR", "figures": ""}'}]}}]})

    monkeypatch.setattr(vision.urllib.request, "urlopen", fake_urlopen)
    result = vision.explain_image(b"\xff\xd8fakejpeg", "en")
    print("RESULT:", result, "LAST_ERROR:", repr(vision.last_error), "CAPTURED:", list(captured.keys()))
    assert "payload" in captured, f"fake_urlopen was not called; last_error={vision.last_error!r}"
    assert captured["payload"]["responseMimeType"] == "application/json"
    assert "responseSchema" in captured["payload"]
    req = captured["payload"]["responseSchema"]["required"]
    assert "doc_type" in req
    assert "figures" in req


def test_vision_no_reread_when_math_ok(monkeypatch):
    _on(monkeypatch)
    bodies = [_body(
        '{"doc_type": "receipt", "summary_hi": "x", '
        '"key_points_hi": [], "action_hi": "x", "currency": "INR", '
        '"figures": "118", "amount": 118, "subtotal": 100, "gst_amount": 18}')]
    calls = _fake_urlopen(monkeypatch, bodies)
    out, _ = vision.explain_image(b"\xff\xd8fakejpeg", "en")
    assert out is not None and out["amount"] == 118
    assert len(calls) == 1


def test_vision_audit_triggers_reread(monkeypatch):
    _on(monkeypatch)
    bodies = [
        _body('{"doc_type": "receipt", "summary_hi": "x", '
              '"key_points_hi": [], "action_hi": "x", "currency": "INR", '
              '"figures": "150", "amount": 150, "subtotal": 100, "gst_amount": 18}'),
        _body('{"doc_type": "receipt", "summary_hi": "x", '
              '"key_points_hi": [], "action_hi": "x", "currency": "INR", '
              '"figures": "118", "amount": 118, "subtotal": 100, "gst_amount": 18}'),
    ]
    calls = _fake_urlopen(monkeypatch, bodies)
    out, _ = vision.explain_image(b"\xff\xd8fakejpeg", "en")
    assert out is not None and out["amount"] == 118
    assert len(calls) == 2
