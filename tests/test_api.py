"""HTTP tests for atlas.api, the service the Dockerfile of Listing 44.1
starts. Appendix K.6 states that /health returns {"status":"ok"}."""
from fastapi.testclient import TestClient

from atlas.api import create_app
from atlas.core.identity import DIRECTORY, issue_token

from atlas.testing import make_atlas

SVC = make_atlas()
client = TestClient(create_app(SVC))


def auth(user):
    tok = issue_token(DIRECTORY[user], SVC.settings.token_secret.get_secret_value())
    return {"Authorization": f"Bearer {tok}"}


GOOD = {
    "answer": "Up to five days of unused leave may be carried over.",
    "citations": ["policy/leave-v7"],
    "supported": True,
    "confidence": "high",
    "escalate": False,
}


def test_health_returns_status_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_schema_is_the_chapter_12_schema():
    body = client.get("/schema").json()
    assert body["required"] == [
        "answer", "citations", "supported", "confidence", "escalate"]


def test_validate_accepts_a_supported_answer():
    body = client.post("/validate", json={
        "answer": GOOD,
        "valid_sources": ["policy/leave-v7"],
    }).json()
    assert body == {"valid": True, "errors": []}


def test_validate_rejects_a_stale_citation():
    stale = dict(GOOD, citations=["policy/leave-v6"])
    body = client.post("/validate", json={
        "answer": stale,
        "valid_sources": ["policy/leave-v7"],
    }).json()
    assert body["valid"] is False
    assert body["errors"] == ["unknown citation: policy/leave-v6"]


def test_validate_rejects_unsupported_without_escalation():
    quiet = dict(GOOD, supported=False, escalate=False, citations=[])
    body = client.post("/validate", json={"answer": quiet}).json()
    assert body["valid"] is False
    assert "unsupported answer must escalate" in body["errors"]


def test_dev_token_then_ask_end_to_end():
    tok = client.post("/auth/dev-token", json={"username": "alice"}).json()["token"]
    r = client.post("/v1/ask", json={"question": "How many days of unused leave can I carry over?"},
                    headers={"Authorization": f"Bearer {tok}"})
    body = r.json()
    assert r.status_code == 200 and body["outcome"] == "answered"
    assert "five days" in body["answer"]["answer"] and r.headers["X-Request-ID"]


def test_operator_can_read_a_trace_and_others_cannot():
    tid = client.post("/v1/ask", json={"question": "Which form do I use to request a new laptop?"},
                      headers=auth("alice")).json()["trace_id"]
    assert client.get(f"/v1/traces/{tid}", headers=auth("alice")).status_code == 403
    t = client.get(f"/v1/traces/{tid}", headers=auth("olga")).json()
    assert [s["name"] for s in t["spans"]][:3] == ["retrieval", "rerank", "context"]


def test_agent_drafts_and_user_confirms_the_draft():
    r = client.post("/v1/agent/tickets", json={"request": "Docking station broken, see T-1042"},
                    headers=auth("bob")).json()
    assert r["status"] == "done"
    draft_id = next(s["result"] for s in r["steps"] if s["action"] == "draft_ticket")
    ok = client.post(f"/v1/drafts/{draft_id}/submit", headers=auth("bob")).json()
    assert ok["ticket_id"].startswith("T-")
    assert client.post(f"/v1/drafts/{draft_id}/submit", headers=auth("alice")).status_code == 404


def test_request_validation_rejects_bad_input():
    assert client.post("/v1/ask", json={"question": ""}, headers=auth("alice")).status_code == 422
