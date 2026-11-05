"""Lab 6: Implement AI observability (Chapters 32, 37, 45, 46).

Runs offline. Steps: generate traffic including faults; read one trace
and check its required attributes; derive metrics; attribute cost;
classify failures from traces by earliest origin; compute an SLO
burn rate and decide whether to page.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repository root

from atlas.core.identity import DIRECTORY
from atlas.core.observability import REQUIRED
from atlas.gateway.providers import MockProvider
from atlas.testing import make_atlas

primary = MockProvider(name="mock-primary", faults=["bad_citation", "not_json"] + [None] * 4)
fallback = MockProvider(name="mock-fallback")
svc = make_atlas(primary=primary, fallback=fallback)
traffic = [("alice", "How many days of unused leave can I carry over?"),
           ("bob", "Which form do I use to request a new laptop?"),
           ("alice", "What is the salary band for a senior engineer?"),
           ("sam", "What is the salary band for a senior engineer?"),
           ("bob", "Is there a limit on taxi trips?"),
           ("alice", "What is the capital of France?"),
           ("bob", "When must carried-over leave days be used?"),
           ("alice", "What is the daily meal allowance during business travel?")]
print("== Step 1: traffic (two injected model faults)")
results = []
for user, q in traffic:
    r = svc.ask(q, DIRECTORY[user])
    results.append(r)
    print(f"  {user:<5} {r.outcome:<9} ${r.cost_usd:.6f}  {q[:50]}")
primary.fail_next = 99                         # primary outage: two more requests
for user, q in traffic[:2]:
    r = svc.ask(q, DIRECTORY[user])
    results.append(r)
    print(f"  {user:<5} {r.outcome:<9} ${r.cost_usd:.6f}  (primary down) {q[:36]}")
fallback.fail_next = 99                        # both providers down: one request
r = svc.ask(traffic[6][1], DIRECTORY["bob"])
results.append(r)
print(f"  bob   {r.outcome:<9} ${r.cost_usd:.6f}  (all providers down) {traffic[6][1][:28]}")

print("\n== Step 2: one trace, and its required attributes")
t = svc.traces.get(results[0].trace_id)
print(f"  trace {t['trace_id'][:12]}  user={t['user_id']}  versions={t['versions']}")
for s in t["spans"]:
    need = REQUIRED.get(s["name"], set())
    shown = {k: s[k] for k in sorted(need)}
    print(f"  span {s['name']:<10} {s['ms']:>6.2f} ms  required ok: {need <= set(s)}  {shown}")

print("\n== Step 3: metrics derived from traces (Prometheus format)")
for line in svc.metrics.render().splitlines():
    print("  " + line)

print("\n== Step 4: cost attribution")
by_user, by_model = Counter(), Counter()
for rec in svc.ledger.records:
    by_user[rec.user_id] += rec.cost_usd
    by_model[f"{rec.provider}/{rec.model}"] += rec.cost_usd
repairs = sum(len([s for s in svc.traces.get(r.trace_id)["spans"] if s["name"] == "gateway"]) - 1
              for r in results if svc.traces.get(r.trace_id))
print(f"  by user:  {dict((k, round(v, 6)) for k, v in by_user.items())}")
print(f"  by model: {dict((k, round(v, 6)) for k, v in by_model.items())}")
print(f"  repair calls (cost of model faults): {repairs}")


def classify(trace) -> str:
    """Earliest origin on the request path (Chapter 32, simplified)."""
    spans = {s["name"]: s for s in trace["spans"]}
    if "gateway" in spans and any("transient" in a or "breaker" in a
                                  for a in spans["gateway"].get("attempts", [])):
        if trace["outcome"] == "degraded":
            return "integration"
    if not spans.get("context", {}).get("labels"):
        return "retrieval"
    vals = [s for s in trace["spans"] if s["name"] == "validation"]
    if vals and vals[0].get("outcome") == "failed":
        return "model (repaired)" if trace["outcome"] == "answered" else "model"
    if trace["outcome"] == "escalated":
        return "retrieval or context (escalated)"
    return "ok"


print("\n== Step 5: failure classification from traces")
classes = Counter(classify(svc.traces.get(r.trace_id)) for r in results)
for k, v in classes.most_common():
    print(f"  {k:<33} {v}")

print("\n== Step 6: SLO burn rate (availability: 99.5% non-error over 30 days)")
SLO, WINDOW_DAYS = 0.995, 30
bad = sum(1 for r in results if r.outcome == "degraded")
rate = bad / len(results)
burn = rate / (1 - SLO)
print("  (illustrative: a real burn rate is computed over a full window, not 11 requests)")
print(f"  last hour: {bad}/{len(results)} degraded = {rate:.1%}; burn rate = {burn:.0f}x")
if burn:
    print(f"  at this rate the 30-day budget is gone in {WINDOW_DAYS * 24 / burn:.1f} hours")
print(f"  decision: {'PAGE' if burn >= 14.4 else 'ticket'} (page when burn >= 14.4x for 1h)")
