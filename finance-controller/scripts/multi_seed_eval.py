#!/usr/bin/env python
"""Task 2: multi-seed validation. Runs the full pipeline across several
different seeds (Tier 4 enabled whenever an API key is configured) and
reports the RANGE of match rate / precision / recall / false-match rate --
not a single cherry-picked run. Any seed that produces a false match or a
precision regression is logged explicitly as a bug to investigate, not
hidden from the summary.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.env import load_dotenv_if_present
load_dotenv_if_present()

from data_generator.generate import build as generate_dataset
from pipeline.orchestrator import Orchestrator
from pipeline import config as pipeline_config
from report import grading, metrics

DEFAULT_SEEDS = [1, 7, 13, 21, 33, 42, 55, 88]


def run_one_seed(seed: int, groups: int, enable_ai: bool, api_key: str | None, provider: str | None) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "data"
        generate_dataset(seed, groups, data_dir)
        orch = Orchestrator(data_dir, api_key=api_key, provider=provider, disable_ai=not enable_ai)
        result = orch.run()
        m = metrics.compute(result)
        gt = grading.load_ground_truth(data_dir)
        g = grading.grade(result["groups"], gt)
        return {
            "seed": seed,
            "match_rate_pct": m["overall_match_rate_pct"],
            "reconciled_value_pct": m["reconciled_value_pct"],
            "precision": g["precision"],
            "recall": g["recall"],
            "recall_full_or_partial": g["recall_full_or_partial"],
            "false_match_rate": g["false_match_rate"],
            "false_merges": g["false_merges"],
            "exception_count": sum(m["exception_count_by_reason"].values()),
            "ai_available": m["ai_available"],
            "ai_provider": m["ai_provider"],
            "ai_calls_made": m["ai_calls_made"],
        }


def summarize(rows: list[dict], key: str) -> dict:
    vals = [r[key] for r in rows]
    return {
        "min": min(vals), "max": max(vals),
        "mean": statistics.mean(vals),
        "stdev": statistics.stdev(vals) if len(vals) > 1 else 0.0,
    }


def write_report(rows: list[dict], summaries: dict, path: Path) -> None:
    lines = []
    lines.append("# Multi-Seed Validation Report\n")
    lines.append(f"Ran the full pipeline across **{len(rows)} seeds**: {', '.join(str(r['seed']) for r in rows)}.\n")
    ai_used = any(r["ai_available"] for r in rows)
    lines.append(f"Tier 4 AI enabled: **{'yes' if ai_used else 'no (no API key configured -- all runs used the Tiers 1-3-5 baseline)'}**\n")

    lines.append("## Summary Across Seeds\n")
    lines.append("| Metric | Min | Max | Mean | Std Dev |")
    lines.append("|---|---|---|---|---|")
    for key, label, pct in [
        ("match_rate_pct", "Match rate", True), ("reconciled_value_pct", "Rupee reconciled", True),
        ("precision", "Precision", False), ("recall", "Recall (full)", False),
        ("recall_full_or_partial", "Recall (full+partial)", False),
        ("false_match_rate", "False-match rate", False),
    ]:
        s = summaries[key]
        fmt = (lambda v: f"{v:.2f}%") if pct else (lambda v: f"{v*100:.1f}%")
        lines.append(f"| {label} | {fmt(s['min'])} | {fmt(s['max'])} | {fmt(s['mean'])} | {fmt(s['stdev'])} |")
    lines.append("")

    lines.append("## Per-Seed Results\n")
    lines.append("| Seed | Match rate | Precision | Recall | False-match | Exceptions | AI calls |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in rows:
        lines.append(f"| {r['seed']} | {r['match_rate_pct']}% | {r['precision']*100:.1f}% | "
                     f"{r['recall']*100:.1f}% | {r['false_match_rate']*100:.1f}% | "
                     f"{r['exception_count']} | {r['ai_calls_made']} |")
    lines.append("")

    flagged = [r for r in rows if r["false_match_rate"] > 0 or r["precision"] < pipeline_config.BASELINE_PRECISION]
    if flagged:
        lines.append("## ⚠ Seeds Flagged for Investigation\n")
        lines.append("These seeds produced a false match or dropped below the precision baseline "
                     f"({pipeline_config.BASELINE_PRECISION*100:.0f}%). Not hidden -- treat as a bug "
                     "the same way the duplicate-settlement issue was handled during the initial build.\n")
        for r in flagged:
            lines.append(f"- **Seed {r['seed']}**: precision {r['precision']*100:.1f}%, "
                         f"false-match rate {r['false_match_rate']*100:.1f}%")
            for fm in r["false_merges"]:
                lines.append(f"  - false merge: bank={fm['bank_ids']} settlement={fm['settlement_ids']} "
                             f"ledger={fm['ledger_ids']} -- {fm['reasoning']}")
        lines.append("")
    else:
        lines.append("## Adversarial / Precision Check\n")
        lines.append(f"No false matches and no precision regressions below "
                     f"{pipeline_config.BASELINE_PRECISION*100:.0f}% across any of the {len(rows)} seeds.\n")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run the pipeline across multiple seeds and report the range")
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument("--groups", type=int, default=40)
    parser.add_argument("--no-ai", action="store_true", help="force Tier 4 disabled for every seed (faster, offline)")
    parser.add_argument("--api-key", type=str, default=None)
    parser.add_argument("--provider", type=str, default=None, choices=["anthropic", "gemini"])
    parser.add_argument("--output", type=str, default=str(ROOT / "output" / "multi_seed_report.md"))
    args = parser.parse_args()

    rows = []
    for seed in args.seeds:
        print(f"[seed {seed}] running...", flush=True)
        row = run_one_seed(seed, args.groups, enable_ai=not args.no_ai, api_key=args.api_key, provider=args.provider)
        rows.append(row)
        print(f"[seed {seed}] match_rate={row['match_rate_pct']}%  precision={row['precision']*100:.1f}%  "
              f"recall={row['recall']*100:.1f}%  false_match={row['false_match_rate']*100:.1f}%  "
              f"ai_calls={row['ai_calls_made']}", flush=True)

    summaries = {k: summarize(rows, k) for k in
                 ("match_rate_pct", "reconciled_value_pct", "precision", "recall", "recall_full_or_partial", "false_match_rate")}

    out_md = Path(args.output)
    write_report(rows, summaries, out_md)
    out_json = out_md.with_suffix(".json")
    out_json.write_text(json.dumps({"rows": rows, "summary": summaries}, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print(f"Match rate:  {summaries['match_rate_pct']['min']:.2f}% - {summaries['match_rate_pct']['max']:.2f}%  "
          f"(mean {summaries['match_rate_pct']['mean']:.2f}%)")
    print(f"Precision:   {summaries['precision']['min']*100:.1f}% - {summaries['precision']['max']*100:.1f}%  "
          f"(mean {summaries['precision']['mean']*100:.1f}%)")
    print(f"Recall:      {summaries['recall']['min']*100:.1f}% - {summaries['recall']['max']*100:.1f}%  "
          f"(mean {summaries['recall']['mean']*100:.1f}%)")
    print(f"False-match: {summaries['false_match_rate']['min']*100:.1f}% - {summaries['false_match_rate']['max']*100:.1f}%")
    print("=" * 60)
    print(f"\nReport: {out_md}")


if __name__ == "__main__":
    main()
