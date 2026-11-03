"""Listing 31.1. Cost and latency distribution for a workflow versus
a bounded agent on the same task, under illustrative assumptions.

Chapter 31, Agents Versus Workflows. Verified by execution; the
assumptions are stated in the code and are not measurements.
Run with: python run.py 31.1
"""
import random
import statistics

random.seed(7)
# illustrative: mean cost of one model call in USD
PRICE_PER_CALL = 0.004
# illustrative seconds, including tool time
LATENCY_PER_CALL = 1.4


def workflow_run():
    calls = 3  # fixed graph: classify, extract, draft
    return calls * PRICE_PER_CALL, calls * LATENCY_PER_CALL


def agent_run(max_steps=10):
    # Reactive agent: usually 3-5 steps; sometimes wanders to the cap.
    steps = min(max_steps, max(3, int(random.gauss(4.2, 1.6))))
    if random.random() < 0.08:          # 8% of runs wander
        steps = max_steps
    return steps * PRICE_PER_CALL, steps * LATENCY_PER_CALL


def summarize(name, runs):
    costs = sorted(c for c, _ in runs)
    lats = sorted(l for _, l in runs)

    def p95(xs):
        return xs[int(0.95 * len(xs)) - 1]

    print(f"{name:9s} cost mean ${statistics.mean(costs):.4f} "
          f"p95 ${p95(costs):.4f} | latency mean "
          f"{statistics.mean(lats):.1f}s p95 {p95(lats):.1f}s")


N = 10_000
summarize("workflow", [workflow_run() for _ in range(N)])
summarize("agent", [agent_run() for _ in range(N)])
