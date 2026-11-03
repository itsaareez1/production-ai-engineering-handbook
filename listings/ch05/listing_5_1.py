"""Listing 5.1. Atlas requirements as a machine-readable file, with a
validator.

Chapter 5, Requirements for AI Systems. Verified by execution.
Run with: python run.py 5.1
"""
import yaml

ATLAS_REQUIREMENTS = """
system: atlas
task: >
  Answer employee questions about internal policies, procedures, and
  tickets using only approved sources, with citations, and escalate
  when confidence is low or the question is out of scope.
accuracy:
  min_correct_rate: 0.95          # graded on the golden set
  max_unsupported_claim_rate: 0.02
  forbidden_errors:
    - cites a document the user cannot access
    - performs a ticket write without user confirmation
latency_ms:
  p50: 2000
  p95: 6000
throughput_rpm:
  peak: 120
cost:
  max_usd_per_request: 0.05
  max_usd_per_month: 4000
data:
  classification: internal
  may_leave_org: false            # self-hosted or contracted
                                  # provider only
  region: eu
human_oversight:
  required_for:
    - ticket_create
    - any answer flagged low_confidence
availability:
  on_provider_outage: degrade     # retrieval-only answers,
                                  # no generation
"""

REQUIRED = {
    "accuracy": {
        "min_correct_rate": float,
        "max_unsupported_claim_rate": float,
    },
    "latency_ms": {"p50": int, "p95": int},
    "cost": {
        "max_usd_per_request": float,
        "max_usd_per_month": (int, float),
    },
    "data": {"classification": str, "may_leave_org": bool},
}


def validate_requirements(doc: dict) -> list[str]:
    problems = []
    for section, fields in REQUIRED.items():
        if section not in doc:
            problems.append(f"missing section: {section}")
            continue
        for name, typ in fields.items():
            value = doc[section].get(name)
            if value is None:
                problems.append(f"missing {section}.{name}")
            elif not isinstance(value, typ):
                problems.append(
                    f"{section}.{name} has wrong type: {value!r}"
                )
    return problems


if __name__ == "__main__":
    reqs = yaml.safe_load(ATLAS_REQUIREMENTS)
    print("problems:", validate_requirements(reqs) or "none")
    reqs["latency_ms"]["p50"] = "fast"
    print("problems:", validate_requirements(reqs))
