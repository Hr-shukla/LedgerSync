"""Bounded subset-sum search and union-find, shared by Tier 3 across both
source pairs (bank<->settlement, settlement<->ledger).

The subset-sum search is deliberately bounded: candidates are pre-filtered to
a date window and a small pool size before any combinatorial search runs, so
this never degenerates into brute force over the whole dataset.
"""
from __future__ import annotations

import itertools

from . import config


def find_subset_matches(target: float, candidates: list[tuple[str, float]], tolerance: float,
                         max_subset_size: int = config.MAX_SUBSET_SIZE) -> list[tuple[str, ...]]:
    """candidates: list of (id, amount). Returns list of id-tuples whose amounts
    sum to `target` within `tolerance`, searching subset sizes 2..max_subset_size
    (size-1 matches are handled by earlier tiers, not here).

    Candidate pool is expected to already be date-windowed and capped by the
    caller (config.MAX_CANDIDATE_POOL) before reaching this function.
    """
    pool = candidates[:config.MAX_CANDIDATE_POOL]
    found = []
    ids = [c[0] for c in pool]
    amounts = [c[1] for c in pool]
    n = min(len(pool), config.MAX_CANDIDATE_POOL)
    max_size = min(max_subset_size, n)
    for size in range(2, max_size + 1):
        for combo_idx in itertools.combinations(range(n), size):
            s = sum(amounts[i] for i in combo_idx)
            if abs(s - target) <= tolerance:
                found.append(tuple(ids[i] for i in combo_idx))
    return found


class UnionFind:
    """Disjoint-set over composite keys like 'bank:BNK000001', used to merge
    bank<->settlement edges and settlement<->ledger edges into final 3-way
    reconciliation groups."""

    def __init__(self):
        self._parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self._parent.setdefault(x, x)
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb

    def groups(self, keys: list[str]) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for k in keys:
            out.setdefault(self.find(k), []).append(k)
        return out
