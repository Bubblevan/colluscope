#!/usr/bin/env python3
"""Independently replay one full-research Monitor phase without inference."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.monitor_aggregate_budget import AggregateBudget  # noqa: E402
from colluscope.sprint_baselines import (  # noqa: E402
    _b0_prediction, _b1_prediction, canonical_json, parse_model_output,
    provenance_gate,
)
from colluscope.sprint_metrics import score_one  # noqa: E402
from colluscope.sprint_replay import reference_for_case  # noqa: E402
from scripts import audit_sprint_monitor_live as legacy_auditor  # noqa: E402
from scripts import prepare_full_research_monitor as freeze  # noqa: E402
from scripts import run_sprint_monitor as monitor  # noqa: E402
from scripts.local_llama_security import verify_private_directory_acl  # noqa: E402


class AuditFailure(RuntimeError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise AuditFailure(f"expected JSON object: {path.name}")
    return value


def _unique(rows: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or value in result:
            raise AuditFailure(f"{label} has missing or duplicate {key}")
        result[value] = row
    return result


def _scores_for(request, prediction: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    reference = reference_for_case(request.source, request.task, request.view_name, request.permission)
    raw_score = score_one(request.source, reference, request.baseline_id, prediction,
                          view_name=request.view_name, permission=request.permission)
    gate = provenance_gate(prediction, request.task, request.evidence)
    gated_prediction = {**prediction, "label": gate["gated_label"]}
    gated_score = score_one(request.source, reference, f"{request.baseline_id}_gated",
                            gated_prediction, view_name=request.view_name,
                            permission=request.permission)
    gated_row = {"raw_label": prediction["label"], "gated_label": gate["gated_label"],
                 "gate_reason": gate["gate_reason"],
                 "citation_membership_valid": gate["citation_membership_valid"],
                 "score": gated_score}
    return reference, raw_score, gated_row


def _metric(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row.get("score") is not None]
    assessable = [row for row in scored if row["score"].get("assessable")]
    correct = sum(row["score"].get("exact_correct") is True for row in assessable)
    positives = [row for row in assessable if row["score"].get("positive_reference")]
    negatives = [row for row in assessable if row["score"].get("negative_reference")]
    true_positive = sum(row["score"].get("positive_prediction") is True for row in positives)
    false_positive = sum(row["score"].get("positive_prediction") is True for row in negatives)
    appropriate = [row for row in scored if row["score"].get("appropriate_abstention") is not None]
    citation_rows = [row for row in scored if row["score"].get("citation_membership_valid") is not None]
    return {
        "requested_rows": len(rows), "scored_rows": len(scored),
        "unscored_rows": len(rows) - len(scored),
        "assessable_rows": len(assessable), "correct_assessable_rows": correct,
        "accuracy_on_assessable": correct / len(assessable) if assessable else None,
        "positive_reference_rows": len(positives),
        "positive_recall": true_positive / len(positives) if positives else None,
        "negative_reference_rows": len(negatives),
        "false_positive_rate_on_negative": false_positive / len(negatives) if negatives else None,
        "positive_predictions_on_negative_rows": false_positive,
        "appropriate_abstention_rows": sum(
            row["score"].get("appropriate_abstention") is True for row in appropriate),
        "abstention_assessable_rows": len(appropriate),
        "appropriate_abstention_rate": (
            sum(row["score"].get("appropriate_abstention") is True for row in appropriate) / len(appropriate)
            if appropriate else None),
        "unsupported_sequence_claims": sum(
            row["score"].get("unsupported_sequence_claim") is True for row in scored),
        "hard_negative_rows": sum(row["score"].get("hard_negative_control") is True for row in scored),
        "citation_membership_valid_rows": sum(
            row["score"].get("citation_membership_valid") is True for row in citation_rows),
        "citation_rows": len(citation_rows),
        "citation_sufficient_positive_rows": sum(
            row["score"].get("citation_sufficient") is True for row in scored),
        "positive_prediction_rows": sum(row["score"].get("positive_prediction") is True for row in scored),
        "abstained_rows": sum(row["score"].get("abstained") is True for row in scored),
    }


def _matched_world_audit(freeze_dir: Path, plan_rows: list[dict[str, Any]],
                         score_records: list[dict[str, Any]]) -> dict[str, Any]:
    pair_path = freeze_dir / "pair_map.private.json"
    pair_meta = _read(pair_path)
    by_req = {row["request_id"]: row for row in plan_rows}
    pred_by_req = {row["request_id"]: row for row in score_records}
    public_equal = privileged_different = 0
    paired_references = Counter()
    world_prediction_rows = []
    for pair in pair_meta["pairs"]:
        sources = [entry["source"] for entry in pair["worlds"]]
        for baseline in ("B4_raw_fusion", "B5_evidence_aware"):
            public_rows = [row for row in plan_rows if row["baseline_id"] == baseline
                           and row.get("instance_id") == f"{pair['pair_id']}-deduplicated-public"]
            if len(public_rows) != 1:
                raise AuditFailure("matched pair lacks one deduplicated Public-only request")
            public_row = public_rows[0]
            public_inputs = [
                monitor.build_monitor_payload(source, baseline, "explicit_sequence", "public_only")[0]
                for source in sources
            ]
            public_bodies = [monitor._json_bytes({"model": "deepseek-flash", **payload})
                             for payload in public_inputs]
            public_refs = [reference_for_case(source, "explicit_sequence",
                                             monitor.VIEW_BY_BASELINE[baseline], "public_only")
                           for source in sources]
            visible_refs = [{key: value for key, value in reference.items()
                             if key not in {"case_ref", "full_sequence_reference"}}
                            for reference in public_refs]
            if public_bodies[0] != public_bodies[1] or visible_refs[0] != visible_refs[1]:
                raise AuditFailure("matched worlds are distinguishable from Public-only evidence")
            public_equal += 1

            privileged_evidence = [
                monitor.build_monitor_payload(source, baseline, "explicit_sequence", "privileged_audit")[1]
                for source in sources
            ]
            if canonical_json(privileged_evidence[0]) != canonical_json(privileged_evidence[1]):
                privileged_different += 1
            for world_index, source in enumerate(sources):
                privileged_row = next((row for row in plan_rows
                                       if row["baseline_id"] == baseline
                                       and row["case_ref"] == source["case_ref"]
                                       and row["permission"] == "privileged_audit"), None)
                if privileged_row is None:
                    raise AuditFailure("matched pair lacks a Privileged request for one world")
                reference = reference_for_case(source, "explicit_sequence",
                                               monitor.VIEW_BY_BASELINE[baseline], "privileged_audit")
                paired_references[reference["label"]] += 1
                result = pred_by_req.get(privileged_row["request_id"], {})
                world_prediction_rows.append({
                    "pair_id": pair["pair_id"], "construction_family": pair["construction_family"],
                    "baseline_id": baseline, "world_index": world_index,
                    "reference_label": reference["label"],
                    "prediction_label": result.get("prediction_label"),
                    "request_status": result.get("status"),
                })
            shared_result = pred_by_req.get(public_row["request_id"], {})
            for world_index, reference in enumerate(public_refs):
                world_prediction_rows.append({
                    "pair_id": pair["pair_id"], "construction_family": pair["construction_family"],
                    "baseline_id": baseline, "world_index": world_index,
                    "permission": "public_only", "reference_label": reference["label"],
                    "prediction_label": shared_result.get("prediction_label"),
                    "request_status": shared_result.get("status"),
                })
    return {
        "matched_pairs": len(pair_meta["pairs"]),
        "public_projection_comparisons": public_equal,
        "public_projection_byte_and_reference_equal": public_equal == 24,
        "privileged_projection_different_comparisons": privileged_different,
        "privileged_projection_different_all_pairs": privileged_different == 24,
        "privileged_reference_label_counts": dict(paired_references),
        "world_level_scoring_rows": world_prediction_rows,
    }


def audit(run: Path, freeze_dir: Path, config_path: Path, phase: str) -> dict[str, Any]:
    run = run.resolve()
    freeze_dir = freeze_dir.resolve()
    config_path = config_path.resolve()
    config = monitor._load_config(config_path)
    freeze_audit = freeze.verify_plan(freeze_dir, config_path)
    requests = freeze.load_plan(freeze_dir, config_path)
    plan_rows = [json.loads(line) for line in (freeze_dir / "plan.jsonl").read_text(encoding="utf-8").splitlines() if line]
    expected = {row.request_id: row for row in requests}
    manifest = _read(run / "run_manifest.json")
    if (manifest.get("requested_mode") != "live"
            or manifest.get("mode") != "live"
            or manifest.get("runtime_revision") != "sprint-monitor-runtime-v1.3"
            or manifest.get("protocol_id") != monitor.PROTOCOL
            or manifest.get("runtime_config_sha256") != _sha(config_path.read_bytes())
            or manifest.get("request_count") != len(expected)
            or manifest.get("request_schedule_sha256") != freeze_audit["schedule_sha256"]
            or manifest.get("endpoint") != config["endpoint"]
            or manifest.get("model_alias") != config["model_alias"]):
        raise AuditFailure("run manifest differs from the frozen full-research phase")
    if (manifest.get("aggregate_budget") or {}).get("execution_id") != freeze.EXECUTION_ID:
        raise AuditFailure("run manifest lacks the full-research aggregate budget identity")
    for relative, expected_hash in manifest.get("prompt_hashes", {}).items():
        path = (ROOT / relative).resolve()
        if ROOT not in path.parents or not path.is_file() or _sha(path.read_bytes()) != expected_hash:
            raise AuditFailure("frozen Monitor prompt changed")
    for relative, expected_hash in manifest.get("runtime_code_sha256", {}).items():
        path = (ROOT / relative).resolve()
        if ROOT not in path.parents or not path.is_file() or _sha(path.read_bytes()) != expected_hash:
            raise AuditFailure(f"runtime source changed after phase freeze: {relative}")
    if phase == "scripted_controls":
        old = legacy_auditor.audit(run, config_path=config_path)
        if old.get("status") != "PASS_LIVE_MONITOR_TRACE_AND_SCORE_REPLAY":
            raise AuditFailure("independent original 280-row auditor did not pass")

    progress = _unique(monitor._read_jsonl(run / "progress.jsonl"), "request_id", "progress")
    attempts = monitor._read_jsonl(run / "attempts.jsonl")
    starts = _unique([row for row in attempts if row.get("event") == "attempt_started"],
                     "request_id", "attempt starts")
    ends = _unique([row for row in attempts if row.get("event") == "attempt_terminal"],
                   "request_id", "attempt terminals")
    if set(progress) != set(expected) or set(starts) != set(ends) or not set(starts) <= set(expected):
        raise AuditFailure("request, progress, or attempt ledgers do not reconcile to the frozen plan")
    if len(starts) > config["max_http_attempts"]:
        raise AuditFailure("phase physical HTTP attempt cap exceeded")
    request_file_ids = {path.stem for path in (run / "requests").glob("*.json")}
    if set(starts) != request_file_ids:
        raise AuditFailure("raw request files do not match started physical attempts")
    response_files = {path.stem for path in (run / "responses").glob("*.json")}
    if response_files != set(starts):
        raise AuditFailure("raw response files do not match started physical attempts")

    raw_saved = _unique(monitor._read_jsonl(run / "raw_predictions.jsonl"), "request_id", "raw predictions")
    gated_saved = _unique(monitor._read_jsonl(run / "gated_predictions.jsonl"), "request_id", "gated predictions")
    score_records = []
    identity_set = set()
    provider_reported_cost = 0.0
    missing_usage_reserve = 0.0
    input_tokens = output_tokens = 0
    elapsed_seconds = 0.0
    for request_id, request in expected.items():
        terminal = progress[request_id]
        if request_id not in starts:
            if terminal.get("status") not in {"NOT_SENT_AFTER_STOP", "BUDGET_EXHAUSTED",
                                               "COST_BUDGET_EXHAUSTED"}:
                raise AuditFailure("unstarted request has an invalid terminal status")
            if request_id in raw_saved or request_id in gated_saved:
                raise AuditFailure("unstarted request has a saved model prediction")
            score_records.append({"request_id": request_id, "status": terminal["status"],
                                  "prediction_label": None, "score": None})
            continue
        start, end = starts[request_id], ends[request_id]
        if (start.get("retry_count") != 0 or end.get("retry_count") != 0
                or start.get("auth_header_saved") is not False
                or end.get("auth_header_saved") is not False
                or start.get("endpoint") != config["endpoint"]
                or start.get("body_sha256") != request.body_sha256
                or end.get("body_sha256") != request.body_sha256
                or end.get("transport_status") != terminal.get("status")):
            raise AuditFailure("attempt receipt differs from frozen schedule or no-retry contract")
        request_path = run / "requests" / f"{request_id}.json"
        request_bytes = request_path.read_bytes()
        if request_bytes != monitor._json_bytes(request.http_payload) or _sha(request_bytes) != request.body_sha256:
            raise AuditFailure("raw outgoing bytes differ from the frozen request")
        if b"Authorization" in request_bytes or b"Bearer " in request_bytes:
            raise AuditFailure("credential material appears in an outgoing request body")
        response_bytes = (run / "responses" / f"{request_id}.json").read_bytes()
        response_hash = _sha(response_bytes)
        if response_hash != terminal.get("response_sha256") or response_hash != end.get("response_sha256"):
            raise AuditFailure("raw provider response hash differs from both terminal ledgers")
        if b"Authorization" in response_bytes or b"Bearer " in response_bytes:
            raise AuditFailure("credential material appears in a saved response")
        try:
            body = json.loads(response_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = None
        usage = body.get("usage") if isinstance(body, dict) else None
        valid_usage = (
            isinstance(usage, dict)
            and type(usage.get("prompt_tokens", usage.get("input_tokens"))) is int
            and type(usage.get("completion_tokens", usage.get("output_tokens"))) is int
            and usage.get("prompt_tokens", usage.get("input_tokens")) >= 0
            and usage.get("completion_tokens", usage.get("output_tokens")) >= 0
            and terminal.get("status") != "INVALID_USAGE_ACCOUNTING"
        )
        if valid_usage:
            in_count = usage.get("prompt_tokens", usage.get("input_tokens"))
            out_count = usage.get("completion_tokens", usage.get("output_tokens"))
            input_tokens += in_count
            output_tokens += out_count
            actual = (in_count * config["input_usd_per_million_tokens_peak_cache_miss"]
                      + out_count * config["output_usd_per_million_tokens_peak"]) / 1_000_000
            provider_reported_cost += actual
        else:
            missing_usage_reserve += request.reserve_usd
        elapsed_seconds += float(terminal.get("elapsed_seconds", 0.0) or 0.0)
        if terminal.get("status") != "COMPLETED":
            if request_id in raw_saved or request_id in gated_saved:
                raise AuditFailure("failed response was silently repaired or scored")
            score_records.append({"request_id": request_id, "status": terminal["status"],
                                  "prediction_label": None, "score": None})
            continue
        if (not isinstance(body, dict) or body.get("model") not in config["expected_response_models"]
                or not isinstance(body.get("system_fingerprint"), str)
                or not body.get("system_fingerprint")):
            raise AuditFailure("completed response lacks the expected identity/fingerprint")
        identity_set.add((body["model"], body["system_fingerprint"]))
        choices = body.get("choices")
        if (not isinstance(choices, list) or len(choices) != 1
                or choices[0].get("finish_reason") not in {"stop", "end_turn"}):
            raise AuditFailure("completed response lacks one valid terminal choice")
        text = choices[0].get("message", {}).get("content")
        if not isinstance(text, str):
            raise AuditFailure("completed response lacks assistant content")
        prediction = parse_model_output(text, request.task)
        reference = reference_for_case(request.source, request.task, request.view_name, request.permission)
        expected_reference = _read(freeze_dir / "references" / f"{request_id}.json")
        if reference != expected_reference:
            raise AuditFailure("pre-frozen independent reference differs from actual-event recomputation")
        reference_file = run / "analysis" / "references" / f"{request_id}.json"
        if reference_file.exists() and _read(reference_file) != reference:
            raise AuditFailure("runtime researcher reference differs from independent recomputation")
        expected_raw_score = score_one(request.source, reference, request.baseline_id, prediction,
                                       view_name=request.view_name, permission=request.permission)
        gate = provenance_gate(prediction, request.task, request.evidence)
        gated_prediction = {**prediction, "label": gate["gated_label"]}
        expected_gated_score = score_one(request.source, reference, f"{request.baseline_id}_gated",
                                         gated_prediction, view_name=request.view_name,
                                         permission=request.permission)
        saved_raw = raw_saved.get(request_id)
        saved_gated = gated_saved.get(request_id)
        if (saved_raw is None or saved_raw.get("raw_prediction") != prediction
                or saved_raw.get("reference_label") != reference["label"]
                or saved_raw.get("reference_assessable") != reference["assessable"]
                or saved_raw.get("score") != expected_raw_score):
            raise AuditFailure("raw model prediction or score does not independently replay")
        if (saved_gated is None or saved_gated.get("raw_label") != prediction["label"]
                or saved_gated.get("gated_label") != gate["gated_label"]
                or saved_gated.get("gate_reason") != gate["gate_reason"]
                or saved_gated.get("citation_membership_valid") != gate["citation_membership_valid"]
                or saved_gated.get("score") != expected_gated_score):
            raise AuditFailure("provenance-gated prediction or score does not independently replay")
        score_records.append({
            "request_id": request_id, "status": terminal["status"],
            "baseline_id": request.baseline_id, "permission": request.permission,
            "task": request.task, "case_ref": request.case_ref,
            "family_id": request.family_id, "prediction_label": prediction["label"],
            "gated_label": gate["gated_label"], "raw_score": expected_raw_score,
            "gated_score": expected_gated_score,
        })

    completed_ids = {row["request_id"] for row in score_records if row["status"] == "COMPLETED"}
    if set(raw_saved) != completed_ids or set(gated_saved) != completed_ids or len(identity_set) > 1:
        raise AuditFailure("saved score rows or stable provider identity do not reconcile")
    budget = AggregateBudget(Path(manifest["aggregate_budget"]["ledger_path"]), freeze.EXECUTION_ID)
    global_rows = budget.rows()
    global_reservations = {row["request_id"]: row for row in global_rows
                           if row.get("event") == "request_reserved" and row.get("phase_id") == phase}
    global_terminals = {row["request_id"]: row for row in global_rows
                        if row.get("event") == "request_terminal" and row.get("phase_id") == phase}
    if set(global_reservations) != set(starts) or set(global_terminals) != set(starts):
        raise AuditFailure("shared budget ledger differs from actual phase attempts")
    for request_id, reservation in global_reservations.items():
        if reservation.get("body_sha256") != expected[request_id].body_sha256:
            raise AuditFailure("global budget ledger request hash differs from frozen schedule")
    budget_summary = budget.summary()
    if (budget_summary["reserved_requests"] > 856
            or budget_summary["reserved_peak_cost_usd"] > 3.0 + 1e-12):
        raise AuditFailure("aggregate DeepSeek budget cap exceeded")
    run_summary = _read(run / "summary.json")
    actual_cost = round(provider_reported_cost + missing_usage_reserve, 12)
    if (run_summary.get("assigned_rows") != len(expected)
            or run_summary.get("terminal_rows") != len(expected)
            or run_summary.get("real_model_or_api_calls") != len(starts)
            or run_summary.get("physical_http_attempts") != len(starts)
            or run_summary.get("retries") != 0
            or abs(run_summary.get("conservative_total_peak_cost_usd", -1) - actual_cost) > 1e-12
            or actual_cost > config["hard_estimated_cost_usd"] + 1e-12):
        raise AuditFailure("run summary differs from independent calls/cost reconstruction")
    if verify_private_directory_acl(run).get("verified") is not True:
        raise AuditFailure("raw Monitor phase directory ACL failed independent verification")

    metric_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    deterministic_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for request in requests:
        reference = reference_for_case(request.source, request.task, request.view_name, request.permission)
        for baseline_name, function in (("B0_always_negative", _b0_prediction),
                                        ("B1_deterministic", _b1_prediction)):
            prediction = function(request.evidence, request.task)
            score = score_one(request.source, reference, baseline_name, prediction,
                              view_name=request.view_name, permission=request.permission)
            deterministic_rows[
                f"{baseline_name}|{request.task}|{request.permission}|{request.view_name}"
            ].append({"score": score})
        result = next(row for row in score_records if row["request_id"] == request.request_id)
        group_key = f"{request.baseline_id}|{request.task}|{request.permission}"
        raw_score = result.get("raw_score")
        metric_rows[group_key].append({"score": raw_score})
        if request.baseline_id == "B5_evidence_aware" and result.get("gated_score") is not None:
            metric_rows[f"B5_provenance_gated|{request.task}|{request.permission}"].append(
                {"score": result["gated_score"]})
    metrics = {key: _metric(rows) for key, rows in sorted(metric_rows.items())}
    deterministic_metrics = {key: _metric(rows) for key, rows in deterministic_rows.items()}
    result = {
        "schema_version": "colluscope-full-research-monitor-independent-audit-v1",
        "phase_id": phase, "integrity_status": "PASS_INDEPENDENT_TRACE_AND_SCORE_REPLAY",
        "input_freeze_status": freeze_audit["status"],
        "assigned_rows": len(expected), "physical_attempts": len(starts),
        "completed_predictions": len(completed_ids),
        "failed_or_unexecuted": len(expected) - len(completed_ids),
        "retries": 0, "returned_model_identity": [list(value) for value in sorted(identity_set)],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens,
                  "provider_reported_cost_usd": round(provider_reported_cost, 12),
                  "missing_usage_reserved_upper_usd": round(missing_usage_reserve, 12),
                  "conservative_cost_usd": actual_cost,
                  "elapsed_seconds_sum": round(elapsed_seconds, 6)},
        "aggregate_budget": budget_summary,
        "task_view_metrics": metrics,
        "deterministic_rule_baselines": deterministic_metrics,
        "per_request_scores": score_records,
        "raw_model_text_in_audit": False,
    }
    if phase == "matched_worlds":
        result["matched_world_identifiability"] = _matched_world_audit(freeze_dir, plan_rows, score_records)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=tuple(freeze.PHASE_CONFIGS))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True,
                        help="private audit output path under ignored runs/")
    args = parser.parse_args()
    phase = args.phase
    freeze_dir = args.freeze or freeze.FREEZE_ROOT / phase
    result = audit(args.run, freeze_dir, freeze.PHASE_CONFIGS[phase], phase)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items()
                      if key not in {"per_request_scores", "task_view_metrics",
                                     "deterministic_rule_baselines", "matched_world_identifiability"}},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
