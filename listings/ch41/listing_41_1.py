"""Listing 41.1. Trace redaction with stable pseudonyms and a
layered retention policy.

Chapter 41, Data Protection and Privacy. Verified by execution.
Run with: python run.py 41.1

NOTE: this file is the listing exactly as printed. Its SECRET falls
back to a hardcoded string when TRACE_HMAC_KEY is unset, which the
comment forbids but the code permits -- see ERRATA.md, ERR-03. The
corrected version is listing_41_1_corrected.py in this directory.
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
# The key comes from the secrets manager in production; the fallback
# is for local runs only and must never reach staging or production.
SECRET = os.environ.get("TRACE_HMAC_KEY", "local-dev-only").encode()


def pseudonym(kind: str, value: str) -> str:
    tag = hmac.new(SECRET, value.encode(),
                   hashlib.sha256).hexdigest()[:8]
    return f"<{kind}:{tag}>"


def redact(text: str) -> str:
    for kind, pat in PATTERNS.items():
        text = pat.sub(lambda m: pseudonym(kind, m.group(0)), text)
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
    q = ("Can you email alice.w@example.com and call "
         "+44 20 7946 0958 about my claim?")
    print(redact(q))
    # The same address produces the same pseudonym.
    print(redact("Reply to alice.w@example.com again."))
    rec = {"request_id": "r-9", "t": time.time() - 40 * 86400,
           "user": "u-17",
           "content": {"question": redact(q), "answer": "..."},
           "restricted_content": {"passage": "salary band data"},
           "context_labels": ["policy-pay/3.1@2026-05-02"],
           "taxonomy": "no-failure"}
    print(sorted(apply_retention(rec, time.time()).keys()))
