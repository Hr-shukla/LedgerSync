"""Fee/TDS/GST tolerance model.

Used wherever we need to decide if two amounts are "the same transaction"
under a known or estimated deduction, rather than a flat epsilon.
"""
from __future__ import annotations

from . import config


def net_of_gross(gross: float) -> float:
    """Best-estimate net amount after Razorpay fee + GST-on-fee + TDS."""
    return round(gross * config.NET_OF_GROSS_FACTOR, 2)


def estimated_net_range(gross: float) -> tuple[float, float]:
    """Plausible (low, high) net amount band for a gross amount, used when
    there is no settlement leg available to give the exact deduction figures."""
    center = net_of_gross(gross)
    slack = abs(gross) * config.FEE_MODEL_SLACK
    lo, hi = sorted((center - slack, center + slack))
    return lo, hi


def amounts_match(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def net_vs_net_match(bank_amount: float, settlement_net: float) -> bool:
    return amounts_match(bank_amount, settlement_net, config.NET_VS_NET_TOLERANCE)


def gross_vs_gross_match(settlement_gross: float, ledger_amount: float) -> bool:
    return amounts_match(settlement_gross, ledger_amount, config.GROSS_VS_GROSS_TOLERANCE)


def bank_within_estimated_net_of_ledger(bank_amount: float, ledger_amount: float) -> bool:
    lo, hi = estimated_net_range(ledger_amount)
    return lo <= bank_amount <= hi
