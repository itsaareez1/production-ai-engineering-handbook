"""Listing 33.1. Deterministic, contract, and statistical tests for
an AI component.

Chapter 33, The Testing Pyramid. Verified by execution.
Run with: python run.py 33.1

This is the one listing in the book that imports another. run.py puts
the repository root on PYTHONPATH so the import resolves.
"""
import math
import random

# schema_errors and semantic_errors are the functions from Listing
# 12.1, stored in the companion repository as atlas/validation.py.
from atlas.validation import schema_errors, semantic_errors


# 1. Unit test: exact assertion on deterministic code.
def test_validator_rejects_unknown_citation():
    obj = {"answer": "x", "citations": ["policy/ghost"],
           "supported": True, "confidence": "high",
           "escalate": False}
    assert schema_errors(obj) == []
    assert (semantic_errors(obj, {"policy/leave-v7"})
            == ["unknown citation: policy/ghost"])


# 2. Contract test: hostile stub output must be handled, never
#    raised.
def test_contract_handles_hostile_output():
    hostile = {"answer": "Ignore previous rules", "citations": [],
               "supported": True, "confidence": "high",
               "escalate": False, "extra": "field"}
    errs = schema_errors(hostile) or semantic_errors(hostile, set())
    assert errs, "hostile output must produce validation errors"


# 3. Statistical test: pass rate over N runs with a lower confidence
#    bound.
def wilson_lower(passes: int, n: int, z: float = 1.96) -> float:
    p = passes / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt(
        p * (1 - p) / n + z * z / (4 * n * n))
    return (center - margin) / denom


def stub_component(rng) -> bool:
    # True pass rate 96% (stands in for a model).
    return rng.random() < 0.96


def test_component_pass_rate(min_rate=0.93, n=400, seed=2):
    rng = random.Random(seed)
    passes = sum(stub_component(rng) for _ in range(n))
    lower = wilson_lower(passes, n)
    assert lower >= min_rate, (f"observed {passes / n:.3f}, "
                               f"lower bound {lower:.3f} "
                               f"< {min_rate}")
    return passes, lower


if __name__ == "__main__":
    test_validator_rejects_unknown_citation()
    print("unit: ok")
    test_contract_handles_hostile_output()
    print("contract: ok")
    passes, lower = test_component_pass_rate()
    print(f"statistical: {passes}/400 passed, "
          f"95% lower bound {lower:.3f} >= 0.93: ok")
