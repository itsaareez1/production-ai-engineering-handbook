# Troubleshooting

Appendix F of the book is the troubleshooting guide for AI
applications in general. This page covers the companion code.

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'atlas'` | Running outside the repository or without the virtual environment | `cd` to the repository root and `source .venv/bin/activate`, or run `.venv/bin/python ...` |
| `ModuleNotFoundError: numpy`, `yaml`, `fastapi`, `psycopg` | Dependencies not installed | `make venv` |
| `python: command not found` / wrong version | Python 3.12+ not on `PATH` | Install Python 3.12 or later; use `python3` |
| Warning `token_secret not configured: generated a random per-process value` | No secrets set in dev/test | Expected in development. Set `ATLAS_TOKEN_SECRET` and `ATLAS_REDACTION_KEY` to keep tokens valid across restarts |
| `ATLAS_TOKEN_SECRET must be set in production` or `must be at least 32 random characters` | `ATLAS_ENV=prod` without real secrets | Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `ATLAS_DATABASE_URL must be a postgresql:// URL` | Wrong scheme | Use `postgresql://user:pass@host:port/db` |
| `could not connect to server` | Database not running or not published | `docker compose up -d db`; check the port mapping (see [SETUP.md](SETUP.md)) |
| `type "vector" does not exist` | pgvector missing | Use the `pgvector/pgvector:pg16` image, or install the extension; migrations run `CREATE EXTENSION vector` |
| 6 tests `skipped` | Integration tests need a database | Expected. Set `ATLAS_TEST_DATABASE_URL` to a **disposable** database to run them |
| `401` from `/v1/ask` | Missing, expired, or forged token | Get a token from `/auth/dev-token` (dev only) and send `Authorization: Bearer <token>` |
| `403` from `/metrics` or `/v1/documents` | The user lacks the operator or ingest role | Use `olga` in development |
| `404` from `/auth/dev-token` | `ATLAS_ENV=prod` | By design: development tokens are disabled in production |
| A document is `quarantined` | The injection scanner found a marker | Read the result's `reasons` (the markers that fired); fix the content, don't disable the scan (Chapter 40) |
| Answer `escalated` | No supported answer in the caller's permitted documents, or validation failed twice | Inspect the trace: `GET /v1/traces/{id}` as an operator |
| Answer `degraded` | Every provider failed, or the daily cost cap was reached | Check the `gateway` span's `attempts`; raise `ATLAS_DAILY_COST_CAP_USD` only deliberately |
| `docker compose up` fails: `port is already allocated` | Port 8000 in use | Stop the other process or change the published port |
| `app` waits forever | `migrate` failed | `docker compose logs migrate` |
| `Cannot connect to the Docker daemon` | Docker not running | Start Docker Desktop, or `colima start` |
| Lab output differs in IDs or milliseconds | Random IDs and wall-clock timings | Expected; everything else is deterministic |
| `listing ... line N is M chars (max 72)` | Book build: a printed listing line is too long | Wrap the line; printed code is limited to 72 characters |
