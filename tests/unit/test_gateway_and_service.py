"""Gateway resilience and the end-to-end answer path (mock provider)."""
import json

import pytest

from atlas.core.identity import DIRECTORY
from atlas.gateway.gateway import (AllProvidersFailed, BudgetExceeded, Gateway, Ledger,
                                   ModelRequest)
from atlas.gateway.providers import MockProvider, strict_schema
from atlas.retrieval.text import Document
from atlas.validation import ANSWER_SCHEMA

from atlas.testing import make_atlas

ALICE, SAM = DIRECTORY["alice"], DIRECTORY["sam"]
REQ = ModelRequest(task="judge", system="s", user=json.dumps({"answer": "x", "must_contain_facts": []}))


def gw(*providers, **kw):
    chain = [(p, f"m{i}") for i, p in enumerate(providers)]
    return Gateway({"judge": chain}, Ledger(daily_cap_usd=kw.pop("cap", 10.0)),
                   sleep=lambda s: None, **kw)


# ------------------------------------------------------------------ gateway
def test_transient_error_is_retried_then_succeeds():
    p = MockProvider(fail_next=1)
    res = gw(p, max_attempts=2).complete(REQ, ALICE)
    assert res.attempts[0].endswith("transient: 503 overloaded") and res.attempts[1].endswith("ok")
    assert not res.fallback_used


def test_fallback_when_primary_keeps_failing():
    res = gw(MockProvider(name="a", fail_next=5), MockProvider(name="b")).complete(REQ, ALICE)
    assert res.fallback_used and res.response.provider == "b"


def test_permanent_error_is_not_retried():
    p = MockProvider(name="a", permanent_failure=True)
    res = gw(p, MockProvider(name="b"), max_attempts=3).complete(REQ, ALICE)
    assert p.calls == 1 and res.response.provider == "b"


def test_circuit_breaker_opens_and_skips_the_failing_provider():
    a, b = MockProvider(name="a", fail_next=100), MockProvider(name="b")
    g = gw(a, b, max_attempts=1, breaker_threshold=2)
    g.complete(REQ, ALICE)
    g.complete(REQ, ALICE)
    calls_before = a.calls
    res = g.complete(REQ, ALICE)
    assert a.calls == calls_before          # skipped without a call
    assert "breaker open" in res.attempts[0]
    assert g.breaker("a", "m0").state == "open"


def test_restricted_requests_never_reach_out_of_region_providers():
    out = MockProvider(name="out", in_region=False)
    inr = MockProvider(name="in")
    g = gw(out, inr)
    res = g.complete(ModelRequest(task="judge", system="s", user=REQ.user,
                                  sensitivity="restricted"), ALICE)
    assert res.response.provider == "in" and out.calls == 0


def test_all_providers_failing_raises_with_attempt_log():
    with pytest.raises(AllProvidersFailed) as e:
        gw(MockProvider(fail_next=9), MockProvider(fail_next=9), max_attempts=1).complete(REQ, ALICE)
    assert len(e.value.attempts) == 2


def test_daily_cost_cap_stops_calls():
    g = gw(MockProvider(), cap=0.000001)
    g.ledger.cost = lambda m, i, o: 1.0
    g.complete(REQ, ALICE)
    with pytest.raises(BudgetExceeded):
        g.complete(REQ, ALICE)


def test_strict_schema_drops_unsupported_keywords():
    s = strict_schema(ANSWER_SCHEMA)
    assert "maxLength" not in s["properties"]["answer"]
    assert s["additionalProperties"] is False


# ------------------------------------------------------------------ service
def test_answer_is_cited_and_uses_the_current_policy(atlas):
    r = atlas.ask("How many days of unused leave can I carry over?", ALICE)
    assert r.outcome == "answered"
    assert "five days" in r.answer["answer"] and "ten" not in r.answer["answer"].lower()
    assert r.answer["citations"][0].startswith("policy-leave#")


def test_restricted_document_is_invisible_to_unauthorized_user(atlas):
    r = atlas.ask("What is the salary band for a senior engineer?", ALICE)
    assert r.outcome == "escalated"
    assert not any(s["label"].startswith("hr-salary") for s in r.sources)
    t = atlas.traces.get(r.trace_id)
    retrieval = next(s for s in t["spans"] if s["name"] == "retrieval")
    assert retrieval["acl_filtered"] >= 1


def test_authorized_user_gets_restricted_answer_routed_as_restricted(atlas):
    r = atlas.ask("What is the salary band for a senior engineer?", SAM)
    assert r.outcome == "answered" and "82,000" in r.answer["answer"]
    ctx = next(s for s in atlas.traces.get(r.trace_id)["spans"] if s["name"] == "context")
    assert ctx["sensitivity"] == "restricted"


@pytest.mark.parametrize("fault", ["bad_citation", "unsupported_claim", "not_json"])
def test_one_bounded_repair_recovers_from_a_bad_first_answer(fault):
    a = make_atlas(primary=MockProvider(name="mock-primary", faults=[fault]))
    r = a.ask("How many days of unused leave can I carry over?", ALICE)
    assert r.outcome == "answered" and r.notes        # repaired, with the problems recorded
    v = [s for s in a.traces.get(r.trace_id)["spans"] if s["name"] == "validation"]
    assert [s["outcome"] for s in v] == ["failed", "ok"]


def test_repeated_bad_answers_escalate_instead_of_looping():
    a = make_atlas(primary=MockProvider(name="mock-primary", faults=["bad_citation"] * 5))
    r = a.ask("How many days of unused leave can I carry over?", ALICE)
    assert r.outcome == "escalated" and r.answer["escalate"] is True
    assert len([s for s in a.traces.get(r.trace_id)["spans"] if s["name"] == "gateway"]) == 2


def test_degraded_response_when_every_provider_fails():
    a = make_atlas(primary=MockProvider(name="p", fail_next=99),
                   fallback=MockProvider(name="f", fail_next=99))
    r = a.ask("How many days of unused leave can I carry over?", ALICE)
    assert r.outcome == "degraded" and r.sources and r.answer["citations"] == []


def test_poisoned_page_is_quarantined_and_never_retrieved(atlas):
    assert "wiki-vpn" in atlas.store.quarantined()
    r = atlas.ask("How do I set up the VPN client?", DIRECTORY["bob"])
    assert not any(s["label"].startswith("wiki-vpn") for s in r.sources)


def test_reconciliation_reports_missing_stale_and_orphaned(atlas):
    src = dict(atlas.store.versions())
    src["policy-leave"] = "8"            # changed at source
    src["new-doc"] = "1"                 # never ingested
    del src["it-faq"]                    # deleted at source
    drift = atlas.reconcile(src)
    assert drift == {"missing": ["new-doc"], "stale": ["policy-leave"], "orphaned": ["it-faq"]}


def test_every_trace_carries_the_required_attributes(atlas):
    from atlas.core.observability import REQUIRED
    r = atlas.ask("Which form do I use to request a new laptop?", ALICE)
    t = atlas.traces.get(r.trace_id)
    for span in t["spans"]:
        assert REQUIRED.get(span["name"], set()) <= set(span), span["name"]
    assert set(t["versions"]) == {"code", "instructions", "model", "index"}


def test_ingest_rejects_documents_without_acl_or_body(atlas):
    assert atlas.ingest(Document("e", "T", "  ", frozenset({"x"}))).outcome == "rejected"
    assert atlas.ingest(Document("n", "T", "text", frozenset())).outcome == "rejected"


def test_cost_is_accounted_per_request(atlas):
    r = atlas.ask("What is the daily meal allowance during business travel?", ALICE)
    assert r.cost_usd > 0
    assert atlas.ledger.records[-1].user_id == "alice"
