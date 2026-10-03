"""Any-image robustness: modes, transparency, formats, garbage input."""
import io

import pytest
from PIL import Image, ImageDraw

from src.backend.pipeline.preprocess import load_and_prepare


def _bytes(img, fmt="PNG"):
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_transparent_background_becomes_white():
    img = Image.new("RGBA", (400, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((20, 80), "Rs. 540", fill=(0, 0, 0, 255))
    prep, gray, jpg = load_and_prepare(_bytes(img))
    assert gray.mode == "L" and prep.mode in ("1", "L")
    back = Image.open(io.BytesIO(jpg))
    assert back.getpixel((5, 5)) == (255, 255, 255)


def test_palette_gray_and_common_formats():
    p = Image.new("P", (300, 150))
    p.putpalette([200] * 768)
    _, _, jpg = load_and_prepare(_bytes(p))
    assert len(jpg) > 0
    g = Image.new("L", (300, 150), 200)
    _, _, jpg = load_and_prepare(_bytes(g))
    assert len(jpg) > 0
    rgb = Image.new("RGB", (300, 150), "white")
    for fmt in ("PNG", "JPEG", "BMP"):
        _, _, jpg = load_and_prepare(_bytes(rgb, fmt))
        assert len(jpg) > 0


def test_garbage_bytes_raise_clearly():
    with pytest.raises(Exception):
        load_and_prepare(b"this is not an image at all")
    with pytest.raises(Exception):
        load_and_prepare(b"")
