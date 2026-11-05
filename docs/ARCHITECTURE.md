# Architecture

Atlas is the internal knowledge assistant and ticket agent that the
book builds chapter by chapter. This repository is its reference
implementation: small enough to read in an afternoon, complete enough
that every production control the book argues for exists in code and
is exercised by a test.

## Request path

```text
client ─► FastAPI (atlas/api)          identity from a signed token only; request ID; no stack traces
            │
            ▼
        Atlas.ask (atlas/service.py)
            ├─ retrieval   store.search_vector + store.search_keyword   ACL and status predicates inside the query
            ├─ fusion      rrf()                                         reciprocal rank fusion
            ├─ rerank      LexicalReranker                               keeps the best N
            ├─ context     assemble()                                    dedup, token budget, SOURCE / UNTRUSTED tags,
            │                                                            restricted flag -> sensitivity
            ├─ gateway     Gateway.complete()                            route, retry, fallback, breaker, region rule, cost cap
            ├─ validation  schema + verify_citations()                   labels and per-sentence support
            ├─ repair      one bounded retry with the problems listed
            └─ outcome     answered | escalated | degraded               trace + metrics recorded for every request
```

## Components

| Package | Responsibility | Book |
|---|---|---|
| `atlas/core/config.py` | Settings from `ATLAS_*` variables, validated at start-up; production refuses missing or placeholder secrets | Ch. 44 |
| `atlas/core/identity.py` | Users, groups, roles; HMAC-signed tokens | Ch. 42 |
| `atlas/core/observability.py` | JSON logs, traces with required attributes per span, Prometheus metrics | Ch. 45 |
| `atlas/retrieval/` | Chunking, embeddings, in-memory and PostgreSQL stores, fusion, reranking, context assembly, citation verification | Ch. 13–18, 36 |
| `atlas/gateway/` | Provider abstraction, routing, retries, breakers, fallback, sensitivity routing, cost ledger and cap | Ch. 9, 24, 46 |
| `atlas/validation.py` | The answer schema and its validator (Listing 12.1 as a module) | Ch. 12 |
| `atlas/agents/` | Tools with levels, the authorization policy, approvals, the bounded planner/executor/verifier agent, idempotent records, hash-chained audit | Ch. 19, 24–29, 43 |
| `atlas/security/controls.py` | Keyed redaction, injection scanning, egress checks | Ch. 39–41 |
| `atlas/evaluation/harness.py` | Golden sets, graders, Wilson intervals, Cohen's kappa, judge calibration, the paired per-category regression gate | Ch. 33–38 |
| `atlas/db/` | SQL migrations with checksum tracking | Ch. 44 |
| `atlas/service.py` | Wires the above: `ingest`, `reconcile`, `ask` | Ch. 3, 52 |
| `atlas/api/` | HTTP interface | Ch. 44 |
| `atlas/cli.py` | Command line: ingest, ask, eval, agent | |

## Storage

`MemoryStore` needs nothing and is what the tests and labs use.
`PostgresStore` uses PostgreSQL 16 with pgvector (HNSW index,
iterative scans) and full-text search (`websearch_to_tsquery`). In
both, permission and status filters run inside the search, so a
document the caller may not read never reaches ranking; the trace
records only how many were filtered. Schema:
`atlas/db/migrations/001_init.sql`.

## Model providers

`MockProvider` is deterministic and free. It can inject faults
(transient errors, permanent errors, bad citations, unsupported
claims, invalid JSON, a stubborn planner) so every failure path is
testable. `AnthropicProvider` and `OpenAIProvider` are thin adapters
for real use; they need the optional SDKs and your own key, and no
test calls them.

## Deployment

`docker-compose.yml` (Listing 44.1): `db` (pgvector) → `migrate`
(one-shot) → `app` (unprivileged, health-checked); `cache` and
`objects` alongside; an `inference` service (vLLM) behind the `live`
profile for a self-hosted model on a GPU.

## Decisions

See [DECISIONS.md](DECISIONS.md).
