"""Tests for the tax-line breakdown report (GST-on-fee / TDS aggregation)."""
from report import tax_breakdown


def _settlement(id_, gross, chargeback=False):
    fee = round(gross * 0.02, 2) if gross > 0 else 0.0
    fee_gst = round(fee * 0.18, 2) if gross > 0 else 0.0
    tds = round(gross * 0.01, 2) if gross > 0 else 0.0
    net = round(gross - fee - fee_gst - tds, 2)
    return {
        "settlement_id": id_, "gross_amount": gross, "fee": fee, "fee_gst": fee_gst,
        "tds": tds, "net_amount": net, "chargeback": chargeback,
    }


def _group(settlement_ids, size):
    return {"bank_ids": [], "settlement_ids": settlement_ids, "ledger_ids": [], "size": size}


def _build_result():
    settlement = {
        "S_MATCHED": _settlement("S_MATCHED", 1000.0),
        "S_EXCEPTION": _settlement("S_EXCEPTION", 2000.0),
        "S_CHARGEBACK": _settlement("S_CHARGEBACK", -500.0, chargeback=True),
        "S_REFUND": _settlement("S_REFUND", -300.0, chargeback=False),
        "S_VARIANT": _settlement("S_VARIANT", 1500.0),
    }
    # deliberately corrupt fee_gst on S_VARIANT so it disagrees with the
    # formula-expected value by more than Rs 1
    settlement["S_VARIANT"]["fee_gst"] = round(settlement["S_VARIANT"]["fee_gst"] + 5.0, 2)

    groups = [
        _group(["S_MATCHED"], 2),          # matched (size > 1) -> reconciled
        _group(["S_EXCEPTION"], 1),        # unresolved exception -> unreconciled
        _group(["S_CHARGEBACK"], 1),
        _group(["S_REFUND"], 1),
        _group(["S_VARIANT"], 2),          # matched but formula-inconsistent
    ]
    return {"settlement": settlement, "groups": groups}


def test_matched_settlement_counts_as_reconciled_with_zero_variance():
    result = _build_result()
    b = tax_breakdown.compute_tax_breakdown(result)

    s = result["settlement"]["S_MATCHED"]
    assert b["reconciled_gst"] >= s["fee_gst"]
    assert b["reconciled_tds"] >= s["tds"]
    assert b["reconciled_fee"] >= s["fee"]
    assert not any(v["settlement_id"] == "S_MATCHED" for v in b["tax_variance_records"])


def test_exception_settlement_counts_as_unreconciled():
    result = _build_result()
    b = tax_breakdown.compute_tax_breakdown(result)

    s = result["settlement"]["S_EXCEPTION"]
    assert b["unreconciled_gst"] >= s["fee_gst"]
    assert b["unreconciled_tds"] >= s["tds"]
    assert b["unreconciled_fee"] >= s["fee"]
    # still counted toward total captured
    assert b["total_gst_captured"] >= s["fee_gst"]
    assert b["total_tds_deducted"] >= s["tds"]


def test_chargeback_excluded_from_all_captured_and_reconciled_sums():
    result = _build_result()
    b = tax_breakdown.compute_tax_breakdown(result)

    # chargeback row has fee=fee_gst=tds=0 by construction, but confirm it's
    # tracked in the exclusion counters and not counted as a considered record
    assert b["excluded_chargeback_or_refund_count"] >= 1
    assert b["excluded_chargeback_or_refund_value"] >= 500.0
    assert b["total_records_considered"] == 3  # MATCHED, EXCEPTION, VARIANT only


def test_refund_excluded_same_as_chargeback():
    result = _build_result()
    b = tax_breakdown.compute_tax_breakdown(result)

    # both chargeback (-500) and refund (-300) contribute to the exclusion bucket
    assert b["excluded_chargeback_or_refund_count"] == 2
    assert b["excluded_chargeback_or_refund_value"] == 800.0


def test_tax_variance_detected_for_corrupted_fee_gst():
    result = _build_result()
    b = tax_breakdown.compute_tax_breakdown(result)

    assert b["tax_variance_count"] == 1
    rec = b["tax_variance_records"][0]
    assert rec["settlement_id"] == "S_VARIANT"

    gross = 1500.0
    expected_fee = round(gross * 0.02, 2)
    expected_gst = round(expected_fee * 0.18, 2)
    expected_tds = round(gross * 0.01, 2)
    actual_gst = round(expected_gst + 5.0, 2)

    assert rec["expected_gst"] == expected_gst
    assert rec["actual_gst"] == actual_gst
    assert rec["expected_tds"] == expected_tds
    assert rec["actual_tds"] == expected_tds
    assert rec["variance_rupees"] == round(abs(actual_gst - expected_gst), 2)


def test_render_markdown_contains_section_and_totals():
    result = _build_result()
    b = tax_breakdown.compute_tax_breakdown(result)
    md = tax_breakdown.render_markdown(b)

    assert "Tax-Line Breakdown" in md
    assert f"{b['total_gst_captured']:,.2f}" in md
    assert f"{b['total_tds_deducted']:,.2f}" in md
    assert "tax variance" in md.lower()
