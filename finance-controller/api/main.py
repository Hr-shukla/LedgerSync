"""FastAPI backend connecting the reconciliation engine to the LedgerSync
frontend (Task 6). Serves everything read-only from the pipeline's own
output (report.json / groups.json / exceptions.json / audit_trail.db / raw
CSVs) plus the two new report modules (forecast, tax breakdown) -- this
process never re-runs Tier 4 AI on a request, so hitting these endpoints
repeatedly never burns LLM quota.

Run:
    uvicorn api.main:app --reload --port 8006
    (any free port works -- just make sure frontend/.env.local's
    VITE_API_BASE_URL points at the same one)

Note on field names: no frontend source was available to this build, so the
JSON shapes below are a best-effort design against the screens described in
the brief (Overview KPIs, Transaction Matching table + side panel, Exceptions
Queue, Audit Log). See api/README.md for the full field-by-field mapping --
adjust names there first if wiring this into an existing Lovable project
that expects different keys.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.env import load_dotenv_if_present
load_dotenv_if_present()

from pipeline import loader as pipeline_loader
from pipeline.models import days_between
from qa.tools import ReconciliationStore, DATE_FIELD_BY_SOURCE
from forecast.cash_forecast import compute_forecast, render_markdown as forecast_markdown
from report.tax_breakdown import compute_tax_breakdown, render_markdown as tax_markdown
from api.resolutions import ResolutionStore

DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"

# Frontend dev server origin (see frontend/vite.config.ts). Exact match, not a
# wildcard -- this API also accepts a POST that mutates state
# (/exceptions/{id}/resolve), so an open CORS policy would let any page in the
# browser call it.
FRONTEND_ORIGIN = "http://localhost:3007"

@asynccontextmanager
async def _lifespan(app: FastAPI):
    _state.update(_load_state())
    yield


app = FastAPI(title="AI Finance Controller API", version="1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: dict = {}


def _as_of_date(store: ReconciliationStore) -> str:
    """Latest transaction date seen anywhere in the batch -- used as "today"
    for age calculations, since this is a static synthetic batch rather than
    a live stream. Same convention forecast/cash_forecast.py uses."""
    all_dates = [row[DATE_FIELD_BY_SOURCE[src]] for src, rows in store.raw.items() for row in rows.values()]
    return max(all_dates) if all_dates else None


def _record_date(store: ReconciliationStore, record_id: str, source: str) -> str | None:
    row = store.raw.get(source, {}).get(record_id)
    return row[DATE_FIELD_BY_SOURCE[source]] if row else None


def _load_state() -> dict:
    missing = [f for f in ("report.json", "groups.json", "exceptions.json") if not (OUTPUT_DIR / f).exists()]
    if missing:
        raise RuntimeError(f"Missing {missing} in {OUTPUT_DIR} -- run `python run_reconciliation.py` first.")
    store = ReconciliationStore(DATA_DIR, OUTPUT_DIR)
    groups = json.loads((OUTPUT_DIR / "groups.json").read_text(encoding="utf-8"))
    for i, g in enumerate(groups):
        g["id"] = f"grp_{i:05d}"
    resolutions = ResolutionStore(OUTPUT_DIR / "resolutions.json")
    return {"store": store, "groups": groups, "resolutions": resolutions, "as_of_date": _as_of_date(store)}


def _reload_if_needed():
    if not _state:
        _state.update(_load_state())
    return _state


# ----------------------------------------------------------------------
# GET /overview -- Overview screen KPI cards
# ----------------------------------------------------------------------
@app.get("/overview")
def overview():
    s = _reload_if_needed()
    m = s["store"].report["with_ai"]["metrics"]
    g = s["store"].report["with_ai"]["grading"]
    return {
        "match_rate_pct": m["overall_match_rate_pct"],
        "reconciled_value_rupees": m["reconciled_value_rupees"],
        "total_value_rupees": m["total_value_rupees"],
        "reconciled_value_pct": m["reconciled_value_pct"],
        "value_at_risk_rupees": m["exception_value_rupees"],
        "open_exceptions_count": sum(m["exception_count_by_reason"].values()),
        "precision_pct": round(g["precision"] * 100, 1),
        "recall_pct": round(g["recall"] * 100, 1),
        "false_match_rate_pct": round(g["false_match_rate"] * 100, 1),
        "per_source": m["per_source"],
        "tier_breakdown": m["tier_usage_across_matched_groups"],
        "ai_available": m["ai_available"],
        "ai_provider": m.get("ai_provider"),
    }


# ----------------------------------------------------------------------
# GET /transactions -- Transaction Matching screen table
# ----------------------------------------------------------------------
def _txn_row(g: dict, store: ReconciliationStore) -> dict:
    def side(ids: list[str], source: str):
        return [store.raw[source][i] for i in ids if i in store.raw[source]] or None

    return {
        "id": g["id"],
        "status": "matched" if g["size"] > 1 else "exception",
        "tiers": g.get("tiers", []),
        "confidence": g.get("confidence", 0.0),
        "bank": side(g["bank_ids"], "bank"),
        "settlement": side(g["settlement_ids"], "settlement"),
        "ledger": side(g["ledger_ids"], "ledger"),
        "record_ids": {"bank": g["bank_ids"], "settlement": g["settlement_ids"], "ledger": g["ledger_ids"]},
    }


@app.get("/transactions")
def transactions(
    status: Optional[str] = Query(None, description="matched | exception"),
    source: Optional[str] = Query(None, description="bank | settlement | ledger -- only rows touching this source"),
    search: Optional[str] = Query(None, description="substring match against any record id in the row"),
    page: int = 1, page_size: int = 25,
):
    s = _reload_if_needed()
    rows = [_txn_row(g, s["store"]) for g in s["groups"]]

    if status:
        rows = [r for r in rows if r["status"] == status]
    if source:
        rows = [r for r in rows if r["record_ids"].get(source)]
    if search:
        needle = search.lower()
        rows = [r for r in rows if any(needle in i.lower() for ids in r["record_ids"].values() for i in ids)]

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]

    all_rows = [_txn_row(g, s["store"]) for g in s["groups"]]
    filter_counts = {
        "all": len(all_rows),
        "matched": sum(1 for r in all_rows if r["status"] == "matched"),
        "exception": sum(1 for r in all_rows if r["status"] == "exception"),
    }
    return {"total": total, "page": page, "page_size": page_size, "filter_counts": filter_counts, "items": page_rows}


# ----------------------------------------------------------------------
# GET /transactions/{id}/audit -- side-panel multi-way comparison + decision tree
# ----------------------------------------------------------------------
@app.get("/transactions/{txn_id}/audit")
def transaction_audit(txn_id: str):
    s = _reload_if_needed()
    group = next((g for g in s["groups"] if g["id"] == txn_id), None)
    if group is None:
        raise HTTPException(404, f"no transaction with id {txn_id}")

    store = s["store"]
    member_ids = group["bank_ids"] + group["settlement_ids"] + group["ledger_ids"]
    per_record = {rid: store.get_record_by_id(rid) for rid in member_ids}

    decision_steps = []
    for rid, rec in per_record.items():
        for row in rec.get("audit_trail", []):
            decision_steps.append({
                "record_id": rid, "tier": row["tier"], "outcome": row["outcome"],
                "matched_against": json.loads(row["matched_against"]) if row.get("matched_against") else [],
                "confidence": row["confidence"], "reasoning": row["reasoning"],
                "exception_reason": row.get("exception_reason", ""),
            })
    decision_steps.sort(key=lambda d: (d["tier"], d["record_id"]))

    return {
        "transaction_id": txn_id, "status": "matched" if group["size"] > 1 else "exception",
        "comparison": {
            "bank": [per_record[i]["raw_record"] for i in group["bank_ids"]],
            "settlement": [per_record[i]["raw_record"] for i in group["settlement_ids"]],
            "ledger": [per_record[i]["raw_record"] for i in group["ledger_ids"]],
        },
        "decision_tree": decision_steps,
        "reasoning_summary": group.get("reasoning", ""),
    }


# ----------------------------------------------------------------------
# GET /exceptions -- Exceptions Queue screen
# ----------------------------------------------------------------------
@app.get("/exceptions")
def exceptions(reason_code: Optional[str] = None, min_age_days: Optional[int] = None,
               page: int = 1, page_size: int = 25):
    s = _reload_if_needed()
    store, res_store, as_of = s["store"], s["resolutions"], s["as_of_date"]
    resolutions = res_store.all()

    def _with_age(e: dict) -> dict:
        record_date = _record_date(store, e["record_id"], e["source"])
        age_days = days_between(as_of, record_date) if record_date and as_of else None
        return {**e, "record_date": record_date, "age_days": age_days}

    all_exceptions = [_with_age(e) for e in store.exceptions]

    by_reason: dict[str, dict] = {}
    for e in all_exceptions:
        b = by_reason.setdefault(e["reason_code"], {"reason_code": e["reason_code"], "count": 0, "value_at_risk_rupees": 0.0})
        b["count"] += 1
        b["value_at_risk_rupees"] += abs(e["amount"])
    summary = sorted(by_reason.values(), key=lambda b: -b["count"])
    for b in summary:
        b["value_at_risk_rupees"] = round(b["value_at_risk_rupees"], 2)

    items = all_exceptions
    if reason_code is not None:
        items = [e for e in items if e["reason_code"] == reason_code]
    if min_age_days is not None:
        items = [e for e in items if (e["age_days"] or 0) >= min_age_days]
    total = len(items)
    start = (page - 1) * page_size
    page_items = []
    for e in items[start:start + page_size]:
        r = resolutions.get(e["record_id"])
        page_items.append({**e, "resolved": bool(r), "resolution": r})

    return {
        "as_of_date": as_of,
        "summary": summary,
        "total_count": len(all_exceptions),
        "total_value_at_risk_rupees": round(sum(abs(e["amount"]) for e in all_exceptions), 2),
        "page": page, "page_size": page_size, "filtered_count": total,
        "items": page_items,
    }


class ResolveRequest(BaseModel):
    note: Optional[str] = None
    resolved_by: Optional[str] = None


@app.post("/exceptions/{record_id}/resolve")
def resolve_exception(record_id: str, body: ResolveRequest = ResolveRequest()):
    s = _reload_if_needed()
    if not any(e["record_id"] == record_id for e in s["store"].exceptions):
        raise HTTPException(404, f"no exception found for record {record_id}")
    entry = s["resolutions"].resolve(record_id, body.note, body.resolved_by)
    return {"status": "resolved", "record_id": record_id, "resolution": entry}


@app.post("/exceptions/{record_id}/unresolve")
def unresolve_exception(record_id: str):
    s = _reload_if_needed()
    removed = s["resolutions"].unresolve(record_id)
    return {"status": "unresolved" if removed else "was not resolved", "record_id": record_id}


# ----------------------------------------------------------------------
# GET /audit-log -- reconciliation run history
# ----------------------------------------------------------------------
@app.get("/audit-log")
def audit_log(limit: int = 50):
    path = OUTPUT_DIR / "run_history.jsonl"
    if not path.exists():
        return {"runs": []}
    lines = path.read_text(encoding="utf-8").splitlines()
    runs = [json.loads(l) for l in lines if l.strip()]
    runs.sort(key=lambda r: r.get("run_at", ""), reverse=True)
    return {"runs": runs[:limit]}


# ----------------------------------------------------------------------
# GET /forecast -- Task 7
# ----------------------------------------------------------------------
@app.get("/forecast")
def forecast(horizons: str = "7,14,30", as_of_date: Optional[str] = None):
    try:
        horizon_tuple = tuple(int(h.strip()) for h in horizons.split(","))
    except ValueError:
        raise HTTPException(400, "horizons must be a comma-separated list of integers, e.g. 7,14,30")
    result = compute_forecast(DATA_DIR, as_of_date=as_of_date, horizons=horizon_tuple)
    result["markdown"] = forecast_markdown(result)
    return result


# ----------------------------------------------------------------------
# GET /tax-summary -- Task 8
# ----------------------------------------------------------------------
@app.get("/tax-summary")
def tax_summary():
    s = _reload_if_needed()
    settlement = pipeline_loader.load_settlements(DATA_DIR)
    result_lite = {"settlement": settlement, "groups": s["groups"]}
    breakdown = compute_tax_breakdown(result_lite)
    breakdown["markdown"] = tax_markdown(breakdown)
    return breakdown
