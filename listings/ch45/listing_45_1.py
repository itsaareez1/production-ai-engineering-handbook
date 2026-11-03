"""Listing 45.1. Trace and span schema for an AI request, with the
derived per-request metrics record.

Chapter 45, Observability for AI Systems. Verified by execution.
Run with: python run.py 45.1

The latency_ms figure is wall-clock and so differs between machines;
every other field is deterministic apart from the generated
request_id.
"""
import json
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class Span:
    name: str
    start: float
    end: float = 0.0
    attrs: dict = field(default_factory=dict)

    def finish(self, **attrs):
        self.end = time.perf_counter()
        self.attrs.update(attrs)
        return self

    @property
    def ms(self):
        return (self.end - self.start) * 1000


@dataclass
class Trace:
    request_id: str
    user_id: str
    tenant: str
    # code, instructions_hash, model, index, judge
    versions: dict
    spans: list = field(default_factory=list)

    def span(self, name, **attrs):
        s = Span(name, time.perf_counter(), attrs=attrs)
        self.spans.append(s)
        return s


REQUIRED_SPAN_ATTRS = {
    "retrieval": {"query_hash", "candidates", "filtered_by_acl",
                  "status_filter", "recall_hit"},
    "context": {"labels", "tokens_in", "dropped",
                "untrusted_present", "max_classification"},
    "gateway": {"candidate", "model_version", "tokens_in",
                "tokens_out", "cost_usd", "outcome",
                "provider_request_id"},
    "tool": {"name", "level", "policy_decision", "approval_id",
             "outcome"},
    "validation": {"schema_ok", "citations_resolve", "supported",
                   "escalate", "repairs"},
}


def check_trace(t: Trace) -> list:
    problems = []
    for s in t.spans:
        kind = s.name.split(":")[0]
        missing = (REQUIRED_SPAN_ATTRS.get(kind, set())
                   - set(s.attrs))
        if missing:
            problems.append(f"{s.name} missing {sorted(missing)}")
    return problems


def metrics_record(t: Trace) -> dict:
    gw = [s for s in t.spans if s.name.startswith("gateway")]
    val = next((s for s in t.spans
                if s.name.startswith("validation")), None)
    tools = [s for s in t.spans if s.name.startswith("tool")]
    return {
        "request_id": t.request_id, "tenant": t.tenant,
        **t.versions,
        "latency_ms": round(sum(s.ms for s in t.spans), 1),
        "model_calls": len(gw),
        "cost_usd": round(sum(s.attrs["cost_usd"] for s in gw), 5),
        "tokens_in": sum(s.attrs["tokens_in"] for s in gw),
        "fallback_used": any(s.attrs["candidate"] != "primary"
                             for s in gw),
        "escalated": bool(val and val.attrs["escalate"]),
        "validation_failed": bool(val
                                  and not val.attrs["schema_ok"]),
        "tool_refusals": sum(
            s.attrs["policy_decision"] == "refuse" for s in tools),
        "untrusted_in_context": any(
            s.attrs.get("untrusted_present") for s in t.spans),
    }


if __name__ == "__main__":
    t = Trace(str(uuid.uuid4())[:8], "u-17", "acme",
              {"code": "2026.09.3", "instructions_hash": "a91f",
               "model": "m-2026-06", "index": "idx-0912",
               "judge": "j-2026-05"})
    t.span("retrieval:hybrid").finish(
        query_hash="q1", candidates=40, filtered_by_acl=3,
        status_filter=True, recall_hit=None)
    t.span("context:assemble").finish(
        labels=["policy-leave/4.2@2026-06-01"], tokens_in=3100,
        dropped=2, untrusted_present=False,
        max_classification="internal")
    t.span("gateway:qa").finish(
        candidate="primary", model_version="m-2026-06",
        tokens_in=3100, tokens_out=210, cost_usd=0.0124,
        outcome="ok", provider_request_id="prov-77")
    t.span("tool:lookup_ticket").finish(
        name="lookup_ticket", level="P1",
        policy_decision="allow", approval_id=None, outcome="ok")
    t.span("validation:answer").finish(
        schema_ok=True, citations_resolve=True, supported=True,
        escalate=False, repairs=0)
    print("schema problems:", check_trace(t) or "none")
    print(json.dumps(metrics_record(t), indent=1))
