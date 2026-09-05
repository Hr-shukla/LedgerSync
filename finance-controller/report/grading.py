"""Grades the pipeline's own predicted groups against the hidden ground-truth
file. This is the "honesty" step the brief calls for: the pipeline itself
never reads ground truth, only this post-hoc grading step does, and it
reports precision/recall/false-match-rate computed from an actual run, not
asserted by hand.

Grading distinguishes three outcomes for a predicted match-group:
  - exact match: predicted id-set == a true group's id-set (full recovery)
  - partial match: predicted id-set is a proper subset of exactly one true
    group's id-set (e.g. settlement<->ledger correctly linked, but the bank
    leg is still an open exception because Tier 4 AI was unavailable) --
    this is NOT wrong, just incomplete, so it does not count against
    precision, but it also isn't full recall.
  - false merge: predicted id-set spans records that truly belong to two or
    more different underlying transactions -- a genuine matching error.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_ground_truth(data_dir: Path) -> list[dict]:
    path = Path(data_dir) / "ground_truth.jsonl"
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _all_ids(g: dict) -> frozenset:
    return frozenset(g["bank_ids"] + g["settlement_ids"] + g["ledger_ids"])


def grade(groups: list[dict], ground_truth: list[dict]) -> dict:
    must_recover = {g["group_id"]: _all_ids(g) for g in ground_truth if len(_all_ids(g)) >= 2}
    case_type_by_group_id = {g["group_id"]: g["case_type"] for g in ground_truth}

    id_to_group_id: dict[str, int] = {}
    for g in ground_truth:
        for rid in _all_ids(g):
            id_to_group_id[rid] = g["group_id"]

    predicted_matches = [g for g in groups if g["size"] > 1]

    exact_group_ids = set()
    partial_group_ids = set()
    false_merges = []
    partial_matches = []

    for pred in predicted_matches:
        pred_ids = _all_ids(pred)
        owners = {id_to_group_id.get(rid) for rid in pred_ids}
        if len(owners) != 1 or None in owners:
            false_merges.append(pred)
            continue
        true_gid = owners.pop()
        true_ids = must_recover.get(true_gid)
        if true_ids is None:
            # every id in this predicted group belongs to what ground truth
            # calls a singleton (no real cross-source counterpart) -- matching
            # them together is a false merge regardless of the shared owner key
            false_merges.append(pred)
            continue
        if pred_ids == true_ids:
            exact_group_ids.add(true_gid)
        elif pred_ids < true_ids:
            partial_group_ids.add(true_gid)
            partial_matches.append({
                "group_id": true_gid, "case_type": case_type_by_group_id[true_gid],
                "predicted_ids": sorted(pred_ids), "true_ids": sorted(true_ids),
                "reasoning": pred["reasoning"],
            })
        else:
            false_merges.append(pred)

    total_predicted = len(predicted_matches)
    total_exact = len(exact_group_ids)
    total_partial = len(partial_group_ids)
    total_correct = total_exact + total_partial  # "not wrong", for precision
    total_must_recover = len(must_recover)

    precision = total_correct / total_predicted if total_predicted else 1.0
    recall_full = total_exact / total_must_recover if total_must_recover else 1.0
    recall_full_or_partial = (total_exact + total_partial) / total_must_recover if total_must_recover else 1.0
    false_match_rate = len(false_merges) / total_predicted if total_predicted else 0.0

    missed = [
        {"group_id": gid, "case_type": case_type_by_group_id[gid], "ids": sorted(ids)}
        for gid, ids in must_recover.items()
        if gid not in exact_group_ids and gid not in partial_group_ids
    ]

    per_case_recovered = {}
    for gid in exact_group_ids:
        ct = case_type_by_group_id[gid]
        per_case_recovered[ct] = per_case_recovered.get(ct, 0) + 1

    per_case_total = {}
    for g in ground_truth:
        if len(_all_ids(g)) >= 2:
            per_case_total[g["case_type"]] = per_case_total.get(g["case_type"], 0) + 1

    return {
        "precision": precision,
        "recall": recall_full,
        "recall_full_or_partial": recall_full_or_partial,
        "false_match_rate": false_match_rate,
        "total_predicted_match_groups": total_predicted,
        "total_exact_groups": total_exact,
        "total_partial_groups": total_partial,
        "total_ground_truth_groups_to_recover": total_must_recover,
        "false_merges": [
            {"bank_ids": g["bank_ids"], "settlement_ids": g["settlement_ids"],
             "ledger_ids": g["ledger_ids"], "tiers": g["tiers"], "reasoning": g["reasoning"]}
            for g in false_merges
        ],
        "partial_matches": partial_matches,
        "missed_groups": missed,
        "recovered_by_case_type": per_case_recovered,
        "total_by_case_type": per_case_total,
    }
