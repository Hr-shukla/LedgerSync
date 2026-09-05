"""Unit tests for the shared subset-sum search and union-find helpers."""
from pipeline.grouping import UnionFind, find_subset_matches


def test_find_subset_matches_finds_valid_combo():
    candidates = [("A", 100.0), ("B", 200.0), ("C", 50.0)]
    hits = find_subset_matches(300.0, candidates, tolerance=0.01)
    assert ("A", "B") in hits


def test_find_subset_matches_respects_tolerance():
    candidates = [("A", 100.0), ("B", 199.0)]
    assert find_subset_matches(300.0, candidates, tolerance=0.01) == []
    assert find_subset_matches(300.0, candidates, tolerance=1.5) == [("A", "B")]


def test_find_subset_matches_bounded_by_max_subset_size():
    candidates = [("A", 10.0), ("B", 10.0), ("C", 10.0), ("D", 10.0), ("E", 10.0)]
    # sum of all 5 == 50, but max_subset_size=2 should never find it
    assert find_subset_matches(50.0, candidates, tolerance=0.01, max_subset_size=2) == []


def test_union_find_merges_transitively():
    uf = UnionFind()
    uf.union("bank:B1", "settlement:S1")
    uf.union("settlement:S1", "ledger:L1")
    groups = uf.groups(["bank:B1", "settlement:S1", "ledger:L1", "bank:B2"])
    assert set(groups[uf.find("bank:B1")]) == {"bank:B1", "settlement:S1", "ledger:L1"}
    assert len(set(uf.find(k) for k in ["bank:B1", "settlement:S1", "ledger:L1"])) == 1
    assert uf.find("bank:B2") != uf.find("bank:B1")
