# Lab 6: Implement AI observability

Book chapters: 32, 37, 45, 46. Estimated time: 30–45 minutes.

## Objectives

- Read one request's trace and check every span carries its required attributes
- Derive metrics from traces in Prometheus format
- Attribute cost by user and by model
- Classify failures by their earliest origin
- Compute an SLO burn rate and decide whether to page

## Prerequisites

- Python 3.12 or later and the repository's virtual environment (`make venv`)
- No API key, no network access to model providers, no paid service

## Estimated time

30–45 minutes.

## Architecture

```text
Atlas.ask() ─► Trace(spans: retrieval, rerank, context, gateway, validation)
       │            └─► TraceStore (by trace_id)  ─► /v1/traces/{id} (operator)
       ├─► Metrics counters ─► /metrics (operator)
       └─► Ledger records ─► cost by user / model
traces ─► classify() ─► failure classes        outcomes ─► burn rate ─► page | ticket
```

## Files

| File | Purpose |
|---|---|
| [`lab.py`](lab.py) | the whole lab |
| [`expected_output.txt`](expected_output.txt) | output of a verified run |
| [`../../atlas/core/observability.py`](../../atlas/core/observability.py) | Trace, Span, REQUIRED attributes, Metrics |
| [`../../atlas/service.py`](../../atlas/service.py) | where spans are recorded |

## Steps

1. **Traffic** of ten questions, with two injected model faults, then a primary outage, then a full outage.
2. **One trace.** Every span carries its required attributes; the trace records the code, instruction, model, and index versions.
3. **Metrics** in Prometheus text format.
4. **Cost** attributed by user and by model, including the cost of the repair call a model fault caused.
5. **Failure classes** by earliest origin (retrieval, model, integration).
6. **Burn rate.** One degraded request in eleven is an 18× burn of a 99.5% SLO, which pages under the 14.4× one-hour rule. With eleven requests this is illustrative; a real burn rate needs a full window.

## Complete code

The complete, runnable code for this lab is [`lab.py`](lab.py) (101 lines), which uses the `atlas` package in this repository. Read it top to bottom: each step above is one block, headed by a `print("== Step N ...")` line.

## Commands

From the repository root:

```bash
make venv            # once
python labs/lab06-observability/lab.py
```

## Expected output

Captured from a verified run (macOS, Python 3.13) on 5 November 2026 and committed as [`expected_output.txt`](expected_output.txt).

```text
== Step 1: traffic (two injected model faults)
  alice escalated $0.004548  How many days of unused leave can I carry over?
  bob   answered  $0.002193  Which form do I use to request a new laptop?
  alice escalated $0.002181  What is the salary band for a senior engineer?
  sam   answered  $0.002352  What is the salary band for a senior engineer?
  bob   escalated $0.002181  Is there a limit on taxi trips?
  alice escalated $0.002169  What is the capital of France?
  bob   answered  $0.002352  When must carried-over leave days be used?
  alice answered  $0.002409  What is the daily meal allowance during business t
  alice answered  $0.000413  (primary down) How many days of unused leave can I 
  bob   answered  $0.000365  (primary down) Which form do I use to request a new
  bob   degraded  $0.000000  (all providers down) When must carried-over leave

== Step 2: one trace, and its required attributes
  trace 5abed22336bf  user=alice  versions={'code': '1.0.0', 'instructions': '0da08c95ae94', 'model': 'mock-large', 'index': 'atlas-hashing-v1'}
  span retrieval    0.17 ms  required ok: True  {'acl_filtered': 0, 'candidates': 8, 'status_filtered': 1}
  span rerank       0.06 ms  required ok: True  {}
  span context      0.02 ms  required ok: True  {'dropped': [], 'labels': ['policy-leave#1@2026-06-01', 'policy-leave#2@2026-06-01', 'policy-leave#0@2026-06-01', 'policy-expenses#1@2026-02-15', 'vendor-notice#0@2026-10-01', 'policy-expenses#0@2026-02-15']}
  span gateway      0.09 ms  required ok: True  {'attempts': ['mock-primary/mock-large#1: ok'], 'cost_usd': 0.002433, 'input_tokens': 556, 'model': 'mock-large', 'output_tokens': 51, 'provider': 'mock-primary'}
  span validation   0.03 ms  required ok: True  {'outcome': 'failed', 'repairs': 0}
  span gateway      0.06 ms  required ok: True  {'attempts': ['mock-primary/mock-large#1: ok'], 'cost_usd': 0.002115, 'input_tokens': 670, 'model': 'mock-large', 'output_tokens': 7, 'provider': 'mock-primary'}
  span validation   0.01 ms  required ok: True  {'outcome': 'failed', 'repairs': 1}

== Step 3: metrics derived from traces (Prometheus format)
  atlas_cost_usd_total{} 0.021163
  atlas_degraded_total{} 1
  atlas_fallback_total{} 2
  atlas_ingested_total{outcome="inserted"} 7
  atlas_quarantined_total{} 1
  atlas_requests_total{outcome="answered"} 6
  atlas_requests_total{outcome="degraded"} 1
  atlas_requests_total{outcome="escalated"} 4
  atlas_validation_failed_total{} 1

== Step 4: cost attribution
  by user:  {'alice': 0.01172, 'bob': 0.007091, 'sam': 0.002352}
  by model: {'mock-primary/mock-large': 0.020385, 'mock-fallback/mock-small': 0.000778}
  repair calls (cost of model faults): 1

== Step 5: failure classification from traces
  ok                                6
  retrieval or context (escalated)  3
  model                             1
  integration                       1

== Step 6: SLO burn rate (availability: 99.5% non-error over 30 days)
  (illustrative: a real burn rate is computed over a full window, not 11 requests)
  last hour: 1/11 degraded = 9.1%; burn rate = 18x
  at this rate the 30-day budget is gone in 39.6 hours
  decision: PAGE (page when burn >= 14.4x for 1h)
```

## Verification

The lab worked if:

- Step 2 shows `required ok: True` on every span
- Step 3 includes `atlas_requests_total{outcome="degraded"} 1`
- Step 6 ends with `decision: PAGE`

## Common errors

| Symptom | Fix |
|---|---|
| Trace IDs and span timings differ from the expected output | They are random IDs and wall-clock timings; everything else is deterministic. |

## Troubleshooting

- `svc.traces.get(trace_id)` returns the full trace as a dict; print it when a class looks wrong.
- If `required ok` is False, a span was recorded without an attribute listed for it in `REQUIRED`.

## Production checklist

- [ ] Every span has its required attributes
- [ ] Traces carry the versions that produced the answer
- [ ] Cost is attributable
- [ ] Failures are classified by origin
- [ ] Alerts are on burn rate, not raw errors

## Challenges

1. Export the spans with the OpenTelemetry SDK and view them in a local Jaeger container.
2. Add a latency SLO and its burn rate.
3. Add a quality signal (validation failures) to the dashboard and decide what should page.
