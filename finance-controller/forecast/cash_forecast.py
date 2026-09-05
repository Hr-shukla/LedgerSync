"""Forward cash forecaster: projects when money already reported by Razorpay
as "settled" will actually land in the bank, using nothing but the observed
historical lag between settlement_date and bank credit date. No modelling,
no smoothing -- an empirical lag distribution plus date arithmetic.
"""
from __future__ import annotations

import statistics
from datetime import timedelta
from pathlib import Path

from pipeline import bank_settlement, loader
from pipeline.models import parse_date

DEFAULT_LAG_DAYS = 3  # used only when there is zero matched history to learn a lag from
MIN_TRUSTED_PAIRS = 3  # below this, the median is reported but flagged as low-confidence


def _edge_lag_days(edge: dict, bank: dict, settlement: dict) -> int | None:
    if not edge["bank_ids"] or not edge["settlement_ids"]:
        return None
    # An edge can group several bank rows and/or several settlement rows
    # (aggregated/split settlements). Rather than trying to pair individual
    # ids within a group, we take the earliest date on each side -- the
    # simplest defensible proxy for "when did this batch settle" vs "when did
    # money first show up in the bank for it".
    settlement_date = min(settlement[sid]["settlement_date"] for sid in edge["settlement_ids"])
    bank_date = min(bank[bid]["date"] for bid in edge["bank_ids"])
    return (parse_date(bank_date) - parse_date(settlement_date)).days


def _lag_distribution(lags: list[int]) -> dict:
    count = len(lags)
    if count == 0:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None, "p25": None, "p75": None}
    if count == 1:
        v = lags[0]
        return {"count": 1, "min": v, "max": v, "mean": v, "median": v, "p25": v, "p75": v}
    q1, _, q3 = statistics.quantiles(lags, n=4, method="inclusive")
    return {
        "count": count,
        "min": min(lags),
        "max": max(lags),
        "mean": round(statistics.mean(lags), 2),
        "median": statistics.median(lags),
        "p25": q1,
        "p75": q3,
    }


def _is_pending(sid: str, settlement: dict, result: bank_settlement.BankSettlementResult, duplicate_ids: set) -> bool:
    if sid in result.claimed_settlement or sid in duplicate_ids:
        return False
    row = settlement[sid]
    # chargebacks/refunds never produce a future bank credit by design -- they
    # represent money going the other way, not an inbound settlement to wait for.
    return not row["chargeback"] and row["net_amount"] > 0


def compute_forecast(data_dir: Path, as_of_date: str | None = None, horizons=(7, 14, 30)) -> dict:
    data_dir = Path(data_dir)
    bank = loader.load_bank(data_dir)
    settlement = loader.load_settlements(data_dir)
    return forecast_from_records(bank, settlement, as_of_date=as_of_date, horizons=horizons)


def forecast_from_records(bank: dict, settlement: dict, as_of_date: str | None = None,
                           horizons=(7, 14, 30)) -> dict:
    """Pure version of compute_forecast that takes already-loaded bank/settlement
    dicts (same shape pipeline.loader produces) instead of a data directory --
    kept separate so the projection logic is testable without touching disk."""
    result = bank_settlement.match(bank, settlement)

    lags = []
    for edge in result.edges:
        lag = _edge_lag_days(edge, bank, settlement)
        if lag is not None:
            lags.append(lag)
    lag_dist = _lag_distribution(lags)

    used_default_lag = lag_dist["median"] is None
    effective_lag = DEFAULT_LAG_DAYS if used_default_lag else lag_dist["median"]

    if as_of_date is None:
        all_dates = [r["date"] for r in bank.values()] + [r["settlement_date"] for r in settlement.values()]
        as_of_date = max(all_dates)
    as_of = parse_date(as_of_date)

    duplicate_ids = {d["id"] for d in result.duplicate_settlements}
    pending_ids = [sid for sid in settlement if _is_pending(sid, settlement, result, duplicate_ids)]

    projected = {}
    for sid in pending_ids:
        settle_date = parse_date(settlement[sid]["settlement_date"])
        projected[sid] = settle_date + timedelta(days=round(effective_lag))

    pending_total = round(sum(settlement[sid]["net_amount"] for sid in pending_ids), 2)

    horizon_out = {}
    for h in horizons:
        window_start, window_end = as_of, as_of + timedelta(days=h)
        in_window = [sid for sid in pending_ids if window_start < projected[sid] <= window_end]
        horizon_out[h] = {
            "horizon_days": h,
            "expected_inflow_rupees": round(sum(settlement[sid]["net_amount"] for sid in in_window), 2),
            "settlement_count": len(in_window),
            "settlement_ids": sorted(in_window),
        }

    # A pending settlement whose projected landing date is already <= as_of_date
    # would otherwise fall through every horizon window and vanish from the
    # report with no explanation -- e.g. as_of_date defaults to the last date
    # seen in a static batch, so most "pending" settlements are already past
    # their expected lag. Surface these explicitly as overdue rather than
    # silently dropping them; in a live daily/hourly run as_of_date would be
    # the real current date and this bucket would normally be small or empty.
    overdue_ids = [sid for sid in pending_ids if projected[sid] <= as_of]
    overdue = {
        "count": len(overdue_ids),
        "value_rupees": round(sum(settlement[sid]["net_amount"] for sid in overdue_ids), 2),
        "settlement_ids": sorted(overdue_ids),
    }

    if lag_dist["count"] == 0:
        basis = (f"No matched bank/settlement pairs were available, so a default lag of "
                 f"{DEFAULT_LAG_DAYS} days was assumed. This has no empirical basis and should "
                 f"not be trusted for planning.")
    elif lag_dist["count"] < MIN_TRUSTED_PAIRS:
        basis = (f"Historical lag = observed days between settlement_date and bank credit date, "
                 f"measured across only {lag_dist['count']} reconciled pair(s) -- too few to be "
                 f"statistically reliable. Pending settlement dates are shifted by the median "
                 f"observed lag ({effective_lag} days) as a best-effort estimate only.")
    else:
        basis = (f"Historical lag = observed days between settlement_date and bank credit date "
                 f"across {lag_dist['count']} reconciled pairs. Pending settlement dates are "
                 f"shifted by the median observed lag ({effective_lag} days) to estimate when "
                 f"each will land in the bank.")

    return {
        "as_of_date": as_of_date,
        "lag_distribution": lag_dist,
        "used_default_lag": used_default_lag,
        "effective_lag_days": effective_lag,
        "pending_total_rupees": pending_total,
        "pending_count": len(pending_ids),
        "horizons": horizon_out,
        "overdue": overdue,
        "methodology": basis,
    }


def render_markdown(forecast: dict) -> str:
    lines = []
    lines.append("## Forward Cash Forecast\n")
    lines.append(f"As of **{forecast['as_of_date']}**, {forecast['pending_count']} settlement(s) "
                 f"totalling Rs {forecast['pending_total_rupees']:,.2f} have not yet shown up as a "
                 f"bank credit.\n")
    lines.append(forecast["methodology"] + "\n")
    lines.append("| Horizon | Expected Inflow (Rs) | Settlements Pending |")
    lines.append("|---|---|---|")
    for h in sorted(forecast["horizons"]):
        row = forecast["horizons"][h]
        lines.append(f"| {h}d | {row['expected_inflow_rupees']:,.2f} | {row['settlement_count']} |")
    lines.append("")

    overdue = forecast.get("overdue")
    if overdue and overdue["count"]:
        lines.append(f"**{overdue['count']} pending settlement(s) totalling Rs {overdue['value_rupees']:,.2f} "
                     f"are already past their expected landing date** as of {forecast['as_of_date']} -- "
                     f"these are NOT included in the horizon buckets above since they're overdue, not "
                     f"upcoming. In a live daily run this bucket should normally be small; a large one "
                     f"is worth investigating as a settlement delay, not a forecasting gap.\n")

    d = forecast["lag_distribution"]
    if d["count"]:
        lines.append(f"_Lag distribution (days): median={d['median']}, p25={d['p25']}, "
                     f"p75={d['p75']}, min={d['min']}, max={d['max']}, n={d['count']}_")
    else:
        lines.append("_Lag distribution: no matched pairs available._")

    return "\n".join(lines)
