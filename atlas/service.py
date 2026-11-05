"""The Atlas application service: wiring and the request paths.

This is the deterministic shell of Chapter 23 around the model calls.
Every step of `ask` is a component from the book, and each records a
span in the trace:

    identity -> retrieval (hybrid, ACL + status in the query) -> fusion
    -> rerank -> context (budget, labels, tiers) -> gateway (routing,
    sensitivity, fallback, cost) -> validation (schema, semantic,
    citations) -> one bounded repair -> answer, escalation, or the
    designed degraded response (retrieval-only).
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from atlas import validation
from atlas.agents.agent import Approvals, TicketAgent, Tickets, ticket_tools
from atlas.agents.records import MemoryAudit, MemoryRecords, PostgresAudit, PostgresRecords
from atlas.core.config import Settings
from atlas.core.identity import Identity
from atlas.core.observability import Metrics, TraceStore, log_event, new_trace
from atlas.gateway.gateway import (AllProvidersFailed, BudgetExceeded, Gateway, Ledger,
                                   ModelRequest)
from atlas.gateway.providers import MockProvider
from atlas.retrieval.context import assemble, verify_citations
from atlas.retrieval.store import MemoryStore, PostgresStore, Store
from atlas.retrieval.text import (Document, HashingEmbedder, LexicalReranker, chunk_document,
                                  rrf)
from atlas.security.controls import Redactor, scan_for_injection, tier_of

log = logging.getLogger("atlas.service")
PROMPTS = Path(__file__).resolve().parent / "prompts"
CODE_VERSION = "1.0.0"


def load_instructions(name: str = "answer_v1.md") -> tuple[str, str]:
    text = (PROMPTS / name).read_text()
    return text, hashlib.sha256(text.encode()).hexdigest()[:12]


@dataclass
class AskResult:
    answer: dict[str, Any]
    sources: list[dict[str, str]]
    trace_id: str
    outcome: str                  # answered | escalated | degraded
    cost_usd: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class IngestResult:
    doc_id: str
    outcome: str                  # inserted | replaced | unchanged | quarantined | rejected
    chunks: int = 0
    reasons: list[str] = field(default_factory=list)


class Atlas:
    def __init__(self, settings: Settings, store: Store | None = None,
                 gateway: Gateway | None = None, records=None, audit=None):
        self.settings = settings
        if settings.database_url and settings.embedding_dim != 256:
            raise ValueError("the PostgreSQL schema stores 256-dimension vectors")
        self.store: Store = store or (PostgresStore(settings.database_url)
                                      if settings.database_url else MemoryStore())
        self.records = records or (PostgresRecords(settings.database_url)
                                   if settings.database_url else MemoryRecords())
        self.audit = audit or (PostgresAudit(settings.database_url)
                               if settings.database_url else MemoryAudit())
        self.embedder = HashingEmbedder(dim=settings.embedding_dim)
        self.reranker = LexicalReranker()
        self.ledger = Ledger(settings.daily_cost_cap_usd)
        self.gateway = gateway or self._default_gateway()
        self.redactor = Redactor(settings.redaction_key.get_secret_value(),
                                 settings.redaction_key_version)
        self.traces = TraceStore()
        self.metrics = Metrics()
        self.instructions, self.instructions_hash = load_instructions()
        self.tickets = Tickets(self.records)
        self.approvals = Approvals(self.records, self.audit, settings.approval_ttl_s)
        self.agent = TicketAgent(self.gateway, ticket_tools(self.tickets), self.approvals,
                                 self.audit, max_steps=settings.agent_max_steps)

    # ------------------------------------------------------------ wiring
    def _default_gateway(self) -> Gateway:
        s = self.settings
        if s.model_provider == "mock":
            primary = MockProvider(name="mock-primary", in_region=True)
            fallback = MockProvider(name="mock-fallback", in_region=True)
        elif s.model_provider == "anthropic":
            from atlas.gateway.providers import AnthropicProvider
            primary = fallback = AnthropicProvider(in_region=True)
        else:
            from atlas.gateway.providers import OpenAIProvider
            primary = fallback = OpenAIProvider(in_region=True)
        chain = [(primary, s.model_primary), (fallback, s.model_fallback)]
        return Gateway({"answer": chain, "plan": chain, "judge": chain}, self.ledger,
                       max_attempts=s.max_attempts_per_candidate, timeout_s=s.request_timeout_s,
                       breaker_threshold=s.breaker_threshold,
                       breaker_cooldown_s=s.breaker_cooldown_s)

    def versions(self) -> dict[str, str]:
        return {"code": CODE_VERSION, "instructions": self.instructions_hash,
                "model": self.settings.model_primary, "index": self.embedder.name}

    # ---------------------------------------------------------- ingestion
    def ingest(self, doc: Document) -> IngestResult:
        if not doc.body.strip():
            return IngestResult(doc.doc_id, "rejected", reasons=["empty document"])
        if doc.status not in ("current", "superseded", "draft"):
            return IngestResult(doc.doc_id, "rejected", reasons=[f"bad status {doc.status!r}"])
        if not doc.acl:
            return IngestResult(doc.doc_id, "rejected", reasons=["no ACL: nobody could read it"])
        markers = scan_for_injection(doc.body) if tier_of(doc.source) != "trusted" else []
        if markers:
            self.store.quarantine(doc, markers)
            self.audit.append("ingestion", "document.quarantined",
                              {"doc_id": doc.doc_id, "markers": markers, "owner": doc.owner})
            self.metrics.inc("quarantined_total")
            return IngestResult(doc.doc_id, "quarantined", reasons=markers)
        chunks = chunk_document(doc)
        vectors = self.embedder.embed([f"{c.heading_path}\n{c.text}" for c in chunks])
        outcome = self.store.upsert(doc, chunks, vectors, self.embedder.name)
        self.metrics.inc("ingested_total", outcome=outcome)
        return IngestResult(doc.doc_id, outcome, len(chunks))

    def reconcile(self, source_versions: dict[str, str]) -> dict[str, list[str]]:
        """Compare the system of record's listing with the index (Chapter 18)."""
        index = self.store.versions()
        quarantined = set(self.store.quarantined())
        drift = {
            "missing": sorted(d for d in source_versions
                              if d not in index and d not in quarantined),
            "stale": sorted(d for d in source_versions if d in index and index[d] != source_versions[d]),
            "orphaned": sorted(d for d in index if d not in source_versions),
        }
        self.metrics.inc("reconciliation_drift", sum(len(v) for v in drift.values()))
        return drift

    # ----------------------------------------------------------- question
    def ask(self, question: str, who: Identity) -> AskResult:
        s = self.settings
        trace = new_trace(who.user_id, self.versions())
        markers = scan_for_injection(question)
        if markers:
            self.metrics.inc("injection_markers_total", where="request")
        with trace.span("retrieval") as sp:
            qvec = self.embedder.embed([question])[0]
            vec = self.store.search_vector(qvec, who.groups, s.retrieval_candidates)
            kw = self.store.search_keyword(question, who.groups, s.retrieval_candidates)
            by_id = {c.chunk_id: c for c, _ in vec.ranked + kw.ranked}
            fused = rrf([[c.chunk_id for c, _ in vec.ranked], [c.chunk_id for c, _ in kw.ranked]])
            sp.set(candidates=len(fused), acl_filtered=kw.acl_filtered,
                   status_filtered=kw.status_filtered, request_markers=markers)
        with trace.span("rerank") as sp:
            cands = [by_id[cid] for cid, _ in fused]
            scores = self.reranker.score(question, [f"{c.heading_path} {c.text}" for c in cands])
            ranked = [c for _, c in sorted(zip(scores, cands), key=lambda t: -t[0])][: s.rerank_keep]
            sp.set(kept=len(ranked), reranker=self.reranker.name)
        with trace.span("context") as sp:
            ctx = assemble(ranked, question, s.context_budget_tokens)
            sp.set(labels=list(ctx.labels), dropped=ctx.dropped, untrusted=ctx.untrusted,
                   sensitivity="restricted" if ctx.restricted else "internal")
        sources = [{"label": lab, "title": c.title, "path": c.heading_path}
                   for lab, c in ctx.labels.items()]
        if not ctx.labels:
            return self._finish(trace, self._escalation("No document you can access covers this."),
                                sources, "escalated", 0.0)
        req = ModelRequest(task="answer", system=self.instructions, user=ctx.text,
                           schema=validation.ANSWER_SCHEMA,
                           sensitivity="restricted" if ctx.restricted else "internal")
        cost, notes, answer = 0.0, [], None
        for attempt in range(2):                     # one bounded repair (Chapter 12)
            with trace.span("gateway") as sp:
                try:
                    res = self.gateway.complete(req, who)
                except (AllProvidersFailed, BudgetExceeded) as exc:
                    sp.set(provider="none", model="none", input_tokens=0, output_tokens=0,
                           cost_usd=0.0, attempts=getattr(exc, "attempts", [str(exc)]))
                    self.metrics.inc("degraded_total")
                    return self._finish(trace, self._degraded(), sources, "degraded", cost,
                                        [str(exc)])
                cost += res.cost_usd
                sp.set(provider=res.response.provider, model=res.response.model,
                       input_tokens=res.response.input_tokens,
                       output_tokens=res.response.output_tokens, cost_usd=res.cost_usd,
                       attempts=res.attempts, fallback=res.fallback_used)
                if res.fallback_used:
                    self.metrics.inc("fallback_total")
            with trace.span("validation") as sp:
                problems = self._validate(res.response.text, ctx.labels)
                sp.set(outcome="ok" if not problems else "failed", repairs=attempt,
                       problems=problems)
            if not problems:
                answer = json.loads(res.response.text)
                break
            notes.extend(problems)
            # the repair notes go before the question, which stays last (Chapter 10)
            body, _, q = ctx.text.rpartition("QUESTION:")
            req = ModelRequest(task="answer", system=self.instructions,
                               user=body + "VALIDATION ERRORS IN YOUR LAST ANSWER: "
                               + "; ".join(problems) + f"\nValid labels: {sorted(ctx.labels)}"
                               + "\n\nQUESTION:" + q,
                               schema=validation.ANSWER_SCHEMA, sensitivity=req.sensitivity)
        if answer is None:
            self.metrics.inc("validation_failed_total")
            return self._finish(trace, self._escalation(
                "I could not produce an answer I can support from your sources."),
                sources, "escalated", cost, notes)
        outcome = "escalated" if answer.get("escalate") else "answered"
        return self._finish(trace, answer, sources, outcome, cost, notes)

    def _validate(self, text: str, labels: dict) -> list[str]:
        try:
            obj = json.loads(text)
        except (ValueError, TypeError):
            return ["output is not valid JSON"]
        if not isinstance(obj, dict):
            return ["output is not a JSON object"]
        problems = list(validation.schema_errors(obj))
        if problems:
            return problems
        problems += validation.semantic_errors(obj, set(labels))
        problems += verify_citations(obj, labels)
        return sorted(set(problems))

    @staticmethod
    def _escalation(message: str) -> dict[str, Any]:
        return {"answer": message, "citations": [], "supported": False,
                "confidence": "low", "escalate": True}

    @staticmethod
    def _degraded() -> dict[str, Any]:
        return {"answer": "A generated answer is temporarily unavailable. The most relevant "
                          "documents you can access are listed below.",
                "citations": [], "supported": False, "confidence": "low", "escalate": False}

    def _finish(self, trace, answer, sources, outcome, cost, notes=None) -> AskResult:
        trace.outcome = outcome
        missing = trace.missing_attributes()
        if missing:
            log.warning("trace missing attributes", extra={"fields": {"problems": missing}})
        self.traces.put(trace)
        self.metrics.inc("requests_total", outcome=outcome)
        self.metrics.inc("cost_usd_total", cost)
        log_event(log, "ask", trace_id=trace.trace_id, user=trace.user_id, outcome=outcome,
                  cost_usd=round(cost, 6), sources=len(sources))
        return AskResult(answer, sources, trace.trace_id, outcome, round(cost, 6), notes or [])
