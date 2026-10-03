"""Voice stage — server-side Hindi speech when available.

Tries the on-disk Piper voice via subprocess (memory is released when the
process exits). If Piper/ffmpeg is missing we return None and the browser
speaks the text itself with its built-in Hindi voice — so Amma always
hears something, even on the smallest free-tier box.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .. import config


def available() -> bool:
    return shutil.which(config.PIPER_BIN) is not None and Path(config.PIPER_VOICE).exists()


def synthesize(text: str) -> bytes | None:
    """Return OGG bytes or None. Never raises."""
    text = (text or "").strip()[:1200]
    if not text or not available():
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "out.wav"
            cmd = [config.PIPER_BIN, "--model", config.PIPER_VOICE,
                   "--output_file", str(wav)]
            proc = subprocess.run(cmd, input=text.encode("utf-8"),
                                  capture_output=True, timeout=60)
            if proc.returncode != 0 or not wav.exists():
                return None
            if shutil.which("ffmpeg"):
                ogg = Path(tmp) / "out.ogg"
                c2 = subprocess.run(["ffmpeg", "-y", "-i", str(wav),
                                     "-c:a", "libvorbis", "-q:a", "3", str(ogg)],
                                    capture_output=True, timeout=60)
                if c2.returncode == 0 and ogg.exists():
                    return ogg.read_bytes()
            return wav.read_bytes()
    except Exception:
        return None
