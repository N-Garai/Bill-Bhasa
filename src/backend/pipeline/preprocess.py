"""Image cleanup before OCR: gray, contrast, threshold, upscale.

Pillow + numpy only (no OpenCV — saves ~30MB RAM/import on free tier).
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

try:
    import pillow_heif  # type: ignore

    pillow_heif.register_heif_opener()  # iPhone .HEIC photos open like any JPEG
except Exception:
    pass  # without it, HEIC uploads fail with a clear error, nothing else breaks


def load_and_prepare(raw: bytes, max_px: int = 1600) -> tuple[Image.Image, Image.Image, bytes]:
    """Return (binarized image, contrast grayscale retry image, downscaled JPEG).

    Heavy binarization helps grimy photos but can erase light print on clean
    receipts — the grayscale version is the second chance for OCR.
    """
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    # Transparency onto white (not black): white text on a transparent
    # screenshot stays readable instead of vanishing into a black page.
    if img.mode == "P":
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    else:
        img = img.convert("RGB")
    w, h = img.size
    scale = min(1.0, max_px / max(w, h))
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Grayscale + gentle contrast boost helps printed bills a lot.
    gray = ImageOps.grayscale(img)
    gray = ImageEnhance.Contrast(gray).enhance(1.6)
    gray = ImageEnhance.Brightness(gray).enhance(1.05)

    # Mild upscale for small phone crops (Tesseract likes ~300 DPI).
    if max(gray.size) < 1200:
        gray = gray.resize((gray.width * 2, gray.height * 2), Image.LANCZOS)

    # Adaptive-ish threshold via numpy mean (cheap, no OpenCV).
    arr = np.asarray(gray).astype(np.float32)
    thresh = float(arr.mean()) * 0.95
    bin_arr = np.where(arr > thresh, 255, 0).astype(np.uint8)
    prepared = Image.fromarray(bin_arr)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72, optimize=True)
    return prepared, gray, buf.getvalue()


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
