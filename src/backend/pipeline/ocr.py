"""OCR stage — Tesseract 5 when available, graceful fallback otherwise.

Never crashes the pipeline: if the binary or language data is missing we
return empty text with confidence 0 and the LLM/heuristic stage produces a
friendly "photo dobara lijiye" message.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from .. import config
from .preprocess import to_png_bytes


def tesseract_available() -> bool:
    return shutil.which(config.TESS_CMD) is not None


def run_ocr(prepared: Image.Image, retry_gray: Image.Image | None = None,
            lang: str = "hi") -> tuple[str, float]:
    """Return (text, mean-confidence 0..100).

    Two passes: binarized first (best for grimy photos), then the softer
    grayscale version (best for clean receipts with light print) if the
    first pass finds almost nothing. Keeps the longer, more confident read.
    """
    if not tesseract_available():
        return "", 0.0
    tess_lang = config.TESS_LANG
    short = (lang or "hi")[:2]
    if short == "en":
        tess_lang = "eng"  # one language = faster + sharper on a 0.1-CPU box
    elif short == "bn" and "ben" not in tess_lang:
        tess_lang = tess_lang + "+ben"  # needs ben.traineddata (see Dockerfile)
    first = _tess(prepared, tess_lang)
    if retry_gray is not None and len(first[0].strip()) < 25:
        second = _tess(retry_gray, tess_lang)
        if len(second[0].strip()) > len(first[0].strip()):
            return second
    return first


def _tess(img: Image.Image, tess_lang: str) -> tuple[str, float]:
    try:
        # Tesseract time grows superlinearly with pixels; 1000px reads
        # printed bills just as well at a fraction of the weak-CPU cost.
        img = _shrink(img, config.OCR_MAX_PX)
        with tempfile.TemporaryDirectory() as tmp:
            img_path = Path(tmp) / "page.png"
            img_path.write_bytes(to_png_bytes(img))
            out_base = str(Path(tmp) / "out")
            cmd = [config.TESS_CMD, str(img_path), out_base,
                   "-l", tess_lang, "--psm", "6", "-c",
                   "tessedit_create_tsv=1"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            txt_path = Path(out_base + ".txt")
            text = txt_path.read_text(encoding="utf-8", errors="ignore") if txt_path.exists() else ""
            conf = _mean_conf(Path(out_base + ".tsv"))
            if proc.returncode != 0 and not text.strip():
                return "", 0.0
            return text.strip(), conf
    except Exception:
        # Optional pure-python wrapper as a second chance.
        return _via_pytesseract(img)


def _shrink(img: Image.Image, max_px: int) -> Image.Image:
    w, h = img.size
    scale = min(1.0, max_px / max(w, h))
    if scale >= 1.0:
        return img
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def _mean_conf(tsv: Path) -> float:
    try:
        lines = tsv.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(lines) < 2:
            return 0.0
        header = lines[0].split("\t")
        ci = header.index("conf")
        vals = [float(p.split("\t")[ci]) for p in lines[1:] if p.split("\t")[ci].strip("- ").lstrip("-").isdigit()]
        vals = [v for v in vals if v >= 0]
        return round(sum(vals) / len(vals), 1) if vals else 0.0
    except Exception:
        return 0.0


def _via_pytesseract(prepared: Image.Image) -> tuple[str, float]:
    try:
        import pytesseract  # type: ignore

        data = pytesseract.image_to_data(prepared, lang=config.TESS_LANG.replace("+", "+"),
                                         output_type=pytesseract.Output.DICT)
        confs = [float(c) for c in data.get("conf", []) if str(c).lstrip("-").isdigit() and float(c) >= 0]
        text = pytesseract.image_to_string(prepared, lang=config.TESS_LANG.replace("+", "+"))
        mean = round(sum(confs) / len(confs), 1) if confs else 0.0
        return text.strip(), mean
    except Exception:
        return "", 0.0
