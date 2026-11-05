"""Executes every runnable listing and fails if any exits with an
error -- the test the book's front matter promises.

It also pins the outputs that the chapters quote, so that a change to
a listing which breaks the book's text fails here rather than in a
reader's terminal.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run import NOT_RUNNABLE, discover, sort_key  # noqa: E402

LISTINGS = discover()


def run_listing(number: str) -> str:
    path = LISTINGS[number]
    proc = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
    )
    assert proc.returncode == 0, (
        f"listing {number} exited {proc.returncode}\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    return proc.stdout


def test_the_book_has_forty_nine_runnable_listings():
    assert len(LISTINGS) == 49
    assert set(NOT_RUNNABLE) == {"14.2", "21.1", "44.1"}


@pytest.mark.parametrize("number", sorted(LISTINGS, key=sort_key))
def test_listing_runs(number):
    assert run_listing(number).strip(), (
        f"listing {number} produced no output")


# --- outputs the chapters quote verbatim --------------------------
# Each assertion below is a sentence from the book. If one fails, the
# book and the code have diverged.

def test_3_1_matches_appendix_k():
    # Appendix K.4 prints this exact line.
    assert run_listing("3.1").strip() == "validated 120.0 1"


def test_5_1_reports_no_problems_then_a_type_error():
    out = run_listing("5.1").splitlines()
    assert out[0] == "problems: none"
    assert out[1] == (
        'problems: ["latency_ms.p50 has wrong type: \'fast\'"]')


def test_6_1_routes_three_by_rule_and_one_by_model():
    assert run_listing("6.1").strip().endswith(
        "{'rule': 3, 'model': 1}")


def test_8_1_costs_match_chapter_8():
    out = run_listing("8.1")
    assert "large: $0.0516" in out
    assert "mid (8% retries): $0.0149" in out
    assert "large w/ cached prefix: $0.0462" in out
    assert "large $2,580, mid $743" in out


def test_9_1_breaker_opens_after_two_failures():
    out = run_listing("9.1")
    # three answers served by the fallback, three records of it
    assert out.count("mid-in-region") == 6
    assert "'breaker open'" in out


def test_10_1_drops_on_source_cap_and_total_budget():
    out = run_listing("10.1")
    assert "'reason': 'source cap'" in out
    assert "'reason': 'total budget'" in out
    assert "UNTRUSTED" not in out.splitlines()[0]  # ticket kept


def test_11_1_fails_then_passes_with_a_different_hash():
    first, second = run_listing("11.1").splitlines()[:2]
    assert '"status": "FAIL"' in first
    assert '"status": "PASS"' in second
    assert first.split('"version": "')[1][:12] != \
        second.split('"version": "')[1][:12]


def test_12_1_repairs_once_in_two_calls():
    assert "repairs: 1 | calls: 2" in run_listing("12.1")


def test_13_1_recall_and_mrr_match_chapter_13():
    out = run_listing("13.1")
    for line in ("recall@1: 0.25", "recall@3: 0.50",
                 "recall@5: 0.75", "MRR: 0.44"):
        assert line in out


def test_14_1_similarities_match_chapter_14():
    out = run_listing("14.1")
    assert "0.992" in out and "0.981" in out


def test_15_1_ranks_the_form_chunk_first():
    out = run_listing("15.1")
    assert out.splitlines()[0].startswith(
        "form HR-27 -> [('forms-hr'")


def test_15_2_fuses_the_actual_rule_to_the_top():
    assert run_listing("15.2").splitlines()[0].endswith("leave-4.2")


def test_15_3_hides_the_restricted_chunk_from_staff():
    staff, hr = run_listing("15.3").splitlines()[:2]
    assert "pay-1" not in staff
    assert "pay-1" in hr


def test_16_1_reranking_moves_recall_from_zero_to_one():
    out = run_listing("16.1")
    assert "recall@5 before rerank: 0%, after: 100%" in out
    assert "['leave-4.2'," in out


def test_17_1_good_passes_and_bad_fails_twice():
    good, bad = run_listing("17.1").splitlines()[:2]
    assert good == "good: ok"
    assert "citation not in context" in bad
    assert "sentence not supported" in bad


def test_18_1_produces_three_chunks_and_is_idempotent():
    out = run_listing("18.1").splitlines()
    assert len([x for x in out if x[:1].isdigit()]) == 3
    assert "replaced | unchanged" in out[-2]
    assert out[-1] == "replaced | writes: 2"


def test_19_1_refuses_with_the_same_message_for_both_cases():
    out = run_listing("19.1")
    assert "not found or not permitted" in out
    assert out.count("UNTRUSTED") == 3


def test_20_1_accepts_one_url_and_rejects_four():
    out = run_listing("20.1")
    assert out.count("OK     ") == 1
    assert out.count("REJECT ") == 4
    assert "host resolves to blocked address 10.20.0.5" in out


def test_22_1_resumes_without_repeating_completed_steps():
    out = run_listing("22.1")
    assert "failed after: route" in out
    assert "completed: ['extract', 'check', 'route', 'notify']" in out


def test_23_1_rejects_a_queue_the_model_invented():
    out = run_listing("23.1").splitlines()
    assert out[2].startswith("3 NEEDS_REVIEW None")
    assert out[3].startswith("4 NEEDS_REVIEW None")


def test_24_1_creates_exactly_one_ticket():
    out = run_listing("24.1")
    assert "'replayed': True} | attempts: 3" in out
    assert out.count("tickets created: 1") == 2


def test_26_1_guard_refuses_the_repeated_action():
    out = run_listing("26.1")
    assert "no-progress guard: repeated action refused" in out
    assert "steps: 4 | tokens: 2400" in out


def test_27_1_rejects_a_sensitive_pref_and_an_untrusted_outcome():
    out = run_listing("27.1")
    assert "pref rejected (sensitive): vpn_password" in out
    assert "outcome rejected (origin untrusted:tool)" in out
    assert "'office': 'London'" in out


def test_28_1_allows_reads_requires_approval_refuses_the_rest():
    out = run_listing("28.1")
    assert out.count("'allow'") == 2
    assert "'approval'" in out
    assert out.count("'refuse'") == 2


def test_29_1_binds_approval_to_the_edited_arguments():
    out = run_listing("29.1")
    assert "self-approval: requester cannot approve" in out
    assert "original args approved? False" in out
    assert "edited args approved?   True" in out
    assert "after expiry?           False" in out


def test_30_1_rejects_the_worker_citing_an_untrusted_source():
    out = run_listing("30.1")
    assert '"rogue"' in out
    assert "non-approved source: untrusted:wiki-comment" in out
    assert out.count('"claim"') == 1


def test_31_1_distributions_match_chapter_31():
    out = run_listing("31.1")
    assert "cost mean $0.0120 p95 $0.0120" in out
    assert "cost mean $0.0181 p95 $0.0400" in out
    assert "latency mean 6.3s p95 14.0s" in out


def test_32_1_assigns_the_stale_citation_to_retrieval():
    out = run_listing("32.1")
    assert "stale policy cited" in out.splitlines()[0]
    assert "retrieval: relevant material" in out.splitlines()[0]
    assert out.splitlines()[-1].endswith("no-failure")


def test_33_1_imports_atlas_validation_and_bounds_the_rate():
    out = run_listing("33.1")
    assert "unit: ok" in out and "contract: ok" in out
    assert "95% lower bound 0.936 >= 0.93: ok" in out


def test_34_1_oversamples_and_finds_the_leak():
    out = run_listing("34.1")
    assert ("{'leave': 10, 'expenses': 10, 'escalated': 15, "
            "'restricted-user': 10}") in out
    assert "dev/holdout: 35 15" in out
    assert out.strip().endswith(
        "['gs-000000', 'gs-000001', 'gs-000002']")


def test_35_1_reports_the_kappa_the_chapter_quotes():
    out = run_listing("35.1")
    assert "judge agreement 0.91, kappa 0.71" in out
    assert "leave {" in out and "expenses {" in out


def test_36_1_names_the_unsupported_claim():
    out = run_listing("36.1")
    assert "claims 3, supported 0.67" in out
    assert "Contractors are excluded" in out
    assert "accuracy=0.90" in out and "accuracy=0.30" in out


def test_37_1_freezes_when_the_quality_budget_runs_low():
    out = run_listing("37.1")
    assert "budget 200 failures" in out
    assert "budget 280 failures" in out
    assert out.strip().endswith("-> freeze quality-affecting changes")


def test_38_1_blocks_on_the_leave_category():
    out = run_listing("38.1")
    assert "BLOCK: regression" in out
    assert out.strip().endswith("BLOCKED")
    # only the leave category blocks; the final line is the verdict
    assert out.count("BLOCK: regression") == 1


def test_39_1_contains_every_injection():
    out = run_listing("39.1")
    assert out.count("PASS") == 4  # three cases plus the suite
    assert out.count("model obeyed: True") == 2


def test_40_1_quarantines_three_of_four_documents():
    out = run_listing("40.1")
    assert out.count("QUARANTINE") == 3
    assert "policy/leave" in out and "index" in out
    assert "zero-width characters" in out


def test_41_1_refuses_without_a_key_then_pseudonymizes_stably():
    out = run_listing("41.1").splitlines()
    assert "TRACE_HMAC_KEY is not set" in out[0]
    token = out[1].split("<EMAIL:v1:")[1].split(">")[0]
    assert f"<EMAIL:v1:{token}>" in out[2]
    assert "content" not in out[3]
    assert "restricted_content" not in out[3]


def test_42_1_ignores_claims_in_the_body_and_the_model_output():
    alice, sam = run_listing("42.1").splitlines()[:2]
    assert "'docs': ['policy-leave']" in alice
    assert "'tool_decision': 'refuse'" in alice
    assert "'policy-pay'" in sam
    assert "'tool_decision': 'allow'" in sam


def test_43_1_scopes_tokens_and_strips_the_query():
    out = run_listing("43.1")
    assert "valid for read: True | valid for write: False" in out
    assert "after expiry: False" in out
    assert "denied issuance: None" in out
    assert out.count("ALLOW") == 2 and out.count("BLOCK") == 2
    assert "docs.vendor.example.com/g\n" in out  # query stripped


def test_45_1_trace_has_no_missing_required_attributes():
    out = run_listing("45.1")
    assert "schema problems: none" in out
    assert '"cost_usd": 0.0124' in out
    assert '"untrusted_in_context": false' in out


def test_46_1_human_review_dominates_and_barely_moves():
    out = run_listing("46.1")
    assert out.count("human_review $10,374") == 3
    assert "generation $540" in out   # baseline
    assert "generation $259" in out   # tiered


def test_47_1_admission_control_removes_every_rejection():
    plain, bucket = [
        x for x in run_listing("47.1").splitlines()
        if x.strip()]
    assert "provider 429s 384" in plain
    assert "provider calls 692" in plain
    assert "provider 429s   0" in bucket
    assert "degraded 197" in bucket


def test_48_1_soaks_then_promotes_then_rolls_back():
    out = run_listing("48.1").splitlines()
    assert "continue-soak" in out[0]
    assert out[1].startswith("promote")
    assert out[3].startswith("rollback")
    assert out[4].startswith("rolled back to: 2026.09.2 a91f")


def test_49_1_totals_match_chapter_49():
    out = run_listing("49.1")
    assert "$  91,700" in out
    assert "$ 105,600" in out
    assert "$  57,540" in out


def test_50_1_finds_exactly_three_erosions():
    out = run_listing("50.1").strip().splitlines()
    assert len(out) == 3
    assert "imports provider SDK" in out[0]
    assert "may not import atlas.orchestration" in out[1]
    assert "may not import atlas.gateway" in out[2]


def test_51_1_flags_only_the_code_self_approval():
    out = run_listing("51.1")
    assert "['code: changer can self-approve']" in out
    assert "evaluation may change instructions? False" in out


def test_52_1_prototype_is_wrong_and_production_is_right():
    out = run_listing("52.1")
    assert "v0.1: You can carry over up to ten days" in out
    assert "v1.0: Up to five days may be carried forward" in out
    assert '"filtered_by_acl": 1' in out
    assert '"filtered_by_status": 1' in out
    assert "v1.0 (restricted): escalated" in out


def test_53_1_atlas_v1_passes_and_v04_does_not():
    out = run_listing("53.1")
    assert "decision: GO | blocking: none" in out
    assert "v0.4 decision: NO-GO" in out
    assert "ownership: score 0/8 below half" in out


def test_54_1_reports_hardening_then_continuous():
    first, second = run_listing("54.1").splitlines()[:2]
    assert "'phase': 'hardening'" in first
    assert "'level': 'L2'" in first
    assert "'phase': 'continuous'" in second
    assert "'level': 'L5'" in second
