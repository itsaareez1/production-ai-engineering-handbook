"""Persistent records (tickets, drafts, approvals) and the action audit.

Two backends with one interface: in-memory for tests and zero-setup
runs, PostgreSQL for the deployed system (tables in migration 001).

The audit log is append-only and hash-chained (Chapter 43): each entry
carries the hash of the previous one, so a deleted or edited entry is
detectable by `verify()`. In PostgreSQL, grant the application role
INSERT and SELECT only on audit_log.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol


class DuplicateKey(Exception):
    def __init__(self, existing_id: str):
        super().__init__(existing_id)
        self.existing_id = existing_id


class Records(Protocol):
    def put(self, kind: str, owner: str, data: dict, idem_key: str | None = None,
            rec_id: str | None = None) -> str: ...

    def get(self, kind: str, rec_id: str) -> dict | None: ...

    def update(self, kind: str, rec_id: str, data: dict) -> None: ...


class AuditLog(Protocol):
    def append(self, actor: str, action: str, detail: dict[str, Any]) -> str: ...

    def entries(self) -> list[dict[str, Any]]: ...

    def verify(self) -> bool: ...


def _hash(prev: str, actor: str, action: str, detail: dict) -> str:
    body = json.dumps([prev, actor, action, detail], sort_keys=True, default=str)
    return hashlib.sha256(body.encode()).hexdigest()


GENESIS = "0" * 64


@dataclass
class MemoryRecords:
    _rows: dict[tuple[str, str], dict] = field(default_factory=dict)
    _idem: dict[tuple[str, str], str] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def put(self, kind, owner, data, idem_key=None, rec_id=None):
        with self._lock:
            if idem_key and (kind, idem_key) in self._idem:
                raise DuplicateKey(self._idem[(kind, idem_key)])
            rid = rec_id or f"{kind[:1].upper()}-{uuid.uuid4().hex[:8]}"
            self._rows[(kind, rid)] = {"id": rid, "owner": owner, **data}
            if idem_key:
                self._idem[(kind, idem_key)] = rid
            return rid

    def get(self, kind, rec_id):
        with self._lock:
            row = self._rows.get((kind, rec_id))
            return dict(row) if row else None

    def update(self, kind, rec_id, data):
        with self._lock:
            self._rows[(kind, rec_id)].update(data)


@dataclass
class MemoryAudit:
    _entries: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def append(self, actor, action, detail):
        with self._lock:
            prev = self._entries[-1]["hash"] if self._entries else GENESIS
            h = _hash(prev, actor, action, detail)
            self._entries.append({"seq": len(self._entries) + 1, "at": time.time(),
                                  "actor": actor, "action": action, "detail": detail,
                                  "prev_hash": prev, "hash": h})
            return h

    def entries(self):
        with self._lock:
            return [dict(e) for e in self._entries]

    def verify(self):
        prev = GENESIS
        for e in self.entries():
            expected = _hash(prev, e["actor"], e["action"], e["detail"])
            if e["prev_hash"] != prev or e["hash"] != expected:
                return False
            prev = e["hash"]
        return True


class PostgresRecords:
    def __init__(self, dsn: str):
        import psycopg

        self._psycopg = psycopg
        self._dsn = dsn

    def put(self, kind, owner, data, idem_key=None, rec_id=None):
        rid = rec_id or f"{kind[:1].upper()}-{uuid.uuid4().hex[:8]}"
        with self._psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            if idem_key:
                cur.execute("SELECT id FROM records WHERE kind=%s AND idem_key=%s",
                            (kind, idem_key))
                row = cur.fetchone()
                if row:
                    raise DuplicateKey(row[0])
            cur.execute("INSERT INTO records (kind, id, owner, idem_key, data) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (kind, rid, owner, idem_key, json.dumps(data)))
            conn.commit()
        return rid

    def get(self, kind, rec_id):
        with self._psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT owner, data FROM records WHERE kind=%s AND id=%s", (kind, rec_id))
            row = cur.fetchone()
        if not row:
            return None
        return {"id": rec_id, "owner": row[0], **row[1]}

    def update(self, kind, rec_id, data):
        with self._psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("UPDATE records SET data = data || %s::jsonb WHERE kind=%s AND id=%s",
                        (json.dumps(data), kind, rec_id))
            conn.commit()


class PostgresAudit:
    def __init__(self, dsn: str):
        import psycopg

        self._psycopg = psycopg
        self._dsn = dsn

    def append(self, actor, action, detail):
        with self._psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("LOCK TABLE audit_log IN SHARE ROW EXCLUSIVE MODE")
            cur.execute("SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1")
            row = cur.fetchone()
            prev = row[0] if row else GENESIS
            h = _hash(prev, actor, action, detail)
            cur.execute("INSERT INTO audit_log (actor, action, detail, prev_hash, hash) "
                        "VALUES (%s,%s,%s,%s,%s)",
                        (actor, action, json.dumps(detail, default=str), prev, h))
            conn.commit()
        return h

    def entries(self):
        with self._psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute("SELECT seq, actor, action, detail, prev_hash, hash FROM audit_log "
                        "ORDER BY seq")
            return [{"seq": r[0], "actor": r[1], "action": r[2], "detail": r[3],
                     "prev_hash": r[4], "hash": r[5]} for r in cur.fetchall()]

    def verify(self):
        prev = GENESIS
        for e in self.entries():
            expected = _hash(prev, e["actor"], e["action"], e["detail"])
            if e["prev_hash"] != prev or e["hash"] != expected:
                return False
            prev = e["hash"]
        return True
