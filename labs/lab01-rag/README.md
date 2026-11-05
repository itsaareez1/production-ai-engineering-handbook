# Lab 1: Build a production RAG application

Book chapters: 13–18. Estimated time: 45–60 minutes.

## Objectives

- Ingest documents with structure-aware chunking that keeps heading paths and whole tables
- Quarantine a poisoned document at ingestion instead of filtering it at answer time
- Measure semantic, keyword, fused (RRF), and reranked retrieval with recall@5 and MRR
- Show that permission and status filters run inside retrieval, before ranking
- Verify citations by label and by sentence, and see three kinds of bad answer caught

## Prerequisites

- Python 3.12 or later and the repository's virtual environment (`make venv`)
- No API key, no network access to model providers, no paid service

## Estimated time

45–60 minutes.

## Architecture

```text
corpus (examples/corpus/*.md) + 120 seeded distractors
   │  chunk_document()  scan_for_injection()
   ▼
MemoryStore ── search_vector (HashingEmbedder) ─┐
           └── search_keyword (BM25-style) ─────┤ rrf() ─► LexicalReranker ─► assemble() ─► verify_citations()
     ACL + status predicates applied inside both searches
```

## Files

| File | Purpose |
|---|---|
| [`lab.py`](lab.py) | the whole lab |
| [`expected_output.txt`](expected_output.txt) | output of a verified run |
| [`../../atlas/retrieval/text.py`](../../atlas/retrieval/text.py) | Document, Chunk, chunking, embedder, RRF, reranker |
| [`../../atlas/retrieval/store.py`](../../atlas/retrieval/store.py) | MemoryStore and PostgresStore |
| [`../../atlas/retrieval/context.py`](../../atlas/retrieval/context.py) | context assembly and citation verification |
| [`../../examples/evaluation/retrieval_set.jsonl`](../../examples/evaluation/retrieval_set.jsonl) | 10 retrieval questions with the relevant document |

## Steps

1. **Ingest.** Eight documents go in. `wiki-vpn` contains a note addressed to the assistant and is quarantined with the markers that fired; nothing from it is ever indexed.
2. **Inspect chunks.** Each chunk is labeled `doc#ordinal@updated` and carries its heading path, which the citation check and the reader both rely on.
3. **Evaluate retrieval.** 120 seeded distractor documents make the task non-trivial. Fusion beats either retriever alone on recall; the reranker fixes the ordering (MRR 0.76 → 0.91). One paraphrase ("time off left at the end of the year") still ranks 8th: a real gap that hashing embeddings cannot close, kept on purpose.
4. **Filters inside retrieval.** Alice's results never contain `hr-salary-bands`, and the trace counts what was filtered (`acl_filtered=1`); Sam (HR) sees it. The superseded leave policy is excluded by status.
5. **Citation verification.** A good answer passes. An appended, unsupported sentence and a citation to the superseded policy are both rejected, with the reason.

## Complete code

The complete, runnable code for this lab is [`lab.py`](lab.py) (114 lines), which uses the `atlas` package in this repository. Read it top to bottom: each step above is one block, headed by a `print("== Step N ...")` line.

## Commands

From the repository root:

```bash
make venv            # once
python labs/lab01-rag/lab.py
```

## Expected output

Captured from a verified run (macOS, Python 3.13) on 5 November 2026 and committed as [`expected_output.txt`](expected_output.txt).

```text
== Step 1: ingest
  hr-salary-bands  inserted     chunks=1 
  it-faq           inserted     chunks=2 
  net-credentials  inserted     chunks=1 
  policy-expenses  inserted     chunks=2 
  policy-leave-v6  inserted     chunks=1 
  policy-leave     inserted     chunks=3 
  vendor-notice    inserted     chunks=1 
  wiki-vpn         quarantined  chunks=0 assistant-directed note, tool or retrieval coercion

== Step 2: structure-aware chunks keep tables and heading paths
  policy-expenses#0@2026-02-15  [Travel and Expenses Policy > Expenses > Meals]  The daily meal allowance during business travel is
  policy-expenses#1@2026-02-15  [Travel and Expenses Policy > Expenses > Claims]  Expense claims must be submitted within 30 days us

== Step 3: retrieval evaluation (recall@5, MRR)
  semantic      recall@5=0.70  MRR=0.73
  keyword       recall@5=0.80  MRR=0.83
  fused         recall@5=0.90  MRR=0.76
  fused+rerank  recall@5=0.90  MRR=0.91
  not first after rerank: 'time off left at the end of the year' (rank 8)

== Step 4: filters run inside retrieval
  alice: docs=['noise-005', 'noise-021', 'noise-038', 'noise-039', 'noise-043', 'noise-045', 'noise-053', 'noise-091', 'noise-116', 'noise-117'] acl_filtered=1
  sam: docs=['hr-salary-bands', 'noise-021', 'noise-038', 'noise-039', 'noise-043', 'noise-045', 'noise-053', 'noise-091', 'noise-116', 'noise-117'] acl_filtered=0
  superseded excluded: True (status_filtered=1)

== Step 5: citation verification
  answer: Up to five days of unused annual leave may be carried over to the next year with manager approval.
  cites:  ['policy-leave#1@2026-06-01']
  good answer problems: []
  appended claim:       ["sentence not supported by cited passages: 'Contractors are excluded.'"]
  stale citation:       ["citations not in context: ['policy-leave-v6#0@2024-01-10']", "sentence not supported by cited passages: 'Up to five days of unused annual leave may be carried over to the next year with manager approval.'"]
```

## Verification

The lab worked if:

- Step 1 shows `wiki-vpn` as `quarantined` with `chunks=0`
- Step 3 shows fused+rerank recall@5 of 0.90 and MRR of 0.91
- Step 4 shows `acl_filtered=1` for alice and `hr-salary-bands` only for sam
- Step 5 reports `[]` for the good answer and a problem for each bad one

## Common errors

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'atlas'` | Run from the repository root, or use the virtual environment from `make venv`. The lab inserts the repository root into `sys.path`, so `python labs/lab01-rag/lab.py` works from anywhere inside the repo. |
| `ModuleNotFoundError: numpy` or `yaml` | Install dependencies: `make venv`. |
| Different recall numbers | You changed the corpus, the distractor seed, or the embedder dimension. The numbers are deterministic for the committed files. |

## Troubleshooting

- To see why a question missed, print `store.search_vector(...)` and `store.search_keyword(...)` separately for it; a miss in both is a vocabulary gap, a miss in one is what fusion is for.
- If a legitimate document is quarantined, print `scan_for_injection(doc.body)` to see which marker fired, then fix the content or the marker list (Chapter 40) rather than disabling the scan.

## Production checklist

- [ ] Poisoned content is quarantined at ingestion
- [ ] Recall and MRR are measured, not assumed
- [ ] ACL and status filters run before ranking
- [ ] Every answer sentence is checked against the passage it cites

## Challenges

1. Replace `HashingEmbedder` with a real embedding model and re-measure; does the paraphrase miss go away?
2. Add a `retrieval_set.jsonl` item for a table row (the taxi limit) and make it pass.
3. Run the same steps on `PostgresStore` (see `tests/integration/test_postgres.py`) and compare the numbers.
