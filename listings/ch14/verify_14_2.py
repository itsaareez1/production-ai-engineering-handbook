"""Execute Listing 14.2 against a real PostgreSQL with pgvector.

Usage: python listings/ch14/verify_14_2.py postgresql://USER:PASS@HOST/DB

Creates a scratch database named listing_14_2 on that server, applies
the schema and settings exactly as printed, PREPAREs the query with
its parameter types, loads two documents with different ACLs, and
runs the query as an all-staff caller and as an HR caller. Drops the
scratch database afterwards.
"""
import sys
from pathlib import Path

import psycopg

SQL = (Path(__file__).with_name("listing_14_2.sql")).read_text()
schema, query = SQL.split("SELECT c.id", 1)
query = "SELECT c.id" + query.strip().rstrip(";")


def main(dsn: str) -> int:
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute("DROP DATABASE IF EXISTS listing_14_2")
        admin.execute("CREATE DATABASE listing_14_2")
    scratch = psycopg.conninfo.make_conninfo(dsn, dbname="listing_14_2")
    checks = []
    try:
        with psycopg.connect(scratch, autocommit=True) as c:
            c.execute(schema)
            ver = c.execute("SELECT extversion FROM pg_extension "
                            "WHERE extname = 'vector'").fetchone()[0]
            print(f"pgvector {ver}; schema, index and settings applied")
            c.execute(f"PREPARE search(vector(1024), text[]) AS {query}")
            print("query prepared with types (vector(1024), text[])")
            v = "[" + ",".join(["1"] + ["0"] * 1023) + "]"
            for i, (doc, head, text, group) in enumerate([
                    ("policy-leave", "Leave > 4.2", "five days carry over", "all-staff"),
                    ("policy-pay", "Pay > 3.1", "salary bands", "hr")]):
                c.execute("INSERT INTO chunks (document_id, chunk_index, heading_path, content,"
                          " content_hash, embedding, embed_model, updated_at)"
                          " VALUES (%s, 0, %s, %s, %s, %s, 'test@1', now())",
                          (doc, head, text, f"h{i}", v))
                c.execute("INSERT INTO document_acl VALUES (%s, %s)", (doc, group))
            for who, groups, want in [("all-staff", ["all-staff"], ["policy-leave"]),
                                      ("hr", ["all-staff", "hr"], ["policy-leave", "policy-pay"])]:
                # EXECUTE is a utility statement: bind on the client side
                cur = psycopg.ClientCursor(c)
                rows = cur.execute("EXECUTE search(%s, %s)", (v, groups)).fetchall()
                got = sorted(r[1] for r in rows)
                checks.append(got == want)
                print(f"{who:<9} caller sees {got}  {'ok' if got == want else 'WRONG'}")
    finally:
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute("DROP DATABASE IF EXISTS listing_14_2")
    print(f"{sum(checks)}/{len(checks)} checks passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
