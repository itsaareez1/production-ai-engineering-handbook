# The Production AI Engineering Handbook: companion code

**Atlas**, a complete, tested reference implementation of a production
AI application: a permission-aware knowledge assistant with a model
gateway, a bounded ticket agent, an evaluation harness, security
controls, observability, and a Docker deployment. It also contains
every code listing from the book and seven hands-on labs.

Everything runs offline on a deterministic mock model. **No API key,
no paid service, no cloud account.**

```bash
git clone https://github.com/itsaareez1/production-ai-engineering-handbook.git
cd production-ai-engineering-handbook
make venv && make verify       # about a minute
```

---

## Relationship with the book

*The Production AI Engineering Handbook: Build, Deploy, Secure,
Evaluate, and Scale Reliable AI Applications* by Arslan ud Din Shafiq
follows one system, Atlas, from demo to production across 54 chapters.
This repository is that system.

- `listings/` holds every code listing exactly as printed, one file per
  listing, runnable by number: `python run.py 15.2`.
- `atlas/` is the full implementation the listings are extracted from
  and simplified for print.
- [`docs/CHAPTER_CODE_MAPPING.md`](docs/CHAPTER_CODE_MAPPING.md) maps
  every chapter to its listings, modules, tests, and labs.

The book's text and figures are not in this repository and are not
covered by its license.

## What you will build

An internal assistant that answers employees' questions from company
documents, cites its sources, never shows a document to someone who
may not read it, refuses when it cannot support an answer, and opens
support tickets through an agent that asks a person before doing
anything risky. Then you deploy it, observe it, evaluate it, attack it,
and review it for production.

## Key features

| Area | What is implemented |
|---|---|
| Retrieval | Structure-aware chunking; vector and keyword search; reciprocal rank fusion; reranking; ACL and status filters inside the query; context budget; citation verification by label and by sentence |
| Model gateway | Provider adapters; routing by task; timeouts; retries with jittered backoff for transient errors only; fallback; circuit breakers; in-region routing for restricted context; cost ledger with a daily cap |
| Agent | Tool registry with risk levels; authorization with the caller's identity; step budget; no-progress guard; approvals bound to the exact proposal, with expiry and no self-approval; idempotent writes; hash-chained audit log |
| Security | Injection scanning and quarantine at ingestion; untrusted-content tags; keyed redaction; egress allowlist with resolved-IP checks; signed tokens; role checks; no stack traces to clients |
| Evaluation | Versioned golden set; deterministic graders; Wilson intervals; judge calibration with Cohen's kappa; paired per-category regression gate |
| Operations | Validated configuration; JSON logs; traces with required attributes; Prometheus metrics; SQL migrations; Docker image running unprivileged; Compose stack |
| Tests | 201 tests: unit, security, API, listings, and PostgreSQL integration |

## Architecture overview

```text
client ─► FastAPI ─► Atlas.ask
                       ├─ retrieval (vector + keyword, ACL/status inside) ─► RRF ─► rerank
                       ├─ context assembly (budget, SOURCE/UNTRUSTED tags, sensitivity)
                       ├─ model gateway (route, retry, fallback, breaker, region rule, cost cap)
                       ├─ validation (schema, citations, per-sentence support) ─► one repair
                       └─ answered | escalated | degraded  ─► trace + metrics
ingestion ─► injection scan ─► quarantine | chunk + embed ─► PostgreSQL/pgvector or memory
agent ─► plan ─► authorize ─► allow | approval | refuse ─► tool ─► audit (hash chain)
```

Details: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Design
choices: [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Repository structure

```text
atlas/                     the reference implementation
  api/  agents/  core/  db/  evaluation/  gateway/  retrieval/  security/
  service.py  cli.py  validation.py  prompts/
listings/chNN/             every book listing, as printed
labs/lab01..lab07/         seven hands-on labs, each with a README
examples/corpus/           eight sample company documents (one poisoned)
examples/evaluation/       golden set and retrieval set
tests/                     unit/, security/, integration/, API and listing tests
docs/                      architecture, setup, verification, mapping, decisions, templates
run.py                     run any listing by number
Dockerfile, docker-compose.yml   Listing 44.1
Makefile                   venv, test, lint, labs, verify targets
.env.example               configuration template (placeholders only)
```

## Prerequisites

- Python 3.12 or later
- Git
- Optional: Docker with Compose for the database, the sandbox step of
  Lab 4, and Lab 5

## Installation

```bash
make venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
```

Without `make`: `python -m venv .venv` then
`.venv/bin/python -m pip install -r requirements-dev.txt`. Full
instructions, including Windows: [`docs/SETUP.md`](docs/SETUP.md).

## Environment configuration

All settings are `ATLAS_*` environment variables, validated at
start-up. None is needed for development. To customize, copy the
template:

```bash
cp .env.example .env
```

In production (`ATLAS_ENV=prod`) the token secret and redaction key
are required, must be at least 32 random characters, and cannot be
placeholders; the service refuses to start otherwise.

## Database setup

Without `ATLAS_DATABASE_URL`, Atlas uses an in-memory store and needs
no database. For PostgreSQL with pgvector:

```bash
docker compose up -d db
docker compose run --rm migrate
```

Migrations live in `atlas/db/migrations/` and are tracked by checksum,
so re-running them applies nothing.

## Starting the application

```bash
python -m atlas.cli ask --user alice "How many days of unused leave can I carry over?"
uvicorn atlas.api:app --port 8000          # HTTP service, in-memory store
docker compose up --build                  # full stack: db, migrate, app, cache, objects
```

```text
{
  "outcome": "answered",
  "answer": "Up to five days of unused annual leave may be carried over to the next year with manager approval.",
  "citations": ["policy-leave#1@2026-06-01"], ...
}
```

## Running tests

```bash
make test                      # 195 passed, 6 skipped (integration tests need a database)
make verify                    # lint + tests + all listings + offline labs
make verify-db                 # with ATLAS_TEST_DATABASE_URL set: integration tests, Listing 14.2
make verify-docker             # Lab 5: build and verify the Compose stack
```

There is no CI in this repository, by design. Verification is the
documented manual process in [`docs/VERIFICATION.md`](docs/VERIFICATION.md),
which also records the latest run.

## Running individual labs

| Lab | Command |
|---|---|
| 1. Production RAG | `python labs/lab01-rag/lab.py` |
| 2. Model gateway | `python labs/lab02-model-gateway/lab.py` |
| 3. Evaluation pipeline | `python labs/lab03-evaluation/lab.py` |
| 4. Agent security | `python labs/lab04-agent-security/lab.py` |
| 5. Deployment | `python labs/lab05-deployment/lab.py` (Docker) |
| 6. Observability | `python labs/lab06-observability/lab.py` |
| 7. Production readiness | `python labs/lab07-production-readiness/lab.py` |

Each lab's README has objectives, steps, expected output, and
challenges. Overview: [`labs/README.md`](labs/README.md).

Book listings: `python run.py --list`, `python run.py 14.1`,
`python run.py --all`.

## Troubleshooting

The common problems and their fixes are in
[`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md). The three most
frequent: run from the repository root with the virtual environment
active; six skipped tests are expected without a database; and IDs and
timings in lab output differ between runs by design.

## Security guidance

- Never commit secrets. `.env` is ignored by git; `.env.example`
  contains placeholders only.
- Development tokens are disabled in production, and production
  refuses to start without real secrets.
- The development users and the poisoned sample document are fixtures
  for testing controls; replace identity with your own provider.
- This is teaching code with tests, not audited software. Review it
  before using it with real data.
- Report vulnerabilities privately: see [`SECURITY.md`](SECURITY.md).

## Contributing

Bug reports, especially errors in the book's code, are welcome. Read
[`CONTRIBUTING.md`](CONTRIBUTING.md) first: listings must match the
printed book, tests and labs must stay offline and free, and the
repository takes no CI configuration. Participation follows the
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

The code in this repository is released under the MIT License; see
[`LICENSE`](LICENSE). The book's text, figures, and manuscript are
copyright of the author, are not included here, and are not covered by
this license.

## Book and author

**The Production AI Engineering Handbook**
*Build, Deploy, Secure, Evaluate, and Scale Reliable AI Applications*
Arslan ud Din Shafiq, 2026.

Arslan ud Din Shafiq is a software architect and founder-engineer with
more than ten years of building and operating commercial software,
Founder and Director of Stacklab X Ltd, and a 9× Alibaba Cloud MVP. He
is also the author of *The AI-Powered Small Business*. He writes at
[imarslan.net](https://imarslan.net).
