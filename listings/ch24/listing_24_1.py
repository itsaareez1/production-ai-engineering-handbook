"""Listing 24.1. Idempotent write with bounded, jittered retries and
error classification.

Chapter 24, Reliability Patterns.
Verified by execution with a stubbed external system.
Run with: python run.py 24.1
"""
import hashlib
import random
import time


class Retryable(Exception):
    pass


class NotRetryable(Exception):
    pass


def intent_key(*parts) -> str:
    joined = "|".join(map(str, parts)).encode()
    return hashlib.sha256(joined).hexdigest()[:16]


class TicketSystem:
    """Stub: attempt 1 fails before effect; attempt 2 performs the
    effect but the response is lost; attempt 3 succeeds and returns
    the existing ticket."""

    def __init__(self):
        self.tickets = {}
        self.by_key = {}
        self.calls = 0

    def create(self, key: str, payload: dict) -> dict:
        self.calls += 1
        if key in self.by_key:  # replay: return original
            return {"id": self.by_key[key], "replayed": True}
        if self.calls == 1:
            raise Retryable("503 upstream unavailable")
        tid = f"T-{2000 + len(self.tickets)}"
        self.tickets[tid] = payload      # effect performed
        self.by_key[key] = tid
        if self.calls == 2:
            raise Retryable("connection reset after send")  # ack lost
        return {"id": tid, "replayed": False}


def with_retries(fn, max_attempts=4, budget_s=10.0, base=0.05,
                 cap=1.0, sleep=time.sleep):
    start = time.monotonic()
    last = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(), attempt
        except NotRetryable:
            raise
        except Retryable as e:
            last = e
            if (time.monotonic() - start > budget_s
                    or attempt == max_attempts):
                break
            delay = (min(cap, base * 2 ** (attempt - 1))
                     * random.uniform(0.5, 1.5))
            sleep(delay)
    raise RuntimeError(
        f"retries exhausted after {attempt} attempts: {last}")


if __name__ == "__main__":
    ts = TicketSystem()
    key = intent_key("user:alice", "subject:vpn drops",
                     "conv:c-91", "turn:4")
    payload = {"summary": "VPN drops", "requester": "alice"}

    def no_sleep(s):
        return None

    result, attempts = with_retries(
        lambda: ts.create(key, payload), sleep=no_sleep)
    print(result, "| attempts:", attempts,
          "| tickets created:", len(ts.tickets))
    result2, _ = with_retries(
        lambda: ts.create(key, payload), sleep=no_sleep)
    print(result2, "| tickets created:", len(ts.tickets))
