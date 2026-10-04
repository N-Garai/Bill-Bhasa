"""Voice stage — server-side speech in the user's own language.

Tries the on-disk Piper voice for the request language via subprocess
(memory is released when the process exits). A Hindi request with no Hindi
voice (or Bengali with no Bengali voice) returns None rather than speaking
the wrong language — the browser then speaks with its own voice, so there
is always sound, even on the smallest free-tier box.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .. import config

MONEY_WORD = {"hi": " रुपये ", "bn": " টাকা ", "en": " rupees "}


def voice_for(lang: str = "hi") -> str | None:
    """Baked voice file for this language, or None (use browser voice)."""
    short = (lang or "hi")[:2]
    if short == "bn":
        p = Path(config.PIPER_VOICE_BN)
    elif short == "hi":
        p = Path(config.PIPER_VOICE)
    else:
        return None  # phone English voices are good; skip server synth
    return str(p) if p.exists() else None


def available(lang: str = "hi") -> bool:
    return shutil.which(config.PIPER_BIN) is not None and voice_for(lang) is not None


def for_speech(text: str, lang: str = "hi") -> str:
    """Make text voice-safe: spoken money words, plain digit groups."""
    short = (lang or "hi")[:2]
    s = str(text or "")
    s = s.replace("₹", MONEY_WORD.get(short, MONEY_WORD["hi"]))
    if short in ("hi", "bn"):
        s = re.sub(r"(?<=\d),(?=\d)", "", s)  # 13,715 -> 13715 reads cleanly
    return re.sub(r"\s+", " ", s).strip()[:1200]


def _elevenlabs(text: str, lang: str) -> bytes | None:
    """Better server voice for bn/hi via ElevenLabs, or None to fall back.

    Requests OGG directly (output_format) so it drops straight into the
    audio endpoint unchanged. Any problem (no key, quota, network) returns
    None and the on-box Piper / browser voice takes over.
    """
    key = config.ELEVENLABS_API_KEY
    short = (lang or "hi")[:2]
    voice = {"bn": config.ELEVENLABS_VOICE_BN,
             "hi": config.ELEVENLABS_VOICE_HI}.get(short)
    if not key or not voice or not text:
        return None
    try:
        url = ("https://api.elevenlabs.io/v1/text-to-speech/"
               f"{voice}?output_format=ogg_44100_128")
        payload = json.dumps({
            "text": text,
            "model_id": config.ELEVENLABS_MODEL,
        }).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"xi-api-key": key, "Content-Type": "application/json",
                     "Accept": "application/octet-stream"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        return data or None
    except Exception:
        return None


def synthesize(text: str, lang: str = "hi") -> bytes | None:
    """Return OGG bytes or None. Never raises."""
    text = for_speech(text, lang)
    short = (lang or "hi")[:2]
    # Indic languages get the nicer ElevenLabs voices first (English keeps the
    # phone's own voices, as before). Fails over to Piper, then the browser.
    if short in ("bn", "hi") and config.ELEVENLABS_API_KEY:
        eleven = _elevenlabs(text, lang)
        if eleven:
            return eleven
    voice = voice_for(lang)
    if not text or not voice or shutil.which(config.PIPER_BIN) is None:
        return None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "out.wav"
            cmd = [config.PIPER_BIN, "--model", voice,
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
