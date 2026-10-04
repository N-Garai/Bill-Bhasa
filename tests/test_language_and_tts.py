"""Language lock (English paper -> chosen language) + ElevenLabs TTS fallback."""
import sys
from src.backend import config
from src.backend import prompts
from src.backend.pipeline import tts


# --- language lock: an English paper must be explained in the chosen language ---
def test_every_prompt_has_a_language_lock():
    for lang in ("hi", "bn", "en"):
        p = prompts._pick(lang)
        assert "LANGUAGE LOCK" in p
        assert "READ EVERYTHING" in p


def test_user_prompt_re_locks_language_per_lang():
    assert "SUDHU BANGLA" in prompts.build_user_prompt("BILL", lang="bn")
    assert "ONLY Hindi" in prompts.build_user_prompt("BILL", lang="hi")
    assert "ENTIRE reply in simple ENGLISH" in prompts.build_user_prompt("BILL", lang="en")


# --- ElevenLabs TTS (bn/hi) with graceful fallback -------------------------
class _Resp:
    def __init__(self, data):
        self._d = data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._d


def test_elevenlabs_no_key_is_none(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "")
    assert tts._elevenlabs("Nomoskar", "bn") is None


def test_elevenlabs_returns_mp3_when_key_set(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")
    calls = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        class text_to_speech:
            @staticmethod
            def convert(text=None, voice_id=None, model_id=None, output_format=None):
                calls.append({"text": text, "voice_id": voice_id,
                              "model_id": model_id, "output_format": output_format})
                return b"MP3DATA"

    monkeypatch.setattr(tts, "ElevenLabs", DummyClient)
    out = tts._elevenlabs("Nomoskar", "bn")
    assert out == b"MP3DATA"
    assert calls and calls[0]["voice_id"] == "GuSivqtqi1qfWxEuGhqa"
    assert calls[0]["output_format"] == "mp3_44100_128"


def test_elevenlabs_uses_hindi_voice_for_hi(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")
    calls = []

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        class text_to_speech:
            @staticmethod
            def convert(text=None, voice_id=None, model_id=None, output_format=None):
                calls.append({"voice_id": voice_id})
                return b"MP3DATA"

    monkeypatch.setattr(tts, "ElevenLabs", DummyClient)
    assert tts._elevenlabs("Namaste", "hi") == b"MP3DATA"
    assert calls and calls[0]["voice_id"] == "zT03pEAEi0VHKciJODfn"


def test_elevenlabs_import_error_falls_back(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(tts, "ElevenLabs", None)
    assert tts._elevenlabs("Nomoskar", "bn") is None


def test_synthesize_bn_prefers_elevenlabs(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        class text_to_speech:
            @staticmethod
            def convert(text=None, voice_id=None, model_id=None, output_format=None):
                return b"ELEVEN_MP3"

    monkeypatch.setattr(tts, "ElevenLabs", DummyClient)
    assert tts.synthesize("Nomoskar", "bn") == b"ELEVEN_MP3"  # not the piper path


def test_synthesize_bn_falls_back_when_eleven_fails(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        class text_to_speech:
            @staticmethod
            def convert(text=None, voice_id=None, model_id=None, output_format=None):
                raise RuntimeError("boom")

    monkeypatch.setattr(tts, "ElevenLabs", DummyClient)
    # ElevenLabs fails; no piper on a dev box -> browser fallback -> None.
    assert tts.synthesize("Nomoskar", "bn") is None


def test_synthesize_en_never_calls_elevenlabs(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")
    called = {}

    def fake_urlopen(req, timeout=None):
        called["hit"] = True
        return _Resp(b"X")

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)
    # English keeps the phone's own voice -> no server synth on a dev box.
    assert tts.synthesize("Hello", "en") is None
    assert "hit" not in called
