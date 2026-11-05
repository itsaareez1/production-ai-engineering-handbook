"""Documents, chunks, chunking, embeddings, fusion, and reranking.

Chunking is structure-aware (Chapter 18): split at headings, keep
tables whole, carry the heading path into the chunk text and metadata.

The embedder is a deterministic feature-hashing model so that the
reference implementation and its tests run without downloading a model
or calling a paid API. It captures word overlap, not meaning; replace it
with a real embedding model behind the same `Embedder` protocol and
re-measure recall (Chapter 13). Its name and version are stored with
every vector, as Chapter 14 requires.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Protocol, Sequence

STATUSES = ("current", "superseded", "draft")


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    body: str
    acl: frozenset[str]
    status: str = "current"
    source: str = "wiki"          # determines trust tier
    version: str = "1"
    updated: str = ""
    owner: str = ""
    classification: str = "internal"   # internal | restricted

    def content_hash(self) -> str:
        h = hashlib.sha256()
        for part in (self.title, self.body, ",".join(sorted(self.acl)), self.status,
                     self.version, self.classification):
            h.update(part.encode())
            h.update(b"\x00")
        return h.hexdigest()


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    title: str
    heading_path: str
    text: str
    ordinal: int
    status: str
    source: str
    updated: str
    classification: str = "internal"

    @property
    def label(self) -> str:
        """Origin label the model cites and the validator resolves (Ch. 17)."""
        return f"{self.doc_id}#{self.ordinal}@{self.updated or 'undated'}"


def approx_tokens(text: str) -> int:
    """Four characters per token (Chapter 7); replace with a tokenizer."""
    return max(1, len(text) // 4)


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def chunk_document(doc: Document, target_tokens: int = 400) -> list[Chunk]:
    path: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current: list[str] = []
    for line in doc.body.splitlines():
        m = _HEADING.match(line)
        if m:
            if current and any(x.strip() for x in current):
                sections.append((" > ".join([doc.title, *path]), current))
            level = len(m.group(1))
            path = path[: level - 1] + [m.group(2)]
            current = []
        else:
            current.append(line)
    if current and any(x.strip() for x in current):
        sections.append((" > ".join([doc.title, *path]), current))

    chunks: list[Chunk] = []
    for heading_path, lines in sections:
        blocks: list[str] = []
        buf: list[str] = []
        in_table = False
        for line in lines + [""]:
            is_table = line.lstrip().startswith("|")
            if is_table != in_table and buf:
                blocks.append("\n".join(buf).strip())
                buf = []
            in_table = is_table
            if line.strip() == "" and not in_table:
                if buf:
                    blocks.append("\n".join(buf).strip())
                    buf = []
            else:
                buf.append(line)
        piece: list[str] = []
        for block in [b for b in blocks if b]:
            if piece and approx_tokens("\n\n".join(piece + [block])) > target_tokens \
                    and not block.lstrip().startswith("|"):
                chunks.append(_mk(doc, heading_path, piece, len(chunks)))
                piece = []
            piece.append(block)
        if piece:
            chunks.append(_mk(doc, heading_path, piece, len(chunks)))
    return chunks


def _mk(doc: Document, heading_path: str, blocks: list[str], ordinal: int) -> Chunk:
    return Chunk(
        chunk_id=f"{doc.doc_id}#{ordinal}",
        doc_id=doc.doc_id,
        title=doc.title,
        heading_path=heading_path,
        text="\n\n".join(blocks),
        ordinal=ordinal,
        status=doc.status,
        source=doc.source,
        updated=doc.updated,
        classification=doc.classification,
    )


_WORD = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
STOP = frozenset(
    "a an and are as at be by can do does for from has have how i if in is it its "
    "may me my of on or our the their there this to was we what when where which "
    "who will with you your".split()
)


def words(text: str) -> list[str]:
    return [w for w in _WORD.findall(text.lower()) if w not in STOP]


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass
class HashingEmbedder:
    """Deterministic feature-hashing embedder (see module docstring)."""

    dim: int = 256
    name: str = "atlas-hashing-v1"

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        ws = words(text)
        feats = ws + [f"{a} {b}" for a, b in zip(ws, ws[1:])]
        for f in feats:
            h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
            v[h % self.dim] += 1.0 if (h >> 63) == 0 else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def rrf(rankings: Sequence[Sequence[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal rank fusion (Chapter 15): sum 1/(k + rank) over lists."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))


class Reranker(Protocol):
    name: str

    def score(self, query: str, passages: Sequence[str]) -> list[float]: ...


@dataclass
class LexicalReranker:
    """Stand-in for a cross-encoder (Chapter 16): content-word coverage of
    the query, with a bonus for matches in the first sentence. Replace
    with a real reranker behind the same protocol and measure the gain."""

    name: str = "atlas-lexical-rerank-v1"

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        q = set(words(query))
        out = []
        for p in passages:
            pw = words(p)
            if not q or not pw:
                out.append(0.0)
                continue
            cover = len(q & set(pw)) / len(q)
            first = set(words(p.split(".")[0]))
            out.append(cover + 0.2 * len(q & first) / len(q))
        return out


@dataclass
class Hit:
    chunk: Chunk
    score: float = 0.0
    ranks: dict[str, int] = field(default_factory=dict)
