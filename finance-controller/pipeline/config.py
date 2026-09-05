"""Central tolerances and thresholds for the matching pipeline.

Keeping every magic number here means the report can print exactly what
policy produced a given match, and tests can assert against the same
constants instead of duplicating literals.
"""

# ---- amount tolerances (in rupees) ----
# Bank amount vs settlement net_amount: these should be identical up to paise
# rounding differences injected in the "rounding_diff" case (+/- 0.02).
NET_VS_NET_TOLERANCE = 0.05

# Settlement gross_amount vs ledger invoice_amount: should be exactly equal
# (no fees applied yet), small epsilon for float drift only.
GROSS_VS_GROSS_TOLERANCE = 0.02

# Fee/TDS/GST model used when estimating a plausible net range for a gross
# amount without a settlement leg to explain it (Tier 2 "computed fee/tax
# tolerance" fallback for bank<->ledger direct comparison).
RAZORPAY_FEE_RATE = 0.02
FEE_GST_RATE = 0.18
TDS_RATE = 0.01
# total shrink factor applied to gross to estimate net
NET_OF_GROSS_FACTOR = 1 - (RAZORPAY_FEE_RATE * (1 + FEE_GST_RATE)) - TDS_RATE
# allow some slack around the modelled fee rate since real fee schedules vary
FEE_MODEL_SLACK = 0.03  # +/- 3% of gross

# ---- date windows (days) ----
DATE_WINDOW_TIER2 = 5          # bank vs settlement, settlement vs ledger (tight)
DATE_WINDOW_TIER3_BANK = 6     # subset-sum grouping window on bank<->settlement
DATE_WINDOW_TIER3_LEDGER = 40  # partial payments can straggle across weeks

# ---- fuzzy string matching (Tier 2) ----
UTR_FUZZY_THRESHOLD = 65  # rapidfuzz partial_ratio score (0-100) to consider a mangled UTR match

# ---- grouping / subset-sum (Tier 3) ----
MAX_SUBSET_SIZE = 4  # brief calls for a small bounded window, not brute force over everything
MAX_CANDIDATE_POOL = 14  # cap on candidates considered per subset-sum search (after date prefilter)

# ---- Tier 4 AI-assisted resolution ----
AI_CONFIDENCE_THRESHOLD = 0.75  # below this, goes to exceptions even if AI says "match"
AI_MODEL = "claude-sonnet-4-5-20250929"          # used when ANTHROPIC_API_KEY is present
GEMINI_MODEL = "gemini-flash-lite-latest"        # used when GEMINI_API_KEY/GOOGLE_API_KEY is present instead
# Google's free tier caps each model at a small number of requests/day
# (observed: 20/day on gemini-flash-latest). If the primary model's quota is
# exhausted mid-run, fall through to these in order rather than failing the
# whole Tier 4 pass -- each is billed against its own separate quota bucket.
GEMINI_MODEL_FALLBACKS = ["gemini-3.1-flash-lite", "gemini-flash-latest"]
GROQ_MODEL = "openai/gpt-oss-120b"               # used when GROQ_API_KEY is present instead
# Fallback if the primary model is rate-limited or deprecated. Groq model
# names change fairly often (check https://console.groq.com/docs/models for
# the current list) -- both of these were verified live and support forced
# tool-call output as of this writing.
GROQ_MODEL_FALLBACKS = ["openai/gpt-oss-20b"]
AI_MAX_CANDIDATES = 6  # cap candidates shown to the model per ambiguous record
# how loose a mismatch can be before we bother spending an AI call on it at all
AI_TRIGGER_AMOUNT_RATIO = 0.25   # candidate amount within 25% of target
AI_TRIGGER_DATE_WINDOW = 15      # or date within 15 days

# ---- reconciliation completeness ----
# minimum overall match rate / precision the regression test suite enforces
BASELINE_MATCH_RATE = 0.80
BASELINE_PRECISION = 0.97
