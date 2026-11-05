# Evaluation report

Golden set: `485d5b93d321` (18 items)
System: `{'code': '1.0.0', 'instructions': '0da08c95ae94', 'model': 'mock-large', 'index': 'atlas-hashing-v1'}`

| Category | n | Baseline | Candidate | Gate |
|---|---|---|---|---|
| adversarial | 2 | 1.00 | 1.00 | pass |
| expenses | 5 | 0.80 | 0.80 | pass |
| it | 2 | 1.00 | 1.00 | pass |
| leave | 5 | 1.00 | 0.00 | BLOCK |
| out-of-scope | 1 | 1.00 | 1.00 | pass |
| restricted | 3 | 1.00 | 1.00 | pass |

Judge calibration: agreement 1.0, kappa 1.0 (n=18).
Decision: **BLOCKED**.
