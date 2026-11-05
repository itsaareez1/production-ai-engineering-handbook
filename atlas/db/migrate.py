"""Apply SQL migrations in order, each in its own transaction.

    python -m atlas.db.migrate            # uses ATLAS_DATABASE_URL

Applied migrations are recorded in schema_migrations, so re-running is
safe. Migrations are expand-and-contract (Chapter 44): never edit an
applied file; add a new one.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def migrate(dsn: str) -> list[str]:
    import psycopg

    applied_now = []
    with psycopg.connect(dsn, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "name text PRIMARY KEY, sha256 text NOT NULL, "
                "applied_at timestamptz NOT NULL DEFAULT now())")
            conn.commit()
            cur.execute("SELECT name, sha256 FROM schema_migrations")
            done = dict(cur.fetchall())
        for path in sorted(MIGRATIONS.glob("*.sql")):
            sql = path.read_text()
            digest = hashlib.sha256(sql.encode()).hexdigest()
            if path.name in done:
                if done[path.name] != digest:
                    raise RuntimeError(f"{path.name} changed after it was applied; "
                                       "add a new migration instead")
                continue
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute("INSERT INTO schema_migrations (name, sha256) VALUES (%s, %s)",
                            (path.name, digest))
            conn.commit()
            applied_now.append(path.name)
    return applied_now


if __name__ == "__main__":
    dsn = os.environ.get("ATLAS_DATABASE_URL")
    if not dsn:
        sys.exit("ATLAS_DATABASE_URL is not set")
    names = migrate(dsn)
    print("applied:", ", ".join(names) if names else "nothing (up to date)")
