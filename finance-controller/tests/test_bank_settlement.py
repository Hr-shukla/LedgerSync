"""Edge-case tests for the bank<->settlement matching tiers (Tier 1-3)."""
from pipeline import bank_settlement


def _bank(id_, date, amount, utr, narration="NEFT"):
    return {"bank_txn_id": id_, "date": date, "amount": amount, "utr": utr, "narration": narration}


def _settlement(id_, payment_id, utr, date, gross, net, chargeback=False):
    fee = round(gross * 0.02, 2)
    return {
        "settlement_id": id_, "payment_id": payment_id, "utr": utr, "settlement_date": date,
        "gross_amount": gross, "fee": fee, "fee_gst": round(fee * 0.18, 2),
        "tds": round(gross * 0.01, 2), "net_amount": net, "chargeback": chargeback,
    }


def test_tier1_exact_utr_match():
    bank = {"B1": _bank("B1", "2026-01-05", 966.40, "UTR111")}
    settlement = {"S1": _settlement("S1", "pay_1", "UTR111", "2026-01-04", 1000.0, 966.40)}
    result = bank_settlement.match(bank, settlement)
    assert len(result.edges) == 1
    assert result.edges[0]["tier"] == "tier1_exact"
    assert result.edges[0]["bank_ids"] == ["B1"]
    assert result.edges[0]["settlement_ids"] == ["S1"]


def test_tier1_flags_duplicate_settlement_and_keeps_lowest_id():
    bank = {"B1": _bank("B1", "2026-01-05", 966.40, "UTR111")}
    settlement = {
        "S2": _settlement("S2", "pay_1", "UTR111", "2026-01-04", 1000.0, 966.40),
        "S1": _settlement("S1", "pay_1", "UTR111", "2026-01-04", 1000.0, 966.40),
    }
    result = bank_settlement.match(bank, settlement)
    assert len(result.edges) == 1
    assert result.edges[0]["settlement_ids"] == ["S1"]  # lower id wins deterministically
    assert len(result.duplicate_settlements) == 1
    assert result.duplicate_settlements[0]["id"] == "S2"
    assert result.duplicate_settlements[0]["duplicate_of"] == "S1"


def test_tier2_fuzzy_match_on_mangled_utr():
    bank = {"B1": _bank("B1", "2026-01-06", 966.40, "UTR111XX")}  # mangled
    settlement = {"S1": _settlement("S1", "pay_1", "UTR111222333", "2026-01-04", 1000.0, 966.40)}
    result = bank_settlement.match(bank, settlement)
    assert len(result.edges) == 1
    assert result.edges[0]["tier"] == "tier2_fuzzy"


def test_tier3_aggregated_settlement_many_to_one():
    bank = {"B1": _bank("B1", "2026-01-05", 1932.80, "UTRAGG999")}
    settlement = {
        "S1": _settlement("S1", "pay_1", "UTR001", "2026-01-04", 1000.0, 966.40),
        "S2": _settlement("S2", "pay_2", "UTR002", "2026-01-04", 1000.0, 966.40),
    }
    result = bank_settlement.match(bank, settlement)
    grouping_edges = [e for e in result.edges if e["tier"] == "tier3_grouping"]
    assert len(grouping_edges) == 1
    assert grouping_edges[0]["bank_ids"] == ["B1"]
    assert sorted(grouping_edges[0]["settlement_ids"]) == ["S1", "S2"]


def test_tier3_split_settlement_one_to_many():
    settlement = {"S1": _settlement("S1", "pay_1", "UTR001", "2026-01-04", 2000.0, 1932.80)}
    bank = {
        "B1": _bank("B1", "2026-01-05", 966.40, "UTRSPLIT1"),
        "B2": _bank("B2", "2026-01-06", 966.40, "UTRSPLIT2"),
    }
    result = bank_settlement.match(bank, settlement)
    grouping_edges = [e for e in result.edges if e["tier"] == "tier3_grouping"]
    assert len(grouping_edges) == 1
    assert sorted(grouping_edges[0]["bank_ids"]) == ["B1", "B2"]
    assert grouping_edges[0]["settlement_ids"] == ["S1"]


def test_near_duplicate_amounts_do_not_cross_match():
    """Two unrelated transactions share the same amount and near-same date --
    a naive amount+date matcher would be tempted to cross them. UTR-based
    Tier 1 must resolve each to its own counterpart instead."""
    bank = {
        "B1": _bank("B1", "2026-03-01", 966.40, "UTRAAA"),
        "B2": _bank("B2", "2026-03-02", 966.40, "UTRBBB"),
    }
    settlement = {
        "S1": _settlement("S1", "pay_1", "UTRAAA", "2026-03-01", 1000.0, 966.40),
        "S2": _settlement("S2", "pay_2", "UTRBBB", "2026-03-02", 1000.0, 966.40),
    }
    result = bank_settlement.match(bank, settlement)
    assert len(result.edges) == 2
    by_bank = {e["bank_ids"][0]: e["settlement_ids"][0] for e in result.edges}
    assert by_bank["B1"] == "S1"
    assert by_bank["B2"] == "S2"


def test_orphan_bank_credit_stays_unmatched():
    bank = {"B1": _bank("B1", "2026-01-05", 500.0, "UTRNOMATCH")}
    settlement = {"S1": _settlement("S1", "pay_1", "UTR999", "2026-06-01", 10000.0, 9664.0)}
    result = bank_settlement.match(bank, settlement)
    assert result.edges == []
    assert "B1" not in result.claimed_bank
