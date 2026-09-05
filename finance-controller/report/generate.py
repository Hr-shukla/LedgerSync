"""Produces the final report: a machine-readable JSON summary and a
human-readable Markdown report.

The pipeline is run twice by the caller (run_reconciliation.py): once with
Tier 4 explicitly disabled (the honest baseline) and once with it enabled if
an API key is configured (the headline). This module combines both into one
comparison, and lists exactly which records were only resolved because of
Tier 4, with the AI's reasoning shown verbatim -- so the "AI" claim is
checkable, not just asserted.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import grading, metrics


def _tier4_resolutions(result_ai: dict) -> list[dict]:
    out = []
    for e in result_ai["bs_result"].edges:
        if e["tier"] == "tier4_ai":
            out.append({
                "axis": "bank<->settlement", "bank_ids": e["bank_ids"], "settlement_ids": e["settlement_ids"],
                "ledger_ids": [], "confidence": e["confidence"], "reasoning": e["reasoning"],
            })
    for e in result_ai["sl_result"].edges:
        if e["tier"] == "tier4_ai":
            out.append({
                "axis": "settlement<->ledger", "bank_ids": [], "settlement_ids": e["settlement_ids"],
                "ledger_ids": e["ledger_ids"], "confidence": e["confidence"], "reasoning": e["reasoning"],
            })
    return out


def _adversarial_robustness(result_ai: dict, ground_truth: list[dict]) -> list[dict]:
    """Task 3: prove -- not just assert -- that the adversarial decoy pair
    (an orphan bank credit and an unrelated orphan settlement, engineered
    with a near-identical amount and adjacent date) was genuinely evaluated
    by the cascade and correctly kept apart, by pulling its real audit trail
    entries and final group membership out of this actual run."""
    decoy_ids = []
    for g in ground_truth:
        if g["case_type"] == "adversarial_decoy_no_match":
            decoy_ids += g["bank_ids"] + g["settlement_ids"] + g["ledger_ids"]
    if not decoy_ids:
        return []

    audit_by_id: dict[str, list] = {}
    for e in result_ai["audit"]:
        audit_by_id.setdefault(e.record_id, []).append(e)

    group_by_id = {}
    for g in result_ai["groups"]:
        for rid in g["bank_ids"] + g["settlement_ids"] + g["ledger_ids"]:
            group_by_id[rid] = g

    ai_reason_codes = {"ai_rejected_no_match", "low_ai_confidence", "ai_unavailable_needs_review"}
    out = []
    for rid in decoy_ids:
        events = audit_by_id.get(rid, [])
        group = group_by_id.get(rid)
        final_reason = events[-1].exception_reason if events and events[-1].exception_reason else None

        # A record that was itself the search target gets its own tier4_ai
        # audit row. A record that only showed up as someone else's
        # *candidate* never gets a tier4_ai row under its own id -- the AI
        # decision is logged under the searching record instead -- but its
        # own tier5_exception row still carries the real AI reasoning
        # verbatim via exceptions.classify(), and its reason code proves it
        # was genuinely evaluated rather than skipped.
        tier4_events = [e for e in events if e.tier == "tier4_ai"]
        if tier4_events:
            reached_tier4, confidence, reasoning = True, tier4_events[0].confidence, tier4_events[0].reasoning
        elif final_reason in ai_reason_codes:
            reached_tier4, confidence, reasoning = True, None, events[-1].reasoning
        else:
            reached_tier4, confidence, reasoning = False, None, None

        out.append({
            "record_id": rid, "reached_tier4": reached_tier4,
            "tier4_confidence": confidence, "tier4_reasoning": reasoning,
            "final_exception_reason": final_reason,
            "cross_matched": bool(group and group["size"] > 1),
        })
    return out


def build_comparison(result_no_ai: dict, result_ai: dict, data_dir: Path) -> dict:
    gt = grading.load_ground_truth(data_dir)

    m_no_ai = metrics.compute(result_no_ai)
    g_no_ai = grading.grade(result_no_ai["groups"], gt)
    m_ai = metrics.compute(result_ai)
    g_ai = grading.grade(result_ai["groups"], gt)

    return {
        "with_ai": {"metrics": m_ai, "grading": g_ai},
        "without_ai": {"metrics": m_no_ai, "grading": g_no_ai},
        "tier4_resolutions": _tier4_resolutions(result_ai),
        "adversarial_robustness": _adversarial_robustness(result_ai, gt),
    }


# Back-compat single-run summary (used by tests / scripts that only need one run's grading)
def build_summary(result: dict, data_dir: Path) -> dict:
    m = metrics.compute(result)
    gt = grading.load_ground_truth(data_dir)
    g = grading.grade(result["groups"], gt)
    return {"metrics": m, "grading": g}


def write_json(comparison: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(comparison, indent=2), encoding="utf-8")


def _grading_lines(g: dict) -> list[str]:
    lines = []
    lines.append(f"- Precision: **{g['precision']*100:.1f}%** "
                 f"({g['total_exact_groups'] + g['total_partial_groups']}/{g['total_predicted_match_groups']} "
                 f"predicted match-groups correct -- exact or a correct-but-incomplete subset, never a wrong merge)")
    lines.append(f"- Recall (fully recovered): **{g['recall']*100:.1f}%** "
                 f"({g['total_exact_groups']}/{g['total_ground_truth_groups_to_recover']} true groups fully recovered)")
    lines.append(f"- Recall (full or partial credit): **{g['recall_full_or_partial']*100:.1f}%** "
                 f"({g['total_exact_groups']}+{g['total_partial_groups']} partial)")
    lines.append(f"- False-match rate: **{g['false_match_rate']*100:.1f}%** "
                 f"(predicted groups that wrongly combined records from two different real transactions)")
    return lines


def write_markdown(comparison: dict, result_ai: dict, path: Path) -> None:
    ai = comparison["with_ai"]
    base = comparison["without_ai"]
    m, g = ai["metrics"], ai["grading"]
    bm, bg = base["metrics"], base["grading"]
    tier4 = comparison["tier4_resolutions"]

    lines = []
    lines.append("# AI Finance Controller -- Reconciliation Report\n")

    lines.append("## Headline (Tier 4 / AI enabled)\n")
    if m["ai_available"]:
        lines.append(f"Tier 4 provider: **{m['ai_provider']}**  |  AI calls made: **{m['ai_calls_made']}**\n")
    else:
        lines.append("**No LLM API key was configured for this run** -- the numbers below are identical "
                     "to the no-AI baseline because Tier 4 had nothing to add. Set `ANTHROPIC_API_KEY` or "
                     "`GEMINI_API_KEY`/`GOOGLE_API_KEY` and re-run to see Tier 4 in action.\n")
    lines.append(f"- Overall record-level match rate: **{m['overall_match_rate_pct']}%**")
    for src in ("bank", "settlement", "ledger"):
        s = m["per_source"][src]
        lines.append(f"  - {src}: {s['matched_records']}/{s['total_records']} matched ({s['match_rate_pct']}%)")
    lines.append(f"- Rupee value reconciled: Rs {m['reconciled_value_rupees']:,.2f} / "
                 f"Rs {m['total_value_rupees']:,.2f} ({m['reconciled_value_pct']}%)")
    lines.append(f"- Value at risk in exceptions: Rs {m['exception_value_rupees']:,.2f}\n")
    lines.extend(_grading_lines(g))
    lines.append("")

    lines.append("## Without AI vs With AI (Tiers 1-3-5 only, vs Tiers 1-5)\n")
    lines.append("| Metric | Without AI (baseline) | With AI |")
    lines.append("|---|---|---|")
    lines.append(f"| Overall match rate | {bm['overall_match_rate_pct']}% | {m['overall_match_rate_pct']}% |")
    lines.append(f"| Rupee reconciled | {bm['reconciled_value_pct']}% | {m['reconciled_value_pct']}% |")
    lines.append(f"| Precision | {bg['precision']*100:.1f}% | {g['precision']*100:.1f}% |")
    lines.append(f"| Recall (full) | {bg['recall']*100:.1f}% | {g['recall']*100:.1f}% |")
    lines.append(f"| Recall (full or partial) | {bg['recall_full_or_partial']*100:.1f}% | {g['recall_full_or_partial']*100:.1f}% |")
    lines.append(f"| False-match rate | {bg['false_match_rate']*100:.1f}% | {g['false_match_rate']*100:.1f}% |")
    lines.append(f"| Exception count | {sum(bm['exception_count_by_reason'].values())} | {sum(m['exception_count_by_reason'].values())} |")
    lines.append("")

    lines.append("### Records Resolved Only Because of Tier 4\n")
    if not tier4:
        lines.append("_None in this run_ -- either every ambiguous record was already resolved by "
                     "Tiers 1-3, or no LLM API key was configured (see above).\n")
    else:
        for r in tier4:
            ids = {"bank": r["bank_ids"], "settlement": r["settlement_ids"], "ledger": r["ledger_ids"]}
            ids_str = ", ".join(f"{k}={v}" for k, v in ids.items() if v)
            lines.append(f"- **[{r['axis']}]** {ids_str} (confidence {r['confidence']:.2f})")
            lines.append(f"  > {r['reasoning']}")
        lines.append("")

    lines.append("## Adversarial Robustness\n")
    adv = comparison.get("adversarial_robustness", [])
    if not adv:
        lines.append("_No adversarial decoy pair found in this dataset._\n")
    else:
        lines.append("The generator injects an orphan bank credit and an unrelated orphan settlement "
                     "with a deliberately near-identical amount and adjacent date, specifically to bait "
                     "a matcher that trusts amount+date alone. Pulled directly from this run's own audit "
                     "trail, not asserted:\n")
        any_cross_matched = any(r["cross_matched"] for r in adv)
        for r in adv:
            status = "reached Tier 4" if r["reached_tier4"] else "rejected before Tier 4 (no plausible candidate found)"
            confidence_str = f", confidence {r['tier4_confidence']:.2f}" if r["tier4_confidence"] is not None else ""
            lines.append(f"- **{r['record_id']}** -- {status}{confidence_str}")
            if r["tier4_reasoning"]:
                lines.append(f"  > {r['tier4_reasoning']}")
            if r["cross_matched"]:
                lines.append("  Final: **WRONGLY CROSS-MATCHED -- this would be a bug**")
            else:
                lines.append(f"  Final: correctly kept separate (exception reason: `{r['final_exception_reason']}`)")
        lines.append("")
        if any_cross_matched:
            lines.append("**Result: BUG -- the adversarial pair WAS cross-matched in this run.**\n")
        else:
            lines.append("**Result: the adversarial pair was correctly kept separate in this run.**\n")

    lines.append("## Match Breakdown by Tier (AI-enabled run)\n")
    lines.append("| Tier | Groups resolved |")
    lines.append("|---|---|")
    tier_labels = {
        "tier1_exact": "Tier 1 - exact reference match",
        "tier1_exact_grouped": "Tier 1 - exact reference match (grouped)",
        "tier2_fuzzy": "Tier 2 - deterministic fuzzy/amount+date match",
        "tier3_grouping": "Tier 3 - subset-sum grouping (many:1 / 1:many)",
        "tier4_ai": "Tier 4 - AI-assisted resolution",
    }
    for tier, label in tier_labels.items():
        n = m["tier_usage_across_matched_groups"].get(tier, 0)
        if n:
            lines.append(f"| {label} | {n} |")
    lines.append("")

    lines.append("## Exceptions by Reason (AI-enabled run)\n")
    lines.append("| Reason | Count | Value at risk (Rs) |")
    lines.append("|---|---|---|")
    for reason, count in sorted(m["exception_count_by_reason"].items(), key=lambda kv: -kv[1]):
        val = m["exception_value_by_reason"].get(reason, 0.0)
        lines.append(f"| {reason} | {count} | {val:,.2f} |")
    lines.append("")

    if g["partial_matches"]:
        lines.append("### Partial Matches (correct direction, incomplete -- not a matching error)\n")
        for pm in g["partial_matches"]:
            lines.append(f"- [{pm['case_type']}] predicted={pm['predicted_ids']} vs true={pm['true_ids']} -- {pm['reasoning']}")
        lines.append("")

    if g["false_merges"]:
        lines.append("### False Merges (predicted matches that do not correspond to a real transaction)\n")
        for fm in g["false_merges"]:
            lines.append(f"- bank={fm['bank_ids']} settlement={fm['settlement_ids']} ledger={fm['ledger_ids']} "
                         f"tiers={fm['tiers']} -- {fm['reasoning']}")
        lines.append("")

    if g["missed_groups"]:
        lines.append("### Missed Groups (should have matched, did not)\n")
        for mg in g["missed_groups"]:
            lines.append(f"- [{mg['case_type']}] ids={mg['ids']}")
        lines.append("")

    lines.append("### Recall by Injected Edge Case (AI-enabled run)\n")
    lines.append("| Case type | Recovered | Total |")
    lines.append("|---|---|---|")
    for ct in sorted(g["total_by_case_type"]):
        lines.append(f"| {ct} | {g['recovered_by_case_type'].get(ct, 0)} | {g['total_by_case_type'][ct]} |")
    lines.append("")

    lines.append("## Full Exception List (AI-enabled run)\n")
    lines.append("| Record | Source | Reason | Amount (Rs) | Detail |")
    lines.append("|---|---|---|---|---|")
    for e in sorted(result_ai["exceptions"], key=lambda x: (x["source"], x["reason_code"])):
        detail = e["reason_detail"].replace("|", "/")
        lines.append(f"| {e['record_id']} | {e['source']} | {e['reason_code']} | {e['amount']:,.2f} | {detail} |")

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")
