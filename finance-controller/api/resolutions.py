"""Persisted human resolutions for exceptions.

Deliberately a separate file from audit_trail.db / report.json: those are
overwritten wholesale every time run_reconciliation.py runs (a fresh
pipeline run is a fresh ground truth for what the *pipeline* thinks), but a
human marking an exception resolved must survive that -- Task 9's
idempotency guarantee requires re-running the pipeline to never silently
undo a resolution. Only an explicit new resolve/unresolve call changes this
file.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

_lock = Lock()


class ResolutionStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("{}", encoding="utf-8")

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def all(self) -> dict:
        return self._read()

    def get(self, record_id: str) -> dict | None:
        return self._read().get(record_id)

    def resolve(self, record_id: str, note: str | None, resolved_by: str | None) -> dict:
        with _lock:
            data = self._read()
            entry = {
                "record_id": record_id, "resolved": True,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
                "resolved_by": resolved_by or "api", "note": note or "",
            }
            data[record_id] = entry
            self._write(data)
            return entry

    def unresolve(self, record_id: str) -> bool:
        with _lock:
            data = self._read()
            if record_id in data:
                del data[record_id]
                self._write(data)
                return True
            return False
