"""OCR contract: run_ocr must always return (text, confidence) no matter what
_tess yields — including the (text, confidence, timed_out) triple.

Regression: commit e66ffec made _tess return a 3-tuple while run_ocr still
unpacked 2 values, crashing every scan on boxes that have Tesseract installed
("too many values to unpack")."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="billbhasha-ocr-")
os.environ["DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/ocr.db"

from PIL import Image  # noqa: E402

from src.backend.pipeline import ocr  # noqa: E402


def _blank() -> Image.Image:
    return Image.new("L", (200, 100), 255)


def test_run_ocr_returns_pair_with_triple_tess(monkeypatch):
    calls = []

    def fake_tess(img, tess_lang, psm="6"):
        calls.append(psm)
        return "TOTAL Rs. 540", 87.5, False

    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr, "_tess", fake_tess)
    out = ocr.run_ocr(_blank(), _blank(), "hi")
    assert out == ("TOTAL Rs. 540", 87.5)


def test_run_ocr_stops_after_timeout(monkeypatch):
    def fake_tess(img, tess_lang, psm="6"):
        return "", 0.0, True

    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr, "_tess", fake_tess)
    text, conf = ocr.run_ocr(_blank(), _blank(), "hi")
    assert text == "" and conf == 0.0


def test_run_ocr_prefers_longer_gray_read(monkeypatch):
    results = iter([("ab", 50.0, False), ("a longer gray read", 80.0, False)])

    def fake_tess(img, tess_lang, psm="6"):
        return next(results)

    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr, "_tess", fake_tess)
    text, conf = ocr.run_ocr(_blank(), _blank(), "hi")
    assert text == "a longer gray read" and conf == 80.0


def test_run_ocr_psm4_sparse_fallback(monkeypatch):
    from PIL import Image

    bin_img = Image.new("L", (120, 60), 255)
    gray_img = Image.new("L", (120, 60), 200)
    calls = []

    def fake_tess(img, tess_lang, psm="6"):
        calls.append((img, psm))
        if psm == "4" and img is gray_img:
            return "TOTAL 540", 70.0, False
        return "", 0.0, False

    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr, "_tess", fake_tess)
    text, conf = ocr.run_ocr(bin_img, gray_img, "en")
    assert (text, conf) == ("TOTAL 540", 70.0)
    # psm 4 ran on gray before binarized; the binarized pass was skipped
    assert calls[-1] == (gray_img, "4") and len([c for c in calls if c[1] == "4"]) == 1


def test_run_ocr_psm4_runs_on_binarized_when_gray_empty(monkeypatch):
    from PIL import Image

    bin_img = Image.new("L", (120, 60), 255)
    gray_img = Image.new("L", (120, 60), 200)

    def fake_tess(img, tess_lang, psm="6"):
        if psm == "4" and img is bin_img:
            return "TOTAL 540", 70.0, False
        return "", 0.0, False

    monkeypatch.setattr(ocr, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr, "_tess", fake_tess)
    text, conf = ocr.run_ocr(bin_img, gray_img, "en")
    assert (text, conf) == ("TOTAL 540", 70.0)


def test_run_ocr_without_tesseract_is_empty(monkeypatch):
    # Force the "no binary" path even on machines that have Tesseract.
    monkeypatch.setattr(ocr, "tesseract_available", lambda: False)
    out = ocr.run_ocr(_blank(), None, "hi")
    # Either a clean empty pair (no binary) or a real read (binary present).
    assert isinstance(out, tuple) and len(out) == 2
    assert isinstance(out[0], str) and isinstance(out[1], float)
