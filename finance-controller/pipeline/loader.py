"""CSV loaders for the three reconciliation sources."""
from __future__ import annotations

import csv
from pathlib import Path


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _to_float(v):
    if v in (None, ""):
        return None
    return float(v)


def load_bank(data_dir: Path) -> dict[str, dict]:
    rows = _read_csv(data_dir / "bank_statement.csv")
    out = {}
    for r in rows:
        r["amount"] = _to_float(r["amount"])
        out[r["bank_txn_id"]] = r
    return out


def load_settlements(data_dir: Path) -> dict[str, dict]:
    rows = _read_csv(data_dir / "razorpay_settlements.csv")
    out = {}
    for r in rows:
        for k in ("gross_amount", "fee", "fee_gst", "tds", "net_amount"):
            r[k] = _to_float(r[k])
        r["chargeback"] = str(r.get("chargeback", "")).strip().lower() in ("true", "1", "yes")
        out[r["settlement_id"]] = r
    return out


def load_ledger(data_dir: Path) -> dict[str, dict]:
    rows = _read_csv(data_dir / "internal_ledger.csv")
    out = {}
    for r in rows:
        r["invoice_amount"] = _to_float(r["invoice_amount"])
        out[r["ledger_id"]] = r
    return out


def load_all(data_dir: Path):
    return {
        "bank": load_bank(data_dir),
        "settlement": load_settlements(data_dir),
        "ledger": load_ledger(data_dir),
    }
