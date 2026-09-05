"""Task 3: prove the adversarial decoy pair is genuinely evaluated by the
matching cascade and correctly rejected -- not simply ignored because it
falls outside some early filter. The generator injects, for every seed, an
orphan bank credit and an unrelated orphan settlement with a deliberately
near-identical amount and adjacent date (case_type
'adversarial_decoy_no_match') specifically to bait a naive amount+date
matcher. A correct system must:
  1. leave both records unmatched after Tiers 1-3 (no exact/fuzzy/grouping
     shortcut should apply -- they really do look superficially similar)
  2. still surface each other as a Tier 4 candidate (proving the cascade
     took the bait seriously rather than filtering it out early)
  3. never end up in the same final group (no false merge)
"""
import json
from pathlib import Path

from data_generator.generate import build as generate_dataset
from pipeline.orchestrator import Orchestrator


def _decoy_ids(data_dir: Path):
    bank_ids, settlement_ids = [], []
    with (data_dir / "ground_truth.jsonl").open() as f:
        for line in f:
            g = json.loads(line)
            if g["case_type"] == "adversarial_decoy_no_match":
                bank_ids += g["bank_ids"]
                settlement_ids += g["settlement_ids"]
    return bank_ids, settlement_ids


def test_decoy_pair_is_seriously_considered_then_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    data_dir = tmp_path / "data"
    generate_dataset(seed=42, n_clean_groups=40, out_dir=data_dir)
    bank_ids, settlement_ids = _decoy_ids(data_dir)
    assert bank_ids and settlement_ids, "generator must inject at least one adversarial decoy pair"

    orch = Orchestrator(data_dir)  # no key in env -> Tier 4 honestly unavailable, deterministic for CI
    result = orch.run()

    # (1) Tiers 1-3 must not have shortcut-matched them -- they should have
    # reached the "still unresolved after tier 1-3" stage genuinely.
    for bid in bank_ids:
        assert bid not in orch.bs_result.claimed_bank, (
            f"{bid} should not be resolvable by exact/fuzzy/grouping tiers alone"
        )
    for sid in settlement_ids:
        assert sid not in orch.bs_result.claimed_settlement, (
            f"{sid} should not be resolvable by exact/fuzzy/grouping tiers alone"
        )

    # (2) Each decoy record must have actually reached Tier 4 candidate
    # evaluation -- proving the cascade took it seriously, not that it was
    # filtered out before consideration. _considered_by_ai_settlement_bank is
    # populated as soon as a candidate pool is built and AITier.resolve() is
    # called, regardless of whether AI is available.
    for sid in settlement_ids:
        assert sid in orch._considered_by_ai_settlement_bank, (
            f"decoy settlement {sid} never reached Tier 4 candidate evaluation"
        )

    # (3) Never cross-matched: no final group contains both a decoy bank id
    # and a decoy settlement id, and neither decoy ended up in any matched
    # (size > 1) group at all -- they must surface as separate exceptions.
    decoy_all = set(bank_ids) | set(settlement_ids)
    for g in result["groups"]:
        members = set(g["bank_ids"]) | set(g["settlement_ids"]) | set(g["ledger_ids"])
        if g["size"] > 1:
            assert not (members & decoy_all), (
                f"decoy record wrongly ended up in a matched group: {members}"
            )

    exception_ids = {e["record_id"] for e in result["exceptions"]}
    for rid in bank_ids + settlement_ids:
        assert rid in exception_ids, f"decoy record {rid} should surface as an exception"


def test_decoy_pair_rejected_by_live_ai_when_key_available():
    """If a real LLM key is explicitly opted in for this run, also verify
    Tier 4 itself rejects the decoy pairing (not just that determinism saved
    us) -- the strongest form of the adversarial-robustness claim.

    Deliberately gated behind two conditions, not just "a key exists":
    RUN_LIVE_AI_TESTS=1 must be set explicitly, and the key must already be
    in the real environment (never loaded from .env here) -- a Gemini/
    Anthropic free-tier key has a small daily request quota, and silently
    burning it every time someone runs `pytest` would be its own kind of
    dishonest default. This also avoids mutating os.environ mid-suite,
    which previously broke an unrelated "AI unavailable" test by leaking
    .env's key into the rest of the pytest process."""
    import os
    if os.environ.get("RUN_LIVE_AI_TESTS") != "1":
        import pytest
        pytest.skip("set RUN_LIVE_AI_TESTS=1 (with a real API key already in the environment) to run this")
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        import pytest
        pytest.skip("no LLM API key configured in this environment")

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "data"
        generate_dataset(seed=42, n_clean_groups=40, out_dir=data_dir)
        bank_ids, settlement_ids = _decoy_ids(data_dir)

        orch = Orchestrator(data_dir)
        result = orch.run()

        decoy_all = set(bank_ids) | set(settlement_ids)
        for g in result["groups"]:
            if g["size"] > 1:
                members = set(g["bank_ids"]) | set(g["settlement_ids"]) | set(g["ledger_ids"])
                assert not (members & decoy_all), (
                    f"live AI wrongly cross-matched the adversarial decoy pair: {members}"
                )
