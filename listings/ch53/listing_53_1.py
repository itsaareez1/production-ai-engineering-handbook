"""Listing 53.1. Readiness gate: mandatory items, scored items,
per-section thresholds, and the go/no-go decision, applied to Atlas.

Chapter 53, The Production Readiness Review.
Verified by execution.
Run with: python run.py 53.1
"""

SECTIONS = {
    "requirements": {
        "mandatory": ["numeric_reqs", "forbidden_errors",
                      "oversight_defined"],
        "scored": ["reviewed_quarter", "weights_by_consequence",
                   "out_of_scope"]},
    "architecture": {
        "mandatory": ["ref_arch_owners", "gateway_abstracts",
                      "validate_all", "sor_vs_index"],
        "scored": ["pattern_named", "fitness_functions",
                   "degraded_modes", "build_buy_record"]},
    "evaluation": {
        "mandatory": ["golden_versioned", "per_category_intervals",
                      "judge_calibrated", "gate_all_artifacts"],
        "scored": ["prod_sampled", "holdout_protected",
                   "leakage_check", "consistency",
                   "prod_sampling_audit"]},
    "security": {
        "mandatory": ["trust_tiers", "acl_in_query",
                      "tool_authz_user", "containment_100",
                      "no_creds_in_context"],
        "scored": ["scan_quarantine_owned", "per_turn_rules",
                   "egress_proxy", "broker", "sandbox_or_na",
                   "review_quarter"]},
    "operations": {
        "mandatory": ["trace_schema", "slos_quality_escalation",
                      "alerts_runbooks", "rollback_rehearsed"],
        "scored": ["error_budgets", "failure_injection",
                   "canary_sampling", "rebuild_timed",
                   "live_secondary"]},
    "cost": {
        "mandatory": ["full_model_review", "caps_alerts",
                      "cap_behavior"],
        "scored": ["attribution", "free_levers",
                   "trades_recorded", "monthly_review"]},
    "ownership": {
        "mandatory": ["owners_named", "change_control", "oncall",
                      "incident_process"],
        "scored": ["handover_tested", "audit_records",
                   "reg_classification", "governance_clean"]},
}


def review(answers: dict) -> dict:
    """answers: item -> True/False for mandatory, 0/1/2 for
    scored."""
    report = {"blocking": [], "sections": {}, "decision": "GO"}
    for name, sec in SECTIONS.items():
        missing = [m for m in sec["mandatory"]
                   if not answers.get(m, False)]
        score = sum(int(answers.get(s, 0)) for s in sec["scored"])
        maximum = 2 * len(sec["scored"])
        report["sections"][name] = {"score": score,
                                    "max": maximum,
                                    "missing": missing}
        report["blocking"] += [f"{name}: {m}" for m in missing]
        if score * 2 < maximum:
            report["blocking"].append(
                f"{name}: score {score}/{maximum} below half")
    if report["blocking"]:
        report["decision"] = "NO-GO"
    return report


ATLAS = {  # v1.0 answers, September 2026
    **{m: True for sec in SECTIONS.values()
       for m in sec["mandatory"]},
    "reviewed_quarter": 2, "weights_by_consequence": 2,
    "out_of_scope": 1,
    "pattern_named": 2, "fitness_functions": 2,
    "degraded_modes": 2, "build_buy_record": 2,
    "prod_sampled": 2, "holdout_protected": 2,
    "leakage_check": 2, "consistency": 1,
    "prod_sampling_audit": 2,
    "scan_quarantine_owned": 2, "per_turn_rules": 2,
    "egress_proxy": 2, "broker": 2, "sandbox_or_na": 2,
    "review_quarter": 2,
    "error_budgets": 2, "failure_injection": 1,
    "canary_sampling": 2, "rebuild_timed": 2,
    "live_secondary": 2,
    "attribution": 2, "free_levers": 2, "trades_recorded": 1,
    "monthly_review": 2,
    "handover_tested": 1, "audit_records": 2,
    "reg_classification": 2, "governance_clean": 2,
}


if __name__ == "__main__":
    r = review(ATLAS)
    for name, s in r["sections"].items():
        print(f"{name:13s} {s['score']:2d}/{s['max']:2d}  "
              f"missing: {s['missing'] or '-'}")
    print("decision:", r["decision"],
          "| blocking:", r["blocking"] or "none")
    v04 = {**ATLAS, "containment_100": False,
           "gate_all_artifacts": False, "owners_named": False,
           "handover_tested": 0, "audit_records": 0,
           "reg_classification": 0, "governance_clean": 0}
    r2 = review(v04)
    print("v0.4 decision:", r2["decision"],
          "| blocking:", r2["blocking"])
