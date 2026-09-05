"""Ground-truth-free metrics computed purely from the pipeline's own output:
match rate, rupee value reconciled vs total, exception breakdowns by tier and
reason. These numbers must stand on their own -- no peeking at ground truth.
"""
from __future__ import annotations

from collections import Counter


def _group_value(g: dict, bank: dict, settlement: dict, ledger: dict) -> float:
    if g["ledger_ids"]:
        return sum(ledger[l]["invoice_amount"] for l in g["ledger_ids"])
    if g["settlement_ids"]:
        return sum(abs(settlement[s]["gross_amount"]) for s in g["settlement_ids"])
    return sum(abs(bank[b]["amount"]) for b in g["bank_ids"])


def compute(result: dict) -> dict:
    bank, settlement, ledger = result["bank"], result["settlement"], result["ledger"]
    groups = result["groups"]
    exceptions = result["exceptions"]

    matched_groups = [g for g in groups if g["size"] > 1]
    singleton_groups = [g for g in groups if g["size"] == 1]

    total_value = sum(_group_value(g, bank, settlement, ledger) for g in groups)
    reconciled_value = sum(_group_value(g, bank, settlement, ledger) for g in matched_groups)
    exception_value = total_value - reconciled_value

    per_source = {}
    for name, records, claimed_fn in (
        ("bank", bank, lambda rid: any(rid in g["bank_ids"] for g in matched_groups)),
        ("settlement", settlement, lambda rid: any(rid in g["settlement_ids"] for g in matched_groups)),
        ("ledger", ledger, lambda rid: any(rid in g["ledger_ids"] for g in matched_groups)),
    ):
        total = len(records)
        matched = sum(1 for rid in records if claimed_fn(rid))
        per_source[name] = {
            "total_records": total, "matched_records": matched,
            "match_rate_pct": round(100 * matched / total, 2) if total else 0.0,
        }

    tier_counts = Counter()
    for g in matched_groups:
        for t in g["tiers"]:
            tier_counts[t] += 1

    reason_counts = Counter(e["reason_code"] for e in exceptions)
    reason_value = Counter()
    for e in exceptions:
        reason_value[e["reason_code"]] += abs(e["amount"])

    total_records = len(bank) + len(settlement) + len(ledger)
    total_matched_records = sum(g["size"] for g in matched_groups)

    return {
        "total_records": total_records,
        "per_source": per_source,
        "overall_match_rate_pct": round(100 * total_matched_records / total_records, 2) if total_records else 0.0,
        "matched_group_count": len(matched_groups),
        "exception_group_count": len(singleton_groups),
        "total_value_rupees": round(total_value, 2),
        "reconciled_value_rupees": round(reconciled_value, 2),
        "reconciled_value_pct": round(100 * reconciled_value / total_value, 2) if total_value else 0.0,
        "exception_value_rupees": round(exception_value, 2),
        "tier_usage_across_matched_groups": dict(tier_counts),
        "exception_count_by_reason": dict(reason_counts),
        "exception_value_by_reason": {k: round(v, 2) for k, v in reason_value.items()},
        "ai_available": result["ai_available"],
        "ai_calls_made": result["ai_calls_made"],
        "ai_candidates_evaluated": result.get("ai_candidates_evaluated", result["ai_calls_made"]),
        "ai_provider": result.get("ai_provider"),
    }
