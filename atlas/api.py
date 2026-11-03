"""Minimal Atlas service entry point.

This is the application the Dockerfile of Listing 44.1 starts. It is
deliberately small: a health check and the answer validator of
Chapter 12. Assembling the full Atlas system from the listings is the
reader's project (Appendix K.6).
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from atlas.validation import (
    ANSWER_SCHEMA,
    schema_errors,
    semantic_errors,
)

app = FastAPI(
    title="Atlas (companion code)",
    version="1.0.0",
    description="Health check and the Chapter 12 answer validator.",
)


class ValidateRequest(BaseModel):
    answer: dict
    valid_sources: list[str] = []


@app.get("/health")
def health() -> dict:
    """Appendix K.6: this must return {"status":"ok"}."""
    return {"status": "ok"}


@app.get("/schema")
def schema() -> dict:
    """The answer schema of Listing 12.1."""
    return ANSWER_SCHEMA


@app.post("/validate")
def validate(req: ValidateRequest) -> dict:
    """Run Listing 12.1's two validators over a candidate answer."""
    errors = schema_errors(req.answer)
    if not errors:
        errors = semantic_errors(req.answer, set(req.valid_sources))
    return {"valid": not errors, "errors": errors}
