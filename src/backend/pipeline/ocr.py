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


def run_ocr(prepared: Image.Image, lang: str = "hi") -> tuple[str, float]:
    """Return (text, mean-confidence 0..100)."""
    if not tesseract_available():
        return "", 0.0
    tess_lang = config.TESS_LANG
    if (lang or "hi")[:2] == "bn" and "ben" not in tess_lang:
        tess_lang = tess_lang + "+ben"  # needs ben.traineddata (see Dockerfile)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            img_path = Path(tmp) / "page.png"
            img_path.write_bytes(to_png_bytes(prepared))
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
        return _via_pytesseract(prepared)


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
