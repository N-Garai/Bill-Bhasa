"""Anomaly math: flags real jumps, stays quiet on noise."""
from src.backend.pipeline import anomaly


def test_first_bill_never_flags():
    assert anomaly.detect([], 540) is None
    assert anomaly.detect([], None) is None


def test_spike_flagged_in_hindi():
    flag = anomaly.detect([420, 418, 422], 540)
    assert flag is not None
    assert "120" in flag or "zyada" in flag


def test_small_wobble_stays_quiet():
    assert anomaly.detect([420, 418, 422], 425) is None


def test_drop_is_good_news():
    flag = anomaly.detect([540, 535, 545], 400)
    assert flag is not None
    assert "kam" in flag


def test_bengali_flag_is_bangla():
    flag = anomaly.detect([420, 418, 422], 540, lang="bn")
    assert flag is not None
    assert "beshi" in flag
    hint = anomaly.build_history_hint([420, 418], lang="bn")
    assert "gor" in hint
