"""Listing 37.1. Error budget computation for availability and
quality SLOs, with consumption by incident and by release.

Chapter 37, Reliability Engineering for AI. Verified by execution.
Run with: python run.py 37.1
"""


def error_budget(slo: float, total_events: int) -> float:
    return (1 - slo) * total_events


def budget_report(name, slo, total, failures, consumers):
    budget = error_budget(slo, total)
    used = sum(consumers.values())
    print(f"{name}: SLO {slo:.1%} over {total:,} events "
          f"-> budget {budget:,.0f} failures")
    print(f"  observed failures {failures:,} "
          f"({failures / total:.2%}); "
          f"budget remaining {budget - failures:,.0f}")
    for who, n in consumers.items():
        print(f"    {who:32s} {n:>6,}  "
              f"({n / budget:.0%} of budget)")
    return budget - failures


if __name__ == "__main__":
    # Availability: 30 days, 40k requests, SLO 99.5%.
    budget_report(
        "availability", 0.995, 40_000, failures=160,
        consumers={"provider outage 03 Sep (41 min)": 105,
                   "index rebuild timeout 12 Sep": 38,
                   "misc": 17})
    # Quality: 30 days, 4,000 sampled+graded answers (10%),
    # SLO 93%.
    remaining = budget_report(
        "quality", 0.93, 4_000, failures=235,
        consumers={
            "release 2026.09.1 (instruction change)": 100,
            "baseline error rate": 135})
    freeze = remaining < 0.2 * error_budget(0.93, 4_000)
    print("quality budget remaining:", f"{remaining:.0f}",
          "-> freeze quality-affecting changes" if freeze
          else "-> ok")
