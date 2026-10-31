"""Persistencia SQLite de JobRecord. Thread-safe."""
from __future__ import annotations
import json
import logging
import sqlite3
import threading
from pathlib import Path

from ._utils import data_dir
from .models import JobRecord, JobStatus, JobKind

log = logging.getLogger("foundationcalc.jobs")


_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    task_name TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL,
    progress REAL DEFAULT 0,
    message TEXT,
    payload TEXT,
    result TEXT,
    error TEXT
)
"""


class JobStore:
    """SQLite store thread-safe."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = data_dir() / "jobs.db"
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _init(self) -> None:
        with self._conn() as c:
            c.execute(_DDL)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def save(self, rec: JobRecord) -> None:
        with self._lock, self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO jobs(id, kind, task_name, status, "
                "created_at, started_at, finished_at, progress, message, "
                "payload, result, error) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (rec.id, rec.kind.value, rec.task_name, rec.status.value,
                 rec.created_at, rec.started_at, rec.finished_at,
                 rec.progress, rec.message,
                 json.dumps(rec.payload),
                 json.dumps(rec.result) if rec.result else None,
                 rec.error),
            )

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock, self._conn() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._row_to_rec(row) if row else None

    def list(self, *, status: JobStatus | None = None,
             limit: int = 100) -> list[JobRecord]:
        q = "SELECT * FROM jobs"
        params: tuple = ()
        if status is not None:
            q += " WHERE status=?"
            params = (status.value,)
        q += " ORDER BY created_at DESC LIMIT ?"
        params = params + (limit,)
        with self._lock, self._conn() as c:
            rows = c.execute(q, params).fetchall()
        return [self._row_to_rec(r) for r in rows]

    def delete_old(self, *, older_than_seconds: float) -> int:
        import time
        cutoff = time.time() - older_than_seconds
        with self._lock, self._conn() as c:
            cur = c.execute(
                "DELETE FROM jobs WHERE finished_at IS NOT NULL "
                "AND finished_at < ?", (cutoff,))
            return cur.rowcount

    @staticmethod
    def _row_to_rec(row) -> JobRecord:
        (jid, kind, tname, status, c_at, s_at, f_at, prog, msg,
         payload, result, error) = row
        return JobRecord(
            id=jid, kind=JobKind(kind), task_name=tname,
            status=JobStatus(status),
            created_at=c_at, started_at=s_at, finished_at=f_at,
            progress=prog or 0.0, message=msg or "",
            payload=json.loads(payload) if payload else {},
            result=json.loads(result) if result else None,
            error=error,
        )
