"""Index stores: in-memory and PostgreSQL (pgvector + full-text search).

Both enforce the same rules (Chapters 14, 16, 18):

- Permission and status filters are predicates inside the search, never
  applied to results afterward. The only thing measured about excluded
  chunks is a count, for the trace; their content is never returned.
- Upserts are idempotent and transactional per document: an unchanged
  content hash writes nothing; a changed document replaces all its
  chunks at once.
- Quarantined documents are recorded but never searchable.
"""
from __future__ import annotations

import json
import math
import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from atlas.retrieval.text import Chunk, Document, cosine, words


@dataclass
class SearchResult:
    ranked: list[tuple[Chunk, float]]
    acl_filtered: int = 0
    status_filtered: int = 0


class Store(Protocol):
    def upsert(self, doc: Document, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]],
               embed_model: str) -> str: ...

    def quarantine(self, doc: Document, reasons: list[str]) -> None: ...

    def delete(self, doc_id: str) -> bool: ...

    def search_vector(self, qvec: Sequence[float], groups: frozenset[str], k: int) -> SearchResult: ...

    def search_keyword(self, query: str, groups: frozenset[str], k: int) -> SearchResult: ...

    def versions(self) -> dict[str, str]: ...

    def quarantined(self) -> dict[str, list[str]]: ...


# ------------------------------------------------------------- in-memory
@dataclass
class _Row:
    doc: Document
    chunks: list[Chunk]
    vectors: list[list[float]]
    content_hash: str
    embed_model: str


@dataclass
class MemoryStore:
    _docs: dict[str, _Row] = field(default_factory=dict)
    _quarantine: dict[str, list[str]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def upsert(self, doc, chunks, vectors, embed_model):
        h = doc.content_hash()
        with self._lock:
            self._quarantine.pop(doc.doc_id, None)
            old = self._docs.get(doc.doc_id)
            if old and old.content_hash == h and old.embed_model == embed_model:
                return "unchanged"
            self._docs[doc.doc_id] = _Row(doc, list(chunks), [list(v) for v in vectors], h, embed_model)
            return "replaced" if old else "inserted"

    def quarantine(self, doc, reasons):
        with self._lock:
            self._docs.pop(doc.doc_id, None)
            self._quarantine[doc.doc_id] = reasons

    def delete(self, doc_id):
        with self._lock:
            return self._docs.pop(doc_id, None) is not None

    def _visible(self, row: _Row, groups: frozenset[str]) -> tuple[bool, bool]:
        return bool(row.doc.acl & groups), row.doc.status == "current"

    def search_vector(self, qvec, groups, k):
        scored, acl_x, status_x = [], 0, 0
        with self._lock:
            rows = list(self._docs.values())
        for row in rows:
            acl_ok, status_ok = self._visible(row, groups)
            for c, v in zip(row.chunks, row.vectors):
                if not acl_ok:
                    acl_x += 1
                    continue
                if not status_ok:
                    status_x += 1
                    continue
                scored.append((c, cosine(qvec, v)))
        scored.sort(key=lambda cs: (-cs[1], cs[0].chunk_id))
        return SearchResult(scored[:k], acl_x, status_x)

    def search_keyword(self, query, groups, k):
        q = set(words(query))
        with self._lock:
            rows = list(self._docs.values())
        all_chunks = [(row, c) for row in rows for c in row.chunks]
        n = len(all_chunks) or 1
        df: Counter[str] = Counter()
        lens = []
        toks = {}
        for _, c in all_chunks:
            ws = words(c.heading_path + " " + c.text)
            toks[c.chunk_id] = Counter(ws)
            lens.append(len(ws))
            df.update(set(ws))
        avg = (sum(lens) / len(lens)) if lens else 1.0
        scored, acl_x, status_x = [], 0, 0
        for row, c in all_chunks:
            tf = toks[c.chunk_id]
            if not (q & set(tf)):
                continue
            acl_ok, status_ok = self._visible(row, groups)
            if not acl_ok:
                acl_x += 1
                continue
            if not status_ok:
                status_x += 1
                continue
            dl = sum(tf.values())
            s = 0.0
            for t in q:
                if t in tf:
                    idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                    s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * dl / avg))
            scored.append((c, s))
        scored.sort(key=lambda cs: (-cs[1], cs[0].chunk_id))
        return SearchResult(scored[:k], acl_x, status_x)

    def versions(self):
        with self._lock:
            return {d: r.doc.version for d, r in self._docs.items()}

    def quarantined(self):
        with self._lock:
            return dict(self._quarantine)


# ------------------------------------------------------------ PostgreSQL
def _vec_literal(v: Sequence[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


class PostgresStore:
    """PostgreSQL with pgvector and built-in full-text search.

    Requires the schema in atlas/db/migrations (run `python -m atlas.db.migrate`)."""

    def __init__(self, dsn: str):
        import psycopg  # imported here so the in-memory path needs no driver

        self._psycopg = psycopg
        self._dsn = dsn

    def _conn(self):
        return self._psycopg.connect(self._dsn, autocommit=False)

    def upsert(self, doc, chunks, vectors, embed_model):
        h = doc.content_hash()
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT content_hash, embed_model, quarantined FROM documents "
                        "WHERE doc_id = %s FOR UPDATE", (doc.doc_id,))
            row = cur.fetchone()
            if row and row[0] == h and row[1] == embed_model and not row[2]:
                conn.rollback()
                return "unchanged"
            cur.execute("DELETE FROM documents WHERE doc_id = %s", (doc.doc_id,))
            cur.execute(
                "INSERT INTO documents (doc_id, title, status, source, version, updated, owner, "
                "classification, content_hash, embed_model) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (doc.doc_id, doc.title, doc.status, doc.source, doc.version, doc.updated,
                 doc.owner, doc.classification, h, embed_model))
            cur.executemany("INSERT INTO document_acl (doc_id, group_id) VALUES (%s,%s)",
                            [(doc.doc_id, g) for g in sorted(doc.acl)])
            cur.executemany(
                "INSERT INTO chunks (chunk_id, doc_id, ordinal, heading_path, content, embedding) "
                "VALUES (%s,%s,%s,%s,%s,%s::vector)",
                [(c.chunk_id, c.doc_id, c.ordinal, c.heading_path, c.text, _vec_literal(v))
                 for c, v in zip(chunks, vectors)])
            conn.commit()
            return "replaced" if row else "inserted"

    def quarantine(self, doc, reasons):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE doc_id = %s", (doc.doc_id,))
            cur.execute(
                "INSERT INTO documents (doc_id, title, status, source, version, updated, owner, "
                "content_hash, embed_model, quarantined, quarantine_reason) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'',true,%s)",
                (doc.doc_id, doc.title, doc.status, doc.source, doc.version, doc.updated,
                 doc.owner, doc.content_hash(), json.dumps(reasons)))
            conn.commit()

    def delete(self, doc_id):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE doc_id = %s", (doc_id,))
            n = cur.rowcount
            conn.commit()
            return n > 0

    _VISIBLE = ("NOT d.quarantined AND d.status = 'current' AND EXISTS "
                "(SELECT 1 FROM document_acl a WHERE a.doc_id = d.doc_id "
                "AND a.group_id = ANY(%(groups)s))")
    _ACL_OUT = ("NOT d.quarantined AND NOT EXISTS (SELECT 1 FROM document_acl a "
                "WHERE a.doc_id = d.doc_id AND a.group_id = ANY(%(groups)s))")
    _STATUS_OUT = ("NOT d.quarantined AND d.status <> 'current' AND EXISTS "
                   "(SELECT 1 FROM document_acl a WHERE a.doc_id = d.doc_id "
                   "AND a.group_id = ANY(%(groups)s))")

    def _rows_to_chunks(self, rows):
        return [(Chunk(chunk_id=r[0], doc_id=r[1], title=r[2], heading_path=r[3], text=r[4],
                       ordinal=r[5], status=r[6], source=r[7], updated=r[8],
                       classification=r[9]), float(r[10]))
                for r in rows]

    _COLS = ("c.chunk_id, c.doc_id, d.title, c.heading_path, c.content, c.ordinal, "
             "d.status, d.source, d.updated, d.classification")

    def search_vector(self, qvec, groups, k):
        p = {"q": _vec_literal(qvec), "groups": sorted(groups), "k": k}
        with self._conn() as conn, conn.cursor() as cur:
            # iterative scans keep searching until enough rows pass the filter
            cur.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")
            cur.execute("SET LOCAL hnsw.ef_search = 100")
            cur.execute(
                f"SELECT {self._COLS}, 1 - (c.embedding <=> %(q)s::vector) AS sim "
                f"FROM chunks c JOIN documents d USING (doc_id) WHERE {self._VISIBLE} "
                "ORDER BY c.embedding <=> %(q)s::vector LIMIT %(k)s", p)
            ranked = self._rows_to_chunks(cur.fetchall())
            conn.rollback()
        return SearchResult(ranked)

    def search_keyword(self, query, groups, k):
        p = {"q": " ".join(words(query)) or query, "groups": sorted(groups), "k": k}
        match = "c.tsv @@ websearch_to_tsquery('english', %(q)s)"
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT {self._COLS}, ts_rank_cd(c.tsv, websearch_to_tsquery('english', %(q)s)) "
                f"FROM chunks c JOIN documents d USING (doc_id) WHERE {match} AND {self._VISIBLE} "
                "ORDER BY 11 DESC, c.chunk_id LIMIT %(k)s", p)
            ranked = self._rows_to_chunks(cur.fetchall())
            # counts only: the content of excluded chunks is never read
            cur.execute(f"SELECT count(*) FROM chunks c JOIN documents d USING (doc_id) "
                        f"WHERE {match} AND {self._ACL_OUT}", p)
            acl_x = cur.fetchone()[0]
            cur.execute(f"SELECT count(*) FROM chunks c JOIN documents d USING (doc_id) "
                        f"WHERE {match} AND {self._STATUS_OUT}", p)
            status_x = cur.fetchone()[0]
            conn.rollback()
        return SearchResult(ranked, acl_x, status_x)

    def versions(self):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT doc_id, version FROM documents WHERE NOT quarantined")
            out = dict(cur.fetchall())
            conn.rollback()
            return out

    def quarantined(self):
        with self._conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT doc_id, quarantine_reason FROM documents WHERE quarantined")
            out = {d: json.loads(r or "[]") for d, r in cur.fetchall()}
            conn.rollback()
            return out
