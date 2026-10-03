"""Family spaces — every visitor gets a private silo with an optional PIN.

- No code header  -> "default" space (backwards compatible).
- First visit     -> frontend calls ensure() and stores a personal code.
- Relatives share -> same code on each phone (+ PIN if the owner set one).
- Site-owner PIN  -> FAMILY_PIN env still works as a master override.
"""
from __future__ import annotations

import hashlib
import re
import secrets

from .models import Family

CODE_RE = re.compile(r"^[A-Z0-9-]{4,24}$")
DEFAULT = "default"


def normalize(code: str | None) -> str:
    code = (code or DEFAULT).strip().upper().replace(" ", "")
    if not CODE_RE.match(code):
        return DEFAULT
    return code


def fresh_code() -> str:
    words = ("DEEP", "AMMA", "GHAR", "ALO", "ROSHNI", "PORIBAR", "MITTI", "SURAJ")
    pick = secrets.choice(words)
    return f"{pick}-{secrets.token_hex(2).upper()}"


def _hash(pin: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{pin}".encode()).hexdigest()


def ensure(session, code: str | None) -> tuple[str, bool]:
    """Return (code, has_pin), creating an open space if needed."""
    code = normalize(code) if code else fresh_code()
    fam = session.get(Family, code)
    if fam is None:
        session.add(Family(code=code))
        session.commit()
        return code, False
    return code, bool(fam.pin_hash)


def check(session, code: str, pin: str | None, master_pin: str = "") -> bool:
    """True if this PIN may view the space."""
    if master_pin and pin == master_pin:
        return True  # site owner's master key
    code = normalize(code)
    fam = session.get(Family, code)
    if fam is None:
        return True  # brand-new space: open until the owner sets a PIN
    if not fam.pin_hash:
        return True
    return _hash(pin or "", fam.pin_salt or "") == fam.pin_hash


def set_pin(session, code: str, current_pin: str | None,
            new_pin: str, master_pin: str = "") -> tuple[bool, str]:
    """Set/change a space's own PIN. Returns (ok, message-key)."""
    code = normalize(code)
    new_pin = (new_pin or "").strip()
    if not (4 <= len(new_pin) <= 32):
        return False, "pin-length"
    fam = session.get(Family, code)
    if fam is None:
        fam = Family(code=code)
        session.add(fam)
    elif fam.pin_hash and not check(session, code, current_pin, master_pin):
        return False, "pin-wrong"
    salt = secrets.token_hex(16)
    fam.pin_salt = salt
    fam.pin_hash = _hash(new_pin, salt)
    session.commit()
    return True, "pin-set"
