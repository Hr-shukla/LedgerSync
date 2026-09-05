"""Task 6: exercise every API endpoint against a real (small, AI-disabled for
speed/determinism) pipeline run, using FastAPI's TestClient -- no live server,
no network calls, no LLM quota spent."""
import json

import pytest
from fastapi.testclient import TestClient

from data_generator.generate import build as generate_dataset
from pipeline.orchestrator import Orchestrator
from report.generate import build_comparison, write_json


@pytest.fixture
def api_client(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"
    generate_dataset(seed=42, n_clean_groups=20, out_dir=data_dir)

    result_no_ai = Orchestrator(data_dir, disable_ai=True).run()
    result_ai = Orchestrator(data_dir, disable_ai=True).run()  # no key in test env -> same as baseline
    comparison = build_comparison(result_no_ai, result_ai, data_dir)
    write_json(comparison, output_dir / "report.json")
    (output_dir / "groups.json").write_text(json.dumps(result_ai["groups"], indent=2), encoding="utf-8")
    (output_dir / "exceptions.json").write_text(json.dumps(result_ai["exceptions"], indent=2), encoding="utf-8")
    (output_dir / "run_history.jsonl").write_text(
        json.dumps({"run_at": "2026-01-01T00:00:00+00:00", "seed": 42,
                    "match_rate_pct": comparison["with_ai"]["metrics"]["overall_match_rate_pct"]}) + "\n",
        encoding="utf-8",
    )

    import api.main as api_main
    monkeypatch.setattr(api_main, "DATA_DIR", data_dir)
    monkeypatch.setattr(api_main, "OUTPUT_DIR", output_dir)
    api_main._state.clear()

    return TestClient(api_main.app)


def test_overview(api_client):
    r = api_client.get("/overview")
    assert r.status_code == 200
    body = r.json()
    assert "match_rate_pct" in body and "value_at_risk_rupees" in body


def test_transactions_pagination_and_filters(api_client):
    r = api_client.get("/transactions", params={"page": 1, "page_size": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["filter_counts"]["all"] == body["filter_counts"]["matched"] + body["filter_counts"]["exception"]
    assert len(body["items"]) <= 5

    r2 = api_client.get("/transactions", params={"status": "exception"})
    assert all(item["status"] == "exception" for item in r2.json()["items"])


def test_transaction_audit_detail(api_client):
    txns = api_client.get("/transactions", params={"status": "matched", "page_size": 1}).json()["items"]
    assert txns, "expected at least one matched transaction in this seed"
    txn_id = txns[0]["id"]
    r = api_client.get(f"/transactions/{txn_id}/audit")
    assert r.status_code == 200
    assert "decision_tree" in r.json() and "comparison" in r.json()

    r404 = api_client.get("/transactions/grp_99999/audit")
    assert r404.status_code == 404


def test_exceptions_and_resolve_roundtrip(api_client):
    r = api_client.get("/exceptions")
    assert r.status_code == 200
    body = r.json()
    assert body["total_count"] == sum(s["count"] for s in body["summary"])
    if not body["items"]:
        pytest.skip("no exceptions in this seed/groups combination")
    record_id = body["items"][0]["record_id"]
    assert body["items"][0]["resolved"] is False
    open_count_before = body["total_count"]

    resolve_resp = api_client.post(f"/exceptions/{record_id}/resolve", json={"note": "checked manually"})
    assert resolve_resp.status_code == 200

    # Resolved means open everywhere: it drops out of the default (open-only)
    # list and both total_count and resolved_count reflect it immediately.
    r2 = api_client.get("/exceptions")
    body2 = r2.json()
    assert body2["total_count"] == open_count_before - 1
    assert not any(e["record_id"] == record_id for e in body2["items"])

    # include_resolved=true is how you audit it -- still there, marked resolved.
    r2_all = api_client.get("/exceptions", params={"include_resolved": "true"})
    updated = next(e for e in r2_all.json()["items"] if e["record_id"] == record_id)
    assert updated["resolved"] is True
    assert updated["resolution"]["note"] == "checked manually"

    # /overview's open count must agree with /exceptions' open count.
    overview_after_resolve = api_client.get("/overview").json()
    assert overview_after_resolve["open_exceptions_count"] == open_count_before - 1

    unresolve_resp = api_client.post(f"/exceptions/{record_id}/unresolve")
    assert unresolve_resp.status_code == 200
    r3 = api_client.get("/exceptions")
    body3 = r3.json()
    assert body3["total_count"] == open_count_before
    assert any(e["record_id"] == record_id for e in body3["items"])


def test_resolve_unknown_record_404s(api_client):
    r = api_client.post("/exceptions/NOT_A_REAL_ID/resolve", json={})
    assert r.status_code == 404


def test_audit_log(api_client):
    r = api_client.get("/audit-log")
    assert r.status_code == 200
    assert len(r.json()["runs"]) == 1


def test_forecast_endpoint(api_client):
    r = api_client.get("/forecast", params={"horizons": "7,14,30"})
    assert r.status_code == 200
    body = r.json()
    assert set(body["horizons"].keys()) >= {"7", "14", "30"}
    assert "overdue" in body


def test_tax_summary_endpoint(api_client):
    r = api_client.get("/tax-summary")
    assert r.status_code == 200
    body = r.json()
    assert "total_gst_captured" in body and "total_tds_deducted" in body
