"""Lab 2: Build a model gateway (Chapters 9, 24, 46).

Runs offline with mock providers and a fake clock, so retries,
breakers, and budgets are deterministic. Steps: route by task; retry a
transient error with jittered backoff; fall back; open a circuit
breaker; enforce the restricted-data constraint; account cost and stop
at the daily cap.
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repository root

from atlas.core.identity import DIRECTORY
from atlas.gateway.gateway import (AllProvidersFailed, BudgetExceeded, Gateway, Ledger,
                                   ModelRequest)
from atlas.gateway.providers import MockProvider

ALICE = DIRECTORY["alice"]
REQ = ModelRequest(task="judge", system="Grade.", user=json.dumps(
    {"answer": "five days", "must_contain_facts": ["five days"]}))
now = [0.0]
sleeps = []


def build(primary, fallback, cap=5.0):
    chain = [(primary, "mock-large"), (fallback, "mock-small")]
    return Gateway({"judge": chain}, Ledger(daily_cap_usd=cap, clock=lambda: 86400 * 10),
                   max_attempts=2, breaker_threshold=3, breaker_cooldown_s=30,
                   sleep=sleeps.append, rng=random.Random(1), clock=lambda: now[0])


print("== Step 1: a healthy call")
g = build(MockProvider(name="primary"), MockProvider(name="fallback"))
r = g.complete(REQ, ALICE)
print(f"  provider={r.response.provider} attempts={r.attempts} cost=${r.cost_usd}")

print("\n== Step 2: transient error, retried with jittered backoff")
g = build(MockProvider(name="primary", fail_next=1), MockProvider(name="fallback"))
r = g.complete(REQ, ALICE)
print(f"  attempts={r.attempts}\n  backoff slept {sleeps[-1]:.3f}s (random in [0, 0.25])")

print("\n== Step 3: primary down: fall back")
p, f = MockProvider(name="primary", fail_next=100), MockProvider(name="fallback")
g = build(p, f)
r = g.complete(REQ, ALICE)
print(f"  provider={r.response.provider} fallback_used={r.fallback_used}")
print(f"  attempts={r.attempts}")

print("\n== Step 4: the breaker opens and the primary is skipped without a call")
for _ in range(2):
    g.complete(REQ, ALICE)
calls = p.calls
r = g.complete(REQ, ALICE)
print(f"  breaker={g.breaker('primary', 'mock-large').state} primary calls unchanged: "
      f"{p.calls == calls}\n  attempts={r.attempts}")
now[0] += 31
p.fail_next = 0
r = g.complete(REQ, ALICE)
print(f"  after cooldown: provider={r.response.provider} "
      f"breaker={g.breaker('primary', 'mock-large').state}")

print("\n== Step 5: restricted context never leaves the region")
out = MockProvider(name="out-of-region", in_region=False)
inr = MockProvider(name="in-region")
g = build(out, inr)
r = g.complete(ModelRequest(task="judge", system="s", user=REQ.user,
                            sensitivity="restricted"), ALICE)
print(f"  provider={r.response.provider} out-of-region calls={out.calls}")
g2 = build(MockProvider(name="out", in_region=False), MockProvider(name="out2", in_region=False))
try:
    g2.complete(ModelRequest(task="judge", system="s", user=REQ.user,
                             sensitivity="restricted"), ALICE)
except AllProvidersFailed as exc:
    print(f"  no eligible provider -> {exc.attempts}")

print("\n== Step 6: cost accounting and the daily cap")
g = build(MockProvider(name="primary"), MockProvider(name="fallback"), cap=0.001)
spent = 0
try:
    for i in range(1000):
        spent += g.complete(REQ, ALICE).cost_usd
except BudgetExceeded as exc:
    print(f"  stopped after {i} calls, ${spent:.6f} spent: {exc}")
by_task = {}
for rec in g.ledger.records:
    by_task[(rec.user_id, rec.task, rec.model)] = by_task.get(
        (rec.user_id, rec.task, rec.model), 0) + rec.cost_usd
print(f"  attribution: {by_task}")
