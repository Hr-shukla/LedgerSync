"""Tax-line breakdown report: aggregates GST-on-fee and TDS across every
reconciled settlement, split by reconciled vs unreconciled, and cross-checks
each settlement's recorded fee_gst/tds against what the fee/tax formula in
pipeline.config would produce for its gross_amount.

Chargebacks and refunds/reversals carry no real fee/tax (fee=fee_gst=tds=0
by construction, per data_generator.generate) so they are excluded from the
captured/reconciled sums, but their count and value are still reported for
transparency rather than silently dropped.
"""
from __future__ import annotations

from pipeline import config

VARIANCE_TOLERANCE_RUPEES = 1.00


def _expected_tax_lines(gross_amount: float) -> tuple[float, float, float]:
    fee = round(gross_amount * config.RAZORPAY_FEE_RATE, 2)
    fee_gst = round(fee * config.FEE_GST_RATE, 2)
    tds = round(gross_amount * config.TDS_RATE, 2)
    return fee, fee_gst, tds


def compute_tax_breakdown(result: dict) -> dict:
    settlement = result["settlement"]
    groups = result["groups"]

    reconciled_ids = set()
    for g in groups:
        if g["size"] > 1:
            reconciled_ids.update(g["settlement_ids"])

    excluded_count = 0
    excluded_value = 0.0

    total_fee_captured = 0.0
    total_gst_captured = 0.0
    total_tds_deducted = 0.0
    reconciled_fee = unreconciled_fee = 0.0
    reconciled_gst = unreconciled_gst = 0.0
    reconciled_tds = unreconciled_tds = 0.0

    tax_variance_records = []
    total_records_considered = 0

    for sid, srow in settlement.items():
        if srow.get("chargeback", False) or srow["gross_amount"] <= 0:
            excluded_count += 1
            excluded_value += abs(srow["gross_amount"])
            continue

        total_records_considered += 1
        fee, fee_gst, tds = srow["fee"], srow["fee_gst"], srow["tds"]

        total_fee_captured += fee
        total_gst_captured += fee_gst
        total_tds_deducted += tds

        if sid in reconciled_ids:
            reconciled_fee += fee
            reconciled_gst += fee_gst
            reconciled_tds += tds
        else:
            unreconciled_fee += fee
            unreconciled_gst += fee_gst
            unreconciled_tds += tds

        _, expected_gst, expected_tds = _expected_tax_lines(srow["gross_amount"])
        gst_diff = abs(fee_gst - expected_gst)
        tds_diff = abs(tds - expected_tds)
        if gst_diff > VARIANCE_TOLERANCE_RUPEES or tds_diff > VARIANCE_TOLERANCE_RUPEES:
            tax_variance_records.append({
                "settlement_id": sid,
                "expected_gst": expected_gst, "actual_gst": fee_gst,
                "expected_tds": expected_tds, "actual_tds": tds,
                "variance_rupees": round(max(gst_diff, tds_diff), 2),
            })

    return {
        "total_records_considered": total_records_considered,
        "total_fee_captured": round(total_fee_captured, 2),
        "total_gst_captured": round(total_gst_captured, 2),
        "total_tds_deducted": round(total_tds_deducted, 2),
        "reconciled_fee": round(reconciled_fee, 2),
        "unreconciled_fee": round(unreconciled_fee, 2),
        "reconciled_gst": round(reconciled_gst, 2),
        "unreconciled_gst": round(unreconciled_gst, 2),
        "reconciled_tds": round(reconciled_tds, 2),
        "unreconciled_tds": round(unreconciled_tds, 2),
        "excluded_chargeback_or_refund_count": excluded_count,
        "excluded_chargeback_or_refund_value": round(excluded_value, 2),
        "tax_variance_count": len(tax_variance_records),
        "tax_variance_records": tax_variance_records,
    }


def render_markdown(breakdown: dict) -> str:
    b = breakdown
    lines = []
    lines.append("## Tax-Line Breakdown\n")
    lines.append("| Metric | Amount (Rs) |")
    lines.append("|---|---|")
    lines.append(f"| Total fee captured | {b['total_fee_captured']:,.2f} |")
    lines.append(f"| Total GST (on fee) captured | {b['total_gst_captured']:,.2f} |")
    lines.append(f"| Total TDS deducted | {b['total_tds_deducted']:,.2f} |")
    lines.append(f"| Reconciled GST | {b['reconciled_gst']:,.2f} |")
    lines.append(f"| Unreconciled GST | {b['unreconciled_gst']:,.2f} |")
    lines.append(f"| Reconciled TDS | {b['reconciled_tds']:,.2f} |")
    lines.append(f"| Unreconciled TDS | {b['unreconciled_tds']:,.2f} |")
    lines.append(f"| Reconciled fee | {b['reconciled_fee']:,.2f} |")
    lines.append(f"| Unreconciled fee | {b['unreconciled_fee']:,.2f} |")
    lines.append("")

    lines.append(f"Excluded {b['excluded_chargeback_or_refund_count']} chargeback/refund settlement(s) "
                 f"(Rs {b['excluded_chargeback_or_refund_value']:,.2f}) from the totals above -- "
                 f"these carry no real Razorpay fee or tax by construction.\n")

    if not b["tax_variance_records"]:
        lines.append(f"No tax variances detected in {b['total_records_considered']} settlements checked.")
    else:
        lines.append(f"**{b['tax_variance_count']} tax variance(s) detected** "
                     f"out of {b['total_records_considered']} settlements checked:\n")
        lines.append("| Settlement | Expected GST (Rs) | Actual GST (Rs) | Expected TDS (Rs) | Actual TDS (Rs) | Variance (Rs) |")
        lines.append("|---|---|---|---|---|---|")
        for v in b["tax_variance_records"]:
            lines.append(f"| {v['settlement_id']} | {v['expected_gst']:,.2f} | {v['actual_gst']:,.2f} | "
                         f"{v['expected_tds']:,.2f} | {v['actual_tds']:,.2f} | {v['variance_rupees']:,.2f} |")

    return "\n".join(lines)
