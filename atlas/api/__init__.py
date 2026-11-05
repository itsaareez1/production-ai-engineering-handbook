"""Atlas HTTP API (FastAPI).

`atlas.api:app` is what the Dockerfile of Listing 44.1 starts. The
factory `create_app` builds an app around a given `Atlas` service, which
is how the tests inject the in-memory store and the mock provider.

Endpoints
- GET  /health                       liveness ({"status": "ok"})
- GET  /schema, POST /validate       the Chapter 12 answer schema and validator
- POST /auth/dev-token               dev/test only: token for a directory user
- POST /v1/ask                       grounded, cited answer (or escalation)
- POST /v1/documents                 ingest a document (role: ingest)
- POST /v1/agent/tickets             bounded ticket agent (P2)
- POST /v1/drafts/{id}/submit        user confirms a draft (P2 -> ticket)
- POST /v1/approvals/{id}/decision   reviewer decision (role: reviewer)
- GET  /v1/traces/{id}               trace metadata (role: operator)
- GET  /metrics                      Prometheus text (role: operator)
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from atlas.core.config import Settings
from atlas.core.identity import DIRECTORY, AuthError, Identity, issue_token, verify_token
from atlas.core.observability import configure_logging, request_id_var
from atlas.corpus import load_corpus
from atlas.retrieval.text import Document
from atlas.security.controls import tier_of
from atlas.service import Atlas
from atlas.validation import ANSWER_SCHEMA, schema_errors, semantic_errors

log = logging.getLogger("atlas.api")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class DocumentIn(BaseModel):
    doc_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,80}$")
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=200_000)
    acl: list[str] = Field(min_length=1)
    status: Literal["current", "superseded", "draft"] = "current"
    source: str = "wiki"
    version: str = "1"
    updated: str = ""
    owner: str = ""
    classification: Literal["internal", "restricted"] = "internal"


class AgentRequest(BaseModel):
    request: str = Field(min_length=3, max_length=2000)


class DecisionIn(BaseModel):
    approve: bool
    edited_args: dict | None = None


class ValidateRequest(BaseModel):
    answer: dict
    valid_sources: list[str] = []


class DevTokenRequest(BaseModel):
    username: str


def create_app(atlas: Atlas | None = None) -> FastAPI:
    settings = atlas.settings if atlas else Settings.from_env()
    configure_logging(settings.log_level)
    svc = atlas or Atlas(settings)
    if settings.seed_corpus and settings.env != "prod":
        for doc in load_corpus(Path(settings.seed_corpus)):
            svc.ingest(doc)
    secret = settings.token_secret.get_secret_value()
    app = FastAPI(title="Atlas", version="1.0.0",
                  description="Reference implementation for The Production AI Engineering Handbook")
    app.state.atlas = svc

    @app.middleware("http")
    async def request_ids(request: Request, call_next):
        rid = uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        except Exception:  # never return a stack trace to the caller
            log.exception("unhandled error")
            response = JSONResponse({"error": "internal error", "request_id": rid}, 500)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        return response

    def identity(authorization: Annotated[str | None, Header()] = None) -> Identity:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "missing bearer token")
        try:
            return verify_token(authorization[7:], secret)
        except AuthError as exc:
            raise HTTPException(401, str(exc)) from exc

    def role(name: str):
        def check(who: Identity = Depends(identity)) -> Identity:
            if not who.has_role(name):
                raise HTTPException(403, f"role {name!r} required")
            return who
        return check

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/schema")
    def schema() -> dict:
        return ANSWER_SCHEMA

    @app.post("/validate")
    def validate(req: ValidateRequest) -> dict:
        errors = schema_errors(req.answer)
        if not errors:
            errors = semantic_errors(req.answer, set(req.valid_sources))
        return {"valid": not errors, "errors": errors}

    @app.post("/auth/dev-token")
    def dev_token(req: DevTokenRequest) -> dict:
        if settings.env == "prod":
            raise HTTPException(404, "not found")
        who = DIRECTORY.get(req.username)
        if not who:
            raise HTTPException(404, "unknown user")
        return {"token": issue_token(who, secret), "token_type": "bearer"}

    @app.post("/v1/ask")
    def ask(req: AskRequest, who: Identity = Depends(identity)) -> dict:
        r = svc.ask(req.question, who)
        return {"answer": r.answer, "sources": r.sources, "outcome": r.outcome,
                "trace_id": r.trace_id, "cost_usd": r.cost_usd}

    @app.post("/v1/documents", status_code=201)
    def ingest(doc: DocumentIn, who: Identity = Depends(role("ingest"))) -> dict:
        # The source decides the trust tier, and trusted sources skip the
        # injection scan, so a caller must not be able to claim one.
        # Trusted content arrives through internal connectors only.
        if tier_of(doc.source) == "trusted":
            raise HTTPException(403, "trusted sources cannot be ingested through the API")
        r = svc.ingest(Document(**{**doc.model_dump(), "acl": frozenset(doc.acl)}))
        if r.outcome == "rejected":
            raise HTTPException(422, {"doc_id": r.doc_id, "reasons": r.reasons})
        svc.audit.append(who.user_id, "document.ingested", {"doc_id": r.doc_id, "outcome": r.outcome})
        return {"doc_id": r.doc_id, "outcome": r.outcome, "chunks": r.chunks, "reasons": r.reasons}

    @app.post("/v1/agent/tickets")
    def agent(req: AgentRequest, who: Identity = Depends(identity)) -> dict:
        out = svc.agent.run(who, req.request)
        return {"status": out.status, "summary": out.summary, "approval_id": out.approval_id,
                "steps": [{k: v for k, v in s.items() if k != "args"} for s in out.steps]}

    @app.post("/v1/drafts/{draft_id}/submit")
    def submit(draft_id: str, who: Identity = Depends(identity)) -> dict:
        r = svc.tickets.submit_draft(who, draft_id)
        if not r["ok"]:
            raise HTTPException(404, r["error"])
        svc.audit.append(who.user_id, "draft.submitted", {"draft_id": draft_id, "ticket": r["result"]})
        return {"ticket_id": r["result"], "replayed": r.get("replayed", False)}

    @app.post("/v1/approvals/{approval_id}/decision")
    def decision(approval_id: str, d: DecisionIn, who: Identity = Depends(role("reviewer"))) -> dict:
        try:
            a = svc.approvals.decide(who, approval_id, d.approve, d.edited_args)
        except PermissionError as exc:
            raise HTTPException(403, str(exc)) from exc
        return {"approval_id": approval_id, "state": a["state"]}

    @app.get("/v1/traces/{trace_id}")
    def trace(trace_id: str, who: Identity = Depends(role("operator"))) -> dict:
        t = svc.traces.get(trace_id)
        if not t:
            raise HTTPException(404, "not found")
        return t

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics(who: Identity = Depends(role("operator"))) -> str:
        return svc.metrics.render()

    return app


def __getattr__(name: str):
    # `atlas.api:app` is built lazily, so importing the package (for
    # create_app in tests) does not read the environment.
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
