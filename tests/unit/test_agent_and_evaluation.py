"""Tools, policy, approvals, audit, the bounded agent, and evaluation."""
import pytest

from atlas.agents.agent import NOT_FOUND, Approvals, Tickets, Tool, decide, ticket_tools
from atlas.agents.records import MemoryAudit, MemoryRecords
from atlas.core.identity import DIRECTORY, Identity
from atlas.evaluation.harness import (GoldenItem, RunResult, cohen_kappa, grade, load_golden,
                                      regression_gate, wilson)
from atlas.gateway.providers import MockProvider

from atlas.testing import ROOT, make_atlas

ALICE, BOB, RITA = DIRECTORY["alice"], DIRECTORY["bob"], DIRECTORY["rita"]


def tickets():
    t = Tickets(MemoryRecords())
    t.seed("T-1001", "bob", "VPN drops")
    t.seed("T-1002", "alice", "Laptop fan")
    return t


# -------------------------------------------------------------------- tools
def test_missing_and_forbidden_tickets_return_the_same_message():
    t = tickets()
    assert t.lookup(ALICE, {"ticket_id": "T-1001"}) == {"ok": False, "error": NOT_FOUND}
    assert t.lookup(ALICE, {"ticket_id": "T-9999"}) == {"ok": False, "error": NOT_FOUND}
    assert t.lookup(ALICE, {"ticket_id": "T-1002"})["ok"]
    assert t.lookup(RITA, {"ticket_id": "T-1001"})["ok"]          # support sees all


def test_tool_arguments_are_validated_semantically():
    assert tickets().lookup(ALICE, {"ticket_id": "1001; DROP"})["error"].startswith("ticket_id")


def test_draft_is_idempotent_by_intent():
    t = tickets()
    a = t.draft(ALICE, {"subject": "Monitor broken", "body": "x"})
    b = t.draft(ALICE, {"subject": "monitor broken", "body": "different words"})
    assert a["result"] == b["result"] and b["replayed"] is True


def test_submitting_a_draft_twice_creates_one_ticket():
    t = tickets()
    d = t.draft(ALICE, {"subject": "Dock", "body": "x"})["result"]
    first, second = t.submit_draft(ALICE, d), t.submit_draft(ALICE, d)
    assert first["result"] == second["result"] and second["replayed"]
    assert t.submit_draft(BOB, d)["error"] == NOT_FOUND           # not bob's draft


# ------------------------------------------------------------------- policy
def test_policy_levels_and_untrusted_rule():
    tools = ticket_tools(tickets())
    assert decide(ALICE, None, 2, False).verdict == "refuse"
    assert decide(ALICE, tools["lookup_ticket"], 2, False).verdict == "allow"
    assert decide(ALICE, tools["draft_ticket"], 2, False).verdict == "allow"
    assert decide(ALICE, tools["draft_ticket"], 2, True).verdict == "approval"
    assert decide(ALICE, tools["draft_ticket"], 1, False).verdict == "refuse"
    p4 = Tool("delete_ticket", 4, "", {}, lambda w, a: {})
    assert decide(ALICE, p4, 4, False).verdict == "approval"
    guest = Identity("g", frozenset({"all-staff"}))
    assert decide(guest, tools["lookup_ticket"], 2, False).verdict == "refuse"


# ---------------------------------------------------------------- approvals
def test_approval_binds_to_exact_proposal_and_refuses_self_approval():
    clock = [1000.0]
    ap = Approvals(MemoryRecords(), MemoryAudit(), ttl_s=600, clock=lambda: clock[0])
    aid = ap.request(ALICE, "submit_ticket", {"priority": "P1"})
    with pytest.raises(PermissionError, match="own action"):
        ap.decide(Identity("alice", frozenset(), frozenset({"reviewer"})), aid, True)
    ap.decide(RITA, aid, True, edited_args={"priority": "P3"})
    assert ap.is_approved(aid, "submit_ticket", {"priority": "P3"})
    assert not ap.is_approved(aid, "submit_ticket", {"priority": "P1"})
    clock[0] += 601
    assert not ap.is_approved(aid, "submit_ticket", {"priority": "P3"})


def test_non_reviewer_cannot_decide_and_expired_requests_cannot_be_approved():
    clock = [0.0]
    ap = Approvals(MemoryRecords(), MemoryAudit(), ttl_s=60, clock=lambda: clock[0])
    aid = ap.request(ALICE, "x", {})
    with pytest.raises(PermissionError, match="reviewer"):
        ap.decide(BOB, aid, True)
    clock[0] = 61
    with pytest.raises(PermissionError, match="expired"):
        ap.decide(RITA, aid, True)


# -------------------------------------------------------------------- audit
def test_audit_chain_detects_tampering():
    audit = MemoryAudit()
    for i in range(3):
        audit.append("alice", "tool.executed", {"i": i})
    assert audit.verify()
    audit._entries[1]["detail"] = {"i": 99}
    assert not audit.verify()


# -------------------------------------------------------------------- agent
def test_agent_looks_up_then_drafts_and_verifies():
    a = make_atlas()
    out = a.agent.run(ALICE, "Laptop dead, see T-1042")
    assert out.status == "done"
    assert [s["action"] for s in out.steps] == ["lookup_ticket", "draft_ticket"]
    assert a.audit.verify()


def test_no_progress_guard_and_step_budget_stop_a_stubborn_planner():
    a = make_atlas(primary=MockProvider(name="mock-primary", stubborn_planner=True),
                   agent_max_steps=4)
    out = a.agent.run(ALICE, "Check T-1042 please")
    assert out.status == "budget_exhausted"
    assert sum(1 for s in out.steps if s.get("result") == "repeated action refused") == 3
    assert sum(1 for s in out.steps if s["action"] == "lookup_ticket" and "error" in s) == 1


# --------------------------------------------------------------- evaluation
def test_wilson_and_kappa_known_values():
    lo, hi = wilson(384, 400)
    assert round(lo, 3) == 0.936
    assert cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0
    assert round(cohen_kappa([1, 0, 1, 0], [1, 1, 0, 0]), 3) == 0.0


def test_graders_check_facts_citations_escalation_and_forbidden_text():
    it = GoldenItem("x", "q", "alice", "leave", ("five days",), ("policy-leave",),
                    must_not_contain=("ten days",))
    good = {"answer": "Up to five days.", "citations": ["policy-leave#1@d"], "supported": True,
            "escalate": False}
    assert grade(it, good)["pass"]
    assert not grade(it, {**good, "answer": "ten days or five days"})["pass"]
    assert not grade(it, {**good, "citations": ["it-faq#0@d"]})["pass"]


def test_regression_gate_blocks_the_category_that_regressed_only():
    def rr(passes):
        r = RunResult("v", {})
        for i, (cat, ok) in enumerate(passes):
            r.per_item[f"i{i}"] = {"category": cat, "grades": {"pass": ok}}
        return r
    base = rr([("leave", True)] * 40 + [("it", True)] * 40)
    cand = rr([("leave", i % 3 != 0) for i in range(40)] + [("it", True)] * 40)
    g = regression_gate(base, cand)
    assert g["decision"] == "BLOCKED" and g["blocked"] == ["leave"]
    assert g["categories"]["it"]["verdict"] == "pass"


def test_golden_set_loads_with_a_stable_version_hash():
    items, v1 = load_golden(ROOT / "examples" / "evaluation" / "golden_set.jsonl")
    _, v2 = load_golden(ROOT / "examples" / "evaluation" / "golden_set.jsonl")
    assert len(items) == 18 and v1 == v2
