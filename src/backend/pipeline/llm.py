"""Explanation stage — local open-weight GGUF -> hosted open-weight -> helper.

Priority (env LLM_PROVIDER=auto|local|groq|heuristic):
  1. local     — llama-cpp-python + GGUF file on disk (Apache-2.0 weights).
  2. groq      — free Groq endpoint serving an open-weight Llama model.
  3. heuristic — pure-Python keyword/regex explainer, always available.

The heuristic is a real fallback, not a stub: it classifies, extracts
amounts/dates and writes warm Hindi sentences, and it enforces the same
JSON contract + no-invented-numbers guardrail.
"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

from .. import config
from ..prompts import build_user_prompt, empty_for, _pick

_llm_cache = {"llama": None, "model_path": ""}

AMOUNT_RES = [
    re.compile(r"(?:₹|Rs\.?|INR|৳|Tk\.?|taka|টাকা)\s*([\d,]+(?:\.\d{1,2})?)", re.IGNORECASE),
    re.compile(r"(?:total|amount|payable|bill|કુલ|कुल|মোট|কুল)[^\d₹৳]{0,20}([\d,]{2,}(?:\.\d{1,2})?)", re.IGNORECASE),
]
DATE_RES = [
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
]
DUE_RES = [re.compile(r"(?:due|last date|अंतिम तिथि|due date)[^\d]{0,20}(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE)]

TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("electricity_bill", ("electricity", "bijli", "बिजली", "বিদ্যুৎ", "বিজলি", "power", "kwh", "unit", "tariff", "discom", "meter", "বিল")),
    ("water_bill", ("water", "पानी", "জল", "পানি", "jal board", "kl ")),
    ("gas_bill", ("gas", "गैस", "গ্যাস", "lpg", "cylinder")),
    ("phone_bill", ("mobile", "recharge", "jio", "airtel", "vi ", "broadband", "মোবাইল", "রিচার্জ")),
    ("medical_prescription", ("rx", "doctor", "dr.", "diagnosis", "mg ", "tablet", "dosage", "दवा", "ডাক্তার", "দাক্তার", "ওষুধ", "दिन में", "ব্যবস্থাপত্র", "prescription", "প্রেসক্রিপশন")),
    ("medicine_strip", ("strip", "capsule", "expiry", "batch", "mfg", "पत्ती", "পাতা", "স্ট্রিপ")),
    ("receipt", ("receipt", "cash", "total", "invoice", "bill no", "रसीद", "রসিদ", "রশিদ", "gst")),
]


def explain(ocr_text: str, history_hint: str = "", lang: str = "hi") -> tuple[dict, str]:
    """Return (explanation-json, provider-used). Never raises."""
    lang = (lang or "hi")[:2]
    provider = config.LLM_PROVIDER
    text = (ocr_text or "").strip()
    if not text:
        return empty_for(lang), "heuristic-empty"

    if provider in ("auto", "local"):
        out = _try_local(text, history_hint, lang)
        if out is not None:
            return out, "local"
        if provider == "local":
            return heuristic_explain(text, lang), "heuristic"
    if provider in ("auto", "groq") and config.GROQ_API_KEY:
        out = _try_groq(text, history_hint, lang)
        if out is not None:
            return out, "groq"
        if provider == "groq":
            return heuristic_explain(text, lang), "heuristic"
    return heuristic_explain(text, lang), "heuristic"


# --- local GGUF -----------------------------------------------------------
def _try_local(ocr_text: str, history_hint: str = "", lang: str = "hi") -> dict | None:
    try:
        model_path = Path(config.LLM_MODEL)
        if not model_path.exists():
            return None
        from llama_cpp import Llama  # type: ignore

        llm = _llm_cache.get("llama")
        if llm is None or _llm_cache.get("model_path") != str(model_path):
            llm = Llama(model_path=str(model_path), n_ctx=config.N_CTX,
                        n_threads=config.N_THREADS, verbose=False)
            _llm_cache["llama"] = llm
            _llm_cache["model_path"] = str(model_path)
        resp = llm.create_chat_completion(
            messages=[{"role": "system", "content": _pick(lang)},
                      {"role": "user", "content": build_user_prompt(ocr_text, history_hint, lang)}],
            temperature=0.3, max_tokens=350)
        content = resp["choices"][0]["message"]["content"] or ""
        parsed = _extract_json(content)
        if parsed is not None:
            return _guard_numbers(parsed, ocr_text)
        return None
    except Exception:
        return None


# --- hosted open-weight fallback ------------------------------------------
def _try_groq(ocr_text: str, history_hint: str = "", lang: str = "hi") -> dict | None:
    try:
        payload = json.dumps({
            "model": config.LLM_FALLBACK_MODEL,
            "temperature": 0.3,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _pick(lang)},
                {"role": "user", "content": build_user_prompt(ocr_text, history_hint, lang)},
            ],
        }).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions", data=payload,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {config.GROQ_API_KEY}"})
        with urllib.request.urlopen(req, timeout=45) as r:
            body = json.loads(r.read().decode())
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content) if isinstance(content, str) else content
        return _guard_numbers(parsed, ocr_text)
    except Exception:
        return None


# --- built-in helper (offline, dependency-free) ---------------------------
# Warm templates in both languages; keys match the LLM JSON contract so
# providers stay interchangeable.
_T = {
    "hi": {
        "titles": {
            "electricity_bill": ("bijli ka bill", "yeh aapke ghar ke bijli bill ka kagaz lag raha hai"),
            "water_bill": ("paani ka bill", "yeh paani ke bill ka kagaz lag raha hai"),
            "gas_bill": ("gas ka bill", "yeh gas bill ka kagaz lag raha hai"),
            "phone_bill": ("phone ka bill", "yeh mobile/phone bill ka kagaz lag raha hai"),
            "medical_prescription": ("doctor ka parcha", "yeh doctor ke parche jaisa lag raha hai"),
            "medicine_strip": ("dawa ki patti", "yeh dawa ki patti ka kagaz lag raha hai"),
            "receipt": ("khareed ki raseed", "yeh dukaan ki raseed jaisi lag rahi hai"),
            "unknown": ("kagaz", "yeh kisi bill ya parche jaisa kagaz lag raha hai"),
        },
        "hello": "Namaste!",
        "with_amount": "Is {title} mein kul rakam ₹{amount} likhi hai. ",
        "no_amount": "Ismein rakam saaf nahi dikhi, kripya roshni mein dobara photo lijiye. ",
        "with_due": "Aakhri taareekh {due} likhi hai. ",
        "closer": "Ghabraiye mat, neeche mukhya baatein sun lijiye.",
        "amt_pt": "Kul rakam: ₹{amount}",
        "due_pt": "Jama karne ki aakhri taareekh: {due}",
        "date_pt": "Kagaz par taareekh: {date}",
        "org_pt": "Upar likha naam/sthan: {org}",
        "retry_pt": "Rakam ya taareekh saaf nahi dikhi — dobara photo lijiye",
        "act_bill": "Is kagaz ko sambhal kar rakhiye aur samay par bhugtan kijiye",
        "act_med": "Dawa samay par lijiye",
        "act_none": "kuch karne ki zaroorat nahi",
        "disc_med": "dawa ya dose badalne se pehle doctor/pharmacist se poochhein",
    },
    "bn": {
        "titles": {
            "electricity_bill": ("bijli bill", "eta apnar barir bijli biler kagaj bole mone hocche"),
            "water_bill": ("joler bill", "eta joler biler kagaj bole mone hocche"),
            "gas_bill": ("gas bill", "eta gas biler kagaj bole mone hocche"),
            "phone_bill": ("phone bill", "eta mobile/phone biler kagaj bole mone hocche"),
            "medical_prescription": ("daktarer prescription", "eta daktarer prescription-er moto lagche"),
            "medicine_strip": ("oshudher pata", "eta oshudher patar kagaj bole mone hocche"),
            "receipt": ("dokaaner roshid", "eta dokaaner roshid-er moto lagche"),
            "unknown": ("kagaj", "eta kono bill ba prescription-er kagaj bole mone hocche"),
        },
        "hello": "Nomoskar!",
        "with_amount": "Ei {title}-e moṭ ₹{amount} lekha ache. ",
        "no_amount": "Ete taka sposto dekha jacche na, doya kore alo te abar chobi tulun. ",
        "with_due": "Shesh tarikh {due} lekha ache. ",
        "closer": "Bhabben na, niche mool kothagulo shune nin.",
        "amt_pt": "Moṭ taka: ₹{amount}",
        "due_pt": "Joma deoar shesh tarikh: {due}",
        "date_pt": "Kagoje tarikh: {date}",
        "org_pt": "Upore lekha naam/sthan: {org}",
        "retry_pt": "Taka ba tarikh sposto dekha jacche na — abar chobi tulun",
        "act_bill": "Kagajta jotno kore rakhun ebong somoy moto porishodh korun",
        "act_med": "Oshudh somoy moto khan",
        "act_none": "kichu korar dorkar nei",
        "disc_med": "oshudh ba dose bodlanor age daktar/pharmacist-ke jigyasa korun",
    },
    "en": {
        "titles": {
            "electricity_bill": ("electricity bill", "this looks like your home electricity bill"),
            "water_bill": ("water bill", "this looks like a water bill"),
            "gas_bill": ("gas bill", "this looks like a gas bill"),
            "phone_bill": ("phone bill", "this looks like a mobile/phone bill"),
            "medical_prescription": ("doctor's prescription", "this looks like a doctor's prescription"),
            "medicine_strip": ("medicine strip", "this looks like a medicine strip paper"),
            "receipt": ("shop receipt", "this looks like a shop receipt"),
            "unknown": ("paper", "this looks like some bill or prescription paper"),
        },
        "hello": "Hello!",
        "with_amount": "This {title} shows a total of ₹{amount}. ",
        "no_amount": "I could not read the amount clearly — please retake the photo in better light. ",
        "with_due": "The last date written is {due}. ",
        "closer": "Don't worry, the main points are below.",
        "amt_pt": "Total amount: ₹{amount}",
        "due_pt": "Last date to pay: {due}",
        "date_pt": "Date on the paper: {date}",
        "org_pt": "Name/place written on top: {org}",
        "retry_pt": "Amount or date is not clear — please retake the photo",
        "act_bill": "Keep this paper safe and pay on time",
        "act_med": "Take your medicines on time",
        "act_none": "nothing needs to be done",
        "disc_med": "before changing any medicine or dose, please ask your doctor/pharmacist",
    },
}


def heuristic_explain(ocr_text: str, lang: str = "hi") -> dict:
    lang = (lang or "hi")[:2]
    t = _T.get(lang, _T["hi"])
    text = ocr_text.strip()
    low = text.lower()
    doc_type = "unknown"
    for dtype, keys in TYPE_RULES:
        if any(k in low for k in keys):
            doc_type = dtype
            break
    amount = _find_amount(text)
    date = _find_date(text)
    due = _find_due(text)

    title, opener = t["titles"].get(doc_type, t["titles"]["unknown"])
    if amount is not None:
        summary = f"{t['hello']} {opener}. " + t["with_amount"].format(title=title, amount=f"{amount:,.0f}")
    else:
        summary = f"{t['hello']} {opener}. " + t["no_amount"]
    if due:
        summary += t["with_due"].format(due=due)
    summary += t["closer"]

    points: list[str] = []
    if amount is not None:
        points.append(t["amt_pt"].format(amount=f"{amount:,.0f}"))
    if due:
        points.append(t["due_pt"].format(due=due))
    elif date:
        points.append(t["date_pt"].format(date=date))
    org = _find_org(text)
    if org:
        points.append(t["org_pt"].format(org=org))
    if not points:
        points.append(t["retry_pt"])

    medical = doc_type in ("medical_prescription", "medicine_strip")
    action = (t["act_bill"] if doc_type.endswith("bill") or doc_type == "receipt"
              else (t["act_med"] if medical else t["act_none"]))
    out = {
        "doc_type": doc_type,
        "summary_hi": summary.strip(),
        "key_points_hi": points[:4],
        "unusual_hi": None,
        "action_hi": action,
        "disclaimer_hi": (t["disc_med"] if medical else ""),
        "amount": amount,
        "currency": "INR",
        "date": _iso(date),
    }
    return _guard_numbers(out, text)


def _find_amount(text: str) -> float | None:
    cands: list[float] = []
    for rx in AMOUNT_RES:
        for m in rx.finditer(text):
            try:
                cands.append(float(m.group(1).replace(",", "")))
            except ValueError:
                continue
    if not cands:
        return None
    # Prefer the largest figure on bills (totals > line items).
    return round(max(cands), 2)


def _find_date(text: str) -> str | None:
    for rx in DATE_RES:
        m = rx.search(text)
        if m:
            return m.group(1)
    return None


def _find_due(text: str) -> str | None:
    for rx in DUE_RES:
        m = rx.search(text)
        if m:
            return m.group(1)
    return None


def _find_org(text: str) -> str:
    first = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for ln in first[:3]:
        if len(ln) > 3 and not re.search(r"\d{4,}", ln):
            return re.sub(r"\s+", " ", ln)[:80]
    return ""


def _iso(date: str | None) -> str | None:
    if not date:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date)
    if m:
        return date
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", date)
    if m:
        d, mo, y = m.groups()
        if len(y) == 2:
            y = "20" + y
        return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
    return None


def _extract_json(content: str) -> dict | None:
    try:
        return json.loads(content)
    except Exception:
        pass
    m = re.search(r"\{.*\}", content, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _guard_numbers(parsed: dict, ocr_text: str) -> dict:
    """Keep the structured amount honest: it must match a figure in the OCR.

    Compares numerically (so JSON ``540.0`` matches OCR ``540``) and only
    touches the ``amount`` field — prose is left untouched.
    """
    try:
        ocr_nums: list[float] = []
        for m in re.findall(r"\d[\d,]*\.?\d*", ocr_text or ""):
            try:
                ocr_nums.append(float(m.replace(",", "")))
            except ValueError:
                continue
        amt = parsed.get("amount")
        if amt is not None:
            try:
                af = float(amt)
                if not any(abs(af - o) < 1e-9 for o in ocr_nums):
                    parsed["amount"] = None
            except (TypeError, ValueError):
                parsed["amount"] = None
        parsed.setdefault("currency", "INR")
        return parsed
    except Exception:
        return parsed
