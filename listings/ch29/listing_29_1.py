"""Listing 29.1. An approval gate with proposal-bound, expiring
approvals and an audit log.

Chapter 29, Human Oversight. Verified by execution.
Run with: python run.py 29.1
"""
import hashlib
import json
import time
from dataclasses import dataclass, field


def proposal_hash(tool: str, args: dict) -> str:
    raw = json.dumps([tool, args], sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:12]


@dataclass
class Approval:
    run_id: str
    phash: str
    decision: str
    reviewer: str
    edited_args: "dict | None"
    expires_at: float


@dataclass
class ReviewQueue:
    # run_id -> request
    pending: dict = field(default_factory=dict)
    # (run_id, phash) -> Approval
    decisions: dict = field(default_factory=dict)
    audit: list = field(default_factory=list)
    ttl_s: float = 3600.0

    def request(self, run_id, user, tool, args, justification):
        ph = proposal_hash(tool, args)
        self.pending[run_id] = {
            "user": user, "tool": tool, "args": args,
            "justification": justification, "phash": ph}
        self.audit.append(("requested", run_id, ph))
        return ph

    def decide(self, run_id, reviewer, decision, edited_args=None,
               now=None):
        req = self.pending.pop(run_id)
        if reviewer == req["user"]:
            raise PermissionError(
                "requester cannot approve their own action")
        args = edited_args if edited_args is not None else req["args"]
        # The approval binds to the final arguments.
        ph = proposal_hash(req["tool"], args)
        a = Approval(run_id, ph, decision, reviewer, edited_args,
                     (now or time.time()) + self.ttl_s)
        self.decisions[(run_id, ph)] = a
        self.audit.append((decision, run_id, ph, reviewer))
        return a

    def is_approved(self, run_id, tool, args, now=None) -> bool:
        a = self.decisions.get(
            (run_id, proposal_hash(tool, args)))
        return bool(a and a.decision == "approve"
                    and (now or time.time()) < a.expires_at)


if __name__ == "__main__":
    q = ReviewQueue()
    args = {"summary": "VPN drops on wifi", "priority": "P3"}
    q.request("run-31", "alice", "draft_ticket", args,
              "no open ticket found")
    try:
        q.decide("run-31", "alice", "approve")
    except PermissionError as e:
        print("self-approval:", e)
        q.pending["run-31"] = {
            "user": "alice", "tool": "draft_ticket",
            "args": args, "justification": "...",
            "phash": proposal_hash("draft_ticket", args)}
    edited = {**args, "priority": "P2"}
    q.decide("run-31", "sam", "approve", edited_args=edited)

    def ok(a, **k):
        return q.is_approved("run-31", "draft_ticket", a, **k)

    print("original args approved?", ok(args))
    print("edited args approved?  ", ok(edited))
    print("after expiry?          ",
          ok(edited, now=time.time() + 7200))
    print("audit:", q.audit)
