"""An in-process Atlas for tests, labs, and experiments.

Builds the service on the in-memory store and deterministic mock
providers, with retries that do not sleep, so everything runs offline in
milliseconds. Pass your own MockProvider to inject faults.
"""
from __future__ import annotations

import logging
from pathlib import Path

from atlas.core.config import Settings
from atlas.corpus import load_corpus
from atlas.gateway.gateway import Gateway, Ledger
from atlas.gateway.providers import MockProvider
from atlas.service import Atlas

# test/lab helper: the per-process dev secrets are expected here
logging.getLogger("atlas.config").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "examples" / "corpus"


def make_atlas(primary: MockProvider | None = None, fallback: MockProvider | None = None,
               seed: bool = True, **overrides) -> Atlas:
    settings = Settings(env="test", **overrides)
    primary = primary or MockProvider(name="mock-primary")
    fallback = fallback or MockProvider(name="mock-fallback")
    chain = [(primary, settings.model_primary), (fallback, settings.model_fallback)]
    ledger = Ledger(settings.daily_cost_cap_usd)
    gw = Gateway({"answer": chain, "plan": chain, "judge": chain}, ledger,
                 max_attempts=settings.max_attempts_per_candidate,
                 breaker_threshold=settings.breaker_threshold, sleep=lambda s: None)
    svc = Atlas(settings, gateway=gw)
    svc.ledger = ledger
    if seed:
        for d in load_corpus(CORPUS):
            svc.ingest(d)
    return svc
