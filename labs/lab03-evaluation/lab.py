"""Lab 3: Build an AI evaluation pipeline (Chapters 33-38).

Runs offline. Steps: load and version the golden set; grade the
baseline deterministically per category with Wilson intervals;
calibrate the judge against human labels (agreement and kappa); run a
candidate with a regression confined to one category; let the paired,
per-category gate decide; write a report.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repository root

from atlas.core.identity import DIRECTORY
from atlas.evaluation.harness import calibrate_judge, load_golden, regression_gate, run
from atlas.gateway.gateway import ModelRequest
from atlas.gateway.providers import MockProvider
from atlas.testing import ROOT, make_atlas

HERE = Path(__file__).resolve().parent
items, version = load_golden(ROOT / "examples/evaluation/golden_set.jsonl")
print(f"== Step 1: golden set {version}: {len(items)} items, "
      f"categories {sorted({i.category for i in items})}")

print("\n== Step 2: baseline, graded per category")
base_sys = make_atlas()
baseline = run(items, base_sys.ask, version, base_sys.versions())
for cat, m in baseline.by_category().items():
    print(f"  {cat:<13} n={m['n']}  pass={m['pass_rate']:.2f}  95% CI {m['wilson_95']}")
print(f"  overall       {baseline.overall()}")
failed = [k for k, v in baseline.per_item.items() if not v["grades"]["pass"]]
print(f"  failed items: {failed} -> {baseline.per_item[failed[0]]['grades']}")


def judge(item, answer) -> int:
    r = base_sys.gateway.complete(ModelRequest(task="judge", system="Grade.", user=json.dumps(
        {"answer": answer.get("answer", ""), "must_contain_facts": list(item.must_contain_facts)})),
        DIRECTORY[item.user])
    ok = json.loads(r.response.text)["correct"]
    escalated = bool(answer.get("escalate")) or not answer.get("supported")
    return int(ok and escalated == item.must_escalate)


print("\n== Step 3: judge calibration against human labels")
cal = calibrate_judge(items, baseline, judge)
print(f"  {cal}")
print("  (the mock judge grades with the same reference facts, so perfect agreement here")
print("   shows the machinery works; a real model judge must earn its kappa, Ch. 35)")


class FriendlyRewrite(MockProvider):
    """A candidate whose new instructions add an unsupported, friendly
    sentence to every leave answer (the Chapter 38 regression)."""

    def _answer(self, prompt, fault):
        out = json.loads(super()._answer(prompt, fault))
        q = prompt.rsplit("QUESTION:", 1)[-1].lower()
        if ("leave" in q or "carr" in q) and out.get("supported"):
            out["answer"] += " Your manager will usually agree to more if you ask nicely."
        return json.dumps(out)


print("\n== Step 4: candidate with a regression confined to one category")
cand_sys = make_atlas(primary=FriendlyRewrite(name="mock-primary"),
                      fallback=FriendlyRewrite(name="mock-fallback"))
candidate = run(items, cand_sys.ask, version, cand_sys.versions())
for cat, m in candidate.by_category().items():
    print(f"  {cat:<13} n={m['n']}  pass={m['pass_rate']:.2f}")

print("\n== Step 5: the regression gate")
gate = regression_gate(baseline, candidate, tolerance=0.02)
for cat, r in gate["categories"].items():
    print(f"  {cat:<13} delta={r['delta']:+.2f}  CI={r['ci95']}  {r['verdict']}")
print(f"  DECISION: {gate['decision']} (blocked: {gate['blocked']})")

report = HERE / "eval_report.md"
lines = ["# Evaluation report", "", f"Golden set: `{version}` ({len(items)} items)",
         f"System: `{baseline.system_versions}`", "", "| Category | n | Baseline | Candidate | Gate |",
         "|---|---|---|---|---|"]
for cat, r in gate["categories"].items():
    lines.append(f"| {cat} | {r['n']} | {baseline.by_category()[cat]['pass_rate']:.2f} | "
                 f"{candidate.by_category()[cat]['pass_rate']:.2f} | {r['verdict']} |")
lines += ["", f"Judge calibration: agreement {cal['agreement']}, kappa {cal['kappa']} (n={cal['n']}).",
          f"Decision: **{gate['decision']}**."]
report.write_text("\n".join(lines) + "\n")
print(f"\n  report written: {report.name}")
