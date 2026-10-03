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
    if _L(lang) == "en":
        return f"the average of the last {len(past_amounts)} similar papers was ₹{avg:,.0f}"
    return f"pichhle {len(past_amounts)} isi tarah ke kagazon ka ausat ₹{avg:,.0f} tha"


def detect(past_amounts: list[float], current: float | None, lang: str = "hi",
           native: bool = False) -> str | None:
    """Spike/drop warning. native=True returns native-script text for voices."""
    if current is None or not past_amounts:
        return None
    avg = sum(past_amounts) / len(past_amounts)
    diff = current - avg
    lang2 = _L(lang)
    if lang2 == "en":
        return _en(abs(diff) < 1, diff, current, avg)
    if native and lang2 == "hi":
        return _hi_native(abs(diff) < 1, diff, current, avg)
    if native and lang2 == "bn":
        return _bn_native(abs(diff) < 1, diff, current, avg)
    if lang2 == "bn":
        return _bn(abs(diff) < 1, diff, current, avg)
    return _hi(abs(diff) < 1, diff, current, avg)


def _significant(diff: float, avg: float) -> tuple[bool, bool]:
    pct = (diff / avg * 100) if avg else 0
    up = diff > 0 and (diff >= 100 or pct >= 15)
    down = diff < 0 and (abs(diff) >= 100 or pct <= -15)
    return up, down


def _hi(same: bool, diff: float, cur: float, avg: float) -> str | None:
    if same:
        return "yeh rakam bilkul pichhli baar jaisi hai, sab theek lag raha hai"
    up, down = _significant(diff, avg)
    if up:
        return (f"dhyaan dijiye: yeh ₹{cur:,.0f} hai, jo ausat ₹{avg:,.0f} se "
                f"₹{diff:,.0f} zyada hai. Meter ya bill dobara jaanch lijiye")
    if down:
        return (f"achhi khabar: yeh ₹{cur:,.0f} hai, ausat ₹{avg:,.0f} se "
                f"₹{abs(diff):,.0f} kam hai")
    return None


def _bn(same: bool, diff: float, cur: float, avg: float) -> str | None:
    if same:
        return "eta thik ager barer motoi, sob thik ache bole mone hocche"
    up, down = _significant(diff, avg)
    if up:
        return (f"lokkho korun: eta ₹{cur:,.0f}, ja gor ₹{avg:,.0f} theke "
                f"₹{diff:,.0f} beshi. Meter ba bill abar janch kore nin")
    if down:
        return (f"valo khobor: eta ₹{cur:,.0f}, gor ₹{avg:,.0f} theke "
                f"₹{abs(diff):,.0f} kom")
    return None


def _en(same: bool, diff: float, cur: float, avg: float) -> str | None:
    if same:
        return "this is just like last time, everything looks fine"
    up, down = _significant(diff, avg)
    if up:
        return (f"please note: this is ₹{cur:,.0f}, which is "
                f"₹{diff:,.0f} more than the average ₹{avg:,.0f}. "
                f"Please check the meter or bill again")
    if down:
        return (f"good news: this is ₹{cur:,.0f}, "
                f"₹{abs(diff):,.0f} less than the average ₹{avg:,.0f}")
    return None


def _hi_native(same: bool, diff: float, cur: float, avg: float) -> str | None:
    if same:
        return "यह बिल्कुल पिछली बार जैसा है, सब ठीक लग रहा है"
    up, down = _significant(diff, avg)
    if up:
        return (f"ध्यान दीजिए: यह ₹{cur:,.0f} है, जो औसत ₹{avg:,.0f} से "
                f"₹{diff:,.0f} ज़्यादा है। मीटर या बिल दोबारा जाँच लीजिए")
    if down:
        return (f"अच्छी ख़बर: यह ₹{cur:,.0f} है, औसत ₹{avg:,.0f} से "
                f"₹{abs(diff):,.0f} कम है")
    return None


def _bn_native(same: bool, diff: float, cur: float, avg: float) -> str | None:
    if same:
        return "এটা ঠিক আগের বারের মতোই, সব ঠিক আছে বলে মনে হচ্ছে"
    up, down = _significant(diff, avg)
    if up:
        return (f"লক্ষ্য করুন: এটা ₹{cur:,.0f}, যা গড় ₹{avg:,.0f} থেকে "
                f"₹{diff:,.0f} বেশি। মিটার বা বিল আবার যাচাই করে নিন")
    if down:
        return (f"ভালো খবর: এটা ₹{cur:,.0f}, গড় ₹{avg:,.0f} থেকে "
                f"₹{abs(diff):,.0f} কম")
    return None
