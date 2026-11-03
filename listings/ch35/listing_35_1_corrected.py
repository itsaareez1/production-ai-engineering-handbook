"""Correction to Listing 35.1 (see ERRATA.md, ERR-02).

The printed listing draws its calibration subset with

    calib = {it["id"] for it in items[:200]}

and the items are built with the first 200 in category "leave" and
the last 100 in "expenses". So the judge's agreement and kappa are
measured only on the easy category, and then used to vouch for its
scores on the hard one -- the exact mistake the chapter's own text
warns against.

This file keeps every function of the listing unchanged and replaces
only the selection of the calibration subset: a proportional sample
of each category, plus a guard that refuses to report a calibration
figure measured on a mix that differs from the evaluation mix.

Run with: python listings/ch35/listing_35_1_corrected.py
"""
import random
from collections import Counter, defaultdict

from listing_35_1 import (  # noqa: E402  (same directory)
    StubJudge, build_items, evaluate, report, stub_system,
)


def stratified_calibration(items, fraction=0.5, seed=11):
    """Proportional sample of every category, so agreement is
    measured on the mix the judge is then trusted to score."""
    by_cat = defaultdict(list)
    for it in items:
        by_cat[it["meta"]["category"]].append(it)
    calib = set()
    for cat, group in sorted(by_cat.items()):
        rng = random.Random(f"{seed}-{cat}")
        group = list(group)
        rng.shuffle(group)
        take = max(1, round(len(group) * fraction))
        calib.update(it["id"] for it in group[:take])
    return calib


def check_calibration(items, calib_ids, tolerance=0.05):
    """Fail loudly if the calibration mix differs from the
    evaluation mix."""
    all_mix = Counter(it["meta"]["category"] for it in items)
    cal_mix = Counter(it["meta"]["category"] for it in items
                      if it["id"] in calib_ids)
    n_all, n_cal = sum(all_mix.values()), sum(cal_mix.values())
    for cat in all_mix:
        p_all = all_mix[cat] / n_all
        p_cal = cal_mix.get(cat, 0) / n_cal if n_cal else 0.0
        if abs(p_all - p_cal) > tolerance:
            raise ValueError(
                f"calibration unrepresentative for {cat!r}: "
                f"{p_cal:.2f} vs {p_all:.2f} in the evaluation set"
            )
    return True


def mix(items, ids):
    return dict(Counter(it["meta"]["category"] for it in items
                        if it["id"] in ids))


if __name__ == "__main__":
    items = build_items()

    as_printed = {it["id"] for it in items[:200]}
    print("as printed, calibration mix:", mix(items, as_printed))
    try:
        check_calibration(items, as_printed)
        print("  guard: passed (unexpected)")
    except ValueError as e:
        print("  guard refuses it:", e)

    corrected = stratified_calibration(items)
    print("corrected, calibration mix:", mix(items, corrected))
    check_calibration(items, corrected)
    print("  guard: passed")
    print()
    report(*evaluate(items, stub_system, StubJudge(), corrected))
