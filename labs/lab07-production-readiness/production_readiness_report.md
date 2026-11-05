# Production readiness report: Atlas

Generated 2026-11-05 by `labs/lab07-production-readiness/lab.py` from executed checks.

**Verdict: READY FOR A LIMITED PILOT once the 9 manual items are signed off.** 20 of 20 executed checks passed; 9 items need a named person.

## Executed checks

| Area | Check | Result | Evidence |
|---|---|---|---|
| Code | unit, security and integration tests | PASS | 190 passed, 6 skipped in 2.98s |
| Code | every runnable book listing executes | PASS | RESULT: all listings ran successfully |
| Code | lint (flake8) | PASS | 0 findings |
| Secrets | no credential-shaped strings in tracked files | PASS | 96 files scanned, 0 hits [] |
| Secrets | .env.example holds placeholders only | PASS | 5 secret-bearing entries, all placeholders |
| Config | production refuses missing or placeholder secrets | PASS | refused 2 of 2 unsafe configurations |
| Config | development token endpoint is off in production | PASS | POST /auth/dev-token -> 404 |
| Security | permissions enforced in retrieval | PASS | alice -> escalated, leaked=False |
| Security | poisoned document quarantined at ingestion | PASS | quarantined: ['wiki-vpn'] |
| Security | audit log hash chain verifies | PASS | 6 entries, chain intact |
| Security | container runs as a non-root user | PASS | Dockerfile sets USER atlas |
| Reliability | degraded response when every provider fails | PASS | outcome=degraded, sources kept |
| Reliability | daily cost cap stops spend | PASS | outcomes ['answered', 'degraded', 'degraded'] with a $0.001 cap |
| Reliability | database migrations present and tracked | PASS | ['001_init.sql'], applied with sha256 tracking (atlas/db/migrate.py) |
| Reliability | container images pinned | PASS | 4 images pinned |
| Observability | every span carries its required attributes | PASS | 5 spans, missing=[], versions=['code', 'index', 'instructions', 'model'] |
| Observability | metrics endpoint restricted to operators | PASS | {'alice': 403, 'olga': 200} |
| Evaluation | golden set pass rate (lower 95% bound >= 0.70) | PASS | 0.944 on n=18, 95% CI (0.742, 0.99) |
| Evaluation | regression gate passes the release candidate | PASS | decision=PASS, blocked=[] |
| Repository | no CI workflows (author's cost policy) | PASS | manual verification only; see docs/VERIFICATION.md |

## Manual sign-off

| Area | Item | Owner | Date |
|---|---|---|---|
| Governance | Data processing agreement signed with each model provider (Chapter 5) | | |
| Governance | Threat model reviewed and signed off (Chapter 43, docs/templates) | | |
| Evaluation | Judge calibrated against human labels with a real model (Chapter 35); the mock judge's agreement is not evidence | | |
| Evaluation | Golden set sized for the decisions you will make (Chapter 34); 18 items is a teaching set | | |
| Reliability | Load test on the target hardware and provider quotas (Chapter 47) | | |
| Reliability | Backup restore drill meets the RPO/RTO you set (Chapter 47) | | |
| Operations | On-call rota, paging, and an incident runbook rehearsed (Chapter 51) | | |
| Operations | Alert thresholds tuned on real traffic (Chapter 45) | | |
| Security | Adversarial test suite run against the deployed system (Chapter 39) | | |

A check that cannot be executed here is listed as manual, never as passed.
Re-run this lab after every change to code, instructions, model, or index.
