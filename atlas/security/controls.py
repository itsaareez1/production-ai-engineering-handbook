"""Security controls enforced in code (Part VII).

- Redaction with keyed, stable, versioned pseudonyms (Chapter 41).
- Trust tiers and injection-marker scanning at ingestion and request
  time (Chapter 40). The scanner is a signal that quarantines and
  alerts; containment comes from authorization and egress controls.
- Egress allowlist with resolved-address checks against SSRF
  (Chapters 20 and 43).
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import socket
import unicodedata
from typing import Callable
from urllib.parse import urlsplit, urlunsplit

# ----------------------------------------------------------- redaction
PII_PATTERNS = {
    "EMAIL": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "PHONE": re.compile(r"\+?\d[\d\s().-]{8,}\d"),
    "CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    "SECRET": re.compile(r"\b(?:sk|pk|ghp|xox[abp])[-_][A-Za-z0-9_-]{16,}\b"),
}


class Redactor:
    """Replaces personal data and secret-like tokens with stable pseudonyms.

    The key must be configured (no default); the same value under the
    same key version always maps to the same token, so investigators can
    follow a thread without learning who it concerns."""

    def __init__(self, key: str, version: str):
        if not key:
            raise ValueError("redaction key is required")
        self._key = key.encode()
        self.version = version

    def pseudonym(self, kind: str, value: str) -> str:
        tag = hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()[:12]
        return f"<{kind}:{self.version}:{tag}>"

    def redact(self, text: str) -> str:
        for kind, pat in PII_PATTERNS.items():
            text = pat.sub(lambda m, k=kind: self.pseudonym(k, m.group(0)), text)
        return text


# --------------------------------------------------------- trust tiers
TIER_BY_SOURCE = {
    "repo": "trusted",
    "wiki": "semi", "policy": "semi", "ticket": "semi",
    "email": "untrusted", "web": "untrusted", "tool": "untrusted", "user": "untrusted",
}


def tier_of(source: str) -> str:
    """Unknown sources default to untrusted (Chapter 40)."""
    return TIER_BY_SOURCE.get(source.split("/")[0], "untrusted")


INJECTION_MARKERS = [
    (re.compile(r"\b(ignore|disregard|forget)\b.{0,40}\b(instructions|rules|prompt)", re.I),
     "override phrasing"),
    (re.compile(r"^\s*(system|assistant)\s*:", re.I | re.M), "role impersonation"),
    (re.compile(r"\bnote (for|to) the (assistant|ai|model)\b", re.I), "assistant-directed note"),
    (re.compile("[​‌‍⁠﻿]"), "zero-width characters"),
    (re.compile(r"\b(call|invoke|use|retrieve)\b.{0,40}\b(tool|function|document)\b", re.I),
     "tool or retrieval coercion"),
    (re.compile(r"https?://\S+\?\S*\b(email|token|data|key|secret)=", re.I), "exfiltration URL"),
]


def scan_for_injection(text: str) -> list[str]:
    """Return the markers found. Normalizes Unicode first, because
    homoglyph and width tricks are the first thing tried against a regex."""
    norm = unicodedata.normalize("NFKC", text)
    found = [name for pat, name in INJECTION_MARKERS if pat.search(norm) or pat.search(text)]
    if norm != text:
        found.append("normalization-changed text")
    return sorted(set(found))


# --------------------------------------------------------------- egress
class EgressDenied(Exception):
    """The destination is not permitted; the model never chooses where requests go."""


Resolver = Callable[[str], list[str]]


def _default_resolver(host: str) -> list[str]:
    return [ai[4][0] for ai in socket.getaddrinfo(host, None)]


def check_egress(url: str, allowlist: list[str], resolver: Resolver | None = None,
                 strip_query: bool = True) -> str:
    """Validate a URL against the allowlist and the resolved addresses.

    Returns the URL to fetch (query string stripped by default so a model
    cannot smuggle data out in parameters). Raises EgressDenied."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise EgressDenied("only https is allowed")
    if parts.username or parts.password:
        raise EgressDenied("credentials in URL")
    host = (parts.hostname or "").lower()
    if host not in {h.lower() for h in allowlist}:
        raise EgressDenied(f"host {host!r} not in allowlist")
    for addr in (resolver or _default_resolver)(host):
        ip = ipaddress.ip_address(addr)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved \
                or ip.is_multicast or ip.is_unspecified:
            raise EgressDenied(f"{host} resolves to non-public address {addr}")
    if strip_query:
        parts = parts._replace(query="", fragment="")
    return urlunsplit(parts)
