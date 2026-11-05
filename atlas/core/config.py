"""Configuration from the environment, validated at start-up.

Every setting has a type and a check; a misconfigured service refuses to
start rather than failing on the first request (Chapter 44). Secrets
have no defaults. In development and tests a random per-process secret
is generated when none is configured, and a warning is logged; in
production a missing secret is a start-up error.
"""
from __future__ import annotations

import logging
import os
import secrets
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

log = logging.getLogger("atlas.config")

Env = Literal["dev", "test", "prod"]
ProviderName = Literal["mock", "anthropic", "openai"]


class Settings(BaseModel):
    env: Env = "dev"
    database_url: str | None = Field(
        default=None,
        description="postgresql://... ; unset means the in-memory store",
    )
    token_secret: SecretStr | None = None
    redaction_key: SecretStr | None = None
    redaction_key_version: str = "v1"

    model_provider: ProviderName = "mock"
    model_primary: str = "mock-large"
    model_fallback: str = "mock-small"
    request_timeout_s: float = Field(default=8.0, gt=0, le=120)
    max_attempts_per_candidate: int = Field(default=2, ge=1, le=5)
    breaker_threshold: int = Field(default=3, ge=1)
    breaker_cooldown_s: float = Field(default=30.0, gt=0)

    context_budget_tokens: int = Field(default=3000, ge=256)
    retrieval_candidates: int = Field(default=40, ge=1, le=500)
    rerank_keep: int = Field(default=6, ge=1, le=50)
    embedding_dim: int = Field(default=256, ge=32, le=4096)

    daily_cost_cap_usd: float = Field(default=50.0, gt=0)
    agent_max_steps: int = Field(default=6, ge=1, le=50)
    approval_ttl_s: int = Field(default=3600, ge=60)
    egress_allowlist: list[str] = Field(default_factory=lambda: ["tickets.example.com"])
    log_level: str = "INFO"
    seed_corpus: str | None = Field(
        default=None, description="directory of Markdown documents to ingest at start-up (dev/test)")

    @field_validator("database_url")
    @classmethod
    def _db_scheme(cls, v: str | None) -> str | None:
        if v and not v.startswith(("postgresql://", "postgres://")):
            raise ValueError("ATLAS_DATABASE_URL must be a postgresql:// URL")
        return v

    @field_validator("log_level")
    @classmethod
    def _level(cls, v: str) -> str:
        v = v.upper()
        if v not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            raise ValueError(f"invalid log level {v!r}")
        return v

    @model_validator(mode="after")
    def _secrets(self) -> "Settings":
        for name in ("token_secret", "redaction_key"):
            value = getattr(self, name)
            if value is not None and self.env == "prod" and (
                    len(value.get_secret_value()) < 32 or "CHANGE_ME" in value.get_secret_value()):
                raise ValueError(f"ATLAS_{name.upper()} must be at least 32 random characters "
                                 "in production, not a placeholder")
            if value is None:
                if self.env == "prod":
                    raise ValueError(
                        f"ATLAS_{name.upper()} must be set in production; "
                        "there is no default"
                    )
                setattr(self, name, SecretStr(secrets.token_urlsafe(32)))
                log.warning(
                    "%s not configured: generated a random per-process value "
                    "(env=%s); tokens and pseudonyms will not survive a restart",
                    name, self.env,
                )
        if self.model_fallback == self.model_primary:
            raise ValueError("fallback model must differ from the primary")
        if self.rerank_keep > self.retrieval_candidates:
            raise ValueError("rerank_keep cannot exceed retrieval_candidates")
        return self

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> "Settings":
        e = os.environ if environ is None else environ
        raw: dict[str, object] = {}
        for field_name in cls.model_fields:
            key = f"ATLAS_{field_name.upper()}"
            if key in e and e[key] != "":
                val: object = e[key]
                if field_name == "egress_allowlist":
                    val = [h.strip() for h in str(val).split(",") if h.strip()]
                raw[field_name] = val
        return cls(**raw)
