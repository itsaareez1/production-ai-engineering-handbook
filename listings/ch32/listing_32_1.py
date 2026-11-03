"""Listing 32.1. A first-pass failure classifier applying the
taxonomy's diagnostics to trace records.

Chapter 32, The Failure Taxonomy. Verified by execution.
Run with: python run.py 32.1
"""
from dataclasses import dataclass, field


@dataclass
class Trace:
    request_id: str
    model_version: str
    expected_model_version: str
    # relevant chunk among candidates
    retrieval_recall_hit: bool
    # relevant chunk survived budgeting
    context_included_relevant: bool
    # each entry is {name, error}
    tool_calls: list = field(default_factory=list)
    external_errors: list = field(default_factory=list)
    steps_expected: int = 0
    steps_taken: int = 0
    answer_valid: bool = True
    answer_correct: bool = True
    supported_by_context: bool = True


def classify(t: Trace) -> str:
    if t.answer_correct:
        return "no-failure"
    if t.model_version != t.expected_model_version:
        return "operational: model version mismatch"
    if not t.retrieval_recall_hit:
        return "retrieval: relevant material not retrieved"
    if not t.context_included_relevant:
        return "context: relevant material dropped or mislaid"
    if any(c.get("error") for c in t.tool_calls):
        return "tool: call failed or misused"
    if t.external_errors:
        return "integration: external system error"
    if t.steps_taken != t.steps_expected:
        return "orchestration: control flow deviated"
    if not t.answer_valid:
        return "model: format or contract violation"
    if not t.supported_by_context:
        return "model: unsupported inference from correct context"
    return "unclassified: needs review"


if __name__ == "__main__":
    base = dict(model_version="m-2026-06",
                expected_model_version="m-2026-06",
                retrieval_recall_hit=True,
                context_included_relevant=True,
                steps_expected=3, steps_taken=3,
                answer_correct=False)
    cases = {
        "stale policy cited":
            Trace("r1", **{**base, "retrieval_recall_hit": False}),
        "dropped by budget":
            Trace("r2", **{**base,
                           "context_included_relevant": False}),
        "wrong model deployed":
            Trace("r3", **{**base, "model_version": "m-2026-03"}),
        "invented a rule":
            Trace("r4", **{**base,
                           "supported_by_context": False}),
        "loop skipped verifier":
            Trace("r5", **{**base, "steps_taken": 2}),
        "correct answer":
            Trace("r6", **{**base, "answer_correct": True}),
    }
    for name, tr in cases.items():
        print(f"{name:24s} -> {classify(tr)}")
