# API

FastAPI layer connecting the reconciliation engine to a frontend dashboard.
Read-only against the pipeline's own output — hitting these endpoints never
re-runs Tier 4 AI and never burns LLM quota.

## Run it

```bash
pip install fastapi uvicorn
python run_reconciliation.py          # must run at least once first, to produce output/*.json
uvicorn api.main:app --reload --port 8006
```

CORS is locked to exactly `http://localhost:3007` (the frontend's Vite dev
server, see `frontend/vite.config.ts`) via `FRONTEND_ORIGIN` in `api/main.py`
— not a wildcard, since this API also exposes a mutating `POST` endpoint.
Running the frontend on a different port means updating that constant too.

## Frontend is now connected

`../frontend` (a React + Vite dashboard, originally built against static
mock data) is wired to these endpoints for real — see `frontend/README.md`
for what's genuinely live vs. still a mockup, and `frontend/src/types/index.ts`
for the TypeScript shapes mirroring every response below field-for-field.
`GET /exceptions` also returns a real, computed `age_days`/`record_date`
per item now (derived from the record's own transaction date vs. the
latest date in the batch) — not fabricated, same technique
`forecast/cash_forecast.py` already used for its `as_of_date`.

## Endpoint → screen mapping

| Endpoint | Screen | Notes |
|---|---|---|
| `GET /overview` | Overview | `match_rate_pct`, `reconciled_value_rupees` / `total_value_rupees` / `reconciled_value_pct`, `value_at_risk_rupees`, `open_exceptions_count`, `precision_pct` / `recall_pct` / `false_match_rate_pct`, `tier_breakdown` (tier name -> count), `per_source` (per-source match rate) |
| `GET /transactions` | Transaction Matching (table) | Query params: `status` (`matched`/`exception`), `source` (`bank`/`settlement`/`ledger`), `search` (substring on any record id), `page`, `page_size`. Each row is one reconciliation **group** (not one raw record) — `bank`/`settlement`/`ledger` hold the raw record(s) on each side, `null` if that source has no leg. `filter_counts` gives the chip counts (`all`/`matched`/`exception`) computed over the *unfiltered* set, for filter-chip badges. |
| `GET /transactions/{id}/audit` | Transaction side panel | `{id}` is a transaction id from `/transactions` (`grp_00000`, ...), not a raw record id. `comparison` gives the bank/settlement/ledger rows side by side (multi-way comparison). `decision_tree` is every tier-by-tier audit event across every record in the group, in tier order — this is the "rule resolution decision tree." |
| `GET /exceptions` | Exceptions Queue | Query params: `reason_code`, `min_age_days`, `page`, `page_size`. `summary` is the per-reason-code breakdown for filter chips (count + value at risk). `items` is the paginated worklist; each item carries `age_days`/`record_date` (real, computed vs. `as_of_date`) and `resolved`/`resolution` merged in from persisted human resolutions. |
| `POST /exceptions/{record_id}/resolve` | "Mark Resolved" button | Body: `{"note": "...", "resolved_by": "..."}` (both optional). Persists to `output/resolutions.json` — **not** wiped by re-running the pipeline (see Task 9 / idempotency in the main README). |
| `POST /exceptions/{record_id}/unresolve` | undo action, if the UI wants one | Removes the persisted resolution. |
| `GET /audit-log` | Audit Log (run history) | One entry per `run_reconciliation.py` invocation (append-only, `output/run_history.jsonl`), newest first. Distinct from the per-record audit trail used by `/transactions/{id}/audit`. |
| `GET /forecast` | (Task 7) forward cash forecast | Query params: `horizons` (comma-separated days, default `7,14,30`), `as_of_date` (defaults to the latest date seen in the data). Includes an `overdue` bucket for pending settlements whose projected date has already passed `as_of_date` — see the main README for why that matters. |
| `GET /tax-summary` | (Task 8) tax-line breakdown | GST/TDS/fee captured, split into reconciled vs unreconciled, plus any detected `tax_variance_records`. |

## Resolutions are separate from the pipeline's own state

`output/report.json`, `output/groups.json`, `output/exceptions.json`, and
`output/audit_trail.db` are all overwritten wholesale every time
`run_reconciliation.py` runs — that's intentional, a fresh run is a fresh
statement of what the *pipeline* currently believes. `output/resolutions.json`
is the one piece of state this API owns and the pipeline never touches, so a
human marking something resolved survives every subsequent pipeline re-run.
