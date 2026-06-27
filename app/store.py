"""SQLite-backed record of every remediation run.

One row per (issue -> Devin session). This is the source of truth for the
observability layer: status, success/failure, PR link, timing.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    repo          TEXT NOT NULL,
    issue_number  INTEGER NOT NULL,
    issue_title   TEXT NOT NULL,
    session_id    TEXT,
    session_url   TEXT,
    status        TEXT NOT NULL DEFAULT 'queued',   -- queued|active|done|error
    result        TEXT,                             -- success|failure|null
    pr_url        TEXT,
    error         TEXT,
    created_at    REAL NOT NULL,
    updated_at    REAL NOT NULL,
    UNIQUE(repo, issue_number)
);
"""


class Store:
    """One long-lived connection per Store instance.

    A single shared connection keeps in-memory databases (`:memory:`) alive for
    the process and avoids per-call open/close churn. `check_same_thread=False`
    lets the FastAPI request thread and the background poller thread share it;
    SQLite serialises writes internally and our volume is tiny.
    """

    def __init__(self, path: str) -> None:
        self._path = path
        if path != ":memory:" and os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        with self._connection:
            self._connection.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return self._connection

    def get_by_issue(self, repo: str, issue_number: int) -> dict[str, Any] | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM runs WHERE repo=? AND issue_number=?",
                (repo, issue_number),
            ).fetchone()
            return dict(row) if row else None

    def create_run(self, repo: str, issue_number: int, issue_title: str) -> int:
        now = time.time()
        with self._conn() as c:
            cur = c.execute(
                """INSERT INTO runs (repo, issue_number, issue_title, status, created_at, updated_at)
                   VALUES (?,?,?, 'queued', ?, ?)
                   ON CONFLICT(repo, issue_number) DO UPDATE SET updated_at=excluded.updated_at
                   RETURNING id""",
                (repo, issue_number, issue_title, now, now),
            )
            return int(cur.fetchone()["id"])

    def update_run(self, run_id: int, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k}=?" for k in fields)
        with self._conn() as c:
            c.execute(f"UPDATE runs SET {cols} WHERE id=?", (*fields.values(), run_id))

    def active_runs(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM runs WHERE status='active' AND session_id IS NOT NULL"
            ).fetchall()
            return [dict(r) for r in rows]

    def all_runs(self) -> list[dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM runs ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def metrics(self) -> dict[str, Any]:
        runs = self.all_runs()
        total = len(runs)
        active = sum(1 for r in runs if r["status"] == "active")
        done = sum(1 for r in runs if r["status"] == "done")
        success = sum(1 for r in runs if r["result"] == "success")
        failure = sum(1 for r in runs if r["result"] == "failure")
        errors = sum(1 for r in runs if r["status"] == "error")
        completed = success + failure
        durations = [
            r["updated_at"] - r["created_at"]
            for r in runs
            if r["status"] == "done" and r["updated_at"] and r["created_at"]
        ]
        avg_seconds = round(sum(durations) / len(durations), 1) if durations else 0.0
        return {
            "total": total,
            "active": active,
            "done": done,
            "errors": errors,
            "success": success,
            "failure": failure,
            "success_rate": round(success / completed, 3) if completed else None,
            "avg_resolution_seconds": avg_seconds,
        }


def to_json(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)
