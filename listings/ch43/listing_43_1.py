"""Listing 43.1. Credential broker issuing scoped, short-lived
tokens per action, and an egress policy applied outside the sandbox.

Chapter 43, Agent Security Architecture. Verified by execution.
Run with: python run.py 43.1
"""
import hashlib
import ipaddress
import time
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Token:
    tool: str
    user: str
    scope: str
    expires_at: float
    id: str


class Broker:
    def __init__(self, ttl_s=90):
        self.ttl = ttl_s
        self.issued: list = []

    def issue(self, policy_decision: str, tool: str, user: str,
              action: str, now=None):
        now = now or time.time()
        if policy_decision != "allow":
            self.issued.append({"tool": tool, "user": user,
                                "denied": policy_decision})
            return None
        # Never broader than the action.
        scope = f"{tool}:{action}"
        raw = f"{tool}{user}{action}{now}".encode()
        tid = hashlib.sha256(raw).hexdigest()[:10]
        tok = Token(tool, user, scope, now + self.ttl, tid)
        self.issued.append({"tool": tool, "user": user,
                            "scope": scope, "id": tid})
        return tok

    @staticmethod
    def valid(tok: Token, tool: str, action: str,
              now=None) -> bool:
        return (tok.scope == f"{tool}:{action}"
                and (now or time.time()) < tok.expires_at)


EGRESS_ALLOW = {
    "api.ticketing.example.com": {"strip_query": False},
    "docs.vendor.example.com": {"strip_query": True},
}


def egress_policy(url: str, resolved_ip: str):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    ip = ipaddress.ip_address(resolved_ip)
    if (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved):
        return False, "blocked address range", url
    if host not in EGRESS_ALLOW:
        return False, "host not allowlisted", url
    if EGRESS_ALLOW[host]["strip_query"] and p.query:
        clean = p._replace(query="").geturl()
        return (True,
                "query stripped (model-controlled parameters "
                "removed)",
                clean)
    return True, "ok", url


if __name__ == "__main__":
    b = Broker(ttl_s=90)
    t = b.issue("allow", "lookup_ticket", "alice", "read")

    def v(a, **k):
        return Broker.valid(t, "lookup_ticket", a, **k)

    print("issued scope:", t.scope,
          "| valid for read:", v("read"),
          "| valid for write:", v("write"),
          "| after expiry:", v("read", now=time.time() + 120))
    print("denied issuance:",
          b.issue("approval", "draft_ticket", "alice", "create"))
    urls = [
        ("https://api.ticketing.example.com/t/T-1042",
         "93.184.215.14"),
        ("https://docs.vendor.example.com/g"
         "?email=alice@example.com", "93.184.215.15"),
        ("https://169.254.169.254/latest/meta-data/",
         "169.254.169.254"),
        ("https://evil.example/?e=data", "93.184.215.99"),
    ]
    for url, ip in urls:
        ok, why, final = egress_policy(url, ip)
        print(f"{'ALLOW' if ok else 'BLOCK':5s} {why:52s} {final}")
    print("issuance log:", b.issued)
