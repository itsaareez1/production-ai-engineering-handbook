"""Integration tests against a real PostgreSQL with pgvector.

Skipped unless ATLAS_TEST_DATABASE_URL points at a disposable database,
for example the one `docker compose up db` starts. The tests drop and
recreate the public schema, so never point this at real data.

    export ATLAS_TEST_DATABASE_URL=postgresql://atlas:atlas@localhost:5432/atlas
    python -m pytest tests/integration -q
"""
import os

import pytest

DSN = os.environ.get("ATLAS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="ATLAS_TEST_DATABASE_URL not set")


@pytest.fixture(scope="module")
def db():
    import psycopg

    from atlas.db.migrate import migrate

    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    assert migrate(DSN) == ["001_init.sql"]
    assert migrate(DSN) == []                     # idempotent
    return DSN


@pytest.fixture(scope="module")
def pg_atlas(db):
    from atlas.core.config import Settings
    from atlas.corpus import load_corpus
    from atlas.service import Atlas
    from atlas.testing import CORPUS

    svc = Atlas(Settings(env="test", database_url=db))
    results = {d.doc_id: svc.ingest(d).outcome for d in load_corpus(CORPUS)}
    assert results["wiki-vpn"] == "quarantined"
    assert results["policy-leave"] == "inserted"
    return svc


def test_acl_and_status_predicates_run_inside_sql(pg_atlas):
    from atlas.core.identity import DIRECTORY

    st = pg_atlas.store
    res = st.search_keyword("salary band senior engineer", DIRECTORY["alice"].groups, 10)
    assert all(c.doc_id != "hr-salary-bands" for c, _ in res.ranked)
    assert res.acl_filtered >= 1
    res = st.search_keyword("carry over unused leave", DIRECTORY["alice"].groups, 10)
    assert all(c.doc_id != "policy-leave-v6" for c, _ in res.ranked)
    assert res.status_filtered >= 1
    sam = st.search_keyword("salary band senior engineer", DIRECTORY["sam"].groups, 10)
    assert any(c.doc_id == "hr-salary-bands" for c, _ in sam.ranked)


def test_vector_search_respects_permissions(pg_atlas):
    from atlas.core.identity import DIRECTORY

    q = pg_atlas.embedder.embed(["break-glass router credentials"])[0]
    alice = pg_atlas.store.search_vector(q, DIRECTORY["alice"].groups, 20)
    nina = pg_atlas.store.search_vector(q, DIRECTORY["nina"].groups, 20)
    assert all(c.doc_id != "net-credentials" for c, _ in alice.ranked)
    assert any(c.doc_id == "net-credentials" for c, _ in nina.ranked)


def test_reingest_is_idempotent_in_the_database(pg_atlas):
    from atlas.corpus import load_corpus
    from atlas.testing import CORPUS

    doc = next(d for d in load_corpus(CORPUS) if d.doc_id == "policy-leave")
    assert pg_atlas.ingest(doc).outcome == "unchanged"


def test_full_ask_path_on_postgres(pg_atlas):
    from atlas.core.identity import DIRECTORY

    r = pg_atlas.ask("How many days of unused leave can I carry over?", DIRECTORY["alice"])
    assert r.outcome == "answered" and "five days" in r.answer["answer"]
    assert r.answer["citations"][0].startswith("policy-leave#")


def test_records_and_audit_persist_with_idempotency_and_hash_chain(pg_atlas):
    from atlas.core.identity import DIRECTORY

    alice = DIRECTORY["alice"]
    a = pg_atlas.tickets.draft(alice, {"subject": "Integration draft", "body": "x"})
    b = pg_atlas.tickets.draft(alice, {"subject": "integration draft", "body": "y"})
    assert a["result"] == b["result"] and b["replayed"]
    pg_atlas.audit.append("tester", "integration.check", {"n": 1})
    assert pg_atlas.audit.verify()


def test_reconciliation_against_the_database(pg_atlas):
    drift = pg_atlas.reconcile({**pg_atlas.store.versions(), "brand-new": "1"})
    assert drift["missing"] == ["brand-new"]
