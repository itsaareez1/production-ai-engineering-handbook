"""Listing 36.1. Claim-level grounding with a stubbed entailment
judge, and a calibration table for the system's reported confidence.

Chapter 36, Groundedness and Hallucination. Verified by execution.
Run with: python run.py 36.1
"""
import re
from collections import defaultdict


def split_claims(answer: str) -> list:
    # Production: a model decomposes into atomic claims.
    # Stub: sentence split.
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", answer)
            if s.strip()]


class StubEntailment:
    """Stands in for an NLI-style or model judge: does the passage
    support the claim?"""

    def supports(self, claim: str, passage: str) -> bool:
        key = [w for w in re.findall(r"[a-z]+", claim.lower())
               if len(w) > 4]
        return (sum(w in passage.lower() for w in key)
                >= max(1, len(key) // 2))


def groundedness(answer: str, cited: dict, judge) -> dict:
    claims = split_claims(answer)
    results = []
    for c in claims:
        supported = any(judge.supports(c, p)
                        for p in cited.values())
        results.append((c, supported))
    rate = (sum(s for _, s in results) / len(results)
            if results else 1.0)
    return {"claims": len(claims), "supported_rate": rate,
            "unsupported": [c for c, s in results if not s]}


def confidence_calibration(records: list) -> dict:
    """records: (reported confidence, was_correct) -> per-bucket
    (n, accuracy)."""
    b = defaultdict(list)
    for conf, ok in records:
        b[conf].append(ok)
    return {k: (len(v), sum(v) / len(v)) for k, v in b.items()}


if __name__ == "__main__":
    cited = {
        "policy-leave/4.2@2026-06-01":
            "Unused annual leave may be carried forward up to five "
            "days into the next leave year, subject to manager "
            "approval."
    }
    answer = ("Up to five days of unused annual leave may be "
              "carried forward. "
              "This requires manager approval. "
              "Contractors are excluded from carry-over.")
    g = groundedness(answer, cited, StubEntailment())
    print(f"claims {g['claims']}, "
          f"supported {g['supported_rate']:.2f}, "
          f"unsupported: {g['unsupported']}")

    records = ([("high", True)] * 180 + [("high", False)] * 20
               + [("medium", True)] * 60 + [("medium", False)] * 40
               + [("low", True)] * 15 + [("low", False)] * 35)
    for conf, (n, acc) in confidence_calibration(records).items():
        print(f"confidence={conf:6s} n={n:3d} accuracy={acc:.2f}")
