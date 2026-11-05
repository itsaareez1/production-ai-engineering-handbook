"""Evaluation: golden sets, graders, judge calibration, and the regression gate.

Part VI as code:
- golden items have references stated as properties, metadata, and a
  version hash (Chapter 34)
- deterministic graders for everything they can express (Chapter 35)
- a model judge calibrated against human labels with agreement and
  Cohen's kappa (Chapter 35)
- per-category pass rates with Wilson intervals (Chapter 33)
- a paired, per-category bootstrap regression gate (Chapter 38)
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from atlas.core.identity import DIRECTORY, Identity


@dataclass(frozen=True)
class GoldenItem:
    id: str
    question: str
    user: str
    category: str
    must_contain_facts: tuple[str, ...] = ()
    must_cite_any_of: tuple[str, ...] = ()
    must_escalate: bool = False
    must_not_contain: tuple[str, ...] = ()
    human_label: int | None = None     # 1 correct / 0 incorrect, for judge calibration
    origin: str = "synthetic"


def load_golden(path: Path) -> tuple[list[GoldenItem], str]:
    items, h = [], hashlib.sha256()
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        h.update(line.encode())
        d = json.loads(line)
        items.append(GoldenItem(
            id=d["id"], question=d["question"], user=d["user"], category=d["category"],
            must_contain_facts=tuple(d.get("must_contain_facts", [])),
            must_cite_any_of=tuple(d.get("must_cite_any_of", [])),
            must_escalate=bool(d.get("must_escalate", False)),
            must_not_contain=tuple(d.get("must_not_contain", [])),
            human_label=d.get("human_label"), origin=d.get("origin", "synthetic")))
    ids = [i.id for i in items]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate golden-set ids")
    return items, h.hexdigest()[:12]


def grade(item: GoldenItem, answer: dict[str, Any]) -> dict[str, bool]:
    """Deterministic graders. Each returns True for pass."""
    text = answer.get("answer", "").lower()
    cites = answer.get("citations", [])
    escalated = bool(answer.get("escalate")) or not answer.get("supported", False)
    g = {
        "escalation": escalated == item.must_escalate,
        "facts": all(f.lower() in text for f in item.must_contain_facts),
        "forbidden": not any(f.lower() in text for f in item.must_not_contain),
        "citations": (not item.must_cite_any_of)
        or any(c.split("#")[0] in item.must_cite_any_of for c in cites),
    }
    g["pass"] = all(g.values())
    return g


def wilson(passes: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = passes / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    r = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - r) / d, (c + r) / d)


def cohen_kappa(a: list[int], b: list[int]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


@dataclass
class RunResult:
    golden_version: str
    system_versions: dict[str, str]
    per_item: dict[str, dict[str, Any]] = field(default_factory=dict)

    def by_category(self) -> dict[str, dict[str, Any]]:
        cats: dict[str, list[bool]] = defaultdict(list)
        for r in self.per_item.values():
            cats[r["category"]].append(r["grades"]["pass"])
        out = {}
        for cat, xs in sorted(cats.items()):
            lo, hi = wilson(sum(xs), len(xs))
            out[cat] = {"n": len(xs), "pass_rate": round(sum(xs) / len(xs), 3),
                        "wilson_95": (round(lo, 3), round(hi, 3))}
        return out

    def overall(self) -> dict[str, Any]:
        xs = [r["grades"]["pass"] for r in self.per_item.values()]
        lo, hi = wilson(sum(xs), len(xs))
        return {"n": len(xs), "pass_rate": round(sum(xs) / max(1, len(xs)), 3),
                "wilson_95": (round(lo, 3), round(hi, 3))}


def run(items: Iterable[GoldenItem], ask: Callable[[str, Identity], Any], golden_version: str,
        versions: dict[str, str]) -> RunResult:
    res = RunResult(golden_version, versions)
    for it in items:
        out = ask(it.question, DIRECTORY[it.user])
        res.per_item[it.id] = {"category": it.category, "outcome": out.outcome,
                               "answer": out.answer, "grades": grade(it, out.answer)}
    return res


def calibrate_judge(items: list[GoldenItem], run_result: RunResult,
                    judge: Callable[[GoldenItem, dict], int]) -> dict[str, float]:
    """Agreement and kappa between a judge and human labels on the
    calibration subset (items that carry a human label)."""
    calib = [i for i in items if i.human_label is not None and i.id in run_result.per_item]
    j = [judge(i, run_result.per_item[i.id]["answer"]) for i in calib]
    h = [int(i.human_label) for i in calib]
    agree = sum(x == y for x, y in zip(j, h)) / max(1, len(calib))
    return {"n": len(calib), "agreement": round(agree, 3), "kappa": round(cohen_kappa(j, h), 3)}


def regression_gate(baseline: RunResult, candidate: RunResult, tolerance: float = 0.02,
                    resamples: int = 2000, seed: int = 7) -> dict[str, Any]:
    """Paired bootstrap per category on the same items (Chapter 38).

    Blocks a category when the upper end of the 95% interval on
    (candidate - baseline) lies below -tolerance."""
    rng = random.Random(seed)
    by_cat: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for iid, b in baseline.per_item.items():
        if iid in candidate.per_item:
            by_cat[b["category"]].append((int(b["grades"]["pass"]),
                                          int(candidate.per_item[iid]["grades"]["pass"])))
    report, blocked = {}, []
    for cat, pairs in sorted(by_cat.items()):
        diffs = [c - b for b, c in pairs]
        n = len(diffs)
        boots = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n
                       for _ in range(resamples))
        lo, hi = boots[int(0.025 * resamples)], boots[int(0.975 * resamples) - 1]
        delta = sum(diffs) / n
        verdict = "BLOCK" if hi < -tolerance else "pass"
        if verdict == "BLOCK":
            blocked.append(cat)
        report[cat] = {"n": n, "delta": round(delta, 3), "ci95": (round(lo, 3), round(hi, 3)),
                       "verdict": verdict}
    return {"decision": "BLOCKED" if blocked else "PASS", "blocked": blocked,
            "categories": report, "golden_version": candidate.golden_version}
