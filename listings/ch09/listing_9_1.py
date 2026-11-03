"""Listing 9.1. A minimal model gateway with routing, fallback,
circuit breaking, and accounting.

Chapter 9, Model Gateways, Routing, and Fallbacks.
Verified by execution with stubbed providers.
Run with: python run.py 9.1
"""
import time
from dataclasses import dataclass


class ProviderError(Exception):
    pass


@dataclass
class Candidate:
    name: str
    provider: object         # has .complete(prompt) -> str
    timeout_s: float = 10.0
    failures: int = 0
    open_until: float = 0.0  # circuit breaker state

    def available(self, now):
        return now >= self.open_until


@dataclass
class CallRecord:
    task: str
    candidate: str
    ok: bool
    latency_ms: float
    note: str = ""


class Gateway:
    def __init__(self, routes: dict, breaker_threshold=3,
                 cooldown_s=30.0):
        self.routes = routes     # task -> [Candidate, ...]
        self.threshold = breaker_threshold
        self.cooldown = cooldown_s
        self.records: list[CallRecord] = []

    def complete(self, task: str, prompt: str, degraded):
        for cand in self.routes[task]:
            now = time.monotonic()
            if not cand.available(now):
                self.records.append(CallRecord(
                    task, cand.name, False, 0, "breaker open"))
                continue
            start = time.perf_counter()
            try:
                out = cand.provider.complete(
                    prompt, timeout=cand.timeout_s)
                cand.failures = 0
                ms = (time.perf_counter() - start) * 1000
                self.records.append(
                    CallRecord(task, cand.name, True, ms))
                return out, cand.name
            except (ProviderError, TimeoutError) as e:
                cand.failures += 1
                if cand.failures >= self.threshold:
                    cand.open_until = now + self.cooldown
                ms = (time.perf_counter() - start) * 1000
                self.records.append(CallRecord(
                    task, cand.name, False, ms, str(e)))
        return degraded(prompt), "degraded"


class Stub:
    def __init__(self, name, fail=False):
        self.name, self.fail = name, fail

    def complete(self, prompt, timeout):
        if self.fail:
            raise ProviderError(f"{self.name} unavailable")
        return f"[{self.name}] answer"


if __name__ == "__main__":
    primary = Candidate("large-in-region", Stub("large", fail=True))
    fallback = Candidate("mid-in-region", Stub("mid"))
    gw = Gateway({"qa": [primary, fallback]}, breaker_threshold=2)
    for i in range(3):
        out, used = gw.complete(
            "qa", "What is the leave policy?",
            degraded=lambda p: "[retrieval-only] top documents")
        print(i, used, out)
    print([(r.candidate, r.ok, r.note) for r in gw.records])
