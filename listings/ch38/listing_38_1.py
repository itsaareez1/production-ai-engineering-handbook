"""Listing 38.1. Regression gate: paired comparison of candidate
against baseline per category with bootstrap intervals, thresholds
from the requirements file, and a decision with reasons.

Chapter 38, The Regression Gate. Verified by execution.
Run with: python run.py 38.1
"""
import random

REQUIREMENTS = {
    # from the Chapter 5 requirements file
    "accuracy": {"min_correct_rate": 0.95},
    "gate": {"max_regression": 0.02, "confidence": 0.95},
}


def bootstrap_diff(base: list, cand: list, n_boot=2000, seed=9):
    """Paired bootstrap of (candidate rate - baseline rate), over
    the same items."""
    rng = random.Random(seed)
    n = len(base)
    diffs = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(cand[i] for i in idx) / n
                     - sum(base[i] for i in idx) / n)
    diffs.sort()
    lo = diffs[int(0.025 * n_boot)]
    hi = diffs[int(0.975 * n_boot) - 1]
    return sum(cand) / n - sum(base) / n, lo, hi


def gate(results: dict, metric: str):
    """results: category -> list of (baseline_pass, candidate_pass)
    per item."""
    reasons = []
    ok = True
    max_reg = REQUIREMENTS["gate"]["max_regression"]
    floor = REQUIREMENTS["accuracy"]["min_correct_rate"]
    for cat, pairs in results.items():
        base = [b for b, _ in pairs]
        cand = [c for _, c in pairs]
        diff, lo, hi = bootstrap_diff(base, cand)
        cand_rate = sum(cand) / len(cand)
        line = (f"{metric}/{cat}: cand {cand_rate:.3f} "
                f"diff {diff:+.3f} [{lo:+.3f}, {hi:+.3f}]")
        if hi < -max_reg:
            # The regression confidently exceeds the tolerance.
            ok = False
            line += "  BLOCK: regression"
        elif cand_rate < floor and diff < 0:
            ok = False
            line += "  BLOCK: below floor and not improving"
        reasons.append(line)
    return ok, reasons


def simulate(n, base_rate, cand_rate, seed):
    rng = random.Random(seed)
    return [(rng.random() < base_rate, rng.random() < cand_rate)
            for _ in range(n)]


if __name__ == "__main__":
    # Atlas 2026.09.1: tone improved; citation accuracy fell for
    # the 'leave' category.
    results = {"leave": simulate(300, 0.97, 0.90, seed=2),
               "expenses": simulate(200, 0.94, 0.95, seed=2),
               "it": simulate(200, 0.96, 0.96, seed=3)}
    ok, reasons = gate(results, "citation_accuracy")
    print("\n".join(reasons))
    print("RELEASE" if ok else "BLOCKED")
