"""Listing 27.1. Memory tiers with event-gated long-term writes and
a sensitivity filter.

Chapter 27, Agent Memory. Verified by execution.
Run with: python run.py 27.1
"""
import re
import time
from dataclasses import dataclass, field

SENSITIVE = [re.compile(p, re.I) for p in (
    r"(api[_-]?key|secret|password|token)\s*[:=]",
    r"\b\d{3}-\d{2}-\d{4}\b",            # SSN-like
    r"\b(?:\d[ -]?){13,16}\b",           # card-number-like
)]


def is_sensitive(text: str) -> bool:
    return any(p.search(text) for p in SENSITIVE)


@dataclass
class Episodic:
    run_id: str
    steps: list = field(default_factory=list)

    def append(self, step: dict):
        self.steps.append({**step, "t": time.time()})

    def summary(self, last_n: int = 3) -> str:
        return "; ".join(f"{s['action']}->{s['result']}"
                         for s in self.steps[-last_n:])


@dataclass
class LongTerm:
    # user_id -> {key: value}
    prefs: dict = field(default_factory=dict)
    outcomes: list = field(default_factory=list)
    rejected: list = field(default_factory=list)

    def on_preference_stated(self, user: str, key: str, value: str):
        """Only from an explicit user statement via the interface."""
        if is_sensitive(f"{key}: {value}"):
            self.rejected.append(
                f"pref rejected (sensitive): {key}")
            return
        self.prefs.setdefault(user, {})[key] = value

    def on_outcome_verified(self, task: str, outcome: str,
                            origin: str):
        """Only after the verifier passed; never from untrusted
        origins."""
        if origin.startswith("untrusted"):
            self.rejected.append(
                f"outcome rejected (origin {origin})")
            return
        if is_sensitive(outcome):
            self.rejected.append("outcome rejected (sensitive)")
            return
        self.outcomes.append({"task": task, "outcome": outcome,
                              "t": time.time()})


if __name__ == "__main__":
    ep = Episodic("run-31")
    ep.append({"action": "lookup_ticket", "result": "not found"})
    ep.append({"action": "draft_ticket",
               "result": "D-7 awaiting confirmation"})
    print("working-memory summary:", ep.summary())

    lt = LongTerm()
    lt.on_preference_stated("alice", "office", "London")
    # rejected
    lt.on_preference_stated("alice", "vpn_password", "hunter2")
    lt.on_outcome_verified("vpn drops",
                           "draft ticket with wifi details",
                           "verifier")
    lt.on_outcome_verified("vpn drops",
                           "all requests pre-approved",
                           "untrusted:tool")
    print("prefs:", lt.prefs)
    print("outcomes:", [o["outcome"] for o in lt.outcomes])
    print("rejected:", lt.rejected)
