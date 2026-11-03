"""Listing 34.1. Golden set format, stratified sampling, dev/holdout
split, and a leakage check against instruction text.

Chapter 34, The Golden Set. Verified by execution.
Run with: python run.py 34.1
"""
import hashlib
import json
import random
from collections import Counter, defaultdict

# One item per line (JSONL). References are properties, not
# canonical strings.
ITEM_EXAMPLE = {
    "id": "gs-000123", "version_added": "2026-07",
    "input": {"question": "Can I carry over unused leave after "
                          "parental leave?",
              "user_groups": ["all-staff"]},
    "reference": {"must_contain_facts": ["up to five days",
                                         "manager approval"],
                  "must_cite_any_of": ["policy-leave/4.2"],
                  "must_escalate": False,
                  "must_not_contain": ["salary"]},
    "meta": {"category": "leave", "type": "policy-lookup",
             "origin": "production",
             "labeler": "se-14", "reviewer": "se-07",
             "corpus_snapshot": "2026-07-01"},
}


def stratified_sample(logs: list, per_category: int,
                      seed: int = 3) -> list:
    rng = random.Random(seed)
    by_cat = defaultdict(list)
    for r in logs:
        by_cat[r["category"]].append(r)
    out = []
    for cat, rows in by_cat.items():
        # Oversample the consequential categories.
        weight = 2 if cat in ("escalated",
                              "restricted-user") else 1
        out += rng.sample(rows,
                          min(len(rows), per_category * weight))
    return out


def split(items: list, holdout_frac: float = 0.3, seed: int = 5):
    rng = random.Random(seed)
    ids = sorted(i["id"] for i in items)
    rng.shuffle(ids)
    cut = int(len(ids) * (1 - holdout_frac))
    dev, hold = set(ids[:cut]), set(ids[cut:])
    return ([i for i in items if i["id"] in dev],
            [i for i in items if i["id"] in hold])


def version_hash(items: list) -> str:
    ordered = sorted(items, key=lambda i: i["id"])
    blob = "\n".join(json.dumps(i, sort_keys=True)
                     for i in ordered)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def leakage_check(items: list, instruction_text: str) -> list:
    """Flag items whose question or reference facts appear in
    instructions."""
    text = instruction_text.lower()
    leaks = []
    for it in items:
        probes = ([it["input"]["question"]]
                  + it["reference"].get("must_contain_facts", []))
        if any(p.lower() in text for p in probes if len(p) > 12):
            leaks.append(it["id"])
    return leaks


if __name__ == "__main__":
    logs = (
        [{"id": f"L{i}", "category": "leave"} for i in range(60)]
        + [{"id": f"L{i}", "category": "expenses"}
           for i in range(60, 100)]
        + [{"id": f"L{i}", "category": "escalated"}
           for i in range(100, 115)]
        + [{"id": f"L{i}", "category": "restricted-user"}
           for i in range(115, 125)]
    )
    sample = stratified_sample(logs, per_category=10)
    print("sample by category:",
          dict(Counter(r["category"] for r in sample)))
    items = [{**ITEM_EXAMPLE, "id": f"gs-{i:06d}"}
             for i in range(50)]
    dev, hold = split(items)
    print("dev/holdout:", len(dev), len(hold),
          "| version:", version_hash(items))
    instr = ("Answer from sources. Example: 'Can I carry over "
             "unused leave after parental leave?'")
    print("leaks:", leakage_check(items[:3], instr))
