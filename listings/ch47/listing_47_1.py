"""Listing 47.1. Burst handling: provider rejections and a retry
storm without admission control, versus bounded-wait admission with
a leaky bucket.

Chapter 47, Scaling and Capacity. Verified by execution; a
discrete-event simulation with illustrative parameters.
Run with: python run.py 47.1
"""
import heapq
import random


def simulate(arrival_rate, duration_s, provider_rpm, admission,
             max_wait_s, seed=4):
    """Poisson arrivals. The provider allows provider_rpm requests
    per sliding minute and rejects the rest (429); a rejected
    request retries once after 1 s, adding load. With admission
    control, a leaky bucket at 95% of the provider rate schedules
    each request; it waits up to max_wait_s, otherwise the
    application returns a designed degraded response with no
    provider call and no retry."""
    rng = random.Random(seed)
    t = 0.0
    arrivals = []
    while t < duration_s:
        t += rng.expovariate(arrival_rate)
        arrivals.append((t, False))
    heapq.heapify(arrivals)
    window = []
    served = rejected = degraded = calls = 0
    waits = []
    interval = 60.0 / (provider_rpm * 0.95)
    next_free = 0.0
    while arrivals:
        a, is_retry = heapq.heappop(arrivals)
        if admission:
            start = max(next_free, a)
            wait = start - a
            if wait <= max_wait_s:
                next_free = start + interval
                served += 1
                calls += 1
                waits.append(wait)
            else:
                # Instant, no provider call.
                degraded += 1
            continue
        calls += 1
        window = [w for w in window if w > a - 60.0]
        if len(window) < provider_rpm:
            window.append(a)
            served += 1
            waits.append(0.0)
        else:
            rejected += 1
            if not is_retry:
                # Retry storm.
                heapq.heappush(arrivals, (a + 1.0, True))
    waits.sort()
    p95 = waits[int(0.95 * len(waits)) - 1] if waits else 0.0
    return served, rejected, degraded, calls, p95


if __name__ == "__main__":
    # Burst: 9 req/s for 60 s against a provider limit of 300 rpm
    # (5 req/s).
    for label, adm in [("no admission control", False),
                       ("leaky bucket, wait <= 3 s", True)]:
        s1, r1, d1, c1, p1 = simulate(9.0, 60, 300, adm, 3.0)
        print(f"{label:26s} served {s1:3d}  provider 429s {r1:3d}  "
              f"degraded {d1:3d}  provider calls {c1:3d}  "
              f"p95 wait {p1:.1f}s")
