"""Identity: established once at the interface, carried as an immutable object.

Chapter 42: every enforcement point reads this object and nothing else.
The request body and the model's output are never sources of identity.

Tokens here are compact HMAC-signed tokens standing in for the tokens an
organization's identity provider issues. In production, replace
`issue_token`/`verify_token` with verification of your IdP's tokens
(OIDC); the `Identity` object and everything downstream stay the same.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field


class AuthError(Exception):
    """Authentication failed; maps to HTTP 401."""


@dataclass(frozen=True)
class Identity:
    user_id: str
    groups: frozenset[str]
    roles: frozenset[str] = field(default_factory=frozenset)
    tenant: str = "default"

    def has_role(self, role: str) -> bool:
        return role in self.roles


# A stand-in identity directory: the groups and roles an IdP would hold.
# Group names match the document ACLs in examples/corpus.
DIRECTORY: dict[str, Identity] = {
    "alice": Identity("alice", frozenset({"all-staff"}), frozenset({"employee"})),
    "bob": Identity("bob", frozenset({"all-staff"}), frozenset({"employee"})),
    "sam": Identity("sam", frozenset({"all-staff", "hr"}), frozenset({"employee"})),
    "nina": Identity("nina", frozenset({"all-staff", "network"}), frozenset({"employee"})),
    "rita": Identity("rita", frozenset({"all-staff", "support"}),
                     frozenset({"employee", "reviewer"})),
    "olga": Identity("olga", frozenset({"all-staff"}),
                     frozenset({"employee", "operator", "ingest"})),
}


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def issue_token(identity: Identity, secret: str, ttl_s: int = 3600,
                now: float | None = None) -> str:
    now = time.time() if now is None else now
    payload = {
        "sub": identity.user_id,
        "grp": sorted(identity.groups),
        "rol": sorted(identity.roles),
        "ten": identity.tenant,
        "exp": int(now + ttl_s),
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str, secret: str, now: float | None = None) -> Identity:
    now = time.time() if now is None else now
    try:
        body, sig = token.split(".")
    except ValueError as exc:
        raise AuthError("malformed token") from exc
    expected = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        raise AuthError("bad signature")
    try:
        p = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("malformed payload") from exc
    if p.get("exp", 0) < now:
        raise AuthError("token expired")
    return Identity(
        user_id=str(p["sub"]),
        groups=frozenset(p.get("grp", [])),
        roles=frozenset(p.get("rol", [])),
        tenant=str(p.get("ten", "default")),
    )
