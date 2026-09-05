# LedgerSync Frontend

React + Vite + TypeScript dashboard for the AI Finance Controller reconciliation
engine. Connects to the FastAPI backend in `../finance-controller/api/main.py`
for all real data — no mock data on the four main screens (Overview,
Transactions, Exceptions Queue, Audit Log).

## Running it locally

You need both the backend and this frontend running at the same time.

**1. Backend** (from `finance-controller/`):

```bash
pip install -r requirements.txt
python run_reconciliation.py          # must run at least once to produce output/*.json
uvicorn api.main:app --reload --port 8006
```

The port is arbitrary — pick any free one. If 8000 is already taken by
something else on your machine (a stray leftover process, WSL/Hyper-V port
reservations, etc. can make Windows refuse the bind with `WinError 10013`),
just use a different port here and match it in `.env.local` below.

**2. Frontend** (from `frontend/`):

```bash
npm install
npm run dev
```

Opens on **http://localhost:3007** (pinned via `strictPort` in
`vite.config.ts` — it'll fail loudly instead of silently jumping to another
port if 3007 is taken, so it never silently drifts out of sync with the
backend's CORS allowlist). The
backend's CORS policy is locked to exactly this origin (`api/main.py`,
`FRONTEND_ORIGIN`) — if you run the dev server on a different port, update
that constant too, or CORS will silently block every request.

## Configuring the API base URL

The frontend reads the backend's URL from `VITE_API_BASE_URL`, defaulting to
`http://localhost:8000` if unset (`src/lib/api.ts`). This project currently
ships a `.env.local` pointing at **`http://localhost:8006`** to match the
backend command above — to point at a different backend:

```bash
# edit .env.local: VITE_API_BASE_URL=http://your-backend-host:PORT
```

Vite picks up `.env.local` automatically; restart `npm run dev` after
changing it.

## What's real vs. what's still a mockup

The four screens wired to `src/lib/api.ts` (Overview, Transactions,
Exceptions Queue, Audit Log) show only real backend data, with loading
spinners and error states if the backend is unreachable. A few things from
the original design have **no backend behind them yet** and are visibly
disabled (not silently no-op'd) rather than faked:

- Overview: "Export Executive Summary", "Run Reconcile"
- Transactions: "Re-run Confidence Model", "Flag for Re-check", "Unlink Sources"
- Exceptions: per-item "Escalate", and any assignee/reviewer field (no assignment tracking exists yet)
- The "Ledger Impact" journal tab and any HMAC/Merkle "cryptographic integrity" UI were removed entirely — there's no double-entry bookkeeping or hashing in the backend to back them

The **Data Sources / Reconciliation Rules / Settings** pages, the entity
switcher in the sidebar, and a handful of decorative modals (Compliance
checklist, Merkle verify, global search, keyboard shortcuts, reconcile
progress animation) were out of scope for this pass and still run on
`src/data/mockData.ts` / `src/types/legacy.ts` — untouched, and not
connected to the backend.

## What's genuinely wired up

- **Mark Resolved / Reopen** on the Exceptions Queue calls the real
  `POST /exceptions/{id}/resolve` and `/unresolve` endpoints and updates the
  UI immediately, no page reload.
- **Bulk Resolve** loops the same real endpoint over each selected exception.
- **CSV / JSON exports** (Matching Report, Export Exceptions, Download Run
  History) are real client-side exports of whatever's currently loaded —
  not backend-generated files, but not fabricated data either.
- The Transactions side panel's decision tree and multi-way comparison come
  straight from `GET /transactions/{id}/audit`'s real `decision_tree` and
  `comparison` fields — including the tier-by-tier reasoning text the
  pipeline (or Tier 4's LLM call) actually produced.

## Type contract

`src/types/index.ts` mirrors the backend's actual JSON shapes field-for-field
(not an aspirational contract) — if you change a response shape in
`api/main.py`, update the matching interface here in the same change.
