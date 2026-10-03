"""Voice quality: native-script speech twins, money words, per-lang voices."""
from src.backend.pipeline import llm
from src.backend.pipeline.anomaly import detect
from src.backend.pipeline.tts import for_speech, synthesize, voice_for


def test_speech_text_uses_native_scripts():
    bn, _ = llm.explain("BIJLI BILL\nTotal Rs. 420", lang="bn")
    assert any("\u0980" <= c <= "\u09ff" for c in bn["speech_text"])
    hi, _ = llm.explain("BIJLI BILL\nTotal Rs. 420", lang="hi")
    assert any("\u0900" <= c <= "\u097f" for c in hi["speech_text"])
    en, _ = llm.explain("POWER BILL\nTotal Rs. 420", lang="en")
    assert en["speech_text"].startswith("Hello")
    # display text stays romanized (easier to read)
    assert bn["summary_hi"].startswith("Nomoskar")


def test_for_speech_money_and_commas():
    assert "টাকা" in for_speech("₹540", "bn")
    assert "," not in for_speech("₹13,715", "bn")
    assert "रुपये" in for_speech("₹540", "hi")


def test_native_anomaly_lines():
    flag = detect([420, 418, 422], 540, lang="bn", native=True)
    assert any("\u0980" <= c <= "\u09ff" for c in flag)
    flag_hi = detect([420, 418, 422], 540, lang="hi", native=True)
    assert any("\u0900" <= c <= "\u097f" for c in flag_hi)
    # roman default unchanged
    assert detect([420, 418, 422], 540, lang="bn").startswith("lokkho")


def test_no_voices_locally_falls_back():
    assert voice_for("bn") is None  # /models absent on a dev box
    assert voice_for("hi") is None
    assert synthesize("Nomoskar", "bn") is None
