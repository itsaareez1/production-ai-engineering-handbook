# Lab 2: Build a model gateway

Book chapters: 9, 24, 46. Estimated time: 30–45 minutes.

## Objectives

- Route requests by task to an ordered chain of provider/model candidates
- Retry only transient errors, with exponential backoff and full jitter
- Fall back to the next candidate and open a circuit breaker on a failing one
- Keep restricted context on in-region providers, enforced in code
- Account cost per call and stop at a daily cap

## Prerequisites

- Python 3.12 or later and the repository's virtual environment (`make venv`)
- No API key, no network access to model providers, no paid service

## Estimated time

30–45 minutes.

## Architecture

```text
caller ─► Gateway.complete(ModelRequest, Identity)
            │ route by task ─► [(primary, mock-large), (fallback, mock-small)]
            │ sensitivity=restricted ─► drop out-of-region candidates
            │ Ledger.check() (daily cap)
            ▼
   for each candidate: breaker.allow()? ─► provider.complete() ─► retry transient (jitter) ─► next candidate
            ▼
   Ledger.record() ─► GatewayResult(response, attempts, cost, fallback_used)
```

## Files

| File | Purpose |
|---|---|
| [`lab.py`](lab.py) | the whole lab |
| [`expected_output.txt`](expected_output.txt) | output of a verified run |
| [`../../atlas/gateway/gateway.py`](../../atlas/gateway/gateway.py) | Gateway, CircuitBreaker, Ledger, prices |
| [`../../atlas/gateway/providers.py`](../../atlas/gateway/providers.py) | MockProvider with fault injection; Anthropic and OpenAI adapters |

## Steps

1. **Healthy call.** One attempt, cost recorded.
2. **Transient error.** A 503 is retried once; the backoff is random in [0, 0.25] s.
3. **Fallback.** With the primary failing, the fallback answers and `fallback_used` is true.
4. **Breaker.** After repeated failures the primary is skipped without a call; after the cooldown (a fake clock) it is tried again and closes.
5. **Restricted data.** A restricted request never reaches the out-of-region provider; with no in-region candidate it fails closed.
6. **Cost cap.** Calls stop when the day's spend reaches the cap; spend is attributed by user, task, and model.

## Complete code

The complete, runnable code for this lab is [`lab.py`](lab.py) (91 lines), which uses the `atlas` package in this repository. Read it top to bottom: each step above is one block, headed by a `print("== Step N ...")` line.

## Commands

From the repository root:

```bash
make venv            # once
python labs/lab02-model-gateway/lab.py
```

## Expected output

Captured from a verified run (macOS, Python 3.13) on 5 November 2026 and committed as [`expected_output.txt`](expected_output.txt).

```text
== Step 1: a healthy call
  provider=primary attempts=['primary/mock-large#1: ok'] cost=$0.000108

== Step 2: transient error, retried with jittered backoff
  attempts=['primary/mock-large#1: transient: 503 overloaded', 'primary/mock-large#2: ok']
  backoff slept 0.034s (random in [0, 0.25])

== Step 3: primary down: fall back
  provider=fallback fallback_used=True
  attempts=['primary/mock-large#1: transient: 503 overloaded', 'primary/mock-large#2: transient: 503 overloaded', 'fallback/mock-small#1: ok']

== Step 4: the breaker opens and the primary is skipped without a call
  breaker=open primary calls unchanged: True
  attempts=['primary/mock-large: breaker open, skipped', 'fallback/mock-small#1: ok']
  after cooldown: provider=primary breaker=closed

== Step 5: restricted context never leaves the region
  provider=in-region out-of-region calls=0
  no eligible provider -> ['no eligible provider for this sensitivity']

== Step 6: cost accounting and the daily cap
  stopped after 10 calls, $0.001080 spent: daily cap $0.001 reached
  attribution: {('alice', 'judge', 'mock-large'): 0.00108}
```

## Verification

The lab worked if:

- Step 3 shows `fallback_used=True`
- Step 4 shows `breaker=open` and `primary calls unchanged: True`
- Step 5 shows `out-of-region calls=0`
- Step 6 stops with `daily cap $0.001 reached`

## Common errors

| Symptom | Fix |
|---|---|
| Backoff value differs | The jitter is random by design; the lab seeds it, so a change means you changed the seed or the call order. |
| `KeyError: no route for task` | Every task you send needs a route in the `routes` mapping. |

## Troubleshooting

- Print `gateway.breaker(provider, model).state` after each call to watch the breaker move between closed, open, and half-open.
- If retries never happen, check the error's `transient` flag: permanent errors (400, auth) are deliberately not retried.

## Production checklist

- [ ] Only transient errors are retried, a bounded number of times
- [ ] Fallback and breaker are observable in the attempt log
- [ ] Sensitivity routing is enforced by the gateway, not requested of the model
- [ ] Every call is priced and capped

## Challenges

1. Add a per-user daily cap alongside the global one.
2. Make the breaker threshold a failure *rate* over a window instead of a count.
3. Wire in `AnthropicProvider` with your own key (optional, costs money) and compare the attempt log.
