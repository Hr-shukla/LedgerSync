"""Tier 5: exception classification.

Everything that survives Tiers 1-4 unmatched lands here with an actionable
reason code -- the report must be a worklist, not a dump.
"""
from __future__ import annotations

from . import config

REASON_CODES = (
    "duplicate_suspected",
    "chargeback_dispute",
    "amount_mismatch_beyond_tolerance",
    "low_ai_confidence",
    "ai_rejected_no_match",
    "ai_unavailable_needs_review",
    "no_counterpart_found",
    "refund_no_ledger_expected",
)


def classify(is_chargeback: bool = False, ai_result: dict | None = None,
             had_any_candidate: bool = False, amount_mismatch_only: bool = False) -> tuple[str, str]:
    if is_chargeback:
        return "chargeback_dispute", "settlement flagged as chargeback/dispute; no bank or ledger leg expected"
    if amount_mismatch_only:
        return "amount_mismatch_beyond_tolerance", "reference matched but amount fell outside the configured tolerance"
    if ai_result is not None:
        if ai_result.get("unavailable"):
            return "ai_unavailable_needs_review", ai_result.get("reasoning", "AI tier unavailable")
        if ai_result.get("match") and ai_result.get("confidence", 0.0) < config.AI_CONFIDENCE_THRESHOLD:
            return ("low_ai_confidence",
                    f"AI suggested a match at confidence {ai_result.get('confidence', 0):.2f}, "
                    f"below the {config.AI_CONFIDENCE_THRESHOLD} threshold: {ai_result.get('reasoning', '')}")
        if not ai_result.get("match"):
            return "ai_rejected_no_match", ai_result.get("reasoning", "AI reviewed candidates and found no confident match")
    if not had_any_candidate:
        return "no_counterpart_found", "no plausible candidate found in any other source within tolerance/date window"
    return "no_counterpart_found", "candidates existed but none cleared the matching bar"
