"""Settlement <-> Ledger matching: Tiers 2-3.

There is no shared reference ID between these two sources by design (see the
data generator's note on why invoice_ref/payment_ref are withheld) -- exactly
like a real merchant whose accounting ledger doesn't know the gateway's
internal payment ID. So Tier 1 (exact reference match) does not apply here;
matching starts at Tier 2, using gross_amount vs invoice_amount plus date
proximity, with subset-sum grouping in Tier 3 for partial payments.
"""
from __future__ import annotations

from . import config
from .fees import gross_vs_gross_match
from .grouping import find_subset_matches
from .models import MatchEvent, days_between


class SettlementLedgerResult:
    def __init__(self):
        self.edges = []
        self.audit: list[MatchEvent] = []
        self.claimed_settlement: set[str] = set()
        self.claimed_ledger: set[str] = set()

    def add_edge(self, settlement_ids, ledger_ids, tier, confidence, reasoning):
        self.edges.append({
            "settlement_ids": list(settlement_ids), "ledger_ids": list(ledger_ids),
            "tier": tier, "confidence": confidence, "reasoning": reasoning,
        })
        for sid in settlement_ids:
            self.claimed_settlement.add(sid)
            self.audit.append(MatchEvent(sid, "settlement", tier, "matched", list(ledger_ids), confidence, reasoning))
        for lid in ledger_ids:
            self.claimed_ledger.add(lid)
            self.audit.append(MatchEvent(lid, "ledger", tier, "matched", list(settlement_ids), confidence, reasoning))


def run_tier2(settlement: dict, ledger: dict, result: SettlementLedgerResult) -> None:
    """Deterministic 1:1 match on gross amount + nearest date. When several
    ledger rows tie on amount (the 'near-duplicate trap'), disambiguate by
    picking the strictly closest date rather than the first candidate found --
    a naive amount-only matcher would get this wrong."""
    remaining_ledger = [l for l in ledger if l not in result.claimed_ledger]

    # process settlements in a stable, deterministic order
    for sid in sorted(settlement, key=lambda s: settlement[s]["settlement_date"]):
        if sid in result.claimed_settlement:
            continue
        srow = settlement[sid]
        if srow.get("chargeback"):
            continue  # chargebacks have no ledger counterpart by construction
        scored = []
        for lid in remaining_ledger:
            if lid in result.claimed_ledger:
                continue
            lrow = ledger[lid]
            if not gross_vs_gross_match(srow["gross_amount"], lrow["invoice_amount"]):
                continue
            d = days_between(srow["settlement_date"], lrow["invoice_date"])
            if d > config.DATE_WINDOW_TIER2:
                continue
            scored.append((d, lid))
        if not scored:
            continue
        scored.sort(key=lambda t: t[0])
        best_d, best_lid = scored[0]
        # ambiguous only if a second candidate ties on date proximity too
        tied = len(scored) > 1 and scored[1][0] == best_d
        if tied:
            continue  # leave for Tier 4 -- genuinely ambiguous, don't guess
        reasoning = (
            f"gross amount {srow['gross_amount']:.2f} matches invoice {best_lid} "
            f"({ledger[best_lid]['invoice_amount']:.2f}); dates {best_d}d apart"
        )
        result.add_edge([sid], [best_lid], "tier2_fuzzy", 0.95, reasoning)


def run_tier3(settlement: dict, ledger: dict, result: SettlementLedgerResult) -> None:
    """Partial payments: several settlement gross amounts summing to one
    ledger invoice amount, spread over a wider date window."""
    remaining_settlement = [s for s in settlement if s not in result.claimed_settlement
                             and not settlement[s].get("chargeback")]
    for lid in list(ledger):
        if lid in result.claimed_ledger:
            continue
        lrow = ledger[lid]
        pool = [s for s in remaining_settlement
                if s not in result.claimed_settlement
                and days_between(lrow["invoice_date"], settlement[s]["settlement_date"]) <= config.DATE_WINDOW_TIER3_LEDGER]
        pool.sort(key=lambda s: days_between(lrow["invoice_date"], settlement[s]["settlement_date"]))
        candidates = [(s, settlement[s]["gross_amount"]) for s in pool]
        hits = find_subset_matches(lrow["invoice_amount"], candidates, tolerance=max(0.05, 0.02 * len(candidates)))
        if hits:
            chosen = hits[0]
            amounts_str = ", ".join(f"{settlement[s]['gross_amount']:.2f}" for s in chosen)
            reasoning = (
                f"subset-sum grouping: {len(chosen)} settlement gross amounts "
                f"({amounts_str}) sum to invoice "
                f"{lrow['invoice_amount']:.2f} within {config.DATE_WINDOW_TIER3_LEDGER}d window"
            )
            result.add_edge(list(chosen), [lid], "tier3_grouping", 0.9, reasoning)


def match(settlement: dict, ledger: dict, exclude_settlement_ids: set | None = None) -> SettlementLedgerResult:
    """exclude_settlement_ids: settlement rows already flagged as duplicate
    exports on the bank<->settlement axis. These must never be allowed to
    claim a ledger invoice -- doing so would let a duplicate silently steal
    the real settlement's ledger link."""
    result = SettlementLedgerResult()
    if exclude_settlement_ids:
        result.claimed_settlement |= exclude_settlement_ids
    run_tier2(settlement, ledger, result)
    run_tier3(settlement, ledger, result)
    if exclude_settlement_ids:
        result.claimed_settlement -= exclude_settlement_ids
    return result
