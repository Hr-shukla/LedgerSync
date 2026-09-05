"""Shared data structures for the reconciliation pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class MatchEvent:
    """One audit-trail entry: what happened to one record at one tier."""
    record_id: str
    source: str  # "bank" | "settlement" | "ledger"
    tier: str  # "tier1_exact", "tier2_fuzzy", "tier3_grouping", "tier4_ai", "tier5_exception"
    outcome: str  # "matched" | "unresolved"
    matched_against: list = field(default_factory=list)  # list of record ids
    confidence: float = 0.0
    reasoning: str = ""
    exception_reason: str = ""


@dataclass
class MatchGroup:
    """A resolved (or partially resolved) cluster of records believed to be the same
    underlying transaction, spanning up to three sources."""
    group_id: str
    bank_ids: list = field(default_factory=list)
    settlement_ids: list = field(default_factory=list)
    ledger_ids: list = field(default_factory=list)
    tier: str = ""
    confidence: float = 1.0
    reasoning: str = ""


def parse_date(s: str) -> date:
    return date.fromisoformat(s)


def days_between(a: str, b: str) -> int:
    return abs((parse_date(a) - parse_date(b)).days)
