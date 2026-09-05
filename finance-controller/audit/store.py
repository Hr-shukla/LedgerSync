"""Audit trail persistence: every record's journey through the pipeline,
written to SQLite (queryable) and exported to JSON Lines (grep-able).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    source TEXT NOT NULL,
    tier TEXT NOT NULL,
    outcome TEXT NOT NULL,
    matched_against TEXT NOT NULL,
    confidence REAL NOT NULL,
    reasoning TEXT NOT NULL,
    exception_reason TEXT NOT NULL,
    processed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_record_id ON audit_trail(record_id);
CREATE INDEX IF NOT EXISTS idx_audit_tier ON audit_trail(tier);
CREATE INDEX IF NOT EXISTS idx_audit_outcome ON audit_trail(outcome);
"""


def write_audit_trail(events: list, db_path: Path, jsonl_path: Path | None = None) -> None:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()  # fresh audit trail per run, matching the "clean checkout" contract

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA)
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            (e.record_id, e.source, e.tier, e.outcome, json.dumps(e.matched_against),
             e.confidence, e.reasoning, e.exception_reason, now)
            for e in events
        ]
        conn.executemany(
            "INSERT INTO audit_trail (record_id, source, tier, outcome, matched_against, "
            "confidence, reasoning, exception_reason, processed_at) VALUES (?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()

    if jsonl_path is not None:
        jsonl_path = Path(jsonl_path)
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as f:
            for e in events:
                f.write(json.dumps({
                    "record_id": e.record_id, "source": e.source, "tier": e.tier,
                    "outcome": e.outcome, "matched_against": e.matched_against,
                    "confidence": e.confidence, "reasoning": e.reasoning,
                    "exception_reason": e.exception_reason, "processed_at": now,
                }) + "\n")


def query_by_record(db_path: Path, record_id: str) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM audit_trail WHERE record_id = ? ORDER BY id", (record_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def summary_by_tier(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT tier, outcome, COUNT(*) as n FROM audit_trail GROUP BY tier, outcome ORDER BY tier"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
