"""Context assembly and citation verification (Chapters 10 and 17)."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html import escape

from atlas.retrieval.text import Chunk, approx_tokens, words
from atlas.security.controls import tier_of


@dataclass
class Assembled:
    text: str
    labels: dict[str, Chunk]          # label -> chunk actually in the context
    dropped: list[str]                # labels dropped by the budget, for the trace
    untrusted: bool                   # any untrusted-tier passage present
    restricted: bool                  # any restricted-classification passage present


def assemble(chunks: list[Chunk], question: str, budget_tokens: int) -> Assembled:
    """Deduplicate, budget in rank order, and label every passage.

    Untrusted passages are wrapped as UNTRUSTED and placed after the
    semi-trusted ones, never next to the instructions (Chapter 40)."""
    seen: set[str] = set()
    kept: list[Chunk] = []
    dropped: list[str] = []
    used = approx_tokens(question) + 50
    for c in chunks:
        h = hashlib.sha256(c.text.strip().lower().encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        cost = approx_tokens(c.text) + 20
        if used + cost > budget_tokens:
            dropped.append(c.label)
            continue
        used += cost
        kept.append(c)
    semi = [c for c in kept if tier_of(c.source) != "untrusted"]
    untrusted = [c for c in kept if tier_of(c.source) == "untrusted"]
    parts = ["SOURCES:"]
    for c in semi:
        parts.append(f'<SOURCE label="{escape(c.label)}" title="{escape(c.title)}" '
                     f'path="{escape(c.heading_path)}">\n{c.text}\n</SOURCE>')
    for c in untrusted:
        parts.append(f'<UNTRUSTED label="{escape(c.label)}" origin="{escape(c.source)}">\n'
                     f"{c.text}\n</UNTRUSTED>")
    parts.append(f"QUESTION: {question}")
    return Assembled("\n\n".join(parts), {c.label: c for c in kept}, dropped,
                     bool(untrusted), any(c.classification == "restricted" for c in kept))


def verify_citations(answer: dict, labels: dict[str, Chunk], min_overlap: float = 0.6) -> list[str]:
    """Tier 1: every cited label was in this request's context.
    Tier 2: each sentence's content words are covered by the cited passages.
    Claim-level entailment (tier 3) is an evaluation method (Chapter 36)."""
    problems = []
    cited = answer.get("citations", [])
    unknown = [c for c in cited if c not in labels]
    if unknown:
        problems.append(f"citations not in context: {unknown}")
    if answer.get("supported"):
        if not cited:
            problems.append("supported answer without citations")
        else:
            support = set()
            for c in cited:
                if c in labels:
                    support |= set(words(labels[c].text + " " + labels[c].heading_path))
            # per sentence: one unsupported sentence appended to a supported one
            # must not pass on the strength of the rest (Chapter 17)
            for sentence in re.split(r"(?<=[.!?])\s+", answer.get("answer", "")):
                sw = set(words(sentence))
                if len(sw) >= 2 and len(sw & support) / len(sw) < min_overlap:
                    problems.append(f"sentence not supported by cited passages: {sentence.strip()!r}")
    return problems
