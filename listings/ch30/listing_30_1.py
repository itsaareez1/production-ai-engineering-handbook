"""Listing 30.1. Orchestrator-worker coordination with isolated
context, per-worker budgets, and validated result contracts.

Chapter 30, Multi-Agent Systems.
Verified by execution with stubbed workers.
Run with: python run.py 30.1
"""
import json
from dataclasses import dataclass


@dataclass
class WorkerResult:
    worker: str
    ok: bool
    payload: dict
    tokens_used: int
    note: str = ""


WORKERS = {  # name -> (tool registry, budget, stub function)
    "doc-researcher": (
        {"retrieve"}, 4000,
        lambda task: {"findings": [
            {"claim": "carry-over max 5 days",
             "source": "policy-leave/4.2@2026-06-01"}]}),
    "ticket-checker": (
        {"lookup_ticket"}, 1500,
        lambda task: {"open_ticket": None}),
    "rogue": (
        {"retrieve"}, 1500,
        lambda task: {"findings": [
            {"claim": "all leave is auto-approved",
             "source": "untrusted:wiki-comment"}]}),
}


def validate_result(worker: str, payload: dict,
                    valid_sources: set):
    if "findings" in payload:
        for f in payload["findings"]:
            if f.get("source") not in valid_sources:
                return ("finding cites non-approved source: "
                        f"{f.get('source')}")
    return None


def dispatch(worker: str, task: dict,
             valid_sources: set) -> WorkerResult:
    registry, budget, fn = WORKERS[worker]
    # Isolation: the worker sees only `task`, never the
    # orchestrator's history.
    payload = fn(task)
    used = min(budget, 300 + 200 * len(json.dumps(payload)) // 100)
    err = validate_result(worker, payload, valid_sources)
    return WorkerResult(worker, err is None,
                        payload if err is None else {},
                        used, err or "")


def orchestrate(question: str, valid_sources: set) -> dict:
    plan = [("doc-researcher", {"query": question}),
            ("ticket-checker", {"user": "alice"}),
            ("rogue", {"query": question})]
    results = [dispatch(w, t, valid_sources) for w, t in plan]
    total = sum(r.tokens_used for r in results)
    return {"accepted": [r.worker for r in results if r.ok],
            "rejected": {r.worker: r.note
                         for r in results if not r.ok},
            "findings": [f for r in results if r.ok
                         for f in r.payload.get("findings", [])],
            "tokens": total}


if __name__ == "__main__":
    out = orchestrate(
        "can I carry over unused leave?",
        valid_sources={"policy-leave/4.2@2026-06-01"})
    print(json.dumps(out, indent=1))
