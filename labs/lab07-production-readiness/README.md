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
{"ts": 1793890120.256, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "54ff25b4ea354f37996fb25ea8b89d3f", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793890120.26, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "074e7e351e444438b1661f6ca8b0a7da", "user": "alice", "outcome": "degraded", "cost_usd": 0.0, "sources": 6}
{"ts": 1793890120.265, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "a3955a10c0a74ba789547ae6d1ae01db", "user": "alice", "outcome": "answered", "cost_usd": 0.002478, "sources": 6}
{"ts": 1793890120.266, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "3879afb1a3c247f9b898c9d45d51e886", "user": "alice", "outcome": "degraded", "cost_usd": 0.0, "sources": 6}
{"ts": 1793890120.266, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "52ca61583a98407ba01e4ef18dec5f60", "user": "alice", "outcome": "degraded", "cost_usd": 0.0, "sources": 6}
{"ts": 1793890120.267, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "f053fc31d1f74360ab308a544aa2931c", "user": "alice", "outcome": "answered", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793890120.279, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "e7d0d40670d24265bdab3de97cfa3c6b", "user": "alice", "outcome": "answered", "cost_usd": 0.002478, "sources": 6}
{"ts": 1793890120.279, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "55db88d670b942f6a4b8c525f502f9ac", "user": "bob", "outcome": "answered", "cost_usd": 0.002493, "sources": 6}
{"ts": 1793890120.28, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "f37c5fe05d9c4679bb0e2284ed947b14", "user": "alice", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793890120.28, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "7f312857b84147eb8424d4ffa9413869", "user": "sam", "outcome": "answered", "cost_usd": 0.002454, "sources": 6}
{"ts": 1793890120.281, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "2d6301aa905c4c6aa15817615912c556", "user": "bob", "outcome": "answered", "cost_usd": 0.002382, "sources": 6}
{"ts": 1793890120.281, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "2d4e15edea6048999929f9f347ff5f09", "user": "alice", "outcome": "answered", "cost_usd": 0.002409, "sources": 6}
{"ts": 1793890120.282, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "856d244d72cf48c08908967e1e238509", "user": "bob", "outcome": "answered", "cost_usd": 0.002355, "sources": 6}
{"ts": 1793890120.282, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "d958e8fb19d449d39b8af76ed9914da8", "user": "alice", "outcome": "answered", "cost_usd": 0.002361, "sources": 6}
{"ts": 1793890120.282, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "873dcdd1e2584b38b84d3f0f6b1f3d90", "user": "alice", "outcome": "answered", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793890120.283, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "1ada3af78eee41f5930119a6f02a1173", "user": "bob", "outcome": "answered", "cost_usd": 0.002412, "sources": 6}
{"ts": 1793890120.283, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "175b02852fb44a8fa283015b0ea14160", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793890120.284, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "dceb605888fd4bb7b3824cd9ee84aeee", "user": "sam", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793890120.284, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "7c125df5e7954d399379c314a3dcb372", "user": "alice", "outcome": "escalated", "cost_usd": 0.002139, "sources": 6}
{"ts": 1793890120.285, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "9f9296cd17ec463c85d9e50427d699c0", "user": "bob", "outcome": "escalated", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793890120.285, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "83b0cb33375f479a8737fba0982204ba", "user": "alice", "outcome": "escalated", "cost_usd": 0.00222, "sources": 6}
{"ts": 1793890120.285, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "b8c036cbdbff4b76b807784298444664", "user": "alice", "outcome": "escalated", "cost_usd": 0.002169, "sources": 6}
{"ts": 1793890120.286, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "576f3e2409224253b69725b6f1283631", "user": "bob", "outcome": "answered", "cost_usd": 0.002157, "sources": 6}
{"ts": 1793890120.286, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "c5f3b504ea1a472aa4c4db5734779050", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793890120.291, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "3505c515d5644d1395eaa4273a521677", "user": "alice", "outcome": "answered", "cost_usd": 0.002478, "sources": 6}
{"ts": 1793890120.291, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "26a0fa48aba84066a3a1cc8de71311b1", "user": "bob", "outcome": "answered", "cost_usd": 0.002493, "sources": 6}
{"ts": 1793890120.291, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "7d198acf03f44f5eba440420bf267bc2", "user": "alice", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793890120.292, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "1f9acff8e6044783adb5d0f21e719a8f", "user": "sam", "outcome": "answered", "cost_usd": 0.002454, "sources": 6}
{"ts": 1793890120.292, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "f2a88f6ceff046b1a1da52639d109c64", "user": "bob", "outcome": "answered", "cost_usd": 0.002382, "sources": 6}
{"ts": 1793890120.293, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "bbd768defd544f89afaa9abbf56e2314", "user": "alice", "outcome": "answered", "cost_usd": 0.002409, "sources": 6}
{"ts": 1793890120.293, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "fe0ae3f9e5044efca280ecc528f57bd0", "user": "bob", "outcome": "answered", "cost_usd": 0.002355, "sources": 6}
{"ts": 1793890120.293, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "dd35be1c64b94c3eab8f586dc0a8837f", "user": "alice", "outcome": "answered", "cost_usd": 0.002361, "sources": 6}
{"ts": 1793890120.294, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "f442271f459441ccaa9eabbfa1314d3b", "user": "alice", "outcome": "answered", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793890120.294, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "f6521eb51df045ff885fece404fb3a15", "user": "bob", "outcome": "answered", "cost_usd": 0.002412, "sources": 6}
{"ts": 1793890120.294, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "6227520e56234171b33743ef2847f1a2", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
{"ts": 1793890120.295, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "e9ebb9acb6004285b9729d03a7a0e037", "user": "sam", "outcome": "answered", "cost_usd": 0.002352, "sources": 6}
{"ts": 1793890120.295, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "7b7a3218303541859bf3449f6227d634", "user": "alice", "outcome": "escalated", "cost_usd": 0.002139, "sources": 6}
{"ts": 1793890120.296, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "b63ad84ed5dc4304834f6cb03953524a", "user": "bob", "outcome": "escalated", "cost_usd": 0.002193, "sources": 6}
{"ts": 1793890120.296, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "8aaf7c19c03746478df2b93655f2a18e", "user": "alice", "outcome": "escalated", "cost_usd": 0.00222, "sources": 6}
{"ts": 1793890120.296, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "543160b62355490e92aa2d873bdf715d", "user": "alice", "outcome": "escalated", "cost_usd": 0.002169, "sources": 6}
{"ts": 1793890120.297, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "6b937a8e29f948e7a6f2c1646dc8801c", "user": "bob", "outcome": "answered", "cost_usd": 0.002157, "sources": 6}
{"ts": 1793890120.297, "level": "INFO", "logger": "atlas.service", "msg": "ask", "request_id": "-", "trace_id": "9881b009d91044e1bfb5e2fa4f5f4103", "user": "alice", "outcome": "escalated", "cost_usd": 0.002181, "sources": 6}
== Executed checks
  [PASS] Code: unit, security and integration tests - 190 passed, 6 skipped in 3.02s
  [PASS] Code: every runnable book listing executes - RESULT: all listings ran successfully
  [PASS] Code: lint (flake8) - 0 findings
  [PASS] Secrets: no credential-shaped strings in tracked files - 97 files scanned, 0 hits []
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
