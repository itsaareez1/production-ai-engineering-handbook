"""Listing 54.1. Implementation roadmap as a plan file with
ladder-mapped exit criteria and a phase checker.

Chapter 54, The Implementation Roadmap. Verified by execution.
Run with: python run.py 54.1
"""
import yaml

PLAN = """
phases:
  - name: foundations
    target_level: L2
    exit_criteria:
      - {id: reqs_file, text: "machine-readable requirements",
         chapter: 5}
      - {id: validate_all,
         text: "every output validated before use", chapter: 12}
      - {id: golden_set,
         text: "golden set >= 200 with holdout", chapter: 34}
      - {id: per_category_score,
         text: "per-category score, interval", chapter: 35}
      - {id: trace_schema,
         text: "trace per request, required attrs", chapter: 45}
  - name: hardening
    target_level: L4
    exit_criteria:
      - {id: acl_in_query,
         text: "ACL filter in retrieval query", chapter: 16}
      - {id: trust_tiers,
         text: "every source assigned a trust tier", chapter: 40}
      - {id: containment_100,
         text: "adversarial containment 100%", chapter: 39}
      - {id: gate_all,
         text: "regression gate on all four artifacts",
         chapter: 38}
      - {id: rollback_4,
         text: "rehearsed four-artifact rollback", chapter: 48}
      - {id: slos, text: "SLOs incl. quality + escalation",
         chapter: 37}
  - name: operation
    target_level: L5
    exit_criteria:
      - {id: error_budgets,
         text: "error budgets govern change", chapter: 37}
      - {id: cost_model,
         text: "cost model incl. review; caps", chapter: 46}
      - {id: owners,
         text: "named owners, change control, on-call",
         chapter: 51}
      - {id: handover,
         text: "newcomer shipped via pipeline", chapter: 50}
      - {id: readiness_go,
         text: "readiness gate GO, outsider", chapter: 53}
"""


def status(plan: dict, done: set) -> dict:
    out = {"phase": None, "level": "L0/L1", "remaining": []}
    for ph in plan["phases"]:
        remaining = [c for c in ph["exit_criteria"]
                     if c["id"] not in done]
        if remaining:
            out["phase"] = ph["name"]
            out["remaining"] = [
                f"{c['id']} (Ch. {c['chapter']})"
                for c in remaining]
            return out
        out["level"] = ph["target_level"]
    out["phase"] = "continuous"
    return out


if __name__ == "__main__":
    plan = yaml.safe_load(PLAN)
    done = {"reqs_file", "validate_all", "golden_set",
            "per_category_score", "trace_schema",
            "acl_in_query", "trust_tiers", "gate_all"}
    print(status(plan, done))
    rest = {"containment_100", "rollback_4", "slos",
            "error_budgets", "cost_model", "owners", "handover",
            "readiness_go"}
    print(status(plan, done | rest))
