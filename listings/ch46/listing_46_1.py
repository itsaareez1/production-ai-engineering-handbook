"""Listing 46.1. Total cost of an AI workflow under three
configurations, with attribution by component.

Chapter 46, Cost Engineering. Verified by execution; all prices and
rates are illustrative assumptions.
Run with: python run.py 46.1
"""
from dataclasses import dataclass, replace


@dataclass
class Assumptions:
    requests_month: int = 40_000
    # per-token USD prices (per million) for two tiers
    p_in_large: float = 3.00
    p_out_large: float = 15.00
    p_in_mid: float = 0.80
    p_out_mid: float = 4.00
    tokens_in: int = 3_400
    tokens_out: int = 220
    stable_prefix: int = 1_200
    cache_discount: float = 0.9
    cache_enabled: bool = False
    # fraction of requests with a rewrite call
    rewrite_rate: float = 1.0
    # per request, reranker inference
    rerank_cost: float = 0.0006
    # per request, query embedding
    embed_cost: float = 0.00002
    tiered: bool = False
    easy_share: float = 0.6
    # tiered: easy requests escalated to large
    escalation_rate: float = 0.12
    # fraction needing one repair call
    repair_rate: float = 0.06
    judge_sample: float = 0.10
    judge_cost: float = 0.004
    infra_month: float = 1_800.0
    trace_storage_month: float = 250.0
    review_min_per_escalation: float = 4.0
    escalations_rate: float = 0.08
    reviewer_usd_per_hour: float = 45.0
    weekly_audit_hours: float = 4.0


def model_call(a, tier, tin, tout):
    pi, po = ((a.p_in_large, a.p_out_large) if tier == "large"
              else (a.p_in_mid, a.p_out_mid))
    cached = min(a.stable_prefix, tin) if a.cache_enabled else 0
    return ((tin - cached) * pi
            + cached * pi * (1 - a.cache_discount)
            + tout * po) / 1e6


def per_request(a: Assumptions) -> dict:
    c = {}
    if a.tiered:
        mid = model_call(a, "mid", a.tokens_in, a.tokens_out)
        large = model_call(a, "large", a.tokens_in, a.tokens_out)
        c["generation"] = (
            a.easy_share * mid + (1 - a.easy_share) * large
            + a.easy_share * a.escalation_rate * large)
    else:
        c["generation"] = model_call(
            a, "large", a.tokens_in, a.tokens_out)
    c["rewrite"] = a.rewrite_rate * model_call(a, "mid", 300, 40)
    c["repairs"] = a.repair_rate * model_call(
        a, "large", a.tokens_in + 200, a.tokens_out)
    c["retrieval"] = a.rerank_cost + a.embed_cost
    c["judge_sampling"] = a.judge_sample * a.judge_cost
    return c


def monthly(a: Assumptions) -> dict:
    pr = per_request(a)
    m = {k: v * a.requests_month for k, v in pr.items()}
    m["infrastructure"] = a.infra_month
    m["trace_storage"] = a.trace_storage_month
    esc_hours = (a.requests_month * a.escalations_rate
                 * a.review_min_per_escalation / 60)
    review_hours = esc_hours + a.weekly_audit_hours * 4.3
    m["human_review"] = review_hours * a.reviewer_usd_per_hour
    m["total"] = sum(v for k, v in m.items() if k != "total")
    return m


if __name__ == "__main__":
    base = Assumptions()
    cached = replace(base, cache_enabled=True, rewrite_rate=0.3)
    tiered = replace(cached, tiered=True)
    configs = [("baseline", base),
               ("cache+cond.rewrite", cached),
               ("...+tiered", tiered)]
    for name, a in configs:
        m = monthly(a)
        parts = ", ".join(f"{k} ${v:,.0f}"
                          for k, v in m.items() if k != "total")
        print(f"{name:20s} total ${m['total']:,.0f}/mo  "
              f"({m['total'] / a.requests_month:.4f}/req)")
        print(f"   {parts}")
