"""Tests for atlas/api.py, the service the Dockerfile of Listing 44.1
starts. Appendix K.6 states that /health returns {"status":"ok"}."""
from fastapi.testclient import TestClient

from atlas.api import app

client = TestClient(app)

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
