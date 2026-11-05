"""Configuration, identity, retrieval, and the in-memory store."""
import time

import pytest
from pydantic import ValidationError

from atlas.core.config import Settings
from atlas.core.identity import DIRECTORY, AuthError, issue_token, verify_token
from atlas.retrieval.store import MemoryStore
from atlas.retrieval.text import (Document, HashingEmbedder, LexicalReranker, chunk_document,
                                  rrf)


# ------------------------------------------------------------ configuration
def test_production_refuses_to_start_without_secrets():
    with pytest.raises(ValidationError, match="must be set in production"):
        Settings(env="prod")


def test_development_generates_random_secrets_not_defaults():
    a, b = Settings(env="dev"), Settings(env="dev")
    assert a.token_secret.get_secret_value() != b.token_secret.get_secret_value()


@pytest.mark.parametrize("bad", [
    {"database_url": "mysql://x"},
    {"model_fallback": "mock-large"},
    {"rerank_keep": 50, "retrieval_candidates": 10},
    {"log_level": "LOUD"},
    {"request_timeout_s": 0},
])
def test_invalid_configuration_is_rejected(bad):
    with pytest.raises(ValidationError):
        Settings(env="test", **bad)


def test_settings_from_environment_parses_lists_and_types():
    s = Settings.from_env({"ATLAS_ENV": "test", "ATLAS_EGRESS_ALLOWLIST": "a.example.com, b.example.com",
                           "ATLAS_RETRIEVAL_CANDIDATES": "20"})
    assert s.egress_allowlist == ["a.example.com", "b.example.com"]
    assert s.retrieval_candidates == 20


# ----------------------------------------------------------------- identity
def test_token_round_trip_preserves_identity():
    who = DIRECTORY["sam"]
    assert verify_token(issue_token(who, "s3cret"), "s3cret") == who


def test_tampered_token_is_rejected():
    tok = issue_token(DIRECTORY["alice"], "s3cret")
    body, sig = tok.split(".")
    forged = body[:-2] + ("A" if body[-2] != "A" else "B") + body[-1] + "." + sig
    with pytest.raises(AuthError):
        verify_token(forged, "s3cret")


def test_token_signed_with_another_secret_is_rejected():
    with pytest.raises(AuthError, match="bad signature"):
        verify_token(issue_token(DIRECTORY["alice"], "other"), "s3cret")


def test_expired_token_is_rejected():
    tok = issue_token(DIRECTORY["alice"], "s3cret", ttl_s=60, now=time.time() - 120)
    with pytest.raises(AuthError, match="expired"):
        verify_token(tok, "s3cret")


# ----------------------------------------------------------------- chunking
DOC = Document("d1", "Policy", "# A\n\nIntro text here.\n\n## B\n\nRule one applies.\n\n"
               "| Item | Limit |\n|---|---|\n| Hotel | 180 |\n| Taxi | 40 |\n",
               frozenset({"all-staff"}), updated="2026-01-01")


def test_chunks_carry_heading_paths_and_keep_tables_whole():
    chunks = chunk_document(DOC)
    assert [c.heading_path for c in chunks] == ["Policy > A", "Policy > A > B"]
    table_chunk = chunks[1].text
    assert "| Hotel | 180 |" in table_chunk and "| Taxi | 40 |" in table_chunk
    assert chunks[1].label == "d1#1@2026-01-01"


def test_rrf_rewards_agreement_between_rankings():
    fused = rrf([["a", "b", "c"], ["b", "a", "d"]])
    assert [x for x, _ in fused][:2] in (["a", "b"], ["b", "a"])
    assert dict(fused)["d"] < dict(fused)["a"]


def test_reranker_prefers_the_passage_that_answers():
    r = LexicalReranker().score("carry over unused leave",
                                ["Hotel limit is 180 euros.",
                                 "Unused leave may be carried over up to five days."])
    assert r[1] > r[0]


# -------------------------------------------------------------------- store
def _store_with(*docs):
    st, emb = MemoryStore(), HashingEmbedder()
    for d in docs:
        ch = chunk_document(d)
        st.upsert(d, ch, emb.embed([c.text for c in ch]), emb.name)
    return st, emb


def test_acl_and_status_are_filtered_inside_the_search():
    public = Document("pub", "Leave", "Five days carry over.", frozenset({"all-staff"}))
    old = Document("old", "Leave old", "Ten days carry over.", frozenset({"all-staff"}),
                   status="superseded")
    hr = Document("hr", "Pay", "Salary bands carry over grades.", frozenset({"hr"}))
    st, emb = _store_with(public, old, hr)
    res = st.search_keyword("carry over", frozenset({"all-staff"}), 10)
    ids = {c.doc_id for c, _ in res.ranked}
    assert ids == {"pub"}
    assert res.acl_filtered == 1 and res.status_filtered == 1
    vres = st.search_vector(emb.embed(["carry over"])[0], frozenset({"all-staff"}), 10)
    assert {c.doc_id for c, _ in vres.ranked} == {"pub"}


def test_upsert_is_idempotent_and_replaces_on_change():
    st, emb = MemoryStore(), HashingEmbedder()
    d = Document("x", "T", "Body one.", frozenset({"all-staff"}))
    ch = chunk_document(d)
    vec = emb.embed([c.text for c in ch])
    assert st.upsert(d, ch, vec, emb.name) == "inserted"
    assert st.upsert(d, ch, vec, emb.name) == "unchanged"
    d2 = Document("x", "T", "Body two.", frozenset({"all-staff"}), version="2")
    assert st.upsert(d2, chunk_document(d2), vec, emb.name) == "replaced"
    assert st.versions() == {"x": "2"}


def test_user_with_no_groups_sees_nothing():
    st, emb = _store_with(Document("pub", "Leave", "Five days.", frozenset({"all-staff"})))
    assert st.search_keyword("five days", frozenset(), 10).ranked == []


# ----------------------------------------------------- context and citations
def _chunk(text, heading="Leave > Carry-over", source="policy/leave"):
    from atlas.retrieval.text import Chunk
    return Chunk("c1", "policy-leave", 'Leave "Policy"', heading, text, 1, "current", source,
                 "2026-06-01")


def test_context_attributes_are_escaped_so_headings_cannot_break_tags():
    from atlas.retrieval.context import assemble
    ctx = assemble([_chunk("Five days carry over.", heading='A > B" injected="x')], "q?", 3000)
    assert 'injected="x"' not in ctx.text and "&gt;" in ctx.text and "&quot;" in ctx.text


def test_untrusted_passages_are_tagged_and_flagged():
    from atlas.retrieval.context import assemble
    ctx = assemble([_chunk("Vendor note.", source="web/vendor")], "q?", 3000)
    assert "<UNTRUSTED" in ctx.text and ctx.untrusted


def test_an_appended_unsupported_sentence_fails_citation_verification():
    from atlas.retrieval.context import verify_citations
    c = _chunk("Up to five days of unused annual leave may be carried over with approval.")
    good = {"answer": "Up to five days of unused annual leave may be carried over with approval.",
            "citations": [c.label], "supported": True}
    assert verify_citations(good, {c.label: c}) == []
    bad = {**good, "answer": good["answer"] + " Contractors receive double the allowance."}
    assert any("not supported" in p for p in verify_citations(bad, {c.label: c}))
