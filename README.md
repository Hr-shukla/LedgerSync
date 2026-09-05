# LedgerSync — AI Finance Controller

A real, runnable reconciliation agent for a Razorpay-style payments business,
plus a live dashboard on top of it. Closes the loop across three sources a
finance team normally cross-checks by hand — **bank statement**, **Razorpay
settlement report**, and **internal ledger** — using a tiered cascade (cheap
deterministic rules first, AI only for what's genuinely ambiguous), and
reports its own match rate, ₹ reconciled, exceptions, and precision/recall
against a hidden ground truth. No cherry-picked data: the dataset is
generated fresh with deliberately injected edge cases every run.

```
93.42% match rate  |  100% precision  |  100% recall  |  0% false-match rate
₹95.7L reconciled / ₹1.13Cr total  |  Tier 4 AI: Groq (live)
```
(from an actual run — reproduce it yourself, see below)

## Structure

```
LedgerSync/
├── finance-controller/    Python backend — pipeline, FastAPI, tests
└── frontend/              React + Vite dashboard, wired to real backend data
```

Each has its own README with full detail:
- **[finance-controller/README.md](finance-controller/README.md)** — architecture, the 5-tier matching cascade, multi-provider AI (Claude/Gemini/Groq), adversarial robustness, multi-seed validation, idempotency guarantees
- **[finance-controller/api/README.md](finance-controller/api/README.md)** — API endpoint reference
- **[frontend/README.md](frontend/README.md)** — dashboard setup, what's real vs. still a mockup

## Quick start (both halves, in order)

```bash
# 1. Backend
cd finance-controller
pip install -r requirements.txt
python run_reconciliation.py --regenerate
uvicorn api.main:app --reload --port 8006

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open the dashboard at the port Vite prints (`vite.config.ts`), then set
`frontend/.env.local` → `VITE_API_BASE_URL=http://localhost:8006` if it
doesn't already point at your backend port.

Set `GEMINI_API_KEY`, `GROQ_API_KEY`, or `ANTHROPIC_API_KEY` in
`finance-controller/.env` to enable Tier 4 AI resolution — without one, the
pipeline still runs correctly and reports itself honest about what it
couldn't resolve.

## What's real here

- **The dashboard is wired to real data**, not mocks — every screen (Overview,
  Transactions, Exceptions Queue, Audit Log) reads live from the backend, with
  actual loading/error states if it's unreachable.
- **Mark Resolved** and **Run Reconcile** are real actions — they call real
  endpoints and re-run the real pipeline, not simulated progress bars.
- **The AI claim is proven, not asserted**: an adversarial decoy pair is
  injected into every dataset specifically to bait a false match, and the
  live LLM call rejecting it is shown verbatim in the generated report.
- **Not a single cherry-picked run**: `scripts/multi_seed_eval.py` validates
  across 8 independent seeds — 100% precision and 0% false-match rate held
  in every one.

Everything else — what's still a UI mockup, which buttons are honestly
disabled rather than faked, the full tier-by-tier architecture — is in the
two sub-READMEs linked above.
