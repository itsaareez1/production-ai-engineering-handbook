# Companion code — The Production AI Engineering Handbook

Every listing in the book, one file per listing, runnable with
`python3` wherever its caption says *Verified by execution*.

by Arslan ud Din Shafiq

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py 3.1
```

```
--- Listing 3.1  (listings/ch03/listing_3_1.py) ---
validated 120.0 1
```

Appendix K of the book walks through the same steps for readers new
to Python tooling.

## Commands

| | |
|---|---|
| `python run.py 3.1` | run one listing by number |
| `python run.py --list` | list all 49 runnable listings |
| `python run.py --all` | run every listing (about a second) |
| `python -m pytest tests/ -q` | the test suite (106 tests) |
| `docker compose build && docker compose up` | the Atlas service of Listing 44.1 |

`run.py` finds listings by number, so you never need to know the
folder layout. Python 3.12 or newer is required.

## Layout

```
run.py                     run any listing by number
listings/chNN/             the listings, as printed, one file each
atlas/validation.py        Listing 12.1 as a module (Listing 33.1 imports it)
atlas/api.py               the service the Dockerfile of Listing 44.1 starts
tests/test_listings.py     executes every runnable listing
tests/test_api.py          tests the service
Dockerfile                 Listing 44.1, part 1
docker-compose.yml         Listing 44.1, part 2
VERIFICATION.md            the output of every listing on a real machine
requirements.txt           NumPy and PyYAML for the listings; FastAPI and
                           Uvicorn for the service
```

## Listings by chapter

| Listing | Chapter | What it shows | File |
|---|---|---|---|
| 3.1 | 3 Reference Architecture | application skeleton with a stubbed model | `ch03/listing_3_1.py` |
| 5.1 | 5 Requirements | machine-readable requirements with a validator | `ch05/listing_5_1.py` |
| 6.1 | 6 When Not to Use AI | rules-first routing, model fallback | `ch06/listing_6_1.py` |
| 8.1 | 8 Model Selection | cost per request, caching and retries | `ch08/listing_8_1.py` |
| 9.1 | 9 Gateways | routing, fallback, circuit breaking | `ch09/listing_9_1.py` |
| 10.1 | 10 Context Budgets | per-source caps and a drop log | `ch10/listing_10_1.py` |
| 11.1 | 11 Instructions | versioned instructions, regression check | `ch11/listing_11_1.py` |
| 12.1 | 12 Structured Output | answer schema, validator, repair loop | `ch12/listing_12_1.py` |
| 13.1 | 13 RAG | recall@k and MRR over a labeled set | `ch13/listing_13_1.py` |
| 14.1 | 14 Vector Search | cosine similarity, exact nearest neighbour | `ch14/listing_14_1.py` |
| 14.2 | 14 Vector Search | pgvector schema, permission-filtered query | `ch14/listing_14_2.sql` |
| 15.1 | 15 Hybrid Retrieval | BM25 keyword scoring | `ch15/listing_15_1.py` |
| 15.2 | 15 Hybrid Retrieval | reciprocal rank fusion | `ch15/listing_15_2.py` |
| 15.3 | 15 Hybrid Retrieval | FTS5 search with a permission filter | `ch15/listing_15_3.py` |
| 16.1 | 16 Reranking | reranking a fused list, and measuring it | `ch16/listing_16_1.py` |
| 17.1 | 17 Citation | label resolution and span support | `ch17/listing_17_1.py` |
| 18.1 | 18 Ingestion | structure-aware chunking, idempotent indexing | `ch18/listing_18_1.py` |
| 19.1 | 19 Tool Use | bounded loop with validation and authorization | `ch19/listing_19_1.py` |
| 20.1 | 20 Integrations | URL validation against SSRF | `ch20/listing_20_1.py` |
| 21.1 | 21 MCP | JSON-RPC messages for discovery and invocation | `ch21/listing_21_1.jsonc` |
| 22.1 | 22 Orchestration | checkpointed step graph with resumption | `ch22/listing_22_1.py` |
| 23.1 | 23 Deterministic Shell | state machine, one validated model decision | `ch23/listing_23_1.py` |
| 24.1 | 24 Reliability | idempotent write, bounded jittered retries | `ch24/listing_24_1.py` |
| 26.1 | 26 Agent Architecture | planner, executor, verifier, state, budget | `ch26/listing_26_1.py` |
| 27.1 | 27 Agent Memory | memory tiers with event-gated writes | `ch27/listing_27_1.py` |
| 28.1 | 28 Permission Model | tool registry and a policy layer | `ch28/listing_28_1.py` |
| 29.1 | 29 Human Oversight | proposal-bound, expiring approvals | `ch29/listing_29_1.py` |
| 30.1 | 30 Multi-Agent | orchestrator-worker with result contracts | `ch30/listing_30_1.py` |
| 31.1 | 31 Agents vs Workflows | cost and latency distributions | `ch31/listing_31_1.py` |
| 32.1 | 32 Failure Taxonomy | first-pass failure classifier | `ch32/listing_32_1.py` |
| 33.1 | 33 Testing Pyramid | unit, contract and statistical tests | `ch33/listing_33_1.py` |
| 34.1 | 34 Golden Set | stratified sampling, split, leakage check | `ch34/listing_34_1.py` |
| 35.1 | 35 Evaluation | grading, a judge, and judge calibration | `ch35/listing_35_1.py` |
| 36.1 | 36 Groundedness | claim-level grounding, confidence calibration | `ch36/listing_36_1.py` |
| 37.1 | 37 Reliability Engineering | error budgets by incident and release | `ch37/listing_37_1.py` |
| 38.1 | 38 Regression Gate | paired bootstrap per category | `ch38/listing_38_1.py` |
| 39.1 | 39 Prompt Injection | regression suite checked against effects | `ch39/listing_39_1.py` |
| 40.1 | 40 Trust Boundaries | trust tiers, marker scan, tier-aware wrapping | `ch40/listing_40_1.py` |
| 41.1 | 41 Data Protection | redaction with stable pseudonyms, retention | `ch41/listing_41_1.py` |
| 42.1 | 42 Identity | identity from session; confused deputy refused | `ch42/listing_42_1.py` |
| 43.1 | 43 Agent Security | credential broker and egress policy | `ch43/listing_43_1.py` |
| 44.1 | 44 Environments | container build and Compose definition | `ch44/Dockerfile` |
| 45.1 | 45 Observability | trace and span schema, metrics record | `ch45/listing_45_1.py` |
| 46.1 | 46 Cost Engineering | total cost with attribution by component | `ch46/listing_46_1.py` |
| 47.1 | 47 Scaling | retry storm versus bounded-wait admission | `ch47/listing_47_1.py` |
| 48.1 | 48 Release | manifest, canary decision, rollback | `ch48/listing_48_1.py` |
| 49.1 | 49 Build/Buy | three-year cost including expected exit | `ch49/listing_49_1.py` |
| 50.1 | 50 Maintainability | architecture fitness function | `ch50/listing_50_1.py` |
| 51.1 | 51 Governance | ownership and change-control matrix | `ch51/listing_51_1.py` |
| 52.1 | 52 Atlas End to End | prototype path beside production path | `ch52/listing_52_1.py` |
| 53.1 | 53 Readiness Review | the go/no-go gate, applied to Atlas | `ch53/listing_53_1.py` |
| 54.1 | 54 Roadmap | plan file with ladder-mapped exit criteria | `ch54/listing_54_1.py` |

Chapters 1, 2, 4, 7, 25 and the appendices carry no listing.

## The three listings `run.py` does not run

Their captions say *Reviewed for correctness*, not *Verified by
execution*, and `run.py` tells you what each one needs:

- **14.2** needs PostgreSQL with pgvector.
  `psql "$DATABASE_URL" -f listings/ch14/listing_14_2.sql`
- **21.1** is a transcript of MCP messages, not a program.
  `python listings/ch21/validate_21_1.py` checks it structurally —
  23 assertions on JSON-RPC shape, header/`_meta` agreement, result
  types and id pairing.
- **44.1** needs Docker. `docker compose build && docker compose up`,
  then `curl localhost:8000/health` returns `{"status":"ok"}`.
  The stack runs PostgreSQL with pgvector, Redis, an S3-compatible
  object store (SeaweedFS), and the API.

All three have been checked despite not being run by `run.py` —
14.2 applied to PostgreSQL 16 with pgvector 0.8.7, 21.1 against its
structural checker, 44.1 built and served. `VERIFICATION.md` has the
transcripts.

## Errata

Verifying the manuscript turned up seven defects (ERR-01 to ERR-07):
two code defects in listings, two explanations that did not match the
correct output, an image that could no longer be pulled, a caption that
could be made stronger, and a dead local variable. All seven are fixed
in the first edition of the book and in this repository. The code here
is exactly what the book prints, and the test suite checks the outputs
the chapters quote.

## Notes on the code

The listings are deliberately plain. They use the standard library,
NumPy and PyYAML, and no framework, because the book's argument is
that the controls belong in code the team owns. Models are stubbed
throughout: the stubs are chosen to exercise the failure the chapter
is about, which is why several of them misbehave on purpose.

Lines are kept to 72 characters so the code fits a printed page
without wrapping.

Listing 11.1 writes to an `instructions/` directory in the working
directory; it is created on first run and is ignored by git.

## License

MIT. See `LICENSE`.
