"""Listing 49.1. Three-year cost comparison for build, buy, and
integrate, including expected exit cost.

Chapter 49, Build, Buy, or Integrate. Verified by execution; all
figures are illustrative.
Run with: python run.py 49.1
"""
from dataclasses import dataclass


@dataclass
class Option:
    name: str
    # engineer-months to build
    build_months: float = 0.0
    # engineer-months per year to operate
    ops_months_per_year: float = 0.0
    # USD, flat
    license_per_year: float = 0.0
    # USD, scales with volume
    usage_per_year: float = 0.0
    # engineer-months to migrate away
    exit_months: float = 0.0
    # probability exit is needed within the horizon
    p_exit_in_horizon: float = 0.0


def three_year_cost(o: Option, eng_month_usd: float = 14_000,
                    growth: float = 1.3):
    build = o.build_months * eng_month_usd
    ops = 3 * o.ops_months_per_year * eng_month_usd
    license_ = 3 * o.license_per_year
    # Volume grows.
    usage = sum(o.usage_per_year * growth ** y for y in range(3))
    expected_exit = (o.p_exit_in_horizon * o.exit_months
                     * eng_month_usd)
    total = build + ops + license_ + usage + expected_exit
    return {"build": build, "ops": ops, "license": license_,
            "usage": round(usage),
            "expected_exit": expected_exit,
            "total": round(total)}


if __name__ == "__main__":
    gateway = [
        Option("build (thin gateway)", build_months=2.0,
               ops_months_per_year=1.5, exit_months=0.5,
               p_exit_in_horizon=0.1),
        Option("buy (gateway product)", build_months=0.5,
               ops_months_per_year=0.4, license_per_year=24_000,
               exit_months=2.0, p_exit_in_horizon=0.35),
        Option("integrate (provider-native routing)",
               build_months=0.3, ops_months_per_year=0.2,
               usage_per_year=6_000, exit_months=3.0,
               p_exit_in_horizon=0.5),
    ]
    for o in gateway:
        c = three_year_cost(o)
        print(f"{o.name:38s} total ${c['total']:>8,}")
        print(f"    build {c['build']:,.0f}  "
              f"ops {c['ops']:,.0f}  "
              f"lic {c['license']:,.0f}  "
              f"usage {c['usage']:,}  "
              f"exit {c['expected_exit']:,.0f}")
