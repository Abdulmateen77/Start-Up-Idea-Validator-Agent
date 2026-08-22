"""
Run registry. OWNERSHIP: Lead only.

LangGraph's checkpointer stores graph *state* keyed by thread_id, but it can't answer
"list every run, newest first" — which the dashboard needs. This is that index, and
nothing more. Pipeline data belongs in the checkpoint, never here.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DEFAULT_DB = os.getenv("IVA_DB", "iva.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id     TEXT PRIMARY KEY,
    raw_idea   TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn(db_path: str | None = None):
    conn = sqlite3.connect(db_path or DEFAULT_DB)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_run(run_id: str, raw_idea: str, db_path: str | None = None) -> None:
    ts = _now()
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO runs (run_id, raw_idea, created_at, updated_at)"
            " VALUES (?, ?, ?, ?)",
            (run_id, raw_idea, ts, ts),
        )


def touch_run(run_id: str, db_path: str | None = None) -> None:
    with _conn(db_path) as c:
        c.execute("UPDATE runs SET updated_at = ? WHERE run_id = ?", (_now(), run_id))


def get_run(run_id: str, db_path: str | None = None) -> dict | None:
    with _conn(db_path) as c:
        row = c.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def list_runs(db_path: str | None = None) -> list[dict]:
    with _conn(db_path) as c:
        rows = c.execute("SELECT * FROM runs ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]
