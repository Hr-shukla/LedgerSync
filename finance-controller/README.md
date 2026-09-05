# AI Finance Controller — Multi-Source Reconciliation Agent

A real, runnable reconciliation pipeline for a Razorpay-style payments business.
It reconciles three sources that a finance team normally cross-checks by hand —
**bank statement**, **Razorpay settlement report**, and **internal ledger** —
using a tiered cascade (cheap deterministic rules first, AI only for what's
genuinely ambiguous), and reports its own match rate, ₹ reconciled, exceptions,
and precision/recall against a hidden ground truth. No cherry-picked data: the
dataset is generated fresh with deliberately injected edge cases every run.

## Quick start

```bash
pip install -r requirements.txt
python run_reconciliation.py                 # fixed seed (42), reproducible
python run_reconciliation.py --regenerate     # force fresh synthetic data
python run_reconciliation.py --seed 7 --groups 60   # bigger batch, different seed
pytest tests/ -v                              # edge-case suite + regression guard
```

Every run executes the pipeline **twice**: once with Tier 4 explicitly
disabled (the honest baseline) and once with it enabled if a key is
configured, so the report can show exactly what the AI tier added instead of
just asserting it works.

Set one of these in the environment, or in a local `.env` file (never
committed, never printed) to enable Tier 4. **Checked in this priority order
— the first one found wins:**

1. `ANTHROPIC_API_KEY` — Claude, forced tool-call for structured output
2. `GEMINI_API_KEY` / `GOOGLE_API_KEY` — Gemini, `responseSchema` JSON mode
3. `GROQ_API_KEY` — Groq, OpenAI-compatible forced tool-call output (see below)

Set `FORCE_AI_PROVIDER=anthropic` / `gemini` / `groq` to pin a specific
provider regardless of that priority order — useful for verifying each path
independently when more than one key is configured, without having to unset
the others.

Without any key configured, the pipeline still runs completely and
correctly — records that need AI reasoning are honestly routed to an
`ai_unavailable_needs_review` exception instead of being guessed at.

**Why Groq is the most demo-friendly option:** it's the lowest-latency of
the three (sub-2-second responses observed) and its free tier is generous —
at time of writing, live-observed limits on the default model
(`openai/gpt-oss-120b`) were 1000 requests per rate-limit window with an
8000-token-per-window budget (check `x-ratelimit-*` response headers or
the Groq console for current numbers, since these change). A typical
Tier-4 pass on one generated batch makes well under 10 calls, so this
comfortably covers a live demo — but check the actual per-run call count
(printed by `run_reconciliation.py` and in `report.md`) against whatever
Groq's current limits are before relying on it live, especially if running
the multi-seed sweep. Both Google's and Groq's free tiers can hit rate
limits or per-model quota exhaustion mid-run; Tier 4 handles this the same
way for both providers — self-throttled request spacing, retry with
backoff on transient errors, and automatic fallback to a secondary model
(`pipeline/config.py`: `GEMINI_MODEL_FALLBACKS`, `GROQ_MODEL_FALLBACKS`)
rather than failing the run. Model names on all three providers get
renamed/deprecated over time — if a default stops working, check each
provider's current model list and update `pipeline/config.py`.

Output lands in `output/`:
- `report.md` — human-readable report: AI-enabled headline, no-AI baseline comparison, which records Tier 4 resolved (with its reasoning verbatim), match rate, ₹ reconciled, exceptions, grading
- `report.json` — the same data, machine-readable
- `audit_trail.db` — SQLite audit trail, one row per record per tier decision
- `audit_trail.jsonl` — the same audit trail as JSON Lines
- `multi_seed_report.md` / `.json` — match rate / precision / recall / false-match rate range across multiple seeds (`python scripts/multi_seed_eval.py`), not a single cherry-picked run

## Why the ledger has no direct link to the settlement

The data generator deliberately does **not** export an `invoice_ref` on the
settlement rows or a `payment_ref` on the ledger rows, even though those
fields exist in-memory while ground truth is built. A real merchant's
accounting ledger doesn't know Razorpay's internal payment ID, and a real
settlement export doesn't know your invoice numbering. Handing the matcher a
direct foreign key would trivialize exactly the part of this problem the
brief calls "the hardest and most differentiating" — many-to-one / one-to-many
grouping. Bank↔settlement linking uses the UTR (a real bridge ID present in
both bank narration and settlement reports); settlement↔ledger linking has to
be earned via amount, date, and subset-sum grouping, the way a human reconciler
actually does it.

## Architecture

```
finance-controller/
  data_generator/generate.py    -- seeded synthetic data + hidden ground truth
  pipeline/
    env.py                       -- minimal local .env loader (never committed, never printed)
    loader.py                    -- CSV -> dict records
    config.py                    -- every tolerance/threshold in one place
    fees.py                      -- fee/TDS/GST tolerance model
    grouping.py                  -- bounded subset-sum search + union-find
    bank_settlement.py           -- Tier 1-3 for bank <-> settlement
    settlement_ledger.py         -- Tier 2-3 for settlement <-> ledger
    ai_tier.py                   -- Tier 4: Claude, Gemini, or Groq -- structured/schema-forced output
    exceptions.py                -- Tier 5: reason-code classification
    orchestrator.py              -- runs all tiers, merges into 3-way groups (union-find)
  audit/store.py                 -- SQLite + JSONL audit trail writer/reader
  report/
    metrics.py                   -- match rate / rupee reconciled / exceptions (no ground truth)
    grading.py                   -- precision/recall/false-match rate vs hidden ground truth
    generate.py                  -- JSON + Markdown report, with-AI vs without-AI comparison
  scripts/multi_seed_eval.py     -- runs the pipeline across many seeds, reports the range
  tests/                         -- pytest edge-case suite, adversarial-decoy test, regression guard
  run_reconciliation.py          -- single entrypoint
```

### The 5-tier cascade

1. **Exact match** — bank UTR == settlement UTR, string equality. Also where
   duplicate settlement re-exports (identical payment_id/UTR/amount) are
   detected and de-duplicated, keeping only the lower-ID row as canonical.
2. **Deterministic fuzzy match** — mangled/truncated UTR on the bank leg
   (`rapidfuzz.fuzz.partial_ratio`) corroborated by amount-within-tolerance and
   a date window; on the settlement↔ledger side, gross amount vs invoice
   amount with nearest-date tie-breaking (handles two invoices that happen to
   share an amount on nearly the same day — the "near-duplicate trap").
3. **Many-to-one / one-to-many grouping** — bounded subset-sum search
   (`itertools.combinations`, capped candidate pool, capped subset size) for
   aggregated settlements (N settlements → 1 bank credit), split settlements
   (1 settlement → N bank credits), and partial payments (N settlements →
   1 invoice).
4. **AI-assisted resolution** — for records Tiers 1-3 couldn't place but that
   have at least one plausible nearby candidate, whichever of Claude, Gemini,
   or Groq is configured (see priority order below) is given structured
   context (amounts, dates, references, the learned fee/TDS/GST deduction
   pattern) and forced to return a typed decision — a tool call for Claude
   and Groq (Groq via its OpenAI-compatible `tool_choice`-forced function
   call), a `responseSchema`-constrained JSON response for Gemini — never
   free text. All three are normalized into the exact same
   `{match, matched_ids, confidence, reasoning}` shape before
   `orchestrator.py` ever sees them, so it doesn't need to know which
   provider actually answered. Anything below
   `AI_CONFIDENCE_THRESHOLD` (default 0.75) does **not** count as a match. The
   candidate pool is built and a real resolution attempt is made even when no
   key is configured (the call just returns "unavailable" instead of hitting
   the network) -- this is what lets `tests/test_adversarial_decoy.py` prove
   the adversarial decoy pair is genuinely evaluated, not filtered out early.
5. **Exception classification** — everything still unresolved gets an
   actionable reason code: `no_counterpart_found`, `duplicate_suspected`,
   `chargeback_dispute`, `refund_no_ledger_expected`, `low_ai_confidence`,
   `ai_rejected_no_match`, `ai_unavailable_needs_review`.

Bank↔settlement and settlement↔ledger are matched independently, then merged
into final 3-way groups with a union-find over the two edge sets — this is
what lets a partial payment (3 settlements ↔ 1 invoice) and each settlement's
own bank credit (1↔1) collapse into one coherent transaction group.

### Edge cases injected into every generated batch

Clean 1:1 matches (baseline), fee/TDS/GST deductions, timing lag, partial
payments, aggregated settlements, split settlements, duplicate settlement
exports, refunds/reversals, paise-level rounding differences, mangled/missing
UTRs, orphan bank credits, unpaid invoices, near-duplicate amount traps,
chargebacks, a reference-degraded case solvable only by Tier 4 reasoning, and
an adversarial decoy pair engineered to bait a false match.

## Honesty mechanisms (why the numbers can be trusted)

- **Hidden ground truth**: `data/ground_truth.jsonl` is written by the
  generator but never read by the matching pipeline — only by
  `report/grading.py`, after the pipeline has already produced its output.
- **Grading distinguishes wrong from incomplete**: a predicted group that
  exactly matches ground truth is an exact recovery; a predicted group that's
  a correct subset of a true group (e.g. settlement↔ledger linked correctly
  but the bank leg is still open because Tier 4 is unavailable) is a *partial*
  match — it counts against recall but never against precision, because it
  isn't wrong, just incomplete. Only a group that actually combines records
  from two different real transactions counts as a false merge.
- **No hallucinated matches**: Tier 4 requires forced structured output --
  a tool call for Claude and Groq, a `responseSchema`-constrained response
  for Gemini -- and anything below the confidence threshold is routed to
  exceptions. With no API key configured, the tier reports itself
  unavailable and the affected records go to `ai_unavailable_needs_review`
  instead of being silently matched or dropped. The API key itself is also
  never allowed to leak, for any of the three providers: it's passed via
  header (never a URL) and any error message is
  scrubbed before it can reach the audit trail or a report.
- **Regression guard**: `tests/test_end_to_end_regression.py` runs the full
  pipeline on the fixed seed-42 dataset and fails the build if match rate,
  precision, or false-match rate regress past the baselines in
  `pipeline/config.py`.

## Sample output (seed=42, 40 base groups, Tier 4 via Gemini)

```
HEADLINE (Tier 4 / AI enabled, provider=gemini):
  Overall record-level match rate: 93.42%
    bank: 76/82 matched (92.68%)   settlement: 79/85 matched (92.94%)   ledger: 72/76 matched (94.74%)
  Rupee value reconciled: Rs 9,573,154.96 / Rs 11,337,775.56 (84.44%)
  Precision: 100.0%   Recall: 100.0%   False-match rate: 0.0%
  Records resolved only because of Tier 4: 2 (real Gemini calls, reasoning shown verbatim in report.md)

BASELINE (Tier 4 disabled, Tiers 1-3-5 only):
  Overall record-level match rate: 92.59%
  Precision: 100.0%   Recall: 97.1%   False-match rate: 0.0%
```

This is one run, not the whole story — see **Multi-seed validation** below for
the range across 8 different seeds.

The gap between baseline and headline recall is exactly the two
`ai_needed_degraded_reference` cases: a reference too degraded for
deterministic fuzzy matching plus a small unmodelled bank charge, solvable
only by an LLM reasoning over amount+date+partial-reference evidence. Without
a key, they're honestly left open (`ai_unavailable_needs_review`) rather than
guessed at.

Run `python run_reconciliation.py` yourself to reproduce the baseline exactly
(seeded generation); the AI-enabled numbers will vary slightly run-to-run
since LLM judgment isn't deterministic (see below).

### Multi-seed validation (not one cherry-picked run)

```bash
python scripts/multi_seed_eval.py                # default: seeds 1,7,13,21,33,42,55,88, Tier 4 enabled
python scripts/multi_seed_eval.py --no-ai         # faster, offline baseline-only sweep
```

Real result across all 8 default seeds, Tier 4 enabled (`output/multi_seed_report.md`):

| Metric | Min | Max | Mean | Std Dev |
|---|---|---|---|---|
| Match rate | 93.00% | 93.55% | 93.36% | 0.17% |
| Precision | 100.0% | 100.0% | 100.0% | 0.0% |
| Recall (full) | 98.6% | 100.0% | 99.8% | 0.5% |
| False-match rate | 0.0% | 0.0% | 0.0% | 0.0% |

**Precision and false-match rate are rock solid at 100%/0% across every seed** —
the "no hallucinated matches" bias holds under repetition. Recall has a small
natural variance (98.6%–100%) because the same ambiguous case doesn't always
get the same LLM judgment call twice; this is reported, not hidden, and the
script explicitly flags (rather than suppresses) any seed that would drop
below the precision baseline in `pipeline/config.py`.

### Adversarial robustness

Every run's `report.md` includes an **Adversarial Robustness** section that
pulls the decoy pair's actual audit trail out of that run: whether it reached
Tier 4, the AI's verbatim reasoning for rejecting it, and confirmation it was
never cross-matched. `tests/test_adversarial_decoy.py` asserts this
mechanically (candidate pool built, genuinely evaluated, correctly rejected)
on every `pytest` run, offline; an opt-in live variant
(`RUN_LIVE_AI_TESTS=1 pytest tests/test_adversarial_decoy.py`) re-verifies it
against a real LLM call without spending quota on every normal test run.

## Beyond reconciliation

- **Settlement Q&A agent** (`python qa_agent.py "why didn't STL000167 reconcile?"`) —
  answers natural-language questions by giving an LLM tool-call access to the
  audit trail and report (`qa/tools.py`: `get_record_by_id`,
  `get_exceptions_by_reason`, `get_total_value_at_risk`,
  `get_records_by_date_range`, `get_match_rate_by_source`). Every answer is
  checked afterward for any record ID that didn't actually come from a tool
  result (`--trace` shows the tool calls made).
- **Backend API** (`uvicorn api.main:app --reload`) — Overview/Transactions/
  Exceptions/Audit-Log/Forecast/Tax-Summary endpoints, now genuinely wired up
  to a real React dashboard at `../frontend` (see `api/README.md` and
  `frontend/README.md` for the endpoint-to-screen mapping and what's real vs.
  still a mockup). CORS is locked to the frontend's exact dev origin, not a
  wildcard. Exception resolutions persist in `output/resolutions.json`,
  independent of the pipeline's own (overwritten-every-run) output.
- **Forward cash forecaster** (`forecast/cash_forecast.py`, `GET /forecast`) —
  projects 7/14/30-day cash inflow from pending settlements using nothing but
  the empirical historical settlement-to-bank-credit lag distribution. No ML,
  no smoothing — just observed lag + date arithmetic, with an explicit
  `overdue` bucket for pending settlements already past their projected date
  rather than silently dropping them.
- **Tax-line breakdown** (`report/tax_breakdown.py`, `GET /tax-summary`) —
  aggregates GST/TDS/fee captured, splits reconciled vs unreconciled, and
  flags any settlement whose recorded deduction doesn't match its own
  formula-expected value as `tax_variance_unreconciled`.

## Idempotency: safe to run on a schedule

`tests/test_idempotency.py` proves three things by actually running the
pipeline twice against the same fixed dataset: match rate/precision/recall
come out identical both times, the audit trail is fully replaced (not
appended to) each run so it never accumulates duplicate rows, and a human's
exception resolution in `output/resolutions.json` survives a pipeline re-run
untouched — only an explicit `/exceptions/{id}/unresolve` call changes it.
This is what makes it safe to wire `run_reconciliation.py` into a daily or
hourly schedule rather than a one-shot script.
