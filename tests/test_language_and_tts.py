"""Language lock (English paper -> chosen language) + ElevenLabs TTS fallback."""
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


def test_elevenlabs_returns_ogg_when_key_set(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        return _Resp(b"OGGDATA")

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)
    out = tts._elevenlabs("Nomoskar", "bn")
    assert out == b"OGGDATA"
    assert calls and "GuSivqtqi1qfWxEuGhqa" in calls[0]  # the bn voice id
    assert "mp3_44100_128" in calls[0]


def test_elevenlabs_uses_hindi_voice_for_hi(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req.full_url)
        return _Resp(b"OGGDATA")

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)
    assert tts._elevenlabs("Namaste", "hi") == b"OGGDATA"
    assert "zT03pEAEi0VHKciJODfn" in calls[0]  # the hi voice id


def test_elevenlabs_http_error_falls_back(monkeypatch):
    import urllib.error

    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "bad key", None, None)

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)
    assert tts._elevenlabs("Nomoskar", "bn") is None


def test_synthesize_bn_prefers_elevenlabs(monkeypatch):
    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")

    def fake_urlopen(req, timeout=None):
        return _Resp(b"ELEVEN_OGG")

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)
    assert tts.synthesize("Nomoskar", "bn") == b"ELEVEN_OGG"  # not the piper path


def test_synthesize_bn_falls_back_when_eleven_fails(monkeypatch):
    import urllib.error

    monkeypatch.setattr(config, "ELEVENLABS_API_KEY", "test-key")

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "boom", None, None)

    monkeypatch.setattr(tts.urllib.request, "urlopen", fake_urlopen)
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
