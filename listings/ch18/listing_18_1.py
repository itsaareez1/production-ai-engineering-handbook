"""Listing 18.1. Structure-aware chunking with heading paths,
content hashing, and idempotent indexing.

Chapter 18, Ingestion, Chunking, and Freshness.
Verified by execution.
Run with: python run.py 18.1
"""
import hashlib
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    document_id: str
    index: int
    heading_path: str
    text: str
    content_hash: str


def estimate_tokens(s: str) -> int:
    return max(1, len(s) // 4)


def chunk_markdown(document_id: str, md: str,
                   target_tokens: int = 400) -> list:
    chunks, path, buf = [], [], []

    def flush():
        if not buf:
            return
        text = "\n".join(buf).strip()
        if text:
            hp = " > ".join(path)
            body = f"{hp}: {text}" if hp else text
            h = hashlib.sha256(body.encode()).hexdigest()[:16]
            chunks.append(
                Chunk(document_id, len(chunks), hp, body, h))
        buf.clear()

    for line in md.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:  # heading: new section
            flush()
            level = len(m.group(1))
            path[:] = path[:level - 1] + [m.group(2).strip()]
            continue
        if (line.startswith("|") and buf
                and not buf[-1].startswith("|")):
            flush()  # table starts: keep it whole
        buf.append(line)
        if (not line.startswith("|")
                and estimate_tokens("\n".join(buf)) >= target_tokens):
            flush()  # prose overflow: split at paragraph
    flush()
    return chunks


class Index:
    """Idempotent per-document replace keyed on content hash."""

    def __init__(self):
        self.rows: dict = {}
        self.writes = 0

    def upsert_document(self, chunks: list):
        doc = chunks[0].document_id
        existing = {k: v for k, v in self.rows.items()
                    if k[0] == doc}
        new = {(c.document_id, c.index): c for c in chunks}
        old_h = {k: v.content_hash for k, v in existing.items()}
        new_h = {k: v.content_hash for k, v in new.items()}
        if old_h == new_h:
            return "unchanged"
        for k in existing:  # in production: one transaction
            del self.rows[k]
        self.rows.update(new)
        self.writes += 1
        return "replaced"


DOC = """# Leave Policy
## 4 Carry-over
### 4.2 Limits
Unused annual leave may be carried forward up to five days.
| Grade | Max days |
| A-C   | 5 |
| D+    | 10 |
### 4.3 Exclusions
Contractors may not carry over leave.
"""


if __name__ == "__main__":
    idx = Index()
    chunks = chunk_markdown("policy-leave", DOC)
    for c in chunks:
        print(c.index, repr(c.text[:70]), c.content_hash)
    print(idx.upsert_document(chunks), "|",
          idx.upsert_document(chunks))
    changed = chunk_markdown(
        "policy-leave", DOC.replace("five days", "seven days"))
    print(idx.upsert_document(changed), "| writes:", idx.writes)
