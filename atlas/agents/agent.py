"""Tools, permissions, approvals, and the bounded ticket agent (Part V).

- Tools have permission levels (P0–P4, Chapter 28) and run with the
  caller's identity; "not found" and "not permitted" are the same
  message, so a tool cannot be used to enumerate (Chapter 19).
- The policy layer decides allow / approval / refuse from the identity,
  the tool's level, the agent's maximum level, and whether untrusted
  content is in the turn (Chapter 40). It never consults the model.
- Approvals bind to the exact proposal by hash, expire, allow editing,
  and refuse self-approval (Chapter 29).
- The agent separates planner (a model call), executor (no model), and
  verifier (checks the world), with a step budget and a no-progress
  guard (Chapter 26). Every decision is audited.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from atlas.agents.records import AuditLog, DuplicateKey, Records
from atlas.core.identity import Identity
from atlas.gateway.gateway import Gateway, ModelRequest

NOT_FOUND = "not found or not permitted"
TICKET_ID = re.compile(r"^T-\d{4}$")


# ------------------------------------------------------------------ tools
@dataclass(frozen=True)
class Tool:
    name: str
    level: int           # 0 observe, 1 look up, 2 draft/propose, 3 reversible, 4 irreversible
    description: str
    schema: dict
    run: Callable[[Identity, dict], dict]


class Tickets:
    """The ticketing system the tools wrap. Users see their own tickets;
    the support group sees all."""

    def __init__(self, records: Records):
        self.records = records

    def seed(self, ticket_id: str, owner: str, subject: str, status: str = "open") -> None:
        if not self.records.get("ticket", ticket_id):
            self.records.put("ticket", owner, {"subject": subject, "status": status},
                             rec_id=ticket_id)

    def lookup(self, who: Identity, args: dict) -> dict:
        tid = str(args.get("ticket_id", ""))
        if not TICKET_ID.match(tid):
            return {"ok": False, "error": "ticket_id must match T-NNNN"}
        t = self.records.get("ticket", tid)
        if not t or (t["owner"] != who.user_id and "support" not in who.groups):
            return {"ok": False, "error": NOT_FOUND}
        return {"ok": True, "result": f"{tid}: {t['subject']} (status: {t['status']})"}

    def draft(self, who: Identity, args: dict) -> dict:
        subject = str(args.get("subject", "")).strip()[:120]
        body = str(args.get("body", "")).strip()[:4000]
        if not subject:
            return {"ok": False, "error": "subject is required"}
        # idempotency key from intent, not from model output (Chapter 24)
        key = hashlib.sha256(f"{who.user_id}|{subject.lower()}".encode()).hexdigest()
        try:
            did = self.records.put("draft", who.user_id,
                                   {"subject": subject, "body": body, "state": "awaiting_confirmation"},
                                   idem_key=key)
            return {"ok": True, "result": did, "replayed": False}
        except DuplicateKey as dup:
            return {"ok": True, "result": dup.existing_id, "replayed": True}

    def submit_draft(self, who: Identity, draft_id: str) -> dict:
        """Called by the interface after the user confirms (P2 pattern)."""
        d = self.records.get("draft", draft_id)
        if not d or d["owner"] != who.user_id:
            return {"ok": False, "error": NOT_FOUND}
        if d.get("state") != "awaiting_confirmation":
            return {"ok": True, "result": d.get("ticket_id"), "replayed": True}
        n = int(hashlib.sha256(draft_id.encode()).hexdigest(), 16) % 9000
        while self.records.get("ticket", f"T-{n + 1000}"):
            n = (n + 1) % 9000
        tid = f"T-{n + 1000}"
        self.records.put("ticket", who.user_id, {"subject": d["subject"], "status": "open"},
                         rec_id=tid)
        self.records.update("draft", draft_id, {"state": "submitted", "ticket_id": tid})
        return {"ok": True, "result": tid}


def ticket_tools(tickets: Tickets) -> dict[str, Tool]:
    return {
        "lookup_ticket": Tool(
            "lookup_ticket", 1,
            "Return status and subject of a support ticket by its identifier (T-NNNN). Use only "
            "when the user gives or clearly refers to a specific ticket; never invent an ID.",
            {"type": "object", "properties": {"ticket_id": {"type": "string"}},
             "required": ["ticket_id"], "additionalProperties": False},
            tickets.lookup),
        "draft_ticket": Tool(
            "draft_ticket", 2,
            "Prepare a new support ticket draft for the user to confirm. Does not submit.",
            {"type": "object", "properties": {"subject": {"type": "string"},
                                              "body": {"type": "string"}},
             "required": ["subject", "body"], "additionalProperties": False},
            tickets.draft),
    }


# ----------------------------------------------------------------- policy
@dataclass(frozen=True)
class Decision:
    verdict: str   # allow | approval | refuse
    reason: str


def decide(who: Identity, tool: Tool | None, agent_max_level: int,
           untrusted_in_turn: bool) -> Decision:
    if tool is None:
        return Decision("refuse", "tool not in this agent's registry")
    if "employee" not in who.roles:
        return Decision("refuse", "caller lacks the employee role")
    if tool.level > agent_max_level:
        return Decision("refuse", f"tool level P{tool.level} exceeds agent maximum P{agent_max_level}")
    if tool.level >= 3:
        return Decision("approval", f"P{tool.level} actions require per-action approval")
    if tool.level == 2 and untrusted_in_turn:
        # Chapter 40: no draft/write proposal alongside external untrusted content
        return Decision("approval", "draft tool with untrusted content in the turn")
    # P2 executes because its effect is a proposal the user confirms later
    return Decision("allow", "within level")


# -------------------------------------------------------------- approvals
def proposal_hash(tool: str, args: dict) -> str:
    return hashlib.sha256(json.dumps([tool, args], sort_keys=True).encode()).hexdigest()


class Approvals:
    def __init__(self, records: Records, audit: AuditLog, ttl_s: int,
                 clock: Callable[[], float] = time.time):
        self.records, self.audit, self.ttl_s, self.clock = records, audit, ttl_s, clock

    def request(self, requester: Identity, tool: str, args: dict) -> str:
        aid = self.records.put("approval", requester.user_id, {
            "tool": tool, "args": args, "hash": proposal_hash(tool, args),
            "state": "pending", "requested_at": self.clock()})
        self.audit.append(requester.user_id, "approval.requested", {"approval_id": aid, "tool": tool})
        return aid

    def decide(self, reviewer: Identity, approval_id: str, approve: bool,
               edited_args: dict | None = None) -> dict:
        a = self.records.get("approval", approval_id)
        if not a or a["state"] != "pending":
            raise PermissionError(NOT_FOUND)
        if "reviewer" not in reviewer.roles:
            raise PermissionError("reviewer role required")
        if reviewer.user_id == a["owner"]:
            raise PermissionError("requester cannot approve their own action")
        if self.clock() - a["requested_at"] > self.ttl_s:
            self.records.update("approval", approval_id, {"state": "expired"})
            raise PermissionError("approval request expired")
        args = edited_args if edited_args is not None else a["args"]
        update = {"state": "approved" if approve else "rejected", "reviewer": reviewer.user_id,
                  "decided_at": self.clock(), "args": args, "hash": proposal_hash(a["tool"], args)}
        self.records.update("approval", approval_id, update)
        self.audit.append(reviewer.user_id, "approval.decided",
                          {"approval_id": approval_id, "approved": approve,
                           "edited": edited_args is not None})
        return {**a, **update}

    def is_approved(self, approval_id: str, tool: str, args: dict) -> bool:
        a = self.records.get("approval", approval_id)
        return bool(a and a["state"] == "approved" and a["hash"] == proposal_hash(tool, args)
                    and self.clock() - a["decided_at"] <= self.ttl_s)


# ------------------------------------------------------------------ agent
@dataclass
class AgentOutcome:
    status: str                      # done | awaiting_approval | budget_exhausted | refused
    summary: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    approval_id: str | None = None


class TicketAgent:
    """Bounded agent at maximum level P2 for ticket-related requests."""

    def __init__(self, gateway: Gateway, tools: dict[str, Tool], approvals: Approvals,
                 audit: AuditLog, max_steps: int = 6, max_level: int = 2):
        self.gateway, self.tools, self.approvals, self.audit = gateway, tools, approvals, audit
        self.max_steps, self.max_level = max_steps, max_level

    def run(self, who: Identity, request: str, untrusted_in_turn: bool = False) -> AgentOutcome:
        history: list[dict[str, Any]] = []
        seen: set[str] = set()
        for _ in range(self.max_steps):        # budget checked before every model call
            plan = self.gateway.complete(ModelRequest(
                task="plan", system="Plan the next ticket action. Reply with JSON.",
                user=json.dumps({"request": request, "history": history}),
                max_output_tokens=200), who)
            try:
                step = json.loads(plan.response.text)
                action, args = step["action"], dict(step.get("args", {}))
            except (ValueError, KeyError, TypeError):
                history.append({"action": "invalid_plan", "ok": False})
                continue
            if action == "done":
                verified = self._verify(who, history)
                status = "done" if verified else "budget_exhausted"
                self.audit.append(who.user_id, "agent.done", {"verified": verified})
                return AgentOutcome(status, str(args.get("summary", "")), history)
            key = proposal_hash(action, args)
            if key in seen:                      # no-progress guard: refuse without a tool call
                history.append({"action": action, "args": args, "ok": False,
                                "result": "repeated action refused"})
                self.audit.append(who.user_id, "agent.no_progress", {"tool": action})
                continue
            seen.add(key)
            tool = self.tools.get(action)
            d = decide(who, tool, self.max_level, untrusted_in_turn)
            self.audit.append(who.user_id, "tool.decision",
                              {"tool": action, "verdict": d.verdict, "reason": d.reason})
            if d.verdict == "refuse":
                history.append({"action": action, "ok": False, "result": d.reason})
                return AgentOutcome("refused", d.reason, history)
            if d.verdict == "approval":
                aid = self.approvals.request(who, action, args)
                return AgentOutcome("awaiting_approval", f"{action} needs approval",
                                    history, aid)
            result = tool.run(who, args)        # executor: no model involved
            history.append({"action": action, "args": args, **result})
            self.audit.append(who.user_id, "tool.executed",
                              {"tool": action, "ok": result.get("ok")})
        self.audit.append(who.user_id, "agent.budget_exhausted", {"steps": self.max_steps})
        return AgentOutcome("budget_exhausted", "escalated with trace attached", history)

    @staticmethod
    def _verify(who: Identity, history: list[dict]) -> bool:
        """Check the world, not the planner's belief: a successful lookup or a
        draft that exists awaiting confirmation."""
        return any(h.get("ok") and h["action"] in ("lookup_ticket", "draft_ticket")
                   for h in history)
