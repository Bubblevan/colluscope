#!/usr/bin/env python3
"""Summarize only independently audited, privacy-safe full-research results.

Reads the private raw Monitor ledgers and the corresponding independent audit
outputs. It never copies request bodies, response text, case IDs, or private
messages into public tables or figures. No model/API calls are made.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "runs/full-research-execution-20261020/monitor"
DEFAULT_OUT = ROOT / "docs/results/full-research-execution-20261020"
PHASES = {
    "scripted_controls": 280,
    "m4_trace_eval": 504,
    "matched_worlds": 72,
}
RAW_METHODS = ("B2_text_only", "B3_action_only", "B4_raw_fusion", "B5_evidence_aware")


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _seconds(start: str, end: str) -> float:
    left = datetime.fromisoformat(start.replace("Z", "+00:00"))
    right = datetime.fromisoformat(end.replace("Z", "+00:00"))
    return (right - left).total_seconds()


def _latency(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    starts = {row["request_id"]: row for row in attempts
              if row.get("event") == "attempt_started"}
    ends = {row["request_id"]: row for row in attempts
            if row.get("event") == "attempt_terminal"}
    if set(starts) != set(ends):
        raise ValueError("attempt start/terminal IDs do not match")
    durations = sorted(_seconds(starts[key]["started_utc"], ends[key]["ended_utc"])
                       for key in starts)
    if not durations:
        return {"n": 0, "sum_seconds": 0.0, "mean_seconds": None,
                "median_seconds": None, "p95_seconds": None, "max_seconds": None}
    return {
        "n": len(durations), "sum_seconds": round(sum(durations), 6),
        "mean_seconds": round(sum(durations) / len(durations), 6),
        "median_seconds": round(float(np.median(durations)), 6),
        "p95_seconds": round(float(np.quantile(durations, 0.95, method="higher")), 6),
        "max_seconds": round(durations[-1], 6),
    }


def _identity_probe_attempt_count(paths: list[Path]) -> int:
    rows = [row for path in paths if path.exists() for row in _jsonl(path)]
    starts = [row["request_id"] for row in rows if row.get("event") == "attempt_started"]
    ends = [row["request_id"] for row in rows if row.get("event") == "attempt_terminal"]
    if len(starts) != len(set(starts)) or len(ends) != len(set(ends)) or set(starts) != set(ends):
        raise ValueError("M4 identity-probe attempts do not have unique matching terminals")
    return len(starts)


def _method_coverage(score_rows: list[dict[str, Any]], phase: str,
                     progress_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scheduled: dict[str, list[dict[str, Any]]] = defaultdict(list)
    progress_by_id: dict[str, dict[str, Any]] = {}
    for row in progress_rows:
        request_id = row.get("request_id")
        if not request_id or request_id in progress_by_id:
            raise ValueError(f"missing or duplicate progress request ID in {phase}")
        progress_by_id[request_id] = row
        method = row.get("baseline_id")
        if method in RAW_METHODS:
            scheduled[method].append(row)
    scored_by_id = {row["request_id"]: row for row in score_rows}
    if len(scored_by_id) != len(score_rows):
        raise ValueError(f"duplicate scored request IDs in {phase}")
    if not set(scored_by_id).issubset(progress_by_id):
        raise ValueError(f"scorer contains an unscheduled request ID in {phase}")
    if any(progress_by_id[request_id].get("baseline_id") != row.get("baseline_id")
           for request_id, row in scored_by_id.items()):
        raise ValueError(f"progress/scored baseline mismatch in {phase}")
    result = []
    for method in RAW_METHODS:
        rows = scheduled[method]
        valid = [scored_by_id[row["request_id"]] for row in rows
                 if row.get("request_id") in scored_by_id
                 and scored_by_id[row["request_id"]].get("status") == "COMPLETED"]
        labels = Counter(row.get("prediction_label") for row in valid)
        if any(row.get("baseline_id") != method for row in valid):
            raise ValueError(f"progress/scored baseline mismatch in {phase}/{method}")
        result.append({
            "phase": phase, "method": method, "assigned_rows": len(rows),
            "parsed_predictions": len(valid), "invalid_or_unexecuted": len(rows) - len(valid),
            "parsed_rate": round(len(valid) / len(rows), 6) if rows else None,
            "assessable_predictions": sum(
                bool((row.get("raw_score") or {}).get("assessable")) for row in valid),
            "exact_correct_assessable": sum(
                (row.get("raw_score") or {}).get("exact_correct") is True for row in valid),
            "positive_reference_predictions": sum(
                (row.get("raw_score") or {}).get("positive_reference") is True for row in valid),
            "positive_predictions": sum(
                (row.get("raw_score") or {}).get("positive_prediction") is True for row in valid),
            "hard_negative_predictions": sum(
                (row.get("raw_score") or {}).get("hard_negative_control") is True for row in valid),
            "positive_predictions_on_hard_negatives": sum(
                (row.get("raw_score") or {}).get("hard_negative_control") is True
                and (row.get("raw_score") or {}).get("positive_prediction") is True for row in valid),
            "unsupported_sequence_claims": sum(
                (row.get("raw_score") or {}).get("unsupported_sequence_claim") is True for row in valid),
            "appropriate_abstentions": sum(
                (row.get("raw_score") or {}).get("appropriate_abstention") is True for row in valid),
            "prediction_label_counts": dict(sorted((str(k), v) for k, v in labels.items())),
        })
    return result


def _normalize_prediction_rows(run: Path, audit: dict[str, Any],
                               progress: list[dict[str, Any]], phase: str
                               ) -> list[dict[str, Any]]:
    """Join completed row-level scores to the schedule and compact independent audit."""
    raw = _jsonl(run / "raw_predictions.jsonl")
    compact = {row["request_id"]: row for row in audit["per_request_scores"]}
    progress_by_id = {row["request_id"]: row for row in progress}
    if (len(raw) != audit.get("completed_predictions") or len(compact) != len(progress)
            or len(progress_by_id) != len(progress)):
        raise ValueError(f"raw predictions/audit/progress denominators differ in {phase}")
    normalized = []
    for row in raw:
        request_id = row.get("request_id")
        if not request_id or request_id not in progress_by_id or request_id not in compact:
            raise ValueError(f"raw prediction lacks a frozen schedule/audit row in {phase}")
        progress_row, audit_row = progress_by_id[request_id], compact[request_id]
        score = row.get("score")
        if (not isinstance(score, dict) or progress_row.get("status") != "COMPLETED"
                or audit_row.get("status") != "COMPLETED"
                or audit_row.get("prediction_label") != row.get("raw_prediction", {}).get("label")
                or score.get("baseline_id") != progress_row.get("baseline_id")
                or score.get("task") != progress_row.get("task")
                or score.get("permission") != progress_row.get("permission")):
            raise ValueError(f"raw prediction fails progress or independent audit join in {phase}")
        normalized.append({
            "request_id": request_id, "status": "COMPLETED",
            "baseline_id": score["baseline_id"], "task": score["task"],
            "permission": score["permission"], "case_ref": score.get("case_ref"),
            "prediction_label": row["raw_prediction"]["label"], "raw_score": score,
        })

    # Reconcile key per-cell score counts against the independently emitted phase aggregates.
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized:
        score = row["raw_score"]
        grouped[f"{row['baseline_id']}|{row['task']}|{row['permission']}"].append(score)
    metrics = audit["task_view_metrics"]
    for cell, scores in grouped.items():
        reference = metrics.get(cell)
        checks = {
            "scored_rows": len(scores),
            "assessable_rows": sum(score.get("assessable") is True for score in scores),
            "correct_assessable_rows": sum(score.get("exact_correct") is True for score in scores),
            "abstained_rows": sum(score.get("abstained") is True for score in scores),
            "appropriate_abstention_rows": sum(score.get("appropriate_abstention") is True for score in scores),
            "positive_reference_rows": sum(score.get("positive_reference") is True for score in scores),
            "positive_prediction_rows": sum(score.get("positive_prediction") is True for score in scores),
            "unsupported_sequence_claims": sum(score.get("unsupported_sequence_claim") is True for score in scores),
        }
        if reference is None or any(reference.get(key) != value for key, value in checks.items()):
            raise ValueError(f"row scores do not reconcile with independent aggregates in {phase}/{cell}")
    return normalized


def _coverage_rate(cell: dict[str, Any]) -> float | None:
    """Return None for an unassigned cell; 0/0 is not a zero completion rate."""
    if cell["assigned_rows"] == 0:
        return None
    return cell["parsed_predictions"] / cell["assigned_rows"]


def _method_resource_rows(progress_rows: list[dict[str, Any]],
                          attempts: list[dict[str, Any]], phase: str
                          ) -> list[dict[str, Any]]:
    starts = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_started"}
    ends = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_terminal"}
    if set(starts) != set(ends):
        raise ValueError(f"request timing ledger does not reconcile by method in {phase}")
    result = []
    for method in RAW_METHODS:
        rows = [row for row in progress_rows if row.get("baseline_id") == method]
        durations = [_seconds(starts[row["request_id"]]["started_utc"],
                              ends[row["request_id"]]["ended_utc"])
                     for row in rows if row["request_id"] in starts]
        if len(durations) != len(rows):
            raise ValueError(f"method attempt count differs from assigned rows in {phase}/{method}")
        input_tokens = sum(int(row.get("usage", {}).get("input_tokens", 0)) for row in rows)
        output_tokens = sum(int(row.get("usage", {}).get("output_tokens", 0)) for row in rows)
        cost = round(sum(float(row.get("cost_upper_peak_usd", 0)) for row in rows), 12)
        formula_cost = round(input_tokens * 0.30 / 1_000_000
                             + output_tokens * 1.20 / 1_000_000, 12)
        if cost != formula_cost:
            raise ValueError(f"method usage/cost fails frozen peak-rate reconciliation in {phase}/{method}")
        result.append({
            "phase": phase, "method": method, "assigned_rows": len(rows),
            "parseable_rows": sum(row.get("status") == "COMPLETED" for row in rows),
            "http_attempts": len(durations), "input_tokens": input_tokens,
            "output_tokens": output_tokens, "peak_rate_cost_usd": cost,
            "mean_latency_seconds": round(sum(durations) / len(durations), 6) if durations else None,
            "mean_input_tokens_per_assigned": round(input_tokens / len(rows), 3) if rows else None,
            "mean_output_tokens_per_assigned": round(output_tokens / len(rows), 3) if rows else None,
        })
    return result


def _paired_b4_b5(score_rows: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    """Compare B4/B5 only on common completed, assessable inputs."""
    pairs: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in score_rows:
        method = row.get("baseline_id")
        if method not in {"B4_raw_fusion", "B5_evidence_aware"}:
            continue
        if row.get("status") != "COMPLETED" or not row.get("case_ref"):
            continue
        score = row.get("raw_score") or {}
        if not score.get("assessable") or type(score.get("exact_correct")) is not bool:
            continue
        key = (row["case_ref"], row.get("task", ""), row.get("permission", ""))
        pairs[key][method] = row
    complete = [value for value in pairs.values()
                if set(value) == {"B4_raw_fusion", "B5_evidence_aware"}]
    wins = ties = losses = 0
    for value in complete:
        a = value["B4_raw_fusion"]["raw_score"]["exact_correct"]
        b = value["B5_evidence_aware"]["raw_score"]["exact_correct"]
        if a == b:
            ties += 1
        elif b:
            wins += 1
        else:
            losses += 1
    return {"phase": phase, "common_assessable_instances": len(complete),
            "B5_wins": wins, "ties": ties, "B4_wins": losses,
            "estimable": bool(complete),
            "interpretation": "descriptive conditional comparison; invalid outputs excluded from correctness only"}


def _phase_summary(phase: str, assigned: int, run_root: Path,
                   audit: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]],
                                                   list[dict[str, Any]], list[dict[str, Any]]]:
    if audit.get("phase_id") != phase or audit.get("integrity_status") != "PASS_INDEPENDENT_TRACE_AND_SCORE_REPLAY":
        raise ValueError(f"independent audit did not pass for {phase}")
    if audit.get("assigned_rows") != assigned or audit.get("retries") != 0:
        raise ValueError(f"assigned denominator or retry policy differs for {phase}")
    run = run_root / phase
    progress = _jsonl(run / "progress.jsonl")
    attempts = _jsonl(run / "attempts.jsonl")
    starts = [row for row in attempts if row.get("event") == "attempt_started"]
    ends = [row for row in attempts if row.get("event") == "attempt_terminal"]
    statuses = Counter(row.get("status") for row in progress)
    finish = Counter(str(row.get("finish_reason")) for row in progress)
    parse_errors = Counter(str(row.get("parse_error")) for row in progress if row.get("parse_error"))
    if len(progress) != assigned or len(starts) != audit.get("physical_attempts") or len(ends) != len(starts):
        raise ValueError(f"progress or attempt ledger denominator mismatch for {phase}")
    if any(row.get("auth_header_saved") is not False for row in attempts):
        raise ValueError(f"attempt ledger does not assert auth-header exclusion for {phase}")
    if any(row.get("retry_count") != 0 for row in attempts):
        raise ValueError(f"retry count is nonzero for {phase}")
    if not (run / "requests").is_dir() or not (run / "responses").is_dir():
        raise ValueError(f"raw request/response directories missing for {phase}")
    if len(list((run / "requests").glob("*.json"))) != len(starts):
        raise ValueError(f"saved request count differs from starts for {phase}")
    if len(list((run / "responses").glob("*.json"))) != len(starts):
        raise ValueError(f"saved response count differs from starts for {phase}")

    manifest = _json(run / "run_manifest.json")
    summary = _json(run / "summary.json")
    if (manifest.get("runtime_revision") != "sprint-monitor-runtime-v1.3"
            or manifest.get("model_alias") != "deepseek-flash"
            or manifest.get("requested_mode") != "live"
            or summary.get("physical_http_attempts") != len(starts)
            or summary.get("real_model_or_api_calls") != len(starts)
            or summary.get("retries") != 0):
        raise ValueError(f"runtime manifest or summary mismatch for {phase}")
    if audit.get("physical_attempts") != len(starts):
        raise ValueError(f"audit attempt count differs for {phase}")

    latency = _latency(attempts)
    usage = audit["usage"]
    input_tokens = sum(int(row.get("usage", {}).get("input_tokens", 0)) for row in progress)
    output_tokens = sum(int(row.get("usage", {}).get("output_tokens", 0)) for row in progress)
    if (input_tokens != usage["input_tokens"] or output_tokens != usage["output_tokens"]
            or round(usage["conservative_cost_usd"], 12) != summary["conservative_total_peak_cost_usd"]):
        raise ValueError(f"usage/cost does not reconcile for {phase}")

    score_rows = _normalize_prediction_rows(run, audit, progress, phase)
    method_rows = _method_coverage(score_rows, phase, progress)
    if (sum(row["assigned_rows"] for row in method_rows) != assigned
            or sum(row["parsed_predictions"] for row in method_rows)
            != audit.get("completed_predictions")):
        raise ValueError(f"method denominators do not conserve the phase totals for {phase}")
    paired = _paired_b4_b5(score_rows, phase)
    public = {
        "phase": phase, "assigned_rows": assigned,
        "physical_attempts": len(starts),
        "completed_predictions": audit["completed_predictions"],
        "invalid_or_unexecuted": audit["failed_or_unexecuted"],
        "terminal_status_counts": dict(sorted((str(k), v) for k, v in statuses.items())),
        "finish_reason_counts": dict(sorted(finish.items())),
        "parse_error_counts": dict(sorted(parse_errors.items())),
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "provider_reported_peak_cost_usd": usage["provider_reported_cost_usd"],
        "conservative_cost_usd": usage["conservative_cost_usd"],
        "latency": latency,
        "returned_model_identity": audit["returned_model_identity"],
        "independent_integrity_status": audit["integrity_status"],
    }
    resource_rows = _method_resource_rows(progress, attempts, phase)
    if sum(row["peak_rate_cost_usd"] for row in resource_rows) != round(usage["conservative_cost_usd"], 12):
        raise ValueError(f"method cost rows do not reconcile with phase total for {phase}")
    return public, method_rows, [
        {"phase": phase, "cell": key, **value}
        for key, value in sorted(audit["task_view_metrics"].items())
    ], resource_rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list))
                             else value for key, value in row.items()})


def _plot_m4(m4: dict[str, Any], path: Path) -> None:
    values = [24, 24, m4["messages_recorded"], m4["proposal_eligible_groups"],
              m4["settlements_recomputed"]]
    labels = ["Assigned\ngroups", "Message calls\nattempted", "Messages\nrecorded",
              "Proposal-eligible\ngroups", "Settlements\nrecomputed"]
    colors = ["#536dfe", "#d9534f", "#9aa0a6", "#9aa0a6", "#9aa0a6"]
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylim(0, 27)
    ax.set_ylabel("Count (all 24 assigned groups retained)")
    ax.set_title("M4 message-intervention comparison: no paired behavioral estimate")
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, value + 0.45, str(value), ha="center", va="bottom")
    ax.text(0.5, 0.91,
            "24/24 first message outputs failed strict parsing; no ballots or matched counterfactuals",
            transform=ax.transAxes, ha="center", va="top", color="#7a1c1c", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_method_coverage(method_rows: list[dict[str, Any]], path: Path) -> None:
    phases = list(PHASES)
    methods = list(RAW_METHODS)
    data = {(row["phase"], row["method"]): row for row in method_rows}
    rates = np.array([[100 * _coverage_rate(data[(phase, method)])
                       if _coverage_rate(data[(phase, method)]) is not None else np.nan
                       for phase in phases] for method in methods])
    fig, ax = plt.subplots(figsize=(10.4, 5.4))
    cmap = plt.get_cmap("Blues").copy()
    cmap.set_bad("#e5e7eb")
    image = ax.imshow(np.ma.masked_invalid(rates), cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for row_index, method in enumerate(methods):
        for col_index, phase in enumerate(phases):
            cell = data[(phase, method)]
            if _coverage_rate(cell) is None:
                label, color = "not scheduled", "#202124"
            else:
                count = f"{cell['parsed_predictions']}/{cell['assigned_rows']}"
                color = "white" if rates[row_index, col_index] >= 55 else "#202124"
                label = f"{count}\n{rates[row_index, col_index]:.1f}%"
            ax.text(col_index, row_index, label,
                    ha="center", va="center", color=color, fontsize=10)
    ax.set_xticks(np.arange(len(phases)), ["Scripted controls\n(n=280)", "M4 traces\n(n=504)",
                                             "Matched worlds\n(n=72)"])
    method_labels = ["B2: text only", "B3: action only", "B4: raw fusion", "B5: evidence-aware"]
    ax.set_yticks(np.arange(len(methods)), method_labels)
    ax.set_ylabel("Monitor baseline")
    ax.set_title("Parseable completion by baseline and population", pad=16)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.045, pad=0.04)
    colorbar.set_label("Parseable outputs (%)")
    fig.text(0.5, 0.035,
             "Coverage is not accuracy. 715/856 outputs ended at the 128-token length cap.",
             ha="center", fontsize=9)
    ax.set_xticks(np.arange(-0.5, len(phases), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(methods), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_evidence_sufficiency(matched_audit: dict[str, Any], path: Path) -> None:
    privileged = matched_audit["matched_world_identifiability"]["privileged_reference_label_counts"]
    labels = ["not_visible", "supported", "not_supported", "uncertain", "insufficient_evidence"]
    public_counts = [24, 0, 0, 0, 0]
    private_counts = [0] + [int(privileged.get(label, 0)) for label in labels[1:]]
    colors = ["#9aa0a6", "#54a24b", "#e45756", "#f2cf5b", "#72b7b2"]
    fig, ax = plt.subplots(figsize=(9.4, 4.6))
    y = np.arange(2)
    left = np.zeros(2)
    for label, color, public, private in zip(labels, colors, public_counts, private_counts):
        vals = np.array([public, private])
        ax.barh(y, vals, left=left, label=label, color=color)
        for i, count in enumerate(vals):
            if count:
                ax.text(left[i] + count/2, i, str(count), ha="center", va="center", color="white" if label in {"not_supported", "supported"} else "black")
        left += vals
    ax.set_yticks(y, ["Public-only\n24 projections", "Privileged\n48 projections"])
    ax.set_xlabel("Independently computed observable-reference rows")
    ax.set_title("Evidence sufficiency changes with permission; intent remains unlabeled")
    ax.legend(frameon=False, ncol=3, bbox_to_anchor=(0.5, -0.25), loc="upper center")
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _plot_identifiability(matched_audit: dict[str, Any], matched_summary: dict[str, Any], path: Path) -> None:
    ident = matched_audit["matched_world_identifiability"]
    categories = ["Paired worlds", "Public projection\nidentical", "Privileged evidence\ndiffers", "Parseable LLM\npredictions"]
    counts = [ident["matched_pairs"], ident["public_projection_comparisons"],
              ident["privileged_projection_different_comparisons"],
              matched_summary["completed_predictions"]]
    totals = [ident["matched_pairs"], ident["public_projection_comparisons"],
              ident["public_projection_comparisons"], matched_summary["assigned_rows"]]
    color = ["#4c78a8", "#54a24b", "#f58518", "#b279a2"]
    fig, ax = plt.subplots(figsize=(9.4, 5.3))
    bars = ax.bar(categories, [100*c/t for c,t in zip(counts, totals)], color=color)
    for bar, count, total in zip(bars, counts, totals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2, f"{count}/{total}",
                ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 115)
    ax.set_ylabel("Rate (%)")
    ax.set_title("Matched-world identifiability control", pad=14)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.5, 0.035,
             "Both parseable outputs were B5 Privileged positive-control predictions; not an accuracy estimate.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.09, 1, 1))
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def analyze(run_root: Path = RUN_ROOT, out: Path = DEFAULT_OUT) -> dict[str, Any]:
    phase_summaries = {}
    method_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    resource_rows: list[dict[str, Any]] = []
    deterministic_rows: list[dict[str, Any]] = []
    audits = {}
    for phase, assigned in PHASES.items():
        audit = _json(run_root / "audits" / f"{phase}.json")
        audits[phase] = audit
        summary, methods, metrics, resources = _phase_summary(phase, assigned, run_root, audit)
        phase_summaries[phase] = summary
        method_rows.extend(methods)
        metric_rows.extend(metrics)
        resource_rows.extend(resources)
        deterministic_rows.extend(
            {"phase": phase, "cell": key, **value}
            for key, value in sorted(audit["deterministic_rule_baselines"].items())
        )

    identity_set = {tuple(value) for phase in phase_summaries.values()
                    for value in phase["returned_model_identity"]}
    if identity_set != {("deepseek-flash", "e72d3c7f663d3e1383b00b3884cb4501")}:
        raise ValueError("returned provider model identity or fingerprint drifted")
    ledger_path = run_root / "global_budget_ledger.jsonl"
    ledger = _jsonl(ledger_path)
    reservations = [row for row in ledger if row.get("event") == "request_reserved"]
    terminals = [row for row in ledger if row.get("event") == "request_terminal"]
    if (len(reservations) != 856 or len(terminals) != 856
            or len({row.get("request_id") for row in reservations}) != 856
            or len({row.get("request_id") for row in terminals}) != 856
            or any(row.get("phase_id") not in PHASES for row in reservations + terminals)):
        raise ValueError("global request ledger fails 856-row uniqueness/phase reconciliation")
    actual_cost = round(sum(row["provider_reported_peak_cost_usd"] for row in phase_summaries.values()), 12)
    reserved_cost = round(sum(row["conservative_cost_usd"] for row in phase_summaries.values()), 12)
    if actual_cost != reserved_cost or actual_cost > 3.0:
        raise ValueError("phase cost summaries do not reconcile under USD 3 ceiling")

    total_calls = sum(row["physical_attempts"] for row in phase_summaries.values())
    total_assigned = sum(row["assigned_rows"] for row in phase_summaries.values())
    total_completed = sum(row["completed_predictions"] for row in phase_summaries.values())
    total_invalid = sum(row["invalid_or_unexecuted"] for row in phase_summaries.values())
    total_input = sum(row["input_tokens"] for row in phase_summaries.values())
    total_output = sum(row["output_tokens"] for row in phase_summaries.values())
    length_count = sum(row["finish_reason_counts"].get("length", 0)
                       for row in phase_summaries.values())
    m4 = _json(ROOT / "docs/results/full-research-execution-20261020/m4_behavior_summary.json")
    m4_probe_root = ROOT / "runs/m4"
    m4_probe_dirs = [
        m4_probe_root / "full-research-execution-20261020",
        m4_probe_root / "full-research-execution-20261020-run02",
        m4_probe_root / "full-research-execution-20261020-run03",
    ]
    m4_probe_count = _identity_probe_attempt_count(
        [directory / "identity_probes.jsonl" for directory in m4_probe_dirs])
    if m4_probe_count != 2:
        raise ValueError("the two retained M4 identity-probe HTTP attempts do not reconcile")
    matched_ident = audits["matched_worlds"]["matched_world_identifiability"]
    summary = {
        "schema_version": "colluscope-full-research-independent-results-v1",
        "research_model_calls": {"local_m4_generations": 24, "deepseek_monitor_requests": total_calls,
                                  "deepseek_retries": 0, "total_generations_and_monitor_requests": total_calls + 24,
                                  "local_m4_identity_probe_http_requests": m4_probe_count,
                                  "total_physical_http_requests_including_identity_probes": total_calls + 24 + m4_probe_count},
        "monitor": {"assigned_rows": total_assigned, "physical_http_attempts": total_calls,
                    "completed_predictions": total_completed, "invalid_or_unexecuted": total_invalid,
                    "finish_reason_length": length_count,
                    "length_rate": round(length_count / total_calls, 6),
                    "input_tokens": total_input, "output_tokens": total_output,
                    "provider_reported_cost_usd": actual_cost,
                    "reserved_cost_upper_usd": round(sum(float(row.get("reserve_usd", 0)) for row in reservations), 12),
                    "hard_request_ceiling": 856, "hard_cost_ceiling_usd": 3.0,
                    "returned_model_identity": list(next(iter(identity_set)))},
        "phases": phase_summaries,
        "method_coverage": method_rows,
        "method_resources": resource_rows,
        "deterministic_rule_baselines": deterministic_rows,
        "m4_agent": {k: m4[k] for k in (
            "assigned_groups", "attempts_started", "attempts_terminal", "terminal_statuses",
            "retry_count", "replacement_groups", "messages_recorded", "ballots_recorded",
            "proposal_eligible_groups", "settlements_recomputed", "independent_trace_replay_status",
            "usage_totals")},
        "matched_world_identifiability": {
            "matched_pairs": matched_ident["matched_pairs"],
            "public_projection_comparisons": matched_ident["public_projection_comparisons"],
            "public_projection_byte_and_reference_equal": matched_ident["public_projection_byte_and_reference_equal"],
            "privileged_projection_different_comparisons": matched_ident["privileged_projection_different_comparisons"],
            "privileged_projection_different_all_pairs": matched_ident["privileged_projection_different_all_pairs"],
            "privileged_reference_label_counts": matched_ident["privileged_reference_label_counts"],
            "model_outputs": "2/72 parseable; both B5 Privileged supported predictions on two explicit-proposal-acceptance positive-control worlds; no valid public-only or B4 output",
            "latent_collusion_reference": False,
        },
        "paired_b4_b5_on_common_assessable_instances": [
            _paired_b4_b5(audits[phase]["per_request_scores"], phase)
            for phase in PHASES
        ],
        "interpretation_boundary": [
            "M4 behavior is not estimable because all 24 first message outputs failed strict parsing.",
            "Monitor accuracy comparisons are conditional on parseable completions; 715/856 outputs reached the 128-token finish_reason=length cap.",
            "No experiment creates or validates a latent-collusion gold label.",
            "Public equality and privileged evidence differences are deterministic construction checks, not LLM performance claims.",
        ],
        "raw_text_or_private_message_in_public_summary": False,
    }
    if total_calls != total_assigned or total_completed + total_invalid != total_assigned:
        raise ValueError("assigned, completed and failed request denominators do not conserve")
    out.mkdir(parents=True, exist_ok=True)
    figure_dir = out / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    (out / "full_research_results_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _write_csv(out / "monitor_method_coverage.csv", method_rows)
    _write_csv(out / "monitor_method_resources.csv", resource_rows)
    _write_csv(out / "monitor_task_view_metrics.csv", metric_rows)
    _write_csv(out / "deterministic_rule_baselines.csv", deterministic_rows)
    _plot_m4(m4, figure_dir / "m4_attempt_disposition.png")
    _plot_method_coverage(method_rows, figure_dir / "monitor_method_coverage.png")
    _plot_evidence_sufficiency(audits["matched_worlds"], figure_dir / "matched_evidence_sufficiency.png")
    _plot_identifiability(audits["matched_worlds"], phase_summaries["matched_worlds"],
                          figure_dir / "matched_world_identifiability.png")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=RUN_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = analyze(args.run_root, args.out)
    print(json.dumps({"status": "PASS_ANALYSIS_RECONCILIATION",
                      "monitor_calls": result["monitor"]["physical_http_attempts"],
                      "completed_predictions": result["monitor"]["completed_predictions"],
                      "cost_usd": result["monitor"]["provider_reported_cost_usd"],
                      "summary_path": str((args.out / "full_research_results_summary.json").resolve()),
                      "raw_text_in_output": result["raw_text_or_private_message_in_public_summary"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
