"""Shared fixtures. Everything here runs offline on the mock provider and
the in-memory store; no API key, network, or database is needed."""
from __future__ import annotations

import logging

import pytest

from atlas.testing import CORPUS, ROOT, make_atlas  # noqa: F401  (re-exported for tests)

logging.getLogger("atlas").setLevel(logging.ERROR)


@pytest.fixture
def atlas():
    return make_atlas()
