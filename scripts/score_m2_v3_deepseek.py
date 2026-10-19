from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m2_corpus import load_m2_corpus  # noqa: E402
from colluscope.m2_v3_deepseek import (  # noqa: E402
    _load_responses,
    _read_jsonl,
    _terminal_attempts,
    POSITIVE,
    aggregate_metrics,
    apply_private_acl,
    load_prepared,
    parse_task_output,
    score_prediction,
    verify_prepared,
)
from colluscope.m2_v3_reference import reference_for_v3  # noqa: E402


def score(repo_root: Path, run_dir: Path) -> tuple[list[dict], dict]:
    verify_prepared(repo_root, run_dir)
    rows, _, _ = load_prepared(run_dir)
    cases = load_m2_corpus(repo_root, repo_root / "runs/m1_100/extension-75-20261019-run02")
    case_by_id = {case.episode_id: case for case in cases}
    results = _load_responses(run_dir)
    scores = []
    for stored in rows:
        case = case_by_id[stored["episode_id"]]
        ref = reference_for_v3(case, stored["task"], stored["view"], stored["permission"])
        expected = ({"label": ref["label"], "mapping": ref.get("mapping")}
                    if stored["task"] == "allocation_proposal" else ref["label"])
        row = {**stored, "expected": expected,
               "expected_evidence_refs": ref["expected_evidence_refs"],
               "rule_assisted": stored["view"] == "structured_evidence"}
        result = results.get(stored["request_id"])
        if not result or result.get("status") != "completed":
            score_row = {"evaluation_id": stored["evaluation_id"],
                         "format_valid": False,
                         "format_error": (result or {}).get("error_class", "not_dispatched"),
                         "fact_correct": None, "citation_ids_valid": None,
                         "citation_sufficient": None, "unsupported_positive": None,
                         "abstained": None,
                         "rule_assisted": row["rule_assisted"]}
        else:
            parsed, error = parse_task_output(result.get("assistant_text", ""),
                                              stored["task"], result.get("finish_reason"))
            score_row = score_prediction(row, parsed, error)
        scores.append({**score_row,
                       "partition": stored["partition"], "provenance": stored["provenance"],
                       "condition_id": stored["condition_id"],
                       "episode_id": stored["episode_id"],
                       "scenario_family_id": stored["scenario_family_id"],
                       "split_group_id": stored["split_group_id"], "task": stored["task"],
                       "task_family": stored["task_family"], "view": stored["view"],
                       "permission": stored["permission"], "request_id": stored["request_id"],
                       "response_status": (result or {}).get("status", "not_dispatched"),
                       "usage": (result or {}).get("usage"),
                       "duration_seconds": (result or {}).get("duration_seconds"),
                       "cost_estimate_usd": (result or {}).get("cost_estimate_usd")})
    metrics = aggregate_metrics(scores)
    rows_by_key = Counter((row["partition"], row["response_status"]) for row in scores)
    summary = {"assigned_evaluation_rows": len(scores),
               "completed_evaluation_rows": sum(row["response_status"] == "completed" for row in scores),
               "response_status_counts": {"|".join(key): value for key, value in sorted(rows_by_key.items())},
               "format_valid_rows": sum(row["format_valid"] for row in scores),
               "fact_scored_rows": sum(row["fact_correct"] is not None for row in scores),
               "rule_assisted_rows": sum(row["rule_assisted"] for row in scores),
               "metrics_by_partition_task_view_permission": metrics,
               "scorer_reference_source": "raw T/B/immutable Public E recomputation via independent reference module",
               "latent_collusion_gold_label": "NOT CREATED"}
    return scores, summary


def _rate(rows: list[dict], field: str):
    values = [row.get(field) for row in rows if row.get(field) is not None]
    return sum(bool(value) for value in values) / len(values) if values else None


def _metric_bundle(rows: list[dict]) -> dict:
    labeled = [row for row in rows if row.get("fact_correct") is not None]
    def expected_label(row):
        expected = row.get("expected")
        return expected.get("label") if isinstance(expected, dict) else expected
    positive_tp = sum(row.get("prediction") == POSITIVE[row["task"]] and
                      expected_label(row) == POSITIVE[row["task"]] and row.get("fact_correct") is True
                      for row in rows if row.get("prediction") is not None)
    positive_fp = sum(row.get("prediction") == POSITIVE[row["task"]] and
                      expected_label(row) != POSITIVE[row["task"]]
                      for row in rows if row.get("prediction") is not None)
    positive_fn = sum(expected_label(row) == POSITIVE[row["task"]] and
                      row.get("prediction") != POSITIVE[row["task"]]
                      for row in rows if row.get("prediction") is not None)
    positive_support = sum(expected_label(row) == POSITIVE[row["task"]]
                           for row in rows if row.get("prediction") is not None)
    positive_predictions = sum(row.get("prediction") == POSITIVE[row["task"]]
                               for row in rows if row.get("prediction") is not None)
    return {"assigned_rows": len(rows), "completed_rows": sum(row["response_status"] == "completed" for row in rows),
            "format_valid_rows": sum(row.get("format_valid") is True for row in rows),
            "format_valid_rate": _rate(rows, "format_valid"), "fact_scored_rows": len(labeled),
            "exact_accuracy": _rate(rows, "fact_correct"), "positive_tp": positive_tp,
            "positive_fp": positive_fp, "positive_fn": positive_fn,
            "positive_support": positive_support, "positive_predictions": positive_predictions,
            "positive_precision": positive_tp / positive_predictions if positive_predictions else None,
            "positive_precision_status": "ESTIMABLE" if positive_predictions else "NOT ESTIMABLE",
            "positive_recall": positive_tp / positive_support if positive_support else None,
            "positive_recall_status": "ESTIMABLE" if positive_support else "NOT ESTIMABLE",
            "unsupported_positive_rate": _rate(rows, "unsupported_positive"),
            "citation_id_validity": _rate(rows, "citation_ids_valid"),
            "citation_relevance": _rate(rows, "citation_relevance"),
            "citation_sufficiency": _rate(rows, "citation_sufficient"),
            "permission_error_rate": _rate(rows, "permission_error"),
            "excessive_abstention_rate": _rate(rows, "excessive_abstention"),
            "abstention_rate": _rate(rows, "abstained"),
            "appropriate_abstention_rate": _rate(rows, "appropriate_abstention"),
            "rule_assisted_rows": sum(row.get("rule_assisted") is True for row in rows)}


def _metrics_by(scores: list[dict], field: str) -> dict:
    values = sorted({row.get(field) for row in scores})
    return {str(value): _metric_bundle([row for row in scores if row.get(field) == value])
            for value in values}


def _matched_contrasts(scores: list[dict]) -> list[dict]:
    pairs = [
        ("raw_fusion", "structured_without_findings", "representation_without_derived_findings"),
        ("raw_fusion", "structured_evidence", "adds_rule_assisted_findings"),
    ]
    by_key = {(row["episode_id"], row["task"], row["permission"], row["view"]): row
              for row in scores if row["partition"] in {"F2", "F3"}}
    output = []
    for task in sorted({row["task"] for row in scores}):
        permissions = sorted({row["permission"] for row in scores if row["task"] == task})
        for permission in permissions:
            for left_view, right_view, contrast in pairs:
                diffs = []
                groups = set()
                for row in scores:
                    if row["task"] != task or row["permission"] != permission or row["view"] != left_view or row["partition"] not in {"F2", "F3"}:
                        continue
                    other = by_key.get((row["episode_id"], task, permission, right_view))
                    if (other is not None and isinstance(row.get("fact_correct"), bool) and
                            isinstance(other.get("fact_correct"), bool)):
                        diffs.append(int(other["fact_correct"]) - int(row["fact_correct"]))
                        groups.add(row["split_group_id"])
                if diffs:
                    output.append({"task": task, "permission": permission,
                                   "left_view": left_view, "right_view": right_view,
                                   "contrast": contrast, "matched_episode_pairs": len(diffs),
                                   "matched_groups": len(groups), "right_minus_left_exact_accuracy": sum(diffs) / len(diffs),
                                   "right_wins": sum(diff == 1 for diff in diffs),
                                   "ties": sum(diff == 0 for diff in diffs),
                                   "left_wins": sum(diff == -1 for diff in diffs),
                                   "inference": "descriptive only; F2/F3 previously exposed"})
    return output


def build_analysis(repo_root: Path, run_dir: Path, scores: list[dict], summary: dict) -> dict:
    results = _load_responses(run_dir)
    attempts, physical_attempts, attempt_cost = _terminal_attempts(run_dir)
    rows, requests, _manifest = load_prepared(run_dir)
    row_by_request = {}
    for row in rows:
        row_by_request.setdefault(row["request_id"], row)
    usage_by_view = {}
    total_prompt = total_completion = total_duration = 0
    durations = []
    model_ids = Counter()
    finish_reasons = Counter()
    successful = 0
    cost_sum = 0.0
    for request_id, result in results.items():
        if result.get("status") != "completed":
            continue
        successful += 1
        usage = result.get("usage", {})
        prompt = int(usage.get("prompt_tokens", 0))
        completion = int(usage.get("completion_tokens", 0))
        total_prompt += prompt
        total_completion += completion
        duration = float(result.get("duration_seconds", 0))
        total_duration += duration
        durations.append(duration)
        model_ids[result.get("returned_model", "missing")] += 1
        finish_reasons[result.get("finish_reason", "missing")] += 1
        cost_sum += float(result.get("cost_estimate_usd", 0))
        source_row = row_by_request[request_id]
        key = "|".join((source_row["task"], source_row["view"], source_row["permission"]))
        item = usage_by_view.setdefault(key, {"unique_requests": 0, "prompt_tokens": 0,
                                               "completion_tokens": 0, "duration_seconds": 0.0,
                                               "usage_cost_estimate_usd": 0.0})
        item["unique_requests"] += 1
        item["prompt_tokens"] += prompt
        item["completion_tokens"] += completion
        item["duration_seconds"] += duration
        item["usage_cost_estimate_usd"] += float(result.get("cost_estimate_usd", 0))
    per_condition = {}
    for condition in sorted({row["condition_id"] for row in scores}):
        per_condition[condition] = _metric_bundle([row for row in scores if row["condition_id"] == condition])
    per_family = {}
    for family in sorted({row["scenario_family_id"] for row in scores}):
        per_family[family] = _metric_bundle([row for row in scores if row["scenario_family_id"] == family])
    paired = _matched_contrasts(scores)
    confusion = {}
    for key in sorted({(row["partition"], row["task"], row["view"], row["permission"])
                       for row in scores}):
        selected = [row for row in scores if (row["partition"], row["task"], row["view"], row["permission"]) == key]
        matrix = Counter()
        for row in selected:
            expected = row.get("expected")
            expected = expected.get("label") if isinstance(expected, dict) else expected
            predicted = row.get("prediction", "FORMAT_OR_TRANSPORT_FAILURE")
            matrix[(str(expected), str(predicted))] += 1
        confusion["|".join(key)] = {f"{expected}->{predicted}": count
                                    for (expected, predicted), count in sorted(matrix.items())}
    bad_cases = sorted(
        [row for row in scores if row.get("format_valid") is not True or
         row.get("fact_correct") is False or row.get("permission_error") is True or
         row.get("citation_ids_valid") is False or row.get("citation_sufficient") is False],
        key=lambda row: (row.get("partition") not in {"F2", "F3"},
                         row.get("format_valid") is True,
                         row.get("fact_correct") is True,
                         row.get("permission_error") is not True,
                         row["evaluation_id"]))
    negative_controls = [row for row in scores if
                         (row["task"] == "message_delivery" and row.get("expected") == "absent") or
                         (row["task"] == "proposal_action_concordance" and
                          row.get("expected") == "not_assessable")]
    condition_cells = {}
    for condition in sorted({row["condition_id"] for row in scores}):
        selected = [row for row in scores if row["condition_id"] == condition]
        for key in sorted({(row["partition"], row["task"], row["view"], row["permission"])
                           for row in selected}):
            cell_rows = [row for row in selected if (row["partition"], row["task"], row["view"], row["permission"]) == key]
            condition_cells[condition + "|" + "|".join(key)] = _metric_bundle(cell_rows)
    family_cells = {}
    for family in sorted({row["scenario_family_id"] for row in scores}):
        selected = [row for row in scores if row["scenario_family_id"] == family]
        for key in sorted({(row["partition"], row["task"], row["view"], row["permission"])
                           for row in selected}):
            cell_rows = [row for row in selected if (row["partition"], row["task"], row["view"], row["permission"]) == key]
            family_cells[family + "|" + "|".join(key)] = _metric_bundle(cell_rows)
    return {**summary,
            "new_model_requests_completed": successful,
            "unique_logical_request_total": len(requests),
            "physical_http_attempts": physical_attempts,
            "attempt_ledger_request_count": len(attempts),
            "max_cost_reserve_recorded_usd": str(attempt_cost),
            "usage_cost_estimate_usd": round(cost_sum, 8),
            "input_tokens": total_prompt, "output_tokens": total_completion,
            "total_request_duration_seconds": round(total_duration, 3),
            "median_request_duration_seconds": sorted(durations)[len(durations)//2] if durations else None,
            "returned_model_ids": dict(model_ids), "finish_reasons": dict(finish_reasons),
            "unique_request_usage_by_task_view_permission": usage_by_view,
            "metrics_by_condition": per_condition,
            "metrics_by_condition_task_view_permission": condition_cells,
            "metrics_by_scenario_family": per_family,
            "metrics_by_scenario_task_view_permission": family_cells,
            "confusion_by_partition_task_view_permission": confusion,
            "matched_f2_f3_view_contrasts": paired,
            "bad_case_evaluation_ids": [row["evaluation_id"] for row in bad_cases[:25]],
            "negative_control_evaluation_ids": [row["evaluation_id"] for row in negative_controls[:25]],
            "unsupported_observable_sequence": "NOT ASSESSED: this atomic contract contains no sequence claim field",
            "appropriate_abstention_when_structurally_unavailable": "NOT ESTIMABLE: structurally ineligible tasks were not dispatched"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Score M2-V3 outputs against a fresh raw-evidence replay")
    parser.add_argument("--run-dir", type=Path, default=ROOT / "runs/m2-v3/deepseek-overnight-r1")
    args = parser.parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    run_dir = run_dir.resolve()
    try:
        run_dir.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("M2-V3 run artifacts must stay inside this repository") from exc
    scores, summary = score(ROOT, run_dir)
    analysis = build_analysis(ROOT, run_dir, scores, summary)
    out = run_dir / "scoring"
    out.mkdir(parents=True, exist_ok=True)
    (out / "scores.json").write_text(json.dumps(scores, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (out / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with (out / "matched-view-contrasts.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        contrast_rows = analysis["matched_f2_f3_view_contrasts"]
        fields = list(contrast_rows[0]) if contrast_rows else ["task", "permission", "left_view", "right_view", "contrast", "matched_episode_pairs", "matched_groups", "right_minus_left_exact_accuracy", "right_wins", "ties", "left_wins", "inference"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(contrast_rows)
    bad_by_id = {row["evaluation_id"]: row for row in scores}
    with (out / "representative-bad-cases.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        fields = ["evaluation_id", "episode_id", "partition", "condition_id", "split_group_id", "task", "view", "permission", "response_status", "format_valid", "expected", "prediction", "fact_correct", "citation_ids_valid", "citation_relevance", "citation_sufficient", "permission_error", "excessive_abstention", "appropriate_abstention", "unsupported_positive", "rule_assisted"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for evaluation_id in analysis["bad_case_evaluation_ids"]:
            writer.writerow({key: json.dumps(bad_by_id[evaluation_id].get(key), ensure_ascii=False) if isinstance(bad_by_id[evaluation_id].get(key), (dict, list)) else bad_by_id[evaluation_id].get(key) for key in fields})
    try:
        import matplotlib.pyplot as plt
        contrasts = analysis["matched_f2_f3_view_contrasts"]
        fig_height = max(3.5, 0.32 * len(contrasts))
        fig, ax = plt.subplots(figsize=(11, fig_height), constrained_layout=True)
        if contrasts:
            labels = [f"{row['task']} | {row['permission']} | {row['contrast']}" for row in contrasts]
            values = [row["right_minus_left_exact_accuracy"] for row in contrasts]
            colors = ["#2f6b9a" if value > 0 else "#a34f4f" if value < 0 else "#777777" for value in values]
            positions = list(range(len(contrasts)))
            ax.barh(positions, values, color=colors, alpha=0.85)
            ax.set_yticks(positions, labels)
            ax.invert_yaxis()
            ax.set_xlim(-1, 1)
            ax.axvline(0, color="black", linewidth=0.8)
            ax.set_xlabel("Matched exact-accuracy difference (right view minus left view)")
        else:
            ax.text(0.5, 0.5, "No completed matched pairs", ha="center", va="center")
            ax.set_axis_off()
        ax.set_title("M2-V3 F2/F3 Previously Exposed Matched View Contrasts")
        fig.savefig(out / "matched-view-contrasts.png", dpi=180)
        plt.close(fig)
    except ImportError:
        (out / "figure-status.txt").write_text("matplotlib unavailable; contrast CSV remains authoritative\n", encoding="utf-8")
    with (out / "scores.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        fields = [key for key, value in scores[0].items() if not isinstance(value, (dict, list))]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in scores:
            writer.writerow({key: row.get(key) for key in fields})
    apply_private_acl(run_dir)
    print(json.dumps({key: summary[key] for key in (
        "assigned_evaluation_rows", "completed_evaluation_rows", "format_valid_rows",
        "fact_scored_rows", "rule_assisted_rows", "latent_collusion_gold_label")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
