"""Listing 48.1. Release manifest with four pinned artifacts, canary
decision against bounds, and rollback to the previous manifest.

Chapter 48, Release and Change Management. Verified by execution.
Run with: python run.py 48.1
"""
import hashlib
import json
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Manifest:
    code: str
    instructions_hash: str
    model_version: str
    index_version: str
    judge_version: str
    gate_run_id: str

    @property
    def id(self):
        raw = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()[:10]


BOUNDS = {  # from requirements (Ch. 5) and SLOs (Ch. 37)
    "quality_min": 0.93, "quality_max_drop": 0.02,
    "validation_fail_max": 0.03, "escalation_band": (0.08, 0.20),
    "cost_per_req_max_ratio": 1.15, "p95_latency_max_ms": 6000,
}


def canary_decision(baseline: dict, canary: dict, graded: int,
                    min_graded: int = 400):
    reasons = []
    if graded < min_graded:
        return "continue-soak", [
            f"only {graded}/{min_graded} graded answers"]
    if canary["quality"] < BOUNDS["quality_min"]:
        reasons.append(
            f"quality {canary['quality']:.3f} below floor")
    if (baseline["quality"] - canary["quality"]
            > BOUNDS["quality_max_drop"]):
        drop = baseline["quality"] - canary["quality"]
        reasons.append(f"quality dropped {drop:+.3f}")
    if canary["validation_fail"] > BOUNDS["validation_fail_max"]:
        reasons.append(
            f"validation failures "
            f"{canary['validation_fail']:.3f}")
    lo, hi = BOUNDS["escalation_band"]
    if not lo <= canary["escalation"] <= hi:
        reasons.append(
            f"escalation {canary['escalation']:.3f} outside band")
    cost_cap = (baseline["cost_per_req"]
                * BOUNDS["cost_per_req_max_ratio"])
    if canary["cost_per_req"] > cost_cap:
        reasons.append(
            f"cost/req {canary['cost_per_req']:.4f} "
            f"vs {baseline['cost_per_req']:.4f}")
    if canary["p95_ms"] > BOUNDS["p95_latency_max_ms"]:
        reasons.append(f"p95 {canary['p95_ms']} ms")
    return ("rollback" if reasons else "promote"), reasons


class Releases:
    def __init__(self):
        self.history: list = []

    def current(self):
        return self.history[-1] if self.history else None

    def promote(self, m: Manifest):
        self.history.append(m)
        return m.id

    def rollback(self) -> Manifest:
        self.history.pop()
        # All four artifacts are restored, not just the code.
        return self.current()


if __name__ == "__main__":
    rel = Releases()
    prod = Manifest("2026.09.2", "a91f", "m-2026-06", "idx-0905",
                    "j-2026-05", "gate-311")
    rel.promote(prod)
    cand = Manifest("2026.09.3", "c07d", "m-2026-06", "idx-0912",
                    "j-2026-05", "gate-318")
    baseline = {"quality": 0.951, "validation_fail": 0.012,
                "escalation": 0.11, "cost_per_req": 0.0281,
                "p95_ms": 4900}
    canary = {"quality": 0.947, "validation_fail": 0.014,
              "escalation": 0.12, "cost_per_req": 0.0295,
              "p95_ms": 5100}
    print(canary_decision(baseline, canary, graded=180))
    decision, why = canary_decision(baseline, canary, graded=460)
    print(decision, why)
    if decision == "promote":
        rel.promote(cand)
    live = rel.current()
    print("live:", live.code, live.index_version,
          "| manifest", live.id)
    bad = {**canary, "quality": 0.921, "cost_per_req": 0.041}
    decision, why = canary_decision(baseline, bad, graded=460)
    print(decision, why)
    if decision == "rollback":
        m = rel.rollback()
        print("rolled back to:", m.code, m.instructions_hash,
              m.model_version, m.index_version)
