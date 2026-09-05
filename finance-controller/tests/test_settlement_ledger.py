"""Edge-case tests for the settlement<->ledger matching tiers (Tier 2-3)."""
from pipeline import settlement_ledger


def _settlement(id_, payment_id, utr, date, gross, chargeback=False):
    fee = round(gross * 0.02, 2)
    net = round(gross - fee - round(fee * 0.18, 2) - round(gross * 0.01, 2), 2)
    return {
        "settlement_id": id_, "payment_id": payment_id, "utr": utr, "settlement_date": date,
        "gross_amount": gross, "fee": fee, "fee_gst": round(fee * 0.18, 2),
        "tds": round(gross * 0.01, 2), "net_amount": net, "chargeback": chargeback,
    }


def _ledger(id_, date, amount, customer="Acme"):
    return {"ledger_id": id_, "invoice_date": date, "customer": customer, "invoice_amount": amount, "status": "invoiced"}


def test_tier2_amount_date_match():
    settlement = {"S1": _settlement("S1", "pay_1", "UTR1", "2026-01-05", 1000.0)}
    ledger = {"L1": _ledger("L1", "2026-01-04", 1000.0)}
    result = settlement_ledger.match(settlement, ledger)
    assert len(result.edges) == 1
    assert result.edges[0]["settlement_ids"] == ["S1"]
    assert result.edges[0]["ledger_ids"] == ["L1"]


def test_near_duplicate_amount_disambiguated_by_closest_date():
    """Two invoices share the exact same amount on nearly the same date --
    the settlement must link to the invoice with the closer date, not
    whichever happens to be iterated first."""
    settlement = {
        "S1": _settlement("S1", "pay_1", "UTR1", "2026-03-02", 1000.0),
        "S2": _settlement("S2", "pay_2", "UTR2", "2026-03-01", 1000.0),
    }
    ledger = {
        "L1": _ledger("L1", "2026-03-01", 1000.0),
        "L2": _ledger("L2", "2026-03-02", 1000.0),
    }
    result = settlement_ledger.match(settlement, ledger)
    by_settlement = {e["settlement_ids"][0]: e["ledger_ids"][0] for e in result.edges}
    assert by_settlement["S1"] == "L2"  # both dated 2026-03-02
    assert by_settlement["S2"] == "L1"  # both dated 2026-03-01


def test_tier3_partial_payment_subset_sum():
    settlement = {
        "S1": _settlement("S1", "pay_1", "UTR1", "2026-01-05", 4000.0),
        "S2": _settlement("S2", "pay_2", "UTR2", "2026-01-15", 6000.0),
    }
    ledger = {"L1": _ledger("L1", "2026-01-01", 10000.0)}
    result = settlement_ledger.match(settlement, ledger)
    grouping_edges = [e for e in result.edges if e["tier"] == "tier3_grouping"]
    assert len(grouping_edges) == 1
    assert sorted(grouping_edges[0]["settlement_ids"]) == ["S1", "S2"]
    assert grouping_edges[0]["ledger_ids"] == ["L1"]


def test_chargeback_never_matched_to_ledger():
    settlement = {"S1": _settlement("S1", "pay_1", "UTR1", "2026-01-05", -500.0, chargeback=True)}
    ledger = {"L1": _ledger("L1", "2026-01-05", 500.0)}
    result = settlement_ledger.match(settlement, ledger)
    assert result.edges == []


def test_unpaid_invoice_stays_unmatched():
    settlement = {"S1": _settlement("S1", "pay_1", "UTR1", "2026-01-05", 5000.0)}
    ledger = {"L1": _ledger("L1", "2026-06-01", 999999.0)}
    result = settlement_ledger.match(settlement, ledger)
    assert result.edges == []
    assert "L1" not in result.claimed_ledger


def test_excluded_duplicate_settlement_cannot_claim_ledger():
    """A settlement already flagged as a duplicate export on the bank axis
    must never be allowed to claim a ledger invoice out from under the real
    settlement."""
    settlement = {
        "S1": _settlement("S1", "pay_1", "UTR1", "2026-01-05", 1000.0),
        "S1_DUP": _settlement("S1_DUP", "pay_1", "UTR1", "2026-01-05", 1000.0),
    }
    ledger = {"L1": _ledger("L1", "2026-01-04", 1000.0)}
    result = settlement_ledger.match(settlement, ledger, exclude_settlement_ids={"S1_DUP"})
    assert len(result.edges) == 1
    assert result.edges[0]["settlement_ids"] == ["S1"]
    assert "S1_DUP" not in result.claimed_settlement
