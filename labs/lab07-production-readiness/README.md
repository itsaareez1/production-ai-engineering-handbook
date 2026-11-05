# Lab 7: Production readiness review

Book chapters: 44–47, 51, 53. Estimated time: 20 minutes.

## Objectives

- Run every readiness check that can be executed and record its evidence
- List the checks that need a named person, rather than marking them done
- Compute the verdict from results and write a report a reviewer can sign

## Prerequisites

- Python 3.12 or later and the repository's virtual environment (`make venv`)
- No API key, no network access to model providers, no paid service
- Labs 1–6 are recommended first; this lab re-runs their key checks

## Estimated time

20 minutes.

## Architecture

```text
lab.py ─► executed checks (tests, listings, lint, secrets, config, security,
                           reliability, observability, evaluation, repository)
       ├─► manual items (governance, operations, load, restore, red team)
       └─► production_readiness_report.md  (verdict computed, never asserted)
```

## Files

| File | Purpose |
|---|---|
| [`lab.py`](lab.py) | the checks and the report writer |
| [`expected_output.txt`](expected_output.txt) | output of a verified run |
| [`production_readiness_report.md`](production_readiness_report.md) | the report the lab writes |

## Steps

1. **Code**: the test suite, every runnable listing, and lint.
2. **Secrets and configuration**: no credential-shaped strings in tracked files; `.env.example` holds placeholders; production refuses to start without secrets; the development token endpoint is off in production.
3. **Security**: permissions in retrieval, quarantine, audit chain, non-root container.
4. **Reliability**: degraded mode, the cost cap, tracked migrations, pinned images.
5. **Observability and evaluation**: required span attributes, operator-only metrics, golden-set pass rate by its lower bound, the regression gate.
6. **Manual items** (governance, load, restore, on-call, alert tuning, adversarial testing) that need a person are listed with blank owner and date columns.
7. **Verdict** is computed: any failed check means NOT READY.

## Complete code

The complete, runnable code for this lab is [`lab.py`](lab.py) (265 lines), which uses the `atlas` package in this repository. Read it top to bottom: each step above is one block, headed by a `print("== Step N ...")` line.

## Commands

From the repository root:

```bash
make venv            # once
python labs/lab07-production-readiness/lab.py
```

```bash
python labs/lab07-production-readiness/lab.py --quick   # skips the test suite
```

## Expected output

Captured from a verified run (macOS, Python 3.13) on 5 November 2026 and committed as [`expected_output.txt`](expected_output.txt).

```text
{"ts": 1793891461.372, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "a78a1499424a4f0cab7a8aa84d31ff52", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793891461.374, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "9e7c7522f1a8474f931030520c11a0cb", "user": "alice", "outcome": "degraded", "cost_usd": 0.0, "sources": 6}
{"ts": 1793891461.377, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "af18b79b77a3443183a6fa3228ef427c", "user": "alice", "outcome": "answered", "cost_usd": 0.002478, "sources": 6}
{"ts": 1793891461.377, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "c8a99092abb4466e9daa14a879ca33ad", "user": "alice", "outcome": "degraded", "cost_usd": 0.0, "sources": 6}
{"ts": 1793891461.377, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "8e302a60d1a44586abfa0501c6c0c91a", "user": "alice", "outcome": "degraded", "cost_usd": 0.0, "sources": 6}
{"ts": 1793891461.378, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "fff2b993b5504177982d5e602dc91c07", "user": "alice", "outcome": "answered", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793891461.384, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "8b884573170a4437880cfb41f0f346d7", "user": "alice", "outcome": "answered", "cost_usd": 0.002478, "sources": 6}
{"ts": 1793891461.384, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "164a23b344134663940ba872fe9cb38f", "user": "bob", "outcome": "answered", "cost_usd": 0.002493, "sources": 6}
{"ts": 1793891461.385, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "d06da2d69509460b81ebf1defffbfb6b", "user": "alice", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793891461.385, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "051577e5643144ac910120d76b4bff2e", "user": "sam", "outcome": "answered", "cost_usd": 0.002454, "sources": 6}
{"ts": 1793891461.385, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "68b68136c37a418a926d6187357bac3c", "user": "bob", "outcome": "answered", "cost_usd": 0.002382, "sources": 6}
{"ts": 1793891461.385, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "cc523f9f6d8a41b0b0935309580fbd19", "user": "alice", "outcome": "answered", "cost_usd": 0.002409, "sources": 6}
{"ts": 1793891461.386, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "715940a16e3449be861bbabae0806fa8", "user": "bob", "outcome": "answered", "cost_usd": 0.002355, "sources": 6}
{"ts": 1793891461.386, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "a96792818c2c438fab4cd6ab2fb0f180", "user": "alice", "outcome": "answered", "cost_usd": 0.002361, "sources": 6}
{"ts": 1793891461.386, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "ccecb99dbb784f998f5708eec58b24a4", "user": "alice", "outcome": "answered", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793891461.386, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "2e146e89c5594a3eb6b2fd71d72895e4", "user": "bob", "outcome": "answered", "cost_usd": 0.002412, "sources": 6}
{"ts": 1793891461.387, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "beb03318af39458e939f709568610164", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793891461.387, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "0069faba28e841e9a8763ca608861acc", "user": "sam", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793891461.387, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "ce284d55c6e84606a8ade56e979b5c21", "user": "alice", "outcome": "escalated", "cost_usd": 0.002139, "sources": 6}
{"ts": 1793891461.387, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "4f7e024ac7e04439b9e08ebdab963033", "user": "bob", "outcome": "escalated", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793891461.388, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "fb6e111c23ce4dff9941abbca19e2477", "user": "alice", "outcome": "escalated", "cost_usd": 0.00222, "sources": 6}
{"ts": 1793891461.388, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "0d959c535fd34650babf89370330bb5f", "user": "alice", "outcome": "escalated", "cost_usd": 0.002169, "sources": 6}
{"ts": 1793891461.388, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "f67f711bde834c4f8fe843b42578183f", "user": "bob", "outcome": "answered", "cost_usd": 0.002157, "sources": 6}
{"ts": 1793891461.388, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "76b8ec60380f46bd86681d7ef2f8899d", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793891461.391, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "203da93d0e124866af6b373ce5a2d450", "user": "alice", "outcome": "answered", "cost_usd": 0.002478, "sources": 6}
{"ts": 1793891461.391, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "4c0e41707143406986ce646e52778df4", "user": "bob", "outcome": "answered", "cost_usd": 0.002493, "sources": 6}
{"ts": 1793891461.391, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "efc67ce0b1aa43dabdc1ce9b96c56396", "user": "alice", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793891461.391, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "8cf19647e1fa4aaf9118a33b55d88912", "user": "sam", "outcome": "answered", "cost_usd": 0.002454, "sources": 6}
{"ts": 1793891461.392, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "1b61c1934e85437c9f61f877d6c113fb", "user": "bob", "outcome": "answered", "cost_usd": 0.002382, "sources": 6}
{"ts": 1793891461.392, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "83cf80601a65446aaec96ecc1fbc028a", "user": "alice", "outcome": "answered", "cost_usd": 0.002409, "sources": 6}
{"ts": 1793891461.392, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "4b39f524b1044443986ef292b9915d5f", "user": "bob", "outcome": "answered", "cost_usd": 0.002355, "sources": 6}
{"ts": 1793891461.392, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "da588a7b00ab44afb5bdc14d8b4655a6", "user": "alice", "outcome": "answered", "cost_usd": 0.002361, "sources": 6}
{"ts": 1793891461.393, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "8aaec822075840e19fe084c48ae3a081", "user": "alice", "outcome": "answered", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793891461.393, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "91118e47ef794874bf782a955bce4872", "user": "bob", "outcome": "answered", "cost_usd": 0.002412, "sources": 6}
{"ts": 1793891461.393, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "fd32bf2a61e14589b97b2f92b9edcf9c", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793891461.393, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "8841fe763b5d41e4b45631c11ebdceda", "user": "sam", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793891461.394, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "c2358ed94c514f748a914bb49a8eab86", "user": "alice", "outcome": "escalated", "cost_usd": 0.002139, "sources": 6}
{"ts": 1793891461.394, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "8cd76ea1ef4e4a4181987cee0c957029", "user": "bob", "outcome": "escalated", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793891461.394, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "a112d15b10d3451e9aa976de200e0b44", "user": "alice", "outcome": "escalated", "cost_usd": 0.00222, "sources": 6}
{"ts": 1793891461.394, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "d36dce21150645789a2b1e04e401f6a2", "user": "alice", "outcome": "escalated", "cost_usd": 0.002169, "sources": 6}
{"ts": 1793891461.395, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "198e9aa6e5ed43f2b28fe814092eb6c8", "user": "bob", "outcome": "answered", "cost_usd": 0.002157, "sources": 6}
{"ts": 1793891461.395, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "d8f7f061ffbc4b9f81c2387946eeff8f", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
== Executed checks
  [PASS] Code: unit, security and integration tests - 195 passed, 6 skipped in 2.87s
  [PASS] Code: every runnable book listing executes - RESULT: all listings ran successfully
  [PASS] Code: lint (flake8) - 0 findings
  [PASS] Secrets: no credential-shaped strings in tracked files - 152 files scanned, 0 hits []
  [PASS] Secrets: .env.example holds placeholders only - 5 secret-bearing entries, all placeholders
  [PASS] Config: production refuses missing or placeholder secrets - refused 2 of 2 unsafe configurations
  [PASS] Config: development token endpoint is off in production - POST /auth/dev-token -> 404
  [PASS] Security: permissions enforced in retrieval - alice -> escalated, leaked=False
  [PASS] Security: poisoned document quarantined at ingestion - quarantined: ['wiki-vpn']
  [PASS] Security: audit log hash chain verifies - 6 entries, chain intact
  [PASS] Security: container runs as a non-root user - Dockerfile sets USER atlas
  [PASS] Reliability: degraded response when every provider fails - outcome=degraded, sources kept
  [PASS] Reliability: daily cost cap stops spend - outcomes ['answered', 'degraded', 'degraded'] with a $0.001 cap
  [PASS] Reliability: database migrations present and tracked - ['001_init.sql'], applied with sha256 tracking (atlas/db/migrate.py)
  [PASS] Reliability: container images pinned - 4 images pinned
  [PASS] Observability: every span carries its required attributes - 5 spans, missing=[], versions=['code', 'index', 'instructions', 'model']
  [PASS] Observability: metrics endpoint restricted to operators - {'alice': 403, 'olga': 200}
  [PASS] Evaluation: golden set pass rate (lower 95% bound >= 0.70) - 0.944 on n=18, 95% CI (0.742, 0.99)
  [PASS] Evaluation: regression gate passes the release candidate - decision=PASS, blocked=[]
  [PASS] Repository: no CI workflows (author's cost policy) - manual verification only; see docs/VERIFICATION.md

== Checks that need a person
  [MANUAL] Governance: Data processing agreement signed with each model provider (Chapter 5)
  [MANUAL] Governance: Threat model reviewed and signed off (Chapter 43, docs/templates)
  [MANUAL] Evaluation: Judge calibrated against human labels with a real model (Chapter 35); the mock judge's agreement is not evidence
  [MANUAL] Evaluation: Golden set sized for the decisions you will make (Chapter 34); 18 items is a teaching set
  [MANUAL] Reliability: Load test on the target hardware and provider quotas (Chapter 47)
  [MANUAL] Reliability: Backup restore drill meets the RPO/RTO you set (Chapter 47)
  [MANUAL] Operations: On-call rota, paging, and an incident runbook rehearsed (Chapter 51)
  [MANUAL] Operations: Alert thresholds tuned on real traffic (Chapter 45)
  [MANUAL] Security: Adversarial test suite run against the deployed system (Chapter 39)

== Verdict: READY FOR A LIMITED PILOT once the 9 manual items are signed off
   20/20 executed checks passed, 9 manual items open

Wrote labs/lab07-production-readiness/production_readiness_report.md
```

## Verification

The lab worked if:

- `20/20 executed checks passed, 9 manual items open`
- `production_readiness_report.md` is rewritten with today's date

## Common errors

| Symptom | Fix |
|---|---|
| `Code: lint (flake8)` fails | Install the dev requirements (`make venv`) and fix the reported lines. |
| `container images pinned` fails | An image uses `:latest` or no tag; pin it to a tested version. |

## Troubleshooting

- Use `--quick` to skip the test suite while iterating on other checks.
- Each check prints its evidence; a crashing check is reported as FAIL with the exception, never skipped.

## Production checklist

- [ ] Every executed check has evidence
- [ ] Every manual item has an owner and date before launch
- [ ] The verdict is computed, not written by hand
- [ ] The report is re-run after every change to code, instructions, model, or index

## Challenges

1. Add a check that the golden set has at least 30 items per category, and see it fail honestly.
2. Add a check that `/v1/ask` p95 latency is under a target on your hardware.
3. Turn the manual list into a sign-off table your team actually uses.
