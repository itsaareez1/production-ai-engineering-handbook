"""Listing 41.1. Trace redaction with stable, versioned pseudonyms, a
key that must be configured, and a layered retention policy.

Chapter 41, Data Security and Privacy. Verified by execution.
Run with: python run.py 41.1
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


def load_key() -> "tuple[bytes, str]":
    """The key comes from the secrets manager. There is deliberately
    no silent fallback: a known key would make every pseudonym
    reversible by anyone who has it."""
    key = os.environ.get("TRACE_HMAC_KEY")
    if key:
        return key.encode(), os.environ.get("TRACE_KEY_VERSION", "v1")
    if os.environ.get("TRACE_ALLOW_DEV_KEY") == "1":
        return b"local-dev-only", "dev"
    raise RuntimeError("TRACE_HMAC_KEY is not set; refusing to "
                       "pseudonymize with a known key")


def pseudonym(kind: str, value: str, key: bytes, ver: str) -> str:
    tag = hmac.new(key, value.encode(), hashlib.sha256).hexdigest()
    return f"<{kind}:{ver}:{tag[:12]}>"


def redact(text: str, key: bytes, ver: str) -> str:
    for kind, pat in PATTERNS.items():
        text = pat.sub(
            lambda m: pseudonym(kind, m.group(0), key, ver), text)
    return text


RETENTION_DAYS = {"metadata": 400, "content": 30,
                  "restricted_content": 0}


def apply_retention(record: dict, now: float) -> dict:
    age_days = (now - record["t"]) / 86400
    out = dict(record)
    if age_days > RETENTION_DAYS["content"]:
        out.pop("content", None)
    if RETENTION_DAYS["restricted_content"] == 0:
        # Never stored; labels only.
        out.pop("restricted_content", None)
    return out


if __name__ == "__main__":
    os.environ.pop("TRACE_HMAC_KEY", None)
    try:
        load_key()
    except RuntimeError as e:
        print("no key:", e)

    os.environ["TRACE_HMAC_KEY"] = "from-the-secrets-manager"
    key, ver = load_key()
    q = ("Can you email alice.w@example.com and call "
         "+44 20 7946 0958 about my claim?")
    print(redact(q, key, ver))
    # The same address produces the same pseudonym.
    print(redact("Reply to alice.w@example.com again.", key, ver))

    rec = {"request_id": "r-9", "t": time.time() - 40 * 86400,
           "user": "u-17",
           "content": {"question": redact(q, key, ver),
                       "answer": "..."},
           "restricted_content": {"passage": "salary band data"},
           "context_labels": ["policy-pay/3.1@2026-05-02"],
           "taxonomy": "no-failure"}
    print(sorted(apply_retention(rec, time.time()).keys()))
