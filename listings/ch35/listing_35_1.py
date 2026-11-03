"""Listing 35.1. Evaluation harness: deterministic grading, a model
judge, judge calibration against human labels (agreement and Cohen's
kappa), and per-category reporting.

Chapter 35, Evaluating Generated Output.
Verified by execution with a stubbed system and judge.
Run with: python run.py 35.1

NOTE: this file is the listing exactly as printed, so that running it
reproduces the output the chapter describes. Its calibration subset
is drawn with `items[:200]`, which selects every "leave" item and no
"expenses" item at all -- see ERRATA.md, ERR-02. The corrected
version is listing_35_1_corrected.py in this directory.
"""
import random
from collections import defaultdict


def deterministic_grade(output: dict, ref: dict,
                        context_labels: set) -> dict:
    ans = output["answer"].lower()
    facts_ok = all(f.lower() in ans
                   for f in ref.get("must_contain_facts", []))
    forbid_ok = not any(f.lower() in ans
                        for f in ref.get("must_not_contain", []))
    required = ref.get("must_cite_any_of", [])
    cite_ok = (any(c.split("@")[0] in required
                   for c in output["citations"])
               if required else True)
    cite_resolve = all(c in context_labels
                       for c in output["citations"])
    esc_ok = output["escalate"] == ref.get("must_escalate", False)
    return {"facts": facts_ok, "forbidden": forbid_ok,
            "cites_required": cite_ok,
            "cites_resolve": cite_resolve, "escalation": esc_ok}


def cohen_kappa(a: list, b: list) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa = sum(a) / n
    pb = sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


class StubJudge:
    """Stands in for a model judge; agrees with humans ~92% of the
    time."""

    def __init__(self, seed=2):
        self.rng = random.Random(seed)

    def correct(self, output, ref) -> int:
        truth = ref["_human_label"]
        return truth if self.rng.random() < 0.92 else 1 - truth


def evaluate(items, system, judge, calib_ids):
    per_cat = defaultdict(lambda: defaultdict(list))
    judge_v, human_v = [], []
    cost = lat = 0.0
    for it in items:
        out, ctx_labels, c, l = system(it)
        cost += c
        lat += l
        g = deterministic_grade(out, it["reference"], ctx_labels)
        j = judge.correct(out, it["reference"])
        cat = it["meta"]["category"]
        for k, v in g.items():
            per_cat[cat][k].append(v)
        per_cat[cat]["judge_correct"].append(bool(j))
        if it["id"] in calib_ids:
            judge_v.append(j)
            human_v.append(it["reference"]["_human_label"])
    agree = (sum(x == y for x, y in zip(judge_v, human_v))
             / len(judge_v))
    return (per_cat, agree, cohen_kappa(judge_v, human_v),
            cost / len(items), lat / len(items))


def stub_system(item):
    rng = random.Random(item["id"])
    ok = rng.random() < (
        0.9 if item["meta"]["category"] != "expenses" else 0.7)
    out = {"answer": ("up to five days with manager approval" if ok
                      else "ten days, no approval"),
           "citations": (["policy-leave/4.2@2026-06-01"] if ok
                         else ["policy/ghost"]),
           "supported": True, "confidence": "high",
           "escalate": False}
    return (out, {"policy-leave/4.2@2026-06-01"}, 0.03,
            2.1 + rng.random())


def build_items(n=300):
    items = []
    for i in range(n):
        cat = "leave" if i < 200 else "expenses"
        p_ok = 0.9 if cat != "expenses" else 0.7
        human = (1 if random.Random(f"gs-{i:06d}").random() < p_ok
                 else 0)
        items.append({
            "id": f"gs-{i:06d}",
            "reference": {
                "must_contain_facts": ["five days",
                                       "manager approval"],
                "must_cite_any_of": ["policy-leave/4.2"],
                "_human_label": human},
            "meta": {"category": cat}})
    return items


def report(per_cat, agree, kappa, cost, lat):
    for cat, m in per_cat.items():
        summary = {k: f"{sum(v) / len(v):.2f}"
                   for k, v in m.items()}
        print(cat, summary)
    print(f"judge agreement {agree:.2f}, kappa {kappa:.2f} | "
          f"cost/item ${cost:.3f}, latency {lat:.1f}s")


if __name__ == "__main__":
    items = build_items()
    calib = {it["id"] for it in items[:200]}
    report(*evaluate(items, stub_system, StubJudge(), calib))
