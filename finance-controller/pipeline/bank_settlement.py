"""Bank <-> Settlement matching: Tiers 1-3.

Tier 1 (exact):     bank.utr == settlement.utr, exact string match. Handles
                     1:1 clean matches, 1-settlement-to-N-bank splits and
                     N-bank... no wait: also detects duplicate settlement rows
                     re-ingested under the same UTR/payment_id and keeps only
                     one as the real match.
Tier 2 (fuzzy):      mangled/truncated UTR on the bank narration -- fuzzy
                     string similarity + amount/date corroboration.
Tier 3 (grouping):   bounded subset-sum search for aggregated settlements
                     (many settlement net_amounts -> one bank credit) and
                     split settlements (one settlement -> many bank credits).

Whatever is left unmatched after Tier 3 is handed back to the orchestrator as
"pending AI" candidates (Tier 4) or, if there's nothing plausible nearby, as
direct Tier 5 exceptions.
"""
from __future__ import annotations

from collections import defaultdict

from rapidfuzz import fuzz

from . import config
from .fees import net_vs_net_match
from .grouping import find_subset_matches
from .models import MatchEvent, days_between


class BankSettlementResult:
    def __init__(self):
        self.edges = []  # list of dict(bank_ids, settlement_ids, tier, confidence, reasoning)
        self.audit: list[MatchEvent] = []
        self.duplicate_settlements = []  # list of dict(id, duplicate_of, reasoning)
        self.claimed_bank: set[str] = set()
        self.claimed_settlement: set[str] = set()

    def add_edge(self, bank_ids, settlement_ids, tier, confidence, reasoning):
        self.edges.append({
            "bank_ids": list(bank_ids), "settlement_ids": list(settlement_ids),
            "tier": tier, "confidence": confidence, "reasoning": reasoning,
        })
        for bid in bank_ids:
            self.claimed_bank.add(bid)
            self.audit.append(MatchEvent(bid, "bank", tier, "matched", list(settlement_ids), confidence, reasoning))
        for sid in settlement_ids:
            self.claimed_settlement.add(sid)
            self.audit.append(MatchEvent(sid, "settlement", tier, "matched", list(bank_ids), confidence, reasoning))


def _is_duplicate_pair(a: dict, b: dict) -> bool:
    return (a["payment_id"] == b["payment_id"]
            and abs(a["gross_amount"] - b["gross_amount"]) < 0.01
            and abs(a["net_amount"] - b["net_amount"]) < 0.01)


def run_tier1(bank: dict, settlement: dict, result: BankSettlementResult) -> None:
    bank_by_utr = defaultdict(list)
    for bid, row in bank.items():
        bank_by_utr[row["utr"]].append(bid)
    settlement_by_utr = defaultdict(list)
    for sid, row in settlement.items():
        settlement_by_utr[row["utr"]].append(sid)

    for utr_val, s_ids_raw in settlement_by_utr.items():
        b_ids = bank_by_utr.get(utr_val, [])
        if not b_ids or not utr_val:
            continue
        # process in a deterministic order (not CSV/shuffle order) so which of
        # two identical duplicate rows gets called "the real one" is stable
        s_ids = sorted(s_ids_raw)

        # de-duplicate settlement rows that are re-exports of the same txn
        real_s_ids = [s_ids[0]]
        for sid in s_ids[1:]:
            if _is_duplicate_pair(settlement[s_ids[0]], settlement[sid]):
                result.duplicate_settlements.append({
                    "id": sid, "duplicate_of": s_ids[0],
                    "reasoning": f"identical payment_id/utr/amount as {s_ids[0]}; suspected duplicate export",
                })
                result.claimed_settlement.add(sid)
                result.audit.append(MatchEvent(
                    sid, "settlement", "tier1_exact", "unresolved", [s_ids[0]], 0.0,
                    f"duplicate suspected: identical to {s_ids[0]} on payment_id/utr/amount",
                    exception_reason="duplicate_suspected",
                ))
            else:
                real_s_ids.append(sid)

        bank_total = sum(bank[b]["amount"] for b in b_ids)
        settle_total = sum(settlement[s]["net_amount"] for s in real_s_ids)
        all_dates = [bank[b]["date"] for b in b_ids] + [settlement[s]["settlement_date"] for s in real_s_ids]
        spread = max(days_between(d1, d2) for d1 in all_dates for d2 in all_dates) if len(all_dates) > 1 else 0

        tolerance = max(config.NET_VS_NET_TOLERANCE, 0.02 * len(real_s_ids))
        if abs(bank_total - settle_total) <= tolerance and spread <= config.DATE_WINDOW_TIER2:
            tier = "tier1_exact" if len(b_ids) == 1 and len(real_s_ids) == 1 else "tier1_exact_grouped"
            n = len(b_ids) + len(real_s_ids)
            reasoning = (
                f"exact UTR match ({utr_val}) across {len(b_ids)} bank row(s) and "
                f"{len(real_s_ids)} settlement row(s); amounts reconcile within Rs.{tolerance:.2f}"
                if n > 2 else
                f"exact UTR match ({utr_val}); bank amount {bank[b_ids[0]]['amount']} vs "
                f"settlement net {settlement[real_s_ids[0]]['net_amount']}"
            )
            result.add_edge(b_ids, real_s_ids, tier, 1.0, reasoning)
        # if UTR matches exactly but amounts don't reconcile, leave both sides
        # unclaimed -- this is a genuine "amount mismatch beyond tolerance"
        # exception that Tier 4/5 should see, not a silent tier-1 pass.


def run_tier2(bank: dict, settlement: dict, result: BankSettlementResult) -> None:
    remaining_bank = [b for b in bank if b not in result.claimed_bank]
    remaining_settlement = [s for s in settlement if s not in result.claimed_settlement]

    for bid in remaining_bank:
        if bid in result.claimed_bank:
            continue
        brow = bank[bid]
        best, best_score = None, 0
        for sid in remaining_settlement:
            if sid in result.claimed_settlement:
                continue
            srow = settlement[sid]
            if not net_vs_net_match(brow["amount"], srow["net_amount"]):
                continue
            if days_between(brow["date"], srow["settlement_date"]) > config.DATE_WINDOW_TIER2:
                continue
            score = fuzz.partial_ratio(brow["utr"], srow["utr"])
            if score > best_score:
                best, best_score = sid, score
        if best is not None and best_score >= config.UTR_FUZZY_THRESHOLD:
            srow = settlement[best]
            reasoning = (
                f"fuzzy UTR match: bank '{brow['utr']}' ~ settlement '{srow['utr']}' "
                f"(similarity {best_score:.0f}/100); amount and date corroborate"
            )
            result.add_edge([bid], [best], "tier2_fuzzy", 0.9, reasoning)


def run_tier3(bank: dict, settlement: dict, result: BankSettlementResult) -> None:
    # many settlements -> one bank credit (aggregated settlement)
    remaining_settlement = [s for s in settlement if s not in result.claimed_settlement]
    for bid in list(bank):
        if bid in result.claimed_bank:
            continue
        brow = bank[bid]
        pool = [s for s in remaining_settlement
                if s not in result.claimed_settlement
                and days_between(brow["date"], settlement[s]["settlement_date"]) <= config.DATE_WINDOW_TIER3_BANK]
        pool.sort(key=lambda s: days_between(brow["date"], settlement[s]["settlement_date"]))
        candidates = [(s, settlement[s]["net_amount"]) for s in pool]
        hits = find_subset_matches(brow["amount"], candidates, tolerance=max(0.05, 0.02 * len(candidates)))
        if hits:
            chosen = hits[0]
            amounts_str = ", ".join(f"{settlement[s]['net_amount']:.2f}" for s in chosen)
            reasoning = (
                f"subset-sum grouping: {len(chosen)} settlement net amounts "
                f"({amounts_str}) sum to bank credit "
                f"{brow['amount']:.2f} within date window {config.DATE_WINDOW_TIER3_BANK}d"
            )
            result.add_edge([bid], list(chosen), "tier3_grouping", 0.95, reasoning)

    # one settlement -> many bank credits (split settlement)
    remaining_bank = [b for b in bank if b not in result.claimed_bank]
    for sid in list(settlement):
        if sid in result.claimed_settlement:
            continue
        srow = settlement[sid]
        pool = [b for b in remaining_bank
                if b not in result.claimed_bank
                and days_between(srow["settlement_date"], bank[b]["date"]) <= config.DATE_WINDOW_TIER3_BANK]
        pool.sort(key=lambda b: days_between(srow["settlement_date"], bank[b]["date"]))
        candidates = [(b, bank[b]["amount"]) for b in pool]
        hits = find_subset_matches(srow["net_amount"], candidates, tolerance=max(0.05, 0.02 * len(candidates)))
        if hits:
            chosen = hits[0]
            reasoning = (
                f"subset-sum grouping: {len(chosen)} bank credits sum to settlement net "
                f"{srow['net_amount']:.2f} within date window {config.DATE_WINDOW_TIER3_BANK}d"
            )
            result.add_edge(list(chosen), [sid], "tier3_grouping", 0.95, reasoning)


def match(bank: dict, settlement: dict) -> BankSettlementResult:
    result = BankSettlementResult()
    run_tier1(bank, settlement, result)
    run_tier2(bank, settlement, result)
    run_tier3(bank, settlement, result)
    return result
