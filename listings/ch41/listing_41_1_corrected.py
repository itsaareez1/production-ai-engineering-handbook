"""Correction to Listing 41.1 (see ERRATA.md, ERR-03).

The printed listing reads

    SECRET = os.environ.get("TRACE_HMAC_KEY", "local-dev-only").encode()

under a comment saying the fallback "must never reach staging or
production". Nothing enforces that. A deployment that forgets to set
TRACE_HMAC_KEY pseudonymizes every trace with a key printed in a
published book, which makes every pseudonym in that deployment
reversible by dictionary attack -- the exact property the chapter
says the keyed hash provides.

This version makes the unsafe path explicit and adds the key version
to the token, so that the chapter's claim about rotation ("the key is
per environment and rotated, which breaks linkage across rotations by
design") is visible in the data rather than implied.

Run with: python listings/ch41/listing_41_1_corrected.py
          TRACE_ALLOW_DEV_KEY=1 python .../listing_41_1_corrected.py
"""
import hashlib
import hmac
import os
import re
import time

PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PHONE": re.compile(r"\+?\d[\d\s().-]{8,}\d"),
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
}

KEY_VERSION = os.environ.get("TRACE_HMAC_KEY_VERSION", "v1")


def _load_secret() -> bytes:
    """Refuse to run with a known key unless explicitly allowed."""
    key = os.environ.get("TRACE_HMAC_KEY")
    if key:
        return key.encode()
    if os.environ.get("TRACE_ALLOW_DEV_KEY") == "1":
        return b"local-dev-only"
    raise RuntimeError(
        "TRACE_HMAC_KEY is not set. Refusing to pseudonymize with a "
        "known key: every pseudonym would be reversible by anyone "
        "with a copy of the book. Set TRACE_ALLOW_DEV_KEY=1 for "
        "local runs only."
    )


def pseudonym(kind: str, value: str, secret: bytes) -> str:
    digest = hmac.new(secret, value.encode(), hashlib.sha256)
    return f"<{kind}:{KEY_VERSION}:{digest.hexdigest()[:16]}>"


def redact(text: str, secret: bytes) -> str:
    for kind, pat in PATTERNS.items():
        text = pat.sub(
            lambda m: pseudonym(kind, m.group(0), secret), text)
    return text


RETENTION_DAYS = {"metadata": 400, "content": 30,
                  "restricted_content": 0}


def apply_retention(record: dict, now: float) -> dict:
    age_days = (now - record["t"]) / 86400
    out = dict(record)
    if age_days > RETENTION_DAYS["content"]:
        out.pop("content", None)
    if RETENTION_DAYS["restricted_content"] == 0:
        out.pop("restricted_content", None)
    return out


if __name__ == "__main__":
    print("1. with no key configured at all:")
    for var in ("TRACE_HMAC_KEY", "TRACE_ALLOW_DEV_KEY"):
        os.environ.pop(var, None)
    try:
        _load_secret()
        print("   loaded a key (unexpected)")
    except RuntimeError as e:
        print("   refused:", e)

    print()
    print("2. with a configured key:")
    os.environ["TRACE_HMAC_KEY"] = "a-real-key-from-the-secrets-manager"
    secret = _load_secret()
    q = ("Can you email alice.w@example.com and call "
         "+44 20 7946 0958 about my claim?")
    print("  ", redact(q, secret))
    print("  ", redact("Reply to alice.w@example.com again.", secret))

    print()
    print("3. after a key rotation, linkage is broken by design:")
    rotated = b"the-next-key"
    globals()["KEY_VERSION"] = "v2"
    print("  ", redact("Reply to alice.w@example.com again.", rotated))

    print()
    rec = {"request_id": "r-9", "t": time.time() - 40 * 86400,
           "user": "u-17",
           "content": {"question": redact(q, secret),
                       "answer": "..."},
           "restricted_content": {"passage": "salary band data"},
           "context_labels": ["policy-pay/3.1@2026-05-02"],
           "taxonomy": "no-failure"}
    print("4. after retention:",
          sorted(apply_retention(rec, time.time()).keys()))
