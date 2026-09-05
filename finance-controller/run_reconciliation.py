#!/usr/bin/env python
"""Single entrypoint: generate (or reuse) the synthetic dataset, run the
5-tier reconciliation pipeline TWICE -- once with Tier 4 (AI) disabled as an
honest baseline, once with it enabled if a key is configured -- and write the
audit trail and final report comparing both.

Usage:
    python run_reconciliation.py                  # fixed seed, reproducible
    python run_reconciliation.py --regenerate      # force fresh data generation
    python run_reconciliation.py --seed 7 --groups 60
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from pipeline.env import load_dotenv_if_present
load_dotenv_if_present()

from datetime import datetime, timezone

from data_generator.generate import build as generate_dataset
from pipeline.orchestrator import Orchestrator
from audit.store import write_audit_trail
from report.generate import build_comparison, write_json, write_markdown


def _append_run_history(output_dir: Path, seed: int, comparison: dict) -> None:
    """Append-only log of every pipeline run (distinct from audit_trail.db,
    which is overwritten each run with just the latest run's detail) --
    this is what GET /audit-log serves as the reconciliation run history."""
    m, g = comparison["with_ai"]["metrics"], comparison["with_ai"]["grading"]
    entry = {
        "run_at": datetime.now(timezone.utc).isoformat(), "seed": seed,
        "match_rate_pct": m["overall_match_rate_pct"],
        "reconciled_value_rupees": m["reconciled_value_rupees"],
        "total_value_rupees": m["total_value_rupees"],
        "exceptions_count": sum(m["exception_count_by_reason"].values()),
        "precision_pct": round(g["precision"] * 100, 1),
        "recall_pct": round(g["recall"] * 100, 1),
        "false_match_rate_pct": round(g["false_match_rate"] * 100, 1),
        "ai_available": m["ai_available"], "ai_provider": m.get("ai_provider"),
    }
    path = output_dir / "run_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    parser = argparse.ArgumentParser(description="AI Finance Controller -- run the full reconciliation pipeline")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--groups", type=int, default=40, help="base clean-match group count; scales total record volume")
    parser.add_argument("--data-dir", type=str, default=str(ROOT / "data"))
    parser.add_argument("--output-dir", type=str, default=str(ROOT / "output"))
    parser.add_argument("--regenerate", action="store_true", help="force regeneration even if data files already exist")
    parser.add_argument("--api-key", type=str, default=None, help="LLM API key for Tier 4 (defaults to ANTHROPIC_API_KEY / GEMINI_API_KEY / GOOGLE_API_KEY env var)")
    parser.add_argument("--provider", type=str, default=None, choices=["anthropic", "gemini"], help="force a specific Tier 4 provider")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    bank_csv = data_dir / "bank_statement.csv"
    if args.regenerate or not bank_csv.exists():
        print(f"[1/5] Generating synthetic dataset (seed={args.seed}, groups={args.groups})...")
        stats = generate_dataset(args.seed, args.groups, data_dir)
        print(f"      bank={stats['bank_count']} settlement={stats['settlement_count']} "
              f"ledger={stats['ledger_count']} ground_truth_groups={stats['group_count']}")
    else:
        print(f"[1/5] Reusing existing dataset at {data_dir} (pass --regenerate to force fresh data)")

    print("[2/5] Running Tier 1-5 pipeline: baseline (Tier 4 disabled) + AI-enabled pass...")
    result_no_ai = Orchestrator(data_dir, disable_ai=True).run()
    result_ai = Orchestrator(data_dir, api_key=args.api_key, provider=args.provider).run()

    def summarize(label, result):
        print(f"      [{label}] {len(result['groups'])} groups "
              f"({sum(1 for g in result['groups'] if g['size'] > 1)} matched, "
              f"{sum(1 for g in result['groups'] if g['size'] == 1)} exceptions)")

    summarize("no-AI baseline", result_no_ai)
    summarize("AI-enabled", result_ai)
    if result_ai["ai_available"]:
        print(f"      Tier 4 provider: {result_ai['ai_provider']}  ({result_ai['ai_calls_made']} call(s) made)")
    else:
        print("      NOTE: no LLM API key configured -- AI-enabled pass ran identically to the "
              "baseline (Tier 4 honestly unavailable, nothing was guessed).")

    print("[3/5] Writing audit trail (from the AI-enabled run, the primary result)...")
    db_path = output_dir / "audit_trail.db"
    jsonl_path = output_dir / "audit_trail.jsonl"
    write_audit_trail(result_ai["audit"], db_path, jsonl_path)
    print(f"      {len(result_ai['audit'])} audit events -> {db_path} and {jsonl_path}")

    groups_path = output_dir / "groups.json"
    groups_path.write_text(json.dumps(result_ai["groups"], indent=2), encoding="utf-8")
    exceptions_path = output_dir / "exceptions.json"
    exceptions_path.write_text(json.dumps(result_ai["exceptions"], indent=2), encoding="utf-8")

    print("[4/5] Grading both runs against hidden ground truth and building comparison report...")
    comparison = build_comparison(result_no_ai, result_ai, data_dir)
    write_json(comparison, output_dir / "report.json")
    write_markdown(comparison, result_ai, output_dir / "report.md")
    _append_run_history(output_dir, args.seed, comparison)

    print("[5/5] Done.\n")
    primary = comparison["with_ai"]
    m, g = primary["metrics"], primary["grading"]
    print("=" * 60)
    print(f"HEADLINE (AI-enabled): match rate {m['overall_match_rate_pct']}%   "
          f"precision {g['precision']*100:.1f}%   recall {g['recall']*100:.1f}%   "
          f"false-match {g['false_match_rate']*100:.1f}%")
    baseline = comparison["without_ai"]
    bm, bg = baseline["metrics"], baseline["grading"]
    print(f"Baseline (no AI):      match rate {bm['overall_match_rate_pct']}%   "
          f"precision {bg['precision']*100:.1f}%   recall {bg['recall']*100:.1f}%   "
          f"false-match {bg['false_match_rate']*100:.1f}%")
    print(f"Records resolved only by Tier 4: {len(comparison['tier4_resolutions'])}")
    print("=" * 60)
    print(f"\nFull report: {output_dir / 'report.md'}")
    print(f"JSON summary: {output_dir / 'report.json'}")


if __name__ == "__main__":
    main()
