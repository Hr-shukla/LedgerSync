"""Tool implementations backing the Settlement Q&A agent (Task 5).

Every function here reads only from files the reconciliation pipeline
already produced (output/report.json, output/groups.json,
output/exceptions.json, output/audit_trail.db, and the raw data/*.csv) --
nothing is computed fresh or guessed. This is what makes the Q&A agent's
answers groundable: every number it cites came from calling one of these.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

DATE_FIELD_BY_SOURCE = {"bank": "date", "settlement": "settlement_date", "ledger": "invoice_date"}
ID_FIELD_BY_SOURCE = {"bank": "bank_txn_id", "settlement": "settlement_id", "ledger": "ledger_id"}
CSV_BY_SOURCE = {
    "bank": "bank_statement.csv", "settlement": "razorpay_settlements.csv", "ledger": "internal_ledger.csv",
}
# csv.DictReader returns every field as a string; these are the columns that
# are actually numeric in each source and must be coerced back to numbers --
# otherwise every consumer of ReconciliationStore.raw (the API, the Q&A
# agent) gets amounts as strings, which breaks sorting/formatting/arithmetic
# on the receiving end for no good reason.
NUMERIC_FIELDS_BY_SOURCE = {
    "bank": ("amount",),
    "settlement": ("gross_amount", "fee", "fee_gst", "tds", "net_amount"),
    "ledger": ("invoice_amount",),
}


class ReconciliationStore:
    """Loads everything once; every tool call reads from this in-memory snapshot."""

    def __init__(self, data_dir: Path, output_dir: Path):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.report = json.loads((self.output_dir / "report.json").read_text(encoding="utf-8"))
        self.groups = json.loads((self.output_dir / "groups.json").read_text(encoding="utf-8"))
        self.exceptions = json.loads((self.output_dir / "exceptions.json").read_text(encoding="utf-8"))
        self.audit_db_path = self.output_dir / "audit_trail.db"
        self.raw = {src: self._load_csv(src) for src in CSV_BY_SOURCE}

    def _load_csv(self, source: str) -> dict[str, dict]:
        path = self.data_dir / CSV_BY_SOURCE[source]
        id_field = ID_FIELD_BY_SOURCE[source]
        numeric_fields = NUMERIC_FIELDS_BY_SOURCE[source]
        out = {}
        if not path.exists():
            return out
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for field in numeric_fields:
                    if row.get(field):
                        row[field] = float(row[field])
                if source == "settlement":
                    row["chargeback"] = str(row.get("chargeback", "")).strip().lower() in ("true", "1", "yes")
                out[row[id_field]] = row
        return out

    def _source_of(self, record_id: str) -> str | None:
        for src, rows in self.raw.items():
            if record_id in rows:
                return src
        return None

    def _group_for(self, record_id: str) -> dict | None:
        for g in self.groups:
            if record_id in g["bank_ids"] or record_id in g["settlement_ids"] or record_id in g["ledger_ids"]:
                return g
        return None

    def _audit_rows(self, record_id: str) -> list[dict]:
        if not self.audit_db_path.exists():
            return []
        conn = sqlite3.connect(str(self.audit_db_path))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT * FROM audit_trail WHERE record_id = ? ORDER BY id", (record_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---- the 5 exposed tools -----------------------------------------
    def get_record_by_id(self, record_id: str) -> dict:
        source = self._source_of(record_id)
        if source is None:
            return {"found": False, "record_id": record_id, "error": "no such record in bank/settlement/ledger data"}
        raw_record = self.raw[source][record_id]
        group = self._group_for(record_id)
        exception_entries = [e for e in self.exceptions if e["record_id"] == record_id]
        audit_trail = self._audit_rows(record_id)
        return {
            "found": True, "record_id": record_id, "source": source, "raw_record": raw_record,
            "is_matched": bool(group and group["size"] > 1),
            "group": group, "exceptions": exception_entries, "audit_trail": audit_trail,
        }

    def get_exceptions_by_reason(self, reason_code: str | None = None) -> dict:
        matches = [e for e in self.exceptions if reason_code is None or e["reason_code"] == reason_code]
        return {"reason_code": reason_code, "count": len(matches), "exceptions": matches}

    def get_total_value_at_risk(self, reason_code: str | None = None) -> dict:
        matches = [e for e in self.exceptions if reason_code is None or e["reason_code"] == reason_code]
        total = sum(abs(e["amount"]) for e in matches)
        return {"reason_code": reason_code or "all", "record_count": len(matches), "total_value_rupees": round(total, 2)}

    def get_records_by_date_range(self, source: str, start_date: str, end_date: str) -> dict:
        if source not in CSV_BY_SOURCE:
            return {"error": f"unknown source '{source}', must be one of {list(CSV_BY_SOURCE)}"}
        date_field = DATE_FIELD_BY_SOURCE[source]
        id_field = ID_FIELD_BY_SOURCE[source]
        exception_ids = {e["record_id"] for e in self.exceptions}
        out = []
        for rid, row in self.raw[source].items():
            d = row[date_field]
            if start_date <= d <= end_date:
                group = self._group_for(rid)
                out.append({
                    "record_id": rid, "date": d,
                    "status": "exception" if rid in exception_ids else ("matched" if group and group["size"] > 1 else "unknown"),
                    **{k: v for k, v in row.items() if k != id_field},
                })
        out.sort(key=lambda r: r["date"])
        return {"source": source, "start_date": start_date, "end_date": end_date, "count": len(out), "records": out}

    def get_match_rate_by_source(self, source: str | None = None) -> dict:
        per_source = self.report["with_ai"]["metrics"]["per_source"]
        if source is None:
            return {"overall_match_rate_pct": self.report["with_ai"]["metrics"]["overall_match_rate_pct"],
                    "per_source": per_source}
        if source not in per_source:
            return {"error": f"unknown source '{source}', must be one of {list(per_source)}"}
        return {"source": source, **per_source[source]}


TOOL_SPECS = [
    {
        "name": "get_record_by_id",
        "description": "Look up one record (bank txn id, settlement id, or ledger invoice id) and return its raw data, whether it was matched, which group it belongs to, any exception reason, and its full audit trail history across all reconciliation tiers.",
        "params": {"record_id": {"type": "string", "description": "e.g. BNK000012, STL000045, or INV-2026-00031"}},
        "required": ["record_id"],
    },
    {
        "name": "get_exceptions_by_reason",
        "description": "List reconciliation exceptions, optionally filtered by reason code (e.g. no_counterpart_found, duplicate_suspected, chargeback_dispute, refund_no_ledger_expected, low_ai_confidence, ai_rejected_no_match, ai_unavailable_needs_review). Omit reason_code to list all exceptions.",
        "params": {"reason_code": {"type": "string", "description": "optional exact reason code to filter by"}},
        "required": [],
    },
    {
        "name": "get_total_value_at_risk",
        "description": "Sum the rupee value of exceptions, optionally filtered by reason code. Omit reason_code for the total across all exceptions.",
        "params": {"reason_code": {"type": "string", "description": "optional exact reason code to filter by"}},
        "required": [],
    },
    {
        "name": "get_records_by_date_range",
        "description": "List records from one source (bank, settlement, or ledger) whose transaction date falls within a date range, with their match status.",
        "params": {
            "source": {"type": "string", "description": "one of: bank, settlement, ledger"},
            "start_date": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
            "end_date": {"type": "string", "description": "YYYY-MM-DD, inclusive"},
        },
        "required": ["source", "start_date", "end_date"],
    },
    {
        "name": "get_match_rate_by_source",
        "description": "Get the match rate percentage for one source (bank, settlement, ledger), or overall + all three if source is omitted.",
        "params": {"source": {"type": "string", "description": "optional: bank, settlement, or ledger"}},
        "required": [],
    },
]
