"""Memory stage — compares the new amount with the family's own history.

Pure Python, zero dependencies. Flags only meaningful jumps so Amma is
warned gently instead of scared by noise.
"""
from __future__ import annotations


def _L(lang: str) -> str:
    return (lang or "hi")[:2]


def build_history_hint(past_amounts: list[float], lang: str = "hi") -> str:
    if not past_amounts:
        return ""
    avg = sum(past_amounts) / len(past_amounts)
    if _L(lang) == "bn":
        return f"ager {len(past_amounts)} eki rokom kagoje gor ₹{avg:,.0f} chilo"
    return f"pichhle {len(past_amounts)} isi tarah ke kagazon ka ausat ₹{avg:,.0f} tha"


def detect(past_amounts: list[float], current: float | None, lang: str = "hi") -> str | None:
    if current is None or not past_amounts:
        return None
    avg = sum(past_amounts) / len(past_amounts)
    diff = current - avg
    bn = _L(lang) == "bn"
    if abs(diff) < 1:
        return ("eta thik ager barer motoi, sob thik ache bole mone hocche"
                if bn else "yeh rakam bilkul pichhli baar jaisi hai, sab theek lag raha hai")
    pct = (diff / avg * 100) if avg else 0
    if diff > 0 and (diff >= 100 or pct >= 15):
        if bn:
            return (f"lokkho korun: eta ₹{current:,.0f}, ja gor ₹{avg:,.0f} theke "
                    f"₹{diff:,.0f} beshi. Meter ba bill abar janch kore nin")
        return (f"dhyaan dijiye: yeh ₹{current:,.0f} hai, jo ausat ₹{avg:,.0f} se "
                f"₹{diff:,.0f} zyada hai. Meter ya bill dobara jaanch lijiye")
    if diff < 0 and (abs(diff) >= 100 or pct <= -15):
        if bn:
            return (f"valo khobor: eta ₹{current:,.0f}, gor ₹{avg:,.0f} theke "
                    f"₹{abs(diff):,.0f} kom")
        return (f"achhi khabar: yeh ₹{current:,.0f} hai, ausat ₹{avg:,.0f} se "
                f"₹{abs(diff):,.0f} kam hai")
    return None
