"""Ties Tiers 1-5 together across all three sources and produces:

  - final 3-way reconciliation groups (via union-find over bank<->settlement
    and settlement<->ledger edges)
  - a full audit trail (list of MatchEvent)
  - a classified exception list (Tier 5)

This module never reads the hidden ground-truth file -- grading against it
happens later, in report/grading.py, on the pipeline's own output.
"""
from __future__ import annotations

from pathlib import Path

from . import bank_settlement, config, exceptions, settlement_ledger
from .ai_tier import AITier
from .grouping import UnionFind
from .loader import load_all
from .models import MatchEvent, days_between


def _candidate_pool(target_amount, target_date, pool_ids, pool_amount_fn, pool_date_fn, exclude_ids):
    out = []
    for pid in pool_ids:
        if pid in exclude_ids:
            continue
        amt = pool_amount_fn(pid)
        if target_amount == 0:
            continue
        ratio = abs(amt - target_amount) / max(abs(target_amount), 1e-6)
        if ratio > config.AI_TRIGGER_AMOUNT_RATIO:
            continue
        d = days_between(target_date, pool_date_fn(pid))
        if d > config.AI_TRIGGER_DATE_WINDOW:
            continue
        out.append((pid, ratio, d))
    out.sort(key=lambda t: (t[2], t[1]))
    return out[: config.AI_MAX_CANDIDATES]


class Orchestrator:
    def __init__(self, data_dir: Path, api_key: str | None = None, provider: str | None = None,
                 disable_ai: bool = False):
        self.data_dir = Path(data_dir)
        data = load_all(self.data_dir)
        self.bank = data["bank"]
        self.settlement = data["settlement"]
        self.ledger = data["ledger"]
        if disable_ai:
            self.ai = AITier(api_key=None, provider="none")  # matches no branch -> stays unavailable
            self.ai._unavailable_reason = "Tier 4 explicitly disabled for this run (baseline comparison)"
        else:
            self.ai = AITier(api_key=api_key, provider=provider)
        self.ai_candidates_evaluated = 0  # every Tier-4 attempt, whether or not AI was actually available
        self.ai_live_calls_made = 0       # only real network calls to a configured LLM provider
        self.audit: list[MatchEvent] = []
        self.exception_records: list[dict] = []
        self._considered_by_ai_settlement_bank: dict[str, dict] = {}
        self._considered_by_ai_settlement_ledger: dict[str, dict] = {}

    # ------------------------------------------------------------------
    def run(self) -> dict:
        self.bs_result = bank_settlement.match(self.bank, self.settlement)
        duplicate_settlement_ids = {d["id"] for d in self.bs_result.duplicate_settlements}
        self.sl_result = settlement_ledger.match(self.settlement, self.ledger, duplicate_settlement_ids)
        self.audit.extend(self.bs_result.audit)
        self.audit.extend(self.sl_result.audit)

        self._tier4_bank_settlement()
        self._tier4_settlement_ledger()

        self._classify_exceptions()
        groups = self._assemble_groups()

        return {
            "bank": self.bank, "settlement": self.settlement, "ledger": self.ledger,
            "bs_result": self.bs_result, "sl_result": self.sl_result,
            "groups": groups, "audit": self.audit,
            "exceptions": self.exception_records,
            "ai_available": self.ai.available,
            "ai_candidates_evaluated": self.ai_candidates_evaluated,
            "ai_calls_made": self.ai_live_calls_made,
            "ai_provider": self.ai.provider,
        }

    # ------------------------------------------------------------------
    def _tier4_bank_settlement(self):
        duplicate_ids = {d["id"] for d in self.bs_result.duplicate_settlements}

        for bid in list(self.bank):
            if bid in self.bs_result.claimed_bank:
                continue
            brow = self.bank[bid]
            settlement_pool = [s for s in self.settlement
                                if s not in self.bs_result.claimed_settlement and s not in duplicate_ids]
            scored = _candidate_pool(
                brow["amount"], brow["date"], settlement_pool,
                lambda s: self.settlement[s]["net_amount"],
                lambda s: self.settlement[s]["settlement_date"],
                self.bs_result.claimed_settlement,
            )
            if not scored:
                continue  # no plausible candidate at all -> straight to Tier 5, no AI spend
            candidates = [{
                "id": sid, "source": "settlement", "amount": self.settlement[sid]["net_amount"],
                "date": self.settlement[sid]["settlement_date"], "reference": self.settlement[sid]["utr"],
            } for sid, _, _ in scored]
            case = {
                "record_id": bid, "source": "bank", "amount": brow["amount"], "date": brow["date"],
                "reference": brow["utr"],
                "note": "bank credit unresolved after exact/fuzzy UTR match and subset-sum grouping",
                "candidates": candidates,
            }
            was_available = self.ai.available
            result = self.ai.resolve(case)
            self.ai_candidates_evaluated += 1
            if was_available:
                self.ai_live_calls_made += 1
            for c in candidates:
                self._considered_by_ai_settlement_bank[c["id"]] = result
            if (result.get("match") and result.get("confidence", 0) >= config.AI_CONFIDENCE_THRESHOLD
                    and result.get("matched_ids")):
                matched = [m for m in result["matched_ids"]
                           if m in self.settlement and m not in self.bs_result.claimed_settlement]
                if matched:
                    self.bs_result.add_edge([bid], matched, "tier4_ai", result["confidence"], result["reasoning"])
                    continue
            self.audit.append(MatchEvent(
                bid, "bank", "tier4_ai", "unresolved", [c["id"] for c in candidates],
                result.get("confidence", 0.0), result.get("reasoning", ""),
            ))

    def _tier4_settlement_ledger(self):
        for lid in list(self.ledger):
            if lid in self.sl_result.claimed_ledger:
                continue
            lrow = self.ledger[lid]
            settlement_pool = [s for s in self.settlement
                                if s not in self.sl_result.claimed_settlement and not self.settlement[s].get("chargeback")
                                and self.settlement[s]["gross_amount"] > 0]
            scored = _candidate_pool(
                lrow["invoice_amount"], lrow["invoice_date"], settlement_pool,
                lambda s: self.settlement[s]["gross_amount"],
                lambda s: self.settlement[s]["settlement_date"],
                self.sl_result.claimed_settlement,
            )
            if not scored:
                continue
            candidates = [{
                "id": sid, "source": "settlement", "amount": self.settlement[sid]["gross_amount"],
                "date": self.settlement[sid]["settlement_date"], "reference": self.settlement[sid]["payment_id"],
            } for sid, _, _ in scored]
            case = {
                "record_id": lid, "source": "ledger", "amount": lrow["invoice_amount"], "date": lrow["invoice_date"],
                "reference": lid,
                "note": "invoice unresolved after amount+date match and subset-sum grouping against settlements",
                "candidates": candidates,
            }
            was_available = self.ai.available
            result = self.ai.resolve(case)
            self.ai_candidates_evaluated += 1
            if was_available:
                self.ai_live_calls_made += 1
            for c in candidates:
                self._considered_by_ai_settlement_ledger[c["id"]] = result
            if (result.get("match") and result.get("confidence", 0) >= config.AI_CONFIDENCE_THRESHOLD
                    and result.get("matched_ids")):
                matched = [m for m in result["matched_ids"]
                           if m in self.settlement and m not in self.sl_result.claimed_settlement]
                if matched:
                    self.sl_result.add_edge(matched, [lid], "tier4_ai", result["confidence"], result["reasoning"])
                    continue
            self.audit.append(MatchEvent(
                lid, "ledger", "tier4_ai", "unresolved", [c["id"] for c in candidates],
                result.get("confidence", 0.0), result.get("reasoning", ""),
            ))

    # ------------------------------------------------------------------
    def _classify_exceptions(self):
        duplicate_ids = {d["id"]: d for d in self.bs_result.duplicate_settlements}

        for sid, dup in duplicate_ids.items():
            self.exception_records.append({
                "record_id": sid, "source": "settlement", "reason_code": "duplicate_suspected",
                "reason_detail": dup["reasoning"], "amount": self.settlement[sid]["net_amount"],
            })

        for bid, brow in self.bank.items():
            if bid in self.bs_result.claimed_bank:
                continue
            ai_result = self._considered_by_ai_settlement_bank.get(bid)
            reason_code, detail = exceptions.classify(had_any_candidate=ai_result is not None, ai_result=ai_result)
            self.exception_records.append({
                "record_id": bid, "source": "bank", "reason_code": reason_code,
                "reason_detail": detail, "amount": brow["amount"],
            })

        for sid, srow in self.settlement.items():
            if sid in duplicate_ids:
                continue
            unresolved_bank_side = sid not in self.bs_result.claimed_settlement
            unresolved_ledger_side = sid not in self.sl_result.claimed_settlement
            is_chargeback = srow.get("chargeback", False)
            is_refund = srow["net_amount"] < 0 and not is_chargeback

            if unresolved_bank_side and not is_chargeback:
                ai_result = self._considered_by_ai_settlement_bank.get(sid)
                reason_code, detail = exceptions.classify(had_any_candidate=ai_result is not None, ai_result=ai_result)
                self.exception_records.append({
                    "record_id": sid, "source": "settlement", "reason_code": reason_code,
                    "reason_detail": f"[bank leg] {detail}", "amount": srow["net_amount"],
                })
            elif is_chargeback:
                reason_code, detail = exceptions.classify(is_chargeback=True)
                self.exception_records.append({
                    "record_id": sid, "source": "settlement", "reason_code": reason_code,
                    "reason_detail": detail, "amount": srow["net_amount"],
                })

            if unresolved_ledger_side and not is_chargeback and not is_refund:
                ai_result = self._considered_by_ai_settlement_ledger.get(sid)
                reason_code, detail = exceptions.classify(had_any_candidate=ai_result is not None, ai_result=ai_result)
                self.exception_records.append({
                    "record_id": sid, "source": "settlement", "reason_code": reason_code,
                    "reason_detail": f"[ledger leg] {detail}", "amount": srow["gross_amount"],
                })
            elif unresolved_ledger_side and is_refund:
                self.exception_records.append({
                    "record_id": sid, "source": "settlement", "reason_code": "refund_no_ledger_expected",
                    "reason_detail": "negative settlement amount (refund/reversal); no ledger invoice counterpart expected by design",
                    "amount": srow["gross_amount"],
                })

        for lid, lrow in self.ledger.items():
            if lid in self.sl_result.claimed_ledger:
                continue
            ai_result = self._considered_by_ai_settlement_ledger.get(lid)
            reason_code, detail = exceptions.classify(had_any_candidate=ai_result is not None, ai_result=ai_result)
            self.exception_records.append({
                "record_id": lid, "source": "ledger", "reason_code": reason_code,
                "reason_detail": detail, "amount": lrow["invoice_amount"],
            })

        for rec in self.exception_records:
            self.audit.append(MatchEvent(
                rec["record_id"], rec["source"], "tier5_exception", "unresolved", [],
                0.0, rec["reason_detail"], exception_reason=rec["reason_code"],
            ))

    # ------------------------------------------------------------------
    def _assemble_groups(self):
        uf = UnionFind()
        all_keys = ([f"bank:{k}" for k in self.bank]
                    + [f"settlement:{k}" for k in self.settlement]
                    + [f"ledger:{k}" for k in self.ledger])
        for k in all_keys:
            uf.find(k)  # register singleton

        edge_meta: dict[tuple[str, str], list[dict]] = {}
        for e in self.bs_result.edges:
            for b in e["bank_ids"]:
                for s in e["settlement_ids"]:
                    uf.union(f"bank:{b}", f"settlement:{s}")
            root_key = f"bank:{e['bank_ids'][0]}"
            edge_meta.setdefault(uf.find(root_key), []).append(e)
        for e in self.sl_result.edges:
            for s in e["settlement_ids"]:
                for l in e["ledger_ids"]:
                    uf.union(f"settlement:{s}", f"ledger:{l}")
            root_key = f"settlement:{e['settlement_ids'][0]}"
            edge_meta.setdefault(uf.find(root_key), []).append(e)

        components = uf.groups(all_keys)
        groups = []
        for root, members in components.items():
            bank_ids = [m.split(":", 1)[1] for m in members if m.startswith("bank:")]
            settlement_ids = [m.split(":", 1)[1] for m in members if m.startswith("settlement:")]
            ledger_ids = [m.split(":", 1)[1] for m in members if m.startswith("ledger:")]
            edges = edge_meta.get(root, [])
            tiers = sorted({e["tier"] for e in edges})
            confidence = min((e["confidence"] for e in edges), default=0.0)
            reasoning = "; ".join(e["reasoning"] for e in edges)
            groups.append({
                "bank_ids": bank_ids, "settlement_ids": settlement_ids, "ledger_ids": ledger_ids,
                "tiers": tiers, "confidence": confidence, "reasoning": reasoning,
                "size": len(members),
            })
        return groups
