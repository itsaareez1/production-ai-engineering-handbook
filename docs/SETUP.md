# Setup

## Requirements

- Python 3.12 or later (3.13 is what the verification run used)
- Git
- Optional: Docker with the Compose plugin (Docker Desktop, or colima on macOS) for the database, Lab 4's sandbox step, and Lab 5
- No API key and no paid service

## Install

```bash
git clone https://github.com/itsaareez1/production-ai-engineering-handbook.git
cd production-ai-engineering-handbook
make venv                 # creates .venv and installs requirements-dev.txt
source .venv/bin/activate # Windows: .venv\Scripts\Activate.ps1
```

Without `make` (Windows, for example):

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

## Configure

Configuration comes from `ATLAS_*` environment variables, validated at
start-up (`atlas/core/config.py`). Nothing is required for development:
with no database URL Atlas uses an in-memory store, and with no secrets
it generates random per-process values and logs a warning.

```bash
cp .env.example .env      # optional; .env is ignored by git
```

In production (`ATLAS_ENV=prod`), `ATLAS_TOKEN_SECRET` and
`ATLAS_REDACTION_KEY` are required, must be at least 32 characters, and
may not be placeholders; the service refuses to start otherwise.

## Database

Atlas runs without a database. To use PostgreSQL with pgvector:

```bash
docker compose up -d db
docker compose run --rm migrate          # applies atlas/db/migrations
export ATLAS_DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas
```

The Compose database is not published to the host by default; to reach
it from the host add `ports: ["5432:5432"]` to the `db` service, or use
the disposable test database shown in [VERIFICATION.md](VERIFICATION.md).

## Run

```bash
python run.py 3.1                                  # one book listing
python -m atlas.cli ask --user alice "How many days of unused leave can I carry over?"
uvicorn atlas.api:app --port 8000                  # the HTTP service
docker compose up --build                          # the whole stack (Listing 44.1)
```

Development users are defined in `atlas/core/identity.py` (alice, bob,
sam in HR, nina in network, rita in support and a reviewer, olga an
operator). Get a token in dev with:

```bash
curl -s -X POST localhost:8000/auth/dev-token \
  -H 'content-type: application/json' -d '{"username":"alice"}'
```

## Optional: a real model provider

```bash
pip install -r requirements-providers.txt
export ATLAS_MODEL_PROVIDER=anthropic   # or openai
export ANTHROPIC_API_KEY=...            # your own key; this costs money
```

Real providers are never used by the tests or labs.
