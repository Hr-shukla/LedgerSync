"""Regression guard: runs the full pipeline against a fixed-seed dataset and
fails loudly if match rate or precision drops below the baseline in
pipeline/config.py. This is the test the brief calls for -- a fixed dataset,
graded against its own hidden ground truth, checked on every run."""
import tempfile
from pathlib import Path

from data_generator.generate import build as generate_dataset
from pipeline import config
from pipeline.orchestrator import Orchestrator
from report import grading, metrics


def test_fixed_seed_dataset_meets_baseline(tmp_path):
    # disable_ai=True regardless of environment: this regression guard must
    # stay fast, deterministic, and offline -- Tiers 1-3-5 only. The
    # AI-enabled path is covered separately (and, being LLM-dependent, is
    # inherently non-deterministic) by tests/test_adversarial_decoy.py's
    # opt-in live test and by scripts/multi_seed_eval.py.
    data_dir = tmp_path / "data"
    generate_dataset(seed=42, n_clean_groups=40, out_dir=data_dir)

    result = Orchestrator(data_dir, disable_ai=True).run()
    m = metrics.compute(result)
    gt = grading.load_ground_truth(data_dir)
    g = grading.grade(result["groups"], gt)

    assert m["overall_match_rate_pct"] / 100 >= config.BASELINE_MATCH_RATE, (
        f"match rate {m['overall_match_rate_pct']}% dropped below baseline "
        f"{config.BASELINE_MATCH_RATE*100}%"
    )
    assert g["precision"] >= config.BASELINE_PRECISION, (
        f"precision {g['precision']*100:.1f}% dropped below baseline {config.BASELINE_PRECISION*100}%"
    )
    assert g["false_match_rate"] == 0.0, (
        f"false-match rate {g['false_match_rate']*100:.1f}% -- no hallucinated matches is non-negotiable"
    )


def test_deterministic_generation_is_reproducible(tmp_path):
    dir_a, dir_b = tmp_path / "a", tmp_path / "b"
    stats_a = generate_dataset(seed=7, n_clean_groups=20, out_dir=dir_a)
    stats_b = generate_dataset(seed=7, n_clean_groups=20, out_dir=dir_b)
    assert stats_a == stats_b
    assert (dir_a / "bank_statement.csv").read_text() == (dir_b / "bank_statement.csv").read_text()
    assert (dir_a / "ground_truth.jsonl").read_text() == (dir_b / "ground_truth.jsonl").read_text()


def test_batch_size_meets_minimum_volume(tmp_path):
    data_dir = tmp_path / "data"
    stats = generate_dataset(seed=42, n_clean_groups=40, out_dir=data_dir)
    assert stats["bank_count"] >= 50
    assert stats["settlement_count"] >= 50
    assert stats["ledger_count"] >= 50
    assert stats["bank_count"] + stats["settlement_count"] + stats["ledger_count"] >= 150
