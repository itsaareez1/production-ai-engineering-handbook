"""Listing 51.1. Ownership and change-control matrix as data, with
checks for unowned artifacts and self-approval.

Chapter 51, Ownership and Governance. Verified by execution.
Run with: python run.py 51.1
"""

OWNERS = {
    "code": "engineering", "pipeline": "engineering",
    "architecture_rules": "engineering",
    "instructions": "engineering",
    "answer_schema": "engineering",
    "model_version": "engineering",
    "index_version": "engineering",
    "corpus_scope": "knowledge",
    "quarantine_queue": "knowledge",
    "golden_set": "evaluation",
    "judge_calibration": "evaluation",
    "adversarial_suite": "security", "trust_tiers": "security",
    "permission_levels": "security", "tool_registry": "security",
    "slos": "service", "budget": "service",
    "risk_acceptance": "service",
}
# artifact -> (roles that may change, roles that must approve, notes)
CHANGE_CONTROL = {
    "code": ({"engineering"}, {"engineering"},
             "reviewer != author"),
    "instructions": ({"engineering"},
                     {"engineering", "evaluation"},
                     "gate diff in review"),
    "model_version": ({"engineering"},
                      {"engineering", "service"},
                      "longer canary"),
    "index_version": ({"engineering"},
                      {"engineering", "knowledge"},
                      "recall check"),
    "golden_set": ({"evaluation"},
                   {"evaluation", "engineering"},
                   "changes weaken gate"),
    "adversarial_suite": ({"security"},
                          {"security", "engineering"},
                          "changes weaken gate"),
    "permission_levels": ({"security"}, {"security", "service"},
                          "raises autonomy"),
    "tool_registry": ({"security", "engineering"},
                      {"security"}, ""),
    "slos": ({"service"}, {"service", "engineering"}, ""),
    "corpus_scope": ({"knowledge"}, {"knowledge", "security"},
                     "new source = new tier"),
}
ALERTS = {"quality_burn": "engineering",
          "escalation_band": "knowledge",
          "cost_cap": "service", "drift": "knowledge",
          "injection_markers": "security",
          "fallback_rate": "engineering",
          "version_mismatch": "engineering"}


def audit_governance() -> list:
    problems = []
    for art, (changers, approvers, _) in CHANGE_CONTROL.items():
        if art not in OWNERS:
            problems.append(f"{art}: no owner")
        if changers <= approvers and len(approvers) == 1:
            problems.append(f"{art}: changer can self-approve")
    for a, owner in ALERTS.items():
        if owner not in set(OWNERS.values()):
            problems.append(f"alert {a}: unknown owner")
    return problems


def may_change(role: str, artifact: str) -> bool:
    return role in CHANGE_CONTROL.get(
        artifact, (set(), set(), ""))[0]


def approval_needed(role: str, artifact: str) -> set:
    return CHANGE_CONTROL[artifact][1] - {role}


if __name__ == "__main__":
    print("governance problems:", audit_governance() or "none")
    print("evaluation may change instructions?",
          may_change("evaluation", "instructions"))
    print("engineer changes instructions; approvals needed from:",
          approval_needed("engineering", "instructions"))
    print("security raises permission level; "
          "approvals needed from:",
          approval_needed("security", "permission_levels"))
