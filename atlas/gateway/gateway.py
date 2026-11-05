"""The model gateway (Chapter 9).

Knows providers, models, limits, health, and cost; knows nothing about
tickets, policies, or answers. Responsibilities implemented here:

- provider abstraction (one request/response shape, adapters per provider)
- static routing by task, with a sensitivity constraint: requests whose
  context includes restricted content go only to providers flagged
  in-region (Chapters 5 and 9)
- per-candidate timeouts, bounded retries with exponential backoff and
  jitter for transient errors only (Chapter 24)
- circuit breakers per provider/model (Chapter 9)
- accounting and a daily cost cap (Chapter 46)
"""
from __future__ import annotations

import random
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Protocol

from atlas.core.identity import Identity


@dataclass(frozen=True)
class ModelRequest:
    task: str                      # "answer" | "plan" | "judge"
    system: str
    user: str
    schema: dict | None = None
    max_output_tokens: int = 800
    sensitivity: str = "internal"  # "internal" | "restricted"


@dataclass(frozen=True)
class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    latency_ms: float


class ProviderError(Exception):
    def __init__(self, message: str, transient: bool):
        super().__init__(message)
        self.transient = transient


class Provider(Protocol):
    name: str
    in_region: bool

    def complete(self, model: str, req: ModelRequest, timeout_s: float) -> ModelResponse: ...


class AllProvidersFailed(Exception):
    def __init__(self, attempts: list[str]):
        super().__init__("; ".join(attempts))
        self.attempts = attempts


class BudgetExceeded(Exception):
    """The daily cost cap is reached; behavior at the cap is decided in
    advance (Chapter 46): the caller serves the degraded response."""


# Illustrative prices in USD per million tokens (input, output). Replace
# with your contracted prices; Chapter 46's cost model reads these.
PRICES: dict[str, tuple[float, float]] = {
    "mock-large": (3.00, 15.00),
    "mock-small": (0.50, 2.50),
}


@dataclass
class CallRecord:
    at: float
    user_id: str
    task: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass
class Ledger:
    daily_cap_usd: float
    clock: Callable[[], float] = time.time
    records: list[CallRecord] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def cost(self, model: str, tin: int, tout: int) -> float:
        pin, pout = PRICES.get(model, (0.0, 0.0))
        return round(tin * pin / 1e6 + tout * pout / 1e6, 6)

    def spent_today(self) -> float:
        day = int(self.clock() // 86400)
        with self._lock:
            return sum(r.cost_usd for r in self.records if int(r.at // 86400) == day)

    def check(self) -> None:
        if self.spent_today() >= self.daily_cap_usd:
            raise BudgetExceeded(f"daily cap ${self.daily_cap_usd:g} reached")

    def record(self, user: Identity, task: str, resp: ModelResponse) -> CallRecord:
        rec = CallRecord(self.clock(), user.user_id, task, resp.provider, resp.model,
                         resp.input_tokens, resp.output_tokens,
                         self.cost(resp.model, resp.input_tokens, resp.output_tokens))
        with self._lock:
            self.records.append(rec)
        return rec


@dataclass
class CircuitBreaker:
    threshold: int
    cooldown_s: float
    clock: Callable[[], float] = time.monotonic
    failures: int = 0
    opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        # half-open after the cooldown: let one request test recovery
        return self.clock() - self.opened_at >= self.cooldown_s

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = self.clock()

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        return "half-open" if self.allow() else "open"


@dataclass
class GatewayResult:
    response: ModelResponse
    attempts: list[str]
    cost_usd: float
    fallback_used: bool


class Gateway:
    def __init__(self, routes: dict[str, list[tuple[Provider, str]]], ledger: Ledger,
                 max_attempts: int = 2, timeout_s: float = 8.0,
                 breaker_threshold: int = 3, breaker_cooldown_s: float = 30.0,
                 sleep: Callable[[float], None] = time.sleep,
                 rng: random.Random | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self.routes = routes
        self.ledger = ledger
        self.max_attempts = max_attempts
        self.timeout_s = timeout_s
        self._sleep = sleep
        self._rng = rng or random.Random()
        self._breakers: dict[tuple[str, str], CircuitBreaker] = defaultdict(
            lambda: CircuitBreaker(breaker_threshold, breaker_cooldown_s, clock))

    def breaker(self, provider: str, model: str) -> CircuitBreaker:
        return self._breakers[(provider, model)]

    def complete(self, req: ModelRequest, user: Identity) -> GatewayResult:
        chain = self.routes.get(req.task)
        if not chain:
            raise KeyError(f"no route for task {req.task!r}")
        if req.sensitivity == "restricted":
            # enforced here from a flag set upstream, never by asking the model
            chain = [(p, m) for p, m in chain if p.in_region]
        self.ledger.check()
        attempts: list[str] = []
        for i, (provider, model) in enumerate(chain):
            br = self.breaker(provider.name, model)
            if not br.allow():
                attempts.append(f"{provider.name}/{model}: breaker open, skipped")
                continue
            for attempt in range(1, self.max_attempts + 1):
                try:
                    resp = provider.complete(model, req, self.timeout_s)
                except ProviderError as exc:
                    br.failure()
                    kind = "transient" if exc.transient else "permanent"
                    attempts.append(f"{provider.name}/{model}#{attempt}: {kind}: {exc}")
                    if not exc.transient or not br.allow():
                        break
                    if attempt < self.max_attempts:
                        # exponential backoff with full jitter (Chapter 24)
                        self._sleep(self._rng.uniform(0, 0.25 * 2 ** (attempt - 1)))
                    continue
                br.success()
                rec = self.ledger.record(user, req.task, resp)
                attempts.append(f"{provider.name}/{model}#{attempt}: ok")
                return GatewayResult(resp, attempts, rec.cost_usd, fallback_used=i > 0)
        raise AllProvidersFailed(attempts or ["no eligible provider for this sensitivity"])
