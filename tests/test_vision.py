"""Vision fallback: off without a key, guardrails hold with a transcript."""
import os

os.environ["GEMMA_API_KEY"] = ""

from src.backend import config  # noqa: E402
from src.backend.pipeline import ocr, vision  # noqa: E402
from src.backend.pipeline.llm import _guard_numbers  # noqa: E402


def test_default_model_is_verified_served():
    assert config.GEMMA_VISION_MODEL in vision.VERIFIED_MODELS


def test_vision_off_without_key():
    assert vision.available() is False
    assert vision.explain_image(b"not-an-image") is None
    assert vision.last_error == "no-key"


def test_two_pass_ocr_never_crashes():
    from PIL import Image

    blank = Image.new("L", (120, 120), 255)
    text, conf = ocr.run_ocr(blank, blank, lang="en")
    assert isinstance(text, str) and isinstance(conf, float)


def test_ocr_shrink_keeps_small_images():
    from PIL import Image

    from src.backend.pipeline.ocr import _shrink

    tiny = Image.new("L", (200, 100), 255)
    assert _shrink(tiny, 1000).size == (200, 100)
    big = Image.new("L", (2000, 1000), 255)
    assert max(_shrink(big, 1000).size) == 1000


def test_transcript_guards_vision_amount():
    out = _guard_numbers(
        {"amount": 13715.52, "currency": "INR"},
        "FIGURES: TOTAL 13715.52, 26/04/2019",
    )
    assert out["amount"] == 13715.52
    bad = _guard_numbers({"amount": 99999}, "FIGURES: TOTAL 100")
    assert bad["amount"] is None
