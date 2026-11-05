# Lab 3: Build an AI evaluation pipeline

Book chapters: 33–38. Estimated time: 45 minutes.

## Objectives

- Version a golden set by content hash
- Grade answers deterministically per category, with Wilson intervals
- Calibrate a judge against human labels with agreement and Cohen's kappa
- Gate a release with a paired bootstrap per category, so a regression in one category blocks only that category
- Write an evaluation report a reviewer can read

## Prerequisites

- Python 3.12 or later and the repository's virtual environment (`make venv`)
- No API key, no network access to model providers, no paid service

## Estimated time

45 minutes.

## Architecture

```text
golden_set.jsonl ─► load_golden() (version = content hash)
     ├─► run(baseline)  ─► grade() per item ─► by_category() + Wilson CI
     ├─► calibrate_judge(human labels) ─► agreement, kappa
     └─► run(candidate) ─► regression_gate(baseline, candidate) ─► PASS | BLOCKED(categories)
                                                               └─► eval_report.md
```

## Files

| File | Purpose |
|---|---|
| [`lab.py`](lab.py) | the whole lab |
| [`expected_output.txt`](expected_output.txt) | output of a verified run |
| [`eval_report.md`](eval_report.md) | the report the lab writes |
| [`../../atlas/evaluation/harness.py`](../../atlas/evaluation/harness.py) | grading, Wilson, kappa, run, gate |
| [`../../examples/evaluation/golden_set.jsonl`](../../examples/evaluation/golden_set.jsonl) | 18 items with human labels |

## Steps

1. **Load** the golden set; its version is a hash of its content, so a changed set is a different set.
2. **Baseline.** 17 of 18 pass. `gs-018` (the taxi limit, which lives in a table row) fails honestly; the interval on 18 items is wide (0.742–0.99), which is the point of reporting it.
3. **Judge calibration.** The mock judge agrees perfectly with the human labels because it grades with the same reference facts; this proves the machinery, not a judge. A real model judge has to earn its kappa (Chapter 35).
4. **Candidate** with the leave answers broken.
5. **Gate.** The paired bootstrap blocks `leave` and passes every other category.

## Complete code

The complete, runnable code for this lab is [`lab.py`](lab.py) (87 lines), which uses the `atlas` package in this repository. Read it top to bottom: each step above is one block, headed by a `print("== Step N ...")` line.

## Commands

From the repository root:

```bash
make venv            # once
python labs/lab03-evaluation/lab.py
```

## Expected output

Captured from a verified run (macOS, Python 3.13) on 5 November 2026 and committed as [`expected_output.txt`](expected_output.txt).

```text
== Step 1: golden set 485d5b93d321: 18 items, categories ['adversarial', 'expenses', 'it', 'leave', 'out-of-scope', 'restricted']

== Step 2: baseline, graded per category
  adversarial   n=2  pass=1.00  95% CI (0.342, 1.0)
  expenses      n=5  pass=0.80  95% CI (0.376, 0.964)
  it            n=2  pass=1.00  95% CI (0.342, 1.0)
  leave         n=5  pass=1.00  95% CI (0.566, 1.0)
  out-of-scope  n=1  pass=1.00  95% CI (0.207, 1.0)
  restricted    n=3  pass=1.00  95% CI (0.439, 1.0)
  overall       {'n': 18, 'pass_rate': 0.944, 'wilson_95': (0.742, 0.99)}
  failed items: ['gs-018'] -> {'escalation': False, 'facts': False, 'forbidden': True, 'citations': False, 'pass': False}

== Step 3: judge calibration against human labels
  {'n': 18, 'agreement': 1.0, 'kappa': 1.0}
  (the mock judge grades with the same reference facts, so perfect agreement here
   shows the machinery works; a real model judge must earn its kappa, Ch. 35)

== Step 4: candidate with a regression confined to one category
  adversarial   n=2  pass=1.00
  expenses      n=5  pass=0.80
  it            n=2  pass=1.00
  leave         n=5  pass=0.00
  out-of-scope  n=1  pass=1.00
  restricted    n=3  pass=1.00

== Step 5: the regression gate
  adversarial   delta=+0.00  CI=(0.0, 0.0)  pass
  expenses      delta=+0.00  CI=(0.0, 0.0)  pass
  it            delta=+0.00  CI=(0.0, 0.0)  pass
  leave         delta=-1.00  CI=(-1.0, -1.0)  BLOCK
  out-of-scope  delta=+0.00  CI=(0.0, 0.0)  pass
  restricted    delta=+0.00  CI=(0.0, 0.0)  pass
  DECISION: BLOCKED (blocked: ['leave'])

  report written: eval_report.md
```

## Verification

The lab worked if:

- Step 2 overall pass rate 0.944 with 95% CI (0.742, 0.99)
- Step 5 `DECISION: BLOCKED (blocked: ['leave'])`
- `eval_report.md` is rewritten

## Common errors

| Symptom | Fix |
|---|---|
| Golden set version changed | You edited `golden_set.jsonl`; that is expected and is why the version is recorded with every result. |
| Gate passes a real regression | Small categories have wide intervals; add items to the category (Chapter 34) rather than loosening the tolerance. |

## Troubleshooting

- Print `baseline.per_item[item_id]` to see which grader failed an item.
- If kappa looks too good, check whether the judge sees the reference answer; that is the mock's shortcut.

## Production checklist

- [ ] The golden set is versioned
- [ ] Each category reports an interval, not just a rate
- [ ] The judge's agreement with people is measured
- [ ] The release gate is paired and per category

## Challenges

1. Fix `gs-018` by making table rows retrievable as their own chunks, then show the gate passes the fix.
2. Add ten items to the smallest category and watch its interval narrow.
3. Replace the mock judge with a real model and measure kappa (costs money).
