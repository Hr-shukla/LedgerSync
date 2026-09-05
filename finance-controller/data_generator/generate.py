"""
Synthetic data generator for the AI Finance Controller reconciliation agent.

Produces three source files that a Razorpay-style merchant finance team would
normally cross-check by hand:

  - bank_statement.csv        money that actually landed in the bank account
  - razorpay_settlements.csv  what the payment gateway says was settled
  - internal_ledger.csv       what the business's own books expected

Also writes a hidden ground_truth.jsonl that is NEVER read by the matching
pipeline -- it exists only so the report generator can grade the pipeline's
own precision/recall honestly.

Deterministic: same --seed always produces the same three files + ground truth.
"""
import argparse
import csv
import json
import random
import string
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

GST_RATE = 0.18
RAZORPAY_FEE_RATE = 0.02  # 2% gateway fee, before GST on the fee
TDS_RATE = 0.01

CUSTOMER_NAMES = [
    "Acme Retail Pvt Ltd", "Blue Orbit Traders", "Chandra Textiles", "Delta Foods",
    "Everline Logistics", "Falcon Apparel", "Ganges Electronics", "Horizon Media",
    "Indus Valley Foods", "Jupiter Freight", "Kalinga Steel", "Lotus Interiors",
    "Mysore Silks", "Nimbus Cloud Services", "Orbit Fintech", "Pallavi Exports",
    "Quantum Devices", "Ridge Consulting", "Sunrise Agro", "Trident Motors",
    "Udupi Hospitality", "Vertex Analytics", "Windsor Furniture", "Xenon Labs",
    "Yamuna Chemicals", "Zenith Sports",
]


def utr(rng: random.Random) -> str:
    return "UTR" + "".join(rng.choices(string.digits, k=12))


def rzp_id(rng: random.Random) -> str:
    return "pay_" + "".join(rng.choices(string.ascii_letters + string.digits, k=14))


def inv_id(rng: random.Random, n: int) -> str:
    return f"INV-2026-{n:05d}"


@dataclass
class GroundTruthEntry:
    case_type: str
    bank_ids: list = field(default_factory=list)
    settlement_ids: list = field(default_factory=list)
    ledger_ids: list = field(default_factory=list)
    note: str = ""


class IdGen:
    def __init__(self):
        self._n = 0

    def next(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}{self._n:06d}"


def round2(x: float) -> float:
    return round(x + 1e-9, 2)


def build(seed: int, n_clean_groups: int, out_dir: Path):
    rng = random.Random(seed)
    ids = IdGen()

    bank_rows = []
    settlement_rows = []
    ledger_rows = []
    ground_truth = []

    base_date = date(2026, 1, 5)
    inv_counter = 0

    def new_invoice_amount():
        return round2(rng.uniform(1500, 250000))

    def make_clean_group():
        """Case: clean 1:1 match, possibly with fee/TDS/GST deltas and timing lag."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 240))
        gross = new_invoice_amount()
        fee = round2(gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(gross * TDS_RATE)
        net = round2(gross - fee - fee_gst - tds)

        settle_lag = rng.randint(0, 2)
        bank_lag = settle_lag + rng.randint(0, 3)
        settle_date = invoice_date + timedelta(days=settle_lag)
        bank_date = invoice_date + timedelta(days=bank_lag)

        ref = utr(rng)
        pay_id = rzp_id(rng)
        ledger_id = inv_id(rng, inv_counter)

        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
            "amount": net, "utr": ref, "narration": f"NEFT-{ref}-RAZORPAY",
        }
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": settle_date.isoformat(), "gross_amount": gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
            "invoice_ref": ledger_id,
        }
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
            "payment_ref": pay_id, "status": "invoiced",
        }
        bank_rows.append(bank_row)
        settlement_rows.append(settlement_row)
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "clean_match", [bank_row["bank_txn_id"]], [settlement_row["settlement_id"]],
            [ledger_row["ledger_id"]], "1:1 clean match with standard fee/TDS/GST deltas"
        ))

    def make_reference_mismatch_group():
        """Clean transaction but UTR is truncated/reformatted on the bank side."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 240))
        gross = new_invoice_amount()
        fee = round2(gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(gross * TDS_RATE)
        net = round2(gross - fee - fee_gst - tds)
        settle_date = invoice_date + timedelta(days=rng.randint(0, 2))
        bank_date = invoice_date + timedelta(days=rng.randint(2, 5))

        ref = utr(rng)
        mangled = ref[:6] + rng.choice(["", "XX", ref[-4:]])
        pay_id = rzp_id(rng)
        ledger_id = inv_id(rng, inv_counter)

        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
            "amount": net, "utr": mangled, "narration": f"NEFT/{mangled}/RZP SETTL",
        }
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": settle_date.isoformat(), "gross_amount": gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
            "invoice_ref": ledger_id,
        }
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
            "payment_ref": pay_id, "status": "invoiced",
        }
        bank_rows.append(bank_row)
        settlement_rows.append(settlement_row)
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "reference_mismatch", [bank_row["bank_txn_id"]], [settlement_row["settlement_id"]],
            [ledger_row["ledger_id"]], "UTR truncated/reformatted on bank side, must fuzzy-match"
        ))

    def make_partial_payment_group():
        """One invoice paid across 2-3 settlement+bank transactions."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 240))
        gross_total = new_invoice_amount()
        n_parts = rng.choice([2, 3])
        splits = _random_splits(rng, gross_total, n_parts)
        ledger_id = inv_id(rng, inv_counter)
        b_ids, s_ids = [], []
        for i, part_gross in enumerate(splits):
            fee = round2(part_gross * RAZORPAY_FEE_RATE)
            fee_gst = round2(fee * GST_RATE)
            tds = round2(part_gross * TDS_RATE)
            net = round2(part_gross - fee - fee_gst - tds)
            settle_date = invoice_date + timedelta(days=10 * i + rng.randint(0, 2))
            bank_date = settle_date + timedelta(days=rng.randint(0, 2))
            ref = utr(rng)
            pay_id = rzp_id(rng)
            bank_row = {
                "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
                "amount": net, "utr": ref, "narration": f"NEFT-{ref}-RAZORPAY PARTIAL",
            }
            settlement_row = {
                "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
                "settlement_date": settle_date.isoformat(), "gross_amount": part_gross,
                "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
                "invoice_ref": ledger_id,
            }
            bank_rows.append(bank_row)
            settlement_rows.append(settlement_row)
            b_ids.append(bank_row["bank_txn_id"])
            s_ids.append(settlement_row["settlement_id"])
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross_total,
            "payment_ref": "", "status": "invoiced",
        }
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "partial_payment", b_ids, s_ids, [ledger_id],
            f"invoice split across {n_parts} settlement/bank txns"
        ))

    def make_aggregated_settlement_group():
        """Multiple ledger invoices settled in a single lump bank credit (many:1)."""
        nonlocal inv_counter
        n_invoices = rng.choice([2, 3, 4])
        invoice_date = base_date + timedelta(days=rng.randint(0, 200))
        ledger_ids, settlement_ids = [], []
        total_net = 0.0
        settle_date = invoice_date + timedelta(days=rng.randint(0, 2))
        for _ in range(n_invoices):
            inv_counter += 1
            gross = new_invoice_amount()
            fee = round2(gross * RAZORPAY_FEE_RATE)
            fee_gst = round2(fee * GST_RATE)
            tds = round2(gross * TDS_RATE)
            net = round2(gross - fee - fee_gst - tds)
            total_net = round2(total_net + net)
            ledger_id = inv_id(rng, inv_counter)
            pay_id = rzp_id(rng)
            ref = utr(rng)
            settlement_row = {
                "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
                "settlement_date": settle_date.isoformat(), "gross_amount": gross,
                "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
                "invoice_ref": ledger_id,
            }
            settlement_rows.append(settlement_row)
            settlement_ids.append(settlement_row["settlement_id"])
            ledger_row = {
                "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
                "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
                "payment_ref": pay_id, "status": "invoiced",
            }
            ledger_rows.append(ledger_row)
            ledger_ids.append(ledger_id)
        bank_date = settle_date + timedelta(days=rng.randint(0, 2))
        agg_ref = utr(rng)
        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
            "amount": total_net, "utr": agg_ref, "narration": f"NEFT-{agg_ref}-RAZORPAY BULK SETTLEMENT",
        }
        bank_rows.append(bank_row)
        ground_truth.append(GroundTruthEntry(
            "aggregated_settlement", [bank_row["bank_txn_id"]], settlement_ids, ledger_ids,
            f"{n_invoices} settlements aggregated into one bank credit"
        ))

    def make_split_settlement_group():
        """One large invoice's settlement paid out across multiple bank credits (1:many)."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 200))
        gross = round2(rng.uniform(100000, 400000))
        fee = round2(gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(gross * TDS_RATE)
        net = round2(gross - fee - fee_gst - tds)
        settle_date = invoice_date + timedelta(days=rng.randint(0, 2))
        pay_id = rzp_id(rng)
        ref = utr(rng)
        ledger_id = inv_id(rng, inv_counter)
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": settle_date.isoformat(), "gross_amount": gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
            "invoice_ref": ledger_id,
        }
        settlement_rows.append(settlement_row)
        n_parts = rng.choice([2, 3])
        parts = _random_splits(rng, net, n_parts)
        bank_ids = []
        for i, part in enumerate(parts):
            bank_date = settle_date + timedelta(days=i + rng.randint(0, 1))
            bank_row = {
                "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
                "amount": part, "utr": ref, "narration": f"NEFT-{ref}-RAZORPAY SPLIT {i+1}/{n_parts}",
            }
            bank_rows.append(bank_row)
            bank_ids.append(bank_row["bank_txn_id"])
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
            "payment_ref": pay_id, "status": "invoiced",
        }
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "split_settlement", bank_ids, [settlement_row["settlement_id"]], [ledger_id],
            f"one settlement paid out across {n_parts} bank credits"
        ))

    def make_duplicate_entry():
        """A duplicate row in one source that must not be double-matched."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 240))
        gross = new_invoice_amount()
        fee = round2(gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(gross * TDS_RATE)
        net = round2(gross - fee - fee_gst - tds)
        settle_date = invoice_date + timedelta(days=rng.randint(0, 2))
        bank_date = settle_date + timedelta(days=rng.randint(0, 2))
        ref = utr(rng)
        pay_id = rzp_id(rng)
        ledger_id = inv_id(rng, inv_counter)

        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
            "amount": net, "utr": ref, "narration": f"NEFT-{ref}-RAZORPAY",
        }
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": settle_date.isoformat(), "gross_amount": gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
            "invoice_ref": ledger_id,
        }
        # duplicate settlement row re-ingested by a flaky exporter (same payment_id+utr, new row id)
        dup_settlement_row = dict(settlement_row)
        dup_settlement_row["settlement_id"] = ids.next("STL")
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
            "payment_ref": pay_id, "status": "invoiced",
        }
        bank_rows.append(bank_row)
        settlement_rows.append(settlement_row)
        settlement_rows.append(dup_settlement_row)
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "duplicate_settlement", [bank_row["bank_txn_id"]], [settlement_row["settlement_id"]],
            [ledger_row["ledger_id"]],
            f"duplicate row {dup_settlement_row['settlement_id']} must stay unmatched/flagged, not double-counted"
        ))

    def make_refund_group():
        """Refund/reversal: negative bank amount netting against an earlier settlement."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 200))
        gross = new_invoice_amount()
        fee = round2(gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(gross * TDS_RATE)
        net = round2(gross - fee - fee_gst - tds)
        settle_date = invoice_date + timedelta(days=rng.randint(0, 2))
        bank_date = settle_date + timedelta(days=rng.randint(0, 2))
        ref = utr(rng)
        pay_id = rzp_id(rng)
        ledger_id = inv_id(rng, inv_counter)

        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
            "amount": net, "utr": ref, "narration": f"NEFT-{ref}-RAZORPAY",
        }
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": settle_date.isoformat(), "gross_amount": gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
            "invoice_ref": ledger_id,
        }
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
            "payment_ref": pay_id, "status": "invoiced",
        }
        # refund a few days later
        refund_date = bank_date + timedelta(days=rng.randint(2, 6))
        refund_ref = utr(rng)
        refund_pay_id = "rfnd_" + pay_id[4:]
        refund_amount = -round2(gross * rng.uniform(0.2, 1.0))
        refund_bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": refund_date.isoformat(),
            "amount": refund_amount, "utr": refund_ref, "narration": f"NEFT-{refund_ref}-RAZORPAY REFUND",
        }
        refund_settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": refund_pay_id, "utr": refund_ref,
            "settlement_date": refund_date.isoformat(), "gross_amount": refund_amount,
            "fee": 0.0, "fee_gst": 0.0, "tds": 0.0, "net_amount": refund_amount,
            "invoice_ref": ledger_id, "refund_of": pay_id,
        }
        bank_rows.append(bank_row)
        bank_rows.append(refund_bank_row)
        settlement_rows.append(settlement_row)
        settlement_rows.append(refund_settlement_row)
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "clean_match", [bank_row["bank_txn_id"]], [settlement_row["settlement_id"]],
            [ledger_row["ledger_id"]], "original settlement leg of a refund pair"
        ))
        ground_truth.append(GroundTruthEntry(
            "refund_reversal", [refund_bank_row["bank_txn_id"]], [refund_settlement_row["settlement_id"]],
            [], "refund/reversal, nets against earlier settlement, no ledger counterpart"
        ))

    def make_orphan_bank():
        """Bank credit with no matching settlement or invoice at all."""
        d = base_date + timedelta(days=rng.randint(0, 240))
        amt = new_invoice_amount()
        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": d.isoformat(),
            "amount": round2(amt * 0.97), "utr": utr(rng),
            "narration": "NEFT MISC CREDIT - UNKNOWN SOURCE",
        }
        bank_rows.append(bank_row)
        ground_truth.append(GroundTruthEntry(
            "orphan_bank_credit", [bank_row["bank_txn_id"]], [], [],
            "bank credit with no counterpart in settlement or ledger"
        ))

    def make_orphan_invoice():
        """Invoice raised but never paid."""
        nonlocal inv_counter
        inv_counter += 1
        d = base_date + timedelta(days=rng.randint(0, 240))
        ledger_row = {
            "ledger_id": inv_id(rng, inv_counter), "invoice_date": d.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": new_invoice_amount(),
            "payment_ref": "", "status": "invoiced",
        }
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "unpaid_invoice", [], [], [ledger_row["ledger_id"]],
            "invoice never paid, no counterpart in bank or settlement"
        ))

    def make_near_duplicate_trap():
        """Two unrelated txns, same amount, near-same date -- trap for naive amount+date matching."""
        nonlocal inv_counter
        d = base_date + timedelta(days=rng.randint(0, 230))
        shared_gross = new_invoice_amount()
        b_ids, s_ids, l_ids = [], [], []
        for i in range(2):
            inv_counter += 1
            fee = round2(shared_gross * RAZORPAY_FEE_RATE)
            fee_gst = round2(fee * GST_RATE)
            tds = round2(shared_gross * TDS_RATE)
            net = round2(shared_gross - fee - fee_gst - tds)
            this_date = d + timedelta(days=i)
            ref = utr(rng)
            pay_id = rzp_id(rng)
            ledger_id = inv_id(rng, inv_counter)
            bank_row = {
                "bank_txn_id": ids.next("BNK"), "date": this_date.isoformat(),
                "amount": net, "utr": ref, "narration": f"NEFT-{ref}-RAZORPAY",
            }
            settlement_row = {
                "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
                "settlement_date": this_date.isoformat(), "gross_amount": shared_gross,
                "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
                "invoice_ref": ledger_id,
            }
            ledger_row = {
                "ledger_id": ledger_id, "invoice_date": this_date.isoformat(),
                "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": shared_gross,
                "payment_ref": pay_id, "status": "invoiced",
            }
            bank_rows.append(bank_row)
            settlement_rows.append(settlement_row)
            ledger_rows.append(ledger_row)
            b_ids.append(bank_row["bank_txn_id"])
            s_ids.append(settlement_row["settlement_id"])
            l_ids.append(ledger_row["ledger_id"])
            ground_truth.append(GroundTruthEntry(
                "clean_match_near_dup_trap", [bank_row["bank_txn_id"]], [settlement_row["settlement_id"]],
                [ledger_row["ledger_id"]],
                "same amount/near-same date as another unrelated txn -- must match by UTR not amount+date"
            ))

    def make_chargeback():
        """Chargeback/dispute appearing only in settlement data (debit, no bank/ledger leg yet)."""
        pay_id = rzp_id(rng)
        ref = utr(rng)
        d = base_date + timedelta(days=rng.randint(0, 240))
        amt = -round2(rng.uniform(1000, 50000))
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": d.isoformat(), "gross_amount": amt,
            "fee": 0.0, "fee_gst": 0.0, "tds": 0.0, "net_amount": amt,
            "invoice_ref": "", "chargeback": True,
        }
        settlement_rows.append(settlement_row)
        ground_truth.append(GroundTruthEntry(
            "chargeback_dispute", [], [settlement_row["settlement_id"]], [],
            "chargeback/dispute debit, appears only in settlement data"
        ))

    def make_rounding_case():
        """Clean match but with a paise-level rounding difference injected on the bank leg."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 240))
        gross = new_invoice_amount()
        fee = round2(gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(gross * TDS_RATE)
        net = round2(gross - fee - fee_gst - tds)
        bank_net = round2(net + rng.choice([-0.02, -0.01, 0.01, 0.02]))
        settle_date = invoice_date + timedelta(days=rng.randint(0, 2))
        bank_date = settle_date + timedelta(days=rng.randint(0, 2))
        ref = utr(rng)
        pay_id = rzp_id(rng)
        ledger_id = inv_id(rng, inv_counter)
        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
            "amount": bank_net, "utr": ref, "narration": f"NEFT-{ref}-RAZORPAY",
        }
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": settle_date.isoformat(), "gross_amount": gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
            "invoice_ref": ledger_id,
        }
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
            "payment_ref": pay_id, "status": "invoiced",
        }
        bank_rows.append(bank_row)
        settlement_rows.append(settlement_row)
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "rounding_diff", [bank_row["bank_txn_id"]], [settlement_row["settlement_id"]],
            [ledger_row["ledger_id"]], "paise-level rounding difference between bank and settlement net"
        ))

    def make_ai_needed_case():
        """A genuine transaction that's too degraded for deterministic Tiers 1-3
        but still has real corroborating signal for a careful reasoner: the bank
        narration masks the middle of the UTR (a realistic bank-export pattern --
        prefix/suffix preserved, middle redacted -- fuzzy score still below
        threshold since half the characters are gone) AND a small extra bank
        charge is netted out on top of the normal fee/TDS/GST deductions. There
        is exactly one plausible settlement candidate nearby in amount and date
        -- this is the case Tier 4 AI reasoning exists for."""
        nonlocal inv_counter
        inv_counter += 1
        invoice_date = base_date + timedelta(days=rng.randint(0, 240))
        gross = new_invoice_amount()
        fee = round2(gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(gross * TDS_RATE)
        net = round2(gross - fee - fee_gst - tds)
        extra_bank_charge = round2(rng.uniform(8, 25))
        bank_net = round2(net - extra_bank_charge)
        settle_date = invoice_date + timedelta(days=rng.randint(0, 2))
        bank_date = settle_date + timedelta(days=rng.randint(0, 2))
        ref = utr(rng)
        mangled = ref[:4] + "XXXX" + ref[-4:]  # bank-style middle-masking, not a totally unrelated string
        pay_id = rzp_id(rng)
        ledger_id = inv_id(rng, inv_counter)
        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": bank_date.isoformat(),
            "amount": bank_net, "utr": mangled, "narration": f"NEFT/{mangled}/BANK CHARGES DEDUCTED",
        }
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": pay_id, "utr": ref,
            "settlement_date": settle_date.isoformat(), "gross_amount": gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net,
            "invoice_ref": ledger_id,
        }
        ledger_row = {
            "ledger_id": ledger_id, "invoice_date": invoice_date.isoformat(),
            "customer": rng.choice(CUSTOMER_NAMES), "invoice_amount": gross,
            "payment_ref": pay_id, "status": "invoiced",
        }
        bank_rows.append(bank_row)
        settlement_rows.append(settlement_row)
        ledger_rows.append(ledger_row)
        ground_truth.append(GroundTruthEntry(
            "ai_needed_degraded_reference", [bank_row["bank_txn_id"]], [settlement_row["settlement_id"]],
            [ledger_row["ledger_id"]],
            "reference unrecognizable + extra unmodelled bank charge on top of fee/TDS/GST; "
            "only resolvable via amount+date reasoning over the sole plausible candidate (Tier 4)"
        ))

    def make_adversarial_decoy_pair():
        """Two genuinely UNRELATED, unresolvable records -- an orphan bank credit
        and a standalone settlement with no ledger/bank counterpart -- deliberately
        given a near-identical amount and adjacent date to bait a matcher that
        trusts amount+date alone. Ground truth: neither should ever be matched to
        the other; a correct system leaves both as separate exceptions."""
        d = base_date + timedelta(days=rng.randint(0, 230))
        shared_amount = new_invoice_amount()

        bank_row = {
            "bank_txn_id": ids.next("BNK"), "date": d.isoformat(),
            "amount": round2(shared_amount * 0.97), "utr": utr(rng),
            "narration": "NEFT MISC CREDIT - UNKNOWN SOURCE",
        }
        bank_rows.append(bank_row)
        ground_truth.append(GroundTruthEntry(
            "adversarial_decoy_no_match", [bank_row["bank_txn_id"]], [], [],
            "orphan bank credit deliberately close in amount/date to an unrelated orphan settlement -- must NOT be cross-matched"
        ))

        net_of_gross_factor = 1 - (RAZORPAY_FEE_RATE * (1 + GST_RATE)) - TDS_RATE
        decoy_gross = round2(shared_amount * 0.97 / net_of_gross_factor)
        fee = round2(decoy_gross * RAZORPAY_FEE_RATE)
        fee_gst = round2(fee * GST_RATE)
        tds = round2(decoy_gross * TDS_RATE)
        net = round2(decoy_gross - fee - fee_gst - tds)
        settlement_row = {
            "settlement_id": ids.next("STL"), "payment_id": rzp_id(rng), "utr": utr(rng),
            "settlement_date": (d + timedelta(days=1)).isoformat(), "gross_amount": decoy_gross,
            "fee": fee, "fee_gst": fee_gst, "tds": tds, "net_amount": net, "chargeback": False,
        }
        settlement_rows.append(settlement_row)
        ground_truth.append(GroundTruthEntry(
            "adversarial_decoy_no_match", [], [settlement_row["settlement_id"]], [],
            "standalone settlement (e.g. routed to a different bank account) deliberately close "
            "in amount/date to an unrelated orphan bank credit -- must NOT be cross-matched"
        ))

    # ---- assemble the batch: mix of case types, ~60% clean baseline ----
    for _ in range(n_clean_groups):
        make_clean_group()
    for _ in range(max(1, n_clean_groups // 8)):
        make_reference_mismatch_group()
    for _ in range(max(1, n_clean_groups // 10)):
        make_rounding_case()
    for _ in range(max(1, n_clean_groups // 12)):
        make_partial_payment_group()
    for _ in range(max(1, n_clean_groups // 12)):
        make_aggregated_settlement_group()
    for _ in range(max(1, n_clean_groups // 14)):
        make_split_settlement_group()
    for _ in range(max(1, n_clean_groups // 14)):
        make_duplicate_entry()
    for _ in range(max(1, n_clean_groups // 14)):
        make_refund_group()
    for _ in range(max(1, n_clean_groups // 10)):
        make_orphan_bank()
    for _ in range(max(1, n_clean_groups // 10)):
        make_orphan_invoice()
    for _ in range(max(1, n_clean_groups // 16)):
        make_near_duplicate_trap()
    for _ in range(max(1, n_clean_groups // 18)):
        make_chargeback()
    for _ in range(max(1, n_clean_groups // 16)):
        make_ai_needed_case()
    for _ in range(max(1, n_clean_groups // 18)):
        make_adversarial_decoy_pair()

    rng.shuffle(bank_rows)
    rng.shuffle(settlement_rows)
    rng.shuffle(ledger_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(out_dir / "bank_statement.csv", bank_rows,
               ["bank_txn_id", "date", "amount", "utr", "narration"])
    # NOTE: invoice_ref / payment_ref / refund_of are deliberately NOT exported to the
    # CSVs even though they exist on the in-memory rows (used only to build ground
    # truth). Real settlement exports don't carry your internal invoice ID and real
    # ledgers don't carry the gateway's internal payment ID -- if we handed the
    # matcher a direct foreign key, the hardest part of this problem (amount/date
    # correlation, subset-sum grouping for partial/aggregated/split settlements)
    # would be trivial to cheat. The matcher must earn every ledger<->settlement
    # link the way a human reconciler does: amount + date + grouping logic.
    _write_csv(out_dir / "razorpay_settlements.csv", settlement_rows,
               ["settlement_id", "payment_id", "utr", "settlement_date", "gross_amount",
                "fee", "fee_gst", "tds", "net_amount", "chargeback"])
    _write_csv(out_dir / "internal_ledger.csv", ledger_rows,
               ["ledger_id", "invoice_date", "customer", "invoice_amount", "status"])

    gt_path = out_dir / "ground_truth.jsonl"
    with gt_path.open("w", encoding="utf-8") as f:
        for i, g in enumerate(ground_truth):
            f.write(json.dumps({
                "group_id": i, "case_type": g.case_type, "bank_ids": g.bank_ids,
                "settlement_ids": g.settlement_ids, "ledger_ids": g.ledger_ids, "note": g.note,
            }) + "\n")

    return {
        "bank_count": len(bank_rows),
        "settlement_count": len(settlement_rows),
        "ledger_count": len(ledger_rows),
        "group_count": len(ground_truth),
    }


def _random_splits(rng: random.Random, total: float, n: int):
    """Split `total` into n positive parts (2dp) that sum exactly to total."""
    cuts = sorted(rng.uniform(0.15, 0.85) for _ in range(n - 1))
    bounds = [0.0] + cuts + [1.0]
    parts = [round2(total * (bounds[i + 1] - bounds[i])) for i in range(n)]
    # fix rounding drift on the last part so parts sum exactly to total
    drift = round2(total - sum(parts))
    parts[-1] = round2(parts[-1] + drift)
    return parts


def _write_csv(path: Path, rows: list, fieldnames: list):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic reconciliation dataset")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--groups", type=int, default=40,
                         help="number of clean-match base groups; total records scale from this")
    parser.add_argument("--out", type=str, default=str(Path(__file__).resolve().parent.parent / "data"))
    args = parser.parse_args()

    stats = build(args.seed, args.groups, Path(args.out))
    print(f"Generated dataset (seed={args.seed}):")
    print(f"  bank_statement.csv      : {stats['bank_count']} rows")
    print(f"  razorpay_settlements.csv: {stats['settlement_count']} rows")
    print(f"  internal_ledger.csv     : {stats['ledger_count']} rows")
    print(f"  ground_truth.jsonl      : {stats['group_count']} groups (hidden, matcher must not read this)")


if __name__ == "__main__":
    main()
