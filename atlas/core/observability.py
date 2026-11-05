"""Structured logs, request traces, and in-process metrics (Chapter 45).

One trace per request with a span per component. Spans carry the
attributes the failure taxonomy (Chapter 32) and the cost model
(Chapter 46) need. Logs are JSON lines with request and trace IDs and
never contain secrets or unredacted content: callers log metadata, and
content goes only into the trace's content layer, redacted at write.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
import threading
import time
import uuid
from collections import OrderedDict, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            entry.update(extra)
        if record.exc_info:
            entry["error"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(entry, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger("atlas")
    root.setLevel(level)
    if not any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(JsonFormatter())
        root.addHandler(h)
    root.propagate = False


def log_event(logger: logging.Logger, msg: str, **fields: Any) -> None:
    logger.info(msg, extra={"fields": fields})


# Attributes every span of a given name must carry (Listing 45.1's idea):
REQUIRED = {
    "retrieval": {"candidates", "acl_filtered", "status_filtered"},
    "context": {"labels", "dropped"},
    "gateway": {"provider", "model", "input_tokens", "output_tokens", "cost_usd", "attempts"},
    "validation": {"outcome", "repairs"},
    "tool": {"tool", "decision"},
}


@dataclass
class Span:
    name: str
    start: float
    end: float | None = None
    attrs: dict[str, Any] = field(default_factory=dict)

    def set(self, **attrs: Any) -> None:
        self.attrs.update(attrs)


@dataclass
class Trace:
    trace_id: str
    user_id: str
    versions: dict[str, str]
    spans: list[Span] = field(default_factory=list)
    outcome: str | None = None

    @contextmanager
    def span(self, name: str, **attrs: Any) -> Iterator[Span]:
        s = Span(name, time.perf_counter(), attrs=dict(attrs))
        self.spans.append(s)
        try:
            yield s
        except Exception as exc:  # recorded, then re-raised
            s.set(error=type(exc).__name__)
            raise
        finally:
            s.end = time.perf_counter()

    def missing_attributes(self) -> list[str]:
        problems = []
        for s in self.spans:
            need = REQUIRED.get(s.name, set())
            missing = need - set(s.attrs)
            if missing and "error" not in s.attrs:
                problems.append(f"{s.name}: missing {sorted(missing)}")
        return problems

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "versions": self.versions,
            "outcome": self.outcome,
            "spans": [
                {
                    "name": s.name,
                    "ms": round(((s.end or s.start) - s.start) * 1000, 2),
                    **s.attrs,
                }
                for s in self.spans
            ],
        }


def new_trace(user_id: str, versions: dict[str, str]) -> Trace:
    return Trace(trace_id=uuid.uuid4().hex, user_id=user_id, versions=versions)


class TraceStore:
    """Bounded in-memory store of recent traces (metadata layer).

    Production exports traces to a tracing backend; this keeps the
    reference implementation self-contained and testable."""

    def __init__(self, capacity: int = 1000):
        self._items: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._cap = capacity
        self._lock = threading.Lock()

    def put(self, trace: Trace) -> None:
        with self._lock:
            self._items[trace.trace_id] = trace.to_dict()
            while len(self._items) > self._cap:
                self._items.popitem(last=False)

    def get(self, trace_id: str) -> dict[str, Any] | None:
        with self._lock:
            return self._items.get(trace_id)


class Metrics:
    """Counters and latency samples, exported in Prometheus text format."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._counters[key] += value

    def value(self, name: str, **labels: str) -> float:
        return self._counters.get((name, tuple(sorted(labels.items()))), 0.0)

    def render(self) -> str:
        lines = []
        with self._lock:
            for (name, labels), v in sorted(self._counters.items()):
                lab = ",".join(f'{k}="{val}"' for k, val in labels)
                lines.append(f"atlas_{name}{{{lab}}} {round(v, 6):g}")
        return "\n".join(lines) + "\n"
