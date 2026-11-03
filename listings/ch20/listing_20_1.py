"""Listing 20.1. URL validation against SSRF, with resolved-address
checks and a bounded fetch.

Chapter 20, External Integrations. Address classification verified
by execution; the network fetch is reviewed for correctness (the
book's build environment has no network access).
Run with: python run.py 20.1
"""
import ipaddress
import socket
import urllib.request
from urllib.parse import urlparse

ALLOWED_HOSTS = {"docs.example.internal", "api.ticketing.example.com"}
MAX_BYTES = 512_000
TIMEOUT_S = 5.0


def _is_blocked(ip) -> bool:
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_multicast or ip.is_reserved
            or ip.is_unspecified)


def validate_url(url: str, resolver=socket.getaddrinfo) -> str:
    """Return the validated URL or raise ValueError. Checks scheme,
    host allowlist, and every resolved address, so a name that
    resolves to a private range fails."""
    p = urlparse(url)
    if p.scheme not in ("https",):
        raise ValueError("scheme not allowed")
    if p.username or p.password:
        raise ValueError("credentials in URL not allowed")
    host = (p.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"host not allowlisted: {host}")
    for info in resolver(host, None):
        ip = ipaddress.ip_address(info[4][0])
        if _is_blocked(ip):
            raise ValueError(
                f"host resolves to blocked address {ip}")
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        raise ValueError("redirects not followed")


def fetch_bounded(url: str) -> bytes:
    """Reviewed, not executed here: GET with timeout, no redirects,
    size cap."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "atlas-fetch/1.0"})
    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(req, timeout=TIMEOUT_S) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("response too large")
    return data


if __name__ == "__main__":
    def fake_resolver(host, port):
        table = {
            # private: blocked
            "docs.example.internal": "10.20.0.5",
            # public: allowed
            "api.ticketing.example.com": "93.184.215.14",
        }
        return [(None, None, None, None, (table[host], 0))]

    tests = ["https://api.ticketing.example.com/tickets/T-1042",
             "https://docs.example.internal/page",
             "http://api.ticketing.example.com/x",
             "https://169.254.169.254/latest/meta-data/",
             "https://user:pw@api.ticketing.example.com/"]
    for u in tests:
        try:
            print("OK     ", validate_url(u, resolver=fake_resolver))
        except (ValueError, KeyError) as e:
            print("REJECT ", u, "->", e)
