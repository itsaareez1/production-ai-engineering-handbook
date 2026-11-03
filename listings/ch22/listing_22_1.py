"""Listing 22.1. A checkpointed step-graph orchestrator with routing
and resumption.

Chapter 22, Workflow Orchestration.
Verified by execution with stubbed model steps.
Run with: python run.py 22.1
"""
import json
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Run:
    run_id: str
    state: dict = field(default_factory=dict)
    completed: list = field(default_factory=list)
    trace: list = field(default_factory=list)


class Checkpoints:
    def __init__(self):
        self.store: dict = {}

    def save(self, run: Run):
        self.store[run.run_id] = json.dumps(
            {"state": run.state, "completed": run.completed})

    def load(self, run_id: str) -> Run:
        d = json.loads(self.store[run_id])
        return Run(run_id, d["state"], d["completed"])


Step = Callable[[dict], dict]   # takes state, returns updates


def extract_terms(s):     # model step (stub)
    return {"terms": {"value": 48_000, "term_months": 24,
                      "auto_renew": True}}


def policy_check(s):      # deterministic step
    t = s["terms"]
    flags = []
    if t["value"] > 25_000:
        flags.append("value above delegated limit")
    if t["auto_renew"]:
        flags.append("auto-renewal clause")
    return {"flags": flags}


def route(s):             # deterministic router
    return {"branch": "review" if s["flags"] else "approve"}


def notify_review(s):
    # Side effect (stub); fails the first time to show resumption.
    if not s.get("_notified_once"):
        raise ConnectionError("review queue unavailable")
    return {"queued": True}


GRAPH = {  # step name -> (function, next step or router)
    "extract": (extract_terms, "check"),
    "check": (policy_check, "route"),
    "route": (route, lambda s: {"review": "notify",
                                "approve": "done"}[s["branch"]]),
    "notify": (notify_review, "done"),
}


def run_workflow(run: Run, cps: Checkpoints, start: str = "extract"):
    step = start
    while step != "done":
        fn, nxt = GRAPH[step]
        if step not in run.completed:
            run.state.update(fn(run.state))          # may raise
            run.completed.append(step)
            run.trace.append(step)
            cps.save(run)
        step = nxt(run.state) if callable(nxt) else nxt
    return run


if __name__ == "__main__":
    cps = Checkpoints()
    run = Run("contract-77")
    try:
        run_workflow(run, cps)
    except ConnectionError as e:
        print("failed after:", run.trace[-1], "|", e,
              "| completed:", run.completed)
    resumed = cps.load("contract-77")
    # Simulate the queue recovering.
    resumed.state["_notified_once"] = True
    run_workflow(resumed, cps)
    print("resumed; completed:", resumed.completed,
          "| branch:", resumed.state["branch"])
