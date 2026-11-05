# Lab 5: Deploy an AI application

Book chapters: 44, 47, 48. Estimated time: 30 minutes (plus the first image build).

## Objectives

- Start the whole stack with Docker Compose: database, one-shot migration, application, cache, object store
- Verify the deployment contract instead of trusting that containers started
- Show that restarts are idempotent: migrations and seeding apply nothing twice

## Prerequisites

- Python 3.12 or later and the repository's virtual environment (`make venv`)
- No API key, no network access to model providers, no paid service
- Docker with the Compose plugin (Docker Desktop or colima), about 2 GB free disk
- Port 8000 free on the host (the database is not published)

## Estimated time

30 minutes (plus the first image build).

## Architecture

```text
db (pgvector/pgvector:pg16, healthcheck)
  └─► migrate (one-shot: python -m atlas.db.migrate) ─► completes
        └─► app (uvicorn atlas.api:app, USER atlas, healthcheck /health)
cache (redis)   objects (seaweedfs)   inference (vllm, profile "live", needs a GPU; not started)
```

## Files

| File | Purpose |
|---|---|
| [`lab.py`](lab.py) | starts the stack and runs the checks |
| [`expected_output.txt`](expected_output.txt) | output of a verified run |
| [`../../Dockerfile`](../../Dockerfile) | Listing 44.1, part 1 |
| [`../../docker-compose.yml`](../../docker-compose.yml) | Listing 44.1, part 2 |
| [`../../atlas/db/migrations/001_init.sql`](../../atlas/db/migrations/001_init.sql) | the schema |

## Steps

1. **Configuration** is validated with `docker compose config`.
2. **Build and start**; the lab waits for `/health`.
3. **Contract checks**: migration recorded, seven documents seeded, `wiki-vpn` quarantined in the database, the process is not root, and an authenticated question is answered with a citation.
4. **Restart** the migrate service: nothing is applied twice and no chunk is duplicated.

## Complete code

The complete, runnable code for this lab is [`lab.py`](lab.py) (94 lines), which uses the `atlas` package in this repository. Read it top to bottom: each step above is one block, headed by a `print("== Step N ...")` line.

## Commands

From the repository root:

```bash
make venv            # once
python labs/lab05-deployment/lab.py
```

```bash
python labs/lab05-deployment/lab.py --down
```

## Expected output

Captured from a verified run (macOS, Python 3.13) on 5 November 2026 and committed as [`expected_output.txt`](expected_output.txt).

```text
== Step 1: configuration is valid
  docker compose config: OK

== Step 2: build and start
  healthy after 1.0s

== Step 3: verify the deployment contract
  [PASS] migration applied
  [PASS] corpus seeded
  [PASS] poisoned page quarantined in the database
  [PASS] process runs unprivileged
  [PASS] authenticated question answered with a citation: policy-leave#1@2026-06-01

== Step 4: restart is idempotent
  [PASS] migration re-run applies nothing
  [PASS] re-seeding wrote no duplicate chunks

Deployment checks: 7/7 passed. Stop with: python labs/lab05-deployment/lab.py --down
```

## Verification

The lab worked if:

- `Deployment checks: 7/7 passed.`
- Then stop and remove data: `python labs/lab05-deployment/lab.py --down`

## Common errors

| Symptom | Fix |
|---|---|
| `port is already allocated` | Stop whatever uses port 8000, or change the published ports in `docker-compose.yml`. |
| `app` never becomes healthy | `docker compose logs app migrate`; a failed migration stops the app from starting by design. |
| Build fails on Apple silicon | Make sure Docker uses the native architecture; all images used have arm64 builds. |

## Troubleshooting

- `docker compose ps` shows which service is not healthy.
- `docker compose exec db psql -U atlas -d atlas` opens the database for inspection.

## Production checklist

- [ ] Migrations run once, before the app, and are tracked
- [ ] The app runs unprivileged and holds no secrets in the image
- [ ] Health is checked, not assumed
- [ ] Restarts are idempotent
- [ ] The stack is torn down after the lab

## Challenges

1. Set `ATLAS_ENV=prod` without secrets and confirm the app refuses to start.
2. Add a second migration and show the restart applies only it.
3. Back up the database volume, destroy it, restore it, and time the restore against an RTO (Chapter 47).
