"""Tests for the forward cash forecaster (empirical lag distribution + date
arithmetic over unmatched/pending settlements)."""
from forecast import cash_forecast


def _bank(id_, date, amount, utr, narration="NEFT"):
    return {"bank_txn_id": id_, "date": date, "amount": amount, "utr": utr, "narration": narration}


def _settlement(id_, payment_id, utr, date, gross, net, chargeback=False):
    fee = round(gross * 0.02, 2)
    return {
        "settlement_id": id_, "payment_id": payment_id, "utr": utr, "settlement_date": date,
        "gross_amount": gross, "fee": fee, "fee_gst": round(fee * 0.18, 2),
        "tds": round(gross * 0.01, 2), "net_amount": net, "chargeback": chargeback,
    }


def test_lag_distribution_median_from_three_matched_pairs():
    # Three clean tier-1 matches with lags of 2, 3 and 4 days -> median 3.
    bank = {
        "B1": _bank("B1", "2026-01-03", 966.40, "UTR001"),
        "B2": _bank("B2", "2026-01-04", 966.40, "UTR002"),
        "B3": _bank("B3", "2026-01-05", 966.40, "UTR003"),
    }
    settlement = {
        "S1": _settlement("S1", "pay_1", "UTR001", "2026-01-01", 1000.0, 966.40),
        "S2": _settlement("S2", "pay_2", "UTR002", "2026-01-01", 1000.0, 966.40),
        "S3": _settlement("S3", "pay_3", "UTR003", "2026-01-01", 1000.0, 966.40),
    }
    forecast = cash_forecast.forecast_from_records(bank, settlement, as_of_date="2026-01-05")
    dist = forecast["lag_distribution"]
    assert dist["count"] == 3
    assert dist["median"] == 3
    assert dist["min"] == 2
    assert dist["max"] == 4
    assert forecast["used_default_lag"] is False


def test_unmatched_positive_settlement_is_pending():
    bank = {}
    settlement = {"S1": _settlement("S1", "pay_1", "UTR999", "2026-01-01", 1000.0, 966.40)}
    forecast = cash_forecast.forecast_from_records(bank, settlement, as_of_date="2026-01-01")
    assert forecast["pending_count"] == 1
    assert forecast["pending_total_rupees"] == 966.40
    # no matched history -> default lag (3 days) puts the projected credit
    # date well inside every default horizon (7/14/30 days)
    assert "S1" in forecast["horizons"][30]["settlement_ids"]


def test_chargeback_and_negative_net_are_not_pending():
    bank = {}
    settlement = {
        "S1": _settlement("S1", "pay_1", "UTR001", "2026-01-01", 1000.0, 966.40, chargeback=True),
        "S2": _settlement("S2", "pay_2", "UTR002", "2026-01-01", 1000.0, -500.0),
    }
    forecast = cash_forecast.forecast_from_records(bank, settlement, as_of_date="2026-01-01")
    assert forecast["pending_count"] == 0
    assert forecast["pending_total_rupees"] == 0


def test_horizon_windows_only_include_settlements_landing_inside_them():
    # No matched history at all -> falls back to the documented default lag.
    bank = {}
    settlement = {
        # projected credit date = settlement_date + DEFAULT_LAG_DAYS(3) = 2026-01-04 -> inside 7d window
        "S_SOON": _settlement("S_SOON", "pay_1", "UTRA", "2026-01-01", 1000.0, 900.0),
        # projected credit date = 2026-01-01 + 3 = 2026-01-04 ... need a later one for 30d only
        "S_LATER": _settlement("S_LATER", "pay_2", "UTRB", "2026-01-20", 1000.0, 900.0),
    }
    forecast = cash_forecast.forecast_from_records(bank, settlement, as_of_date="2026-01-01",
                                                     horizons=(7, 30))
    assert forecast["used_default_lag"] is True
    assert forecast["effective_lag_days"] == cash_forecast.DEFAULT_LAG_DAYS

    ids_7 = set(forecast["horizons"][7]["settlement_ids"])
    ids_30 = set(forecast["horizons"][30]["settlement_ids"])
    assert ids_7 == {"S_SOON"}
    assert ids_30 == {"S_SOON", "S_LATER"}
    assert forecast["horizons"][7]["expected_inflow_rupees"] == 900.0
    assert forecast["horizons"][30]["expected_inflow_rupees"] == 1800.0


def test_overdue_settlements_are_surfaced_not_silently_dropped():
    """A pending settlement whose projected lag-adjusted date is already on
    or before as_of_date must not vanish -- it should show up in the
    'overdue' bucket rather than falling out of every horizon window with no
    explanation."""
    bank = {}
    settlement = {
        "S_OVERDUE": _settlement("S_OVERDUE", "pay_1", "UTRA", "2026-01-01", 1000.0, 900.0),
    }
    forecast = cash_forecast.forecast_from_records(bank, settlement, as_of_date="2026-01-10", horizons=(7, 30))
    assert forecast["horizons"][7]["settlement_ids"] == []
    assert forecast["horizons"][30]["settlement_ids"] == []
    assert forecast["overdue"]["count"] == 1
    assert forecast["overdue"]["settlement_ids"] == ["S_OVERDUE"]
    assert forecast["overdue"]["value_rupees"] == 900.0


def test_render_markdown_contains_horizon_numbers():
    bank = {}
    settlement = {"S1": _settlement("S1", "pay_1", "UTR001", "2026-01-01", 1000.0, 966.40)}
    forecast = cash_forecast.forecast_from_records(bank, settlement, as_of_date="2026-01-01",
                                                     horizons=(7, 14, 30))
    md = cash_forecast.render_markdown(forecast)
    assert "## Forward Cash Forecast" in md
    assert "7d" in md and "14d" in md and "30d" in md
    assert "966.40" in md or "0.00" in md  # inflow appears somewhere in the table
