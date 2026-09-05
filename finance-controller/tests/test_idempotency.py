"""Task 9: the pipeline must be safe to run on a recurring (daily/hourly)
schedule against the same underlying data -- re-running must not duplicate
audit rows, must not silently drift the headline metrics, and must never
undo a human's exception resolution unless they explicitly re-trigger it.
"""
import json

from data_generator.generate import build as generate_dataset
from pipeline.orchestrator import Orchestrator
from report import grading, metrics
from audit.store import write_audit_trail
from api.resolutions import ResolutionStore


def test_two_runs_on_same_dataset_produce_identical_metrics(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    data_dir = tmp_path / "data"
    generate_dataset(seed=42, n_clean_groups=30, out_dir=data_dir)

    result_a = Orchestrator(data_dir).run()
    result_b = Orchestrator(data_dir).run()

    m_a, m_b = metrics.compute(result_a), metrics.compute(result_b)
    assert m_a["overall_match_rate_pct"] == m_b["overall_match_rate_pct"]
    assert m_a["reconciled_value_rupees"] == m_b["reconciled_value_rupees"]
    assert m_a["exception_count_by_reason"] == m_b["exception_count_by_reason"]

    gt = grading.load_ground_truth(data_dir)
    g_a, g_b = grading.grade(result_a["groups"], gt), grading.grade(result_b["groups"], gt)
    assert g_a["precision"] == g_b["precision"]
    assert g_a["recall"] == g_b["recall"]
    assert g_a["false_match_rate"] == g_b["false_match_rate"]


def test_audit_trail_does_not_duplicate_rows_on_rerun(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    data_dir = tmp_path / "data"
    generate_dataset(seed=7, n_clean_groups=25, out_dir=data_dir)
    db_path = tmp_path / "output" / "audit_trail.db"

    result_a = Orchestrator(data_dir).run()
    write_audit_trail(result_a["audit"], db_path)
    count_after_first = _row_count(db_path)

    result_b = Orchestrator(data_dir).run()
    write_audit_trail(result_b["audit"], db_path)
    count_after_second = _row_count(db_path)

    assert count_after_first == count_after_second == len(result_a["audit"]) == len(result_b["audit"])


def test_rerunning_pipeline_never_undoes_a_human_resolution(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    generate_dataset(seed=13, n_clean_groups=25, out_dir=data_dir)

    result_a = Orchestrator(data_dir).run()
    assert result_a["exceptions"], "expected at least one exception to resolve in this seed"
    record_id = result_a["exceptions"][0]["record_id"]

    store = ResolutionStore(output_dir / "resolutions.json")
    store.resolve(record_id, note="reviewed, false alarm", resolved_by="ops-team")
    assert store.get(record_id)["resolved"] is True

    # Simulate a second scheduled run of the SAME pipeline against the SAME
    # data -- this must not touch resolutions.json at all.
    write_audit_trail(Orchestrator(data_dir).run()["audit"], output_dir / "audit_trail.db")

    still_resolved = store.get(record_id)
    assert still_resolved is not None
    assert still_resolved["resolved"] is True
    assert still_resolved["note"] == "reviewed, false alarm"


def _row_count(db_path) -> int:
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT COUNT(*) FROM audit_trail").fetchone()[0]
    finally:
        conn.close()
