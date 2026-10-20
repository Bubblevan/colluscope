#!/usr/bin/env python3
"""Offline replay of a saved Sprint Monitor live run; never performs inference."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts import run_sprint_monitor as monitor  # noqa: E402
from colluscope.sprint_baselines import parse_model_output, provenance_gate  # noqa: E402
from colluscope.sprint_metrics import score_one  # noqa: E402
from colluscope.sprint_replay import reference_for_case  # noqa: E402
from scripts.local_llama_security import verify_private_directory_acl  # noqa: E402


class AuditFailure(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuditFailure(f"cannot read valid JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise AuditFailure(f"JSON root is not an object: {path.name}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise AuditFailure(f"blank append-only ledger row: {path.name}:{index}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise AuditFailure(f"invalid JSONL row: {path.name}:{index}") from exc
        if not isinstance(row, dict):
            raise AuditFailure(f"non-object JSONL row: {path.name}:{index}")
        rows.append(row)
    return rows


def _unique(rows: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or value in result:
            raise AuditFailure(f"{label} has a missing or duplicate {key}")
        result[value] = row
    return result


def _expected_predictions(request, raw_text: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    prediction = parse_model_output(raw_text, request.task)
    reference = reference_for_case(request.source, request.task, request.view_name, request.permission)
    raw_score = score_one(request.source, reference, request.baseline_id, prediction,
                          view_name=request.view_name, permission=request.permission)
    gate = provenance_gate(prediction, request.task, request.evidence)
    gated_prediction = {**prediction, "label": gate["gated_label"]}
    gated_score = score_one(request.source, reference, f"{request.baseline_id}_gated",
                            gated_prediction, view_name=request.view_name,
                            permission=request.permission)
    raw_row = {"request_id": request.request_id, "raw_prediction": prediction,
               "reference_label": reference["label"], "reference_assessable": reference["assessable"],
               "score": raw_score}
    gated_row = {"request_id": request.request_id, "raw_label": prediction["label"],
                 "gated_label": gate["gated_label"], "gate_reason": gate["gate_reason"],
                 "citation_membership_valid": gate["citation_membership_valid"],
                 "score": gated_score}
    return raw_row, gated_row, reference


def audit(run: Path, *, config_path: Path = monitor.CONFIG_PATH,
          allow_fake_test_run: bool = False) -> dict[str, Any]:
    run = Path(run).resolve()
    config_path = Path(config_path).resolve()
    config = monitor._load_config(config_path)
    manifest = _read_json(run / "run_manifest.json")
    mode = manifest.get("mode")
    if mode == "live_fake_transport_test":
        if not allow_fake_test_run:
            raise AuditFailure("fake-transport trace is not a real Monitor run")
    elif mode != "live":
        raise AuditFailure("auditor accepts only live or explicitly allowed fake-live traces")
    if (manifest.get("runtime_revision") != "sprint-monitor-runtime-v1.2"
            or manifest.get("requested_mode") != "live"
            or manifest.get("protocol_id") != monitor.PROTOCOL
            or manifest.get("runtime_config_sha256") != monitor._sha(config_path.read_bytes())
            or manifest.get("request_count") != 280
            or manifest.get("endpoint") != config["endpoint"]
            or manifest.get("model_alias") != config["model_alias"]):
        raise AuditFailure("run manifest differs from the frozen live Monitor contract")
    for relative, expected_hash in manifest.get("prompt_hashes", {}).items():
        path = (ROOT / relative).resolve()
        if ROOT not in path.parents or not path.is_file() or monitor._sha(path.read_bytes()) != expected_hash:
            raise AuditFailure(f"frozen prompt artifact changed: {relative}")
    for relative, expected_hash in manifest.get("runtime_code_sha256", {}).items():
        path = (ROOT / relative).resolve()
        if ROOT not in path.parents or not path.is_file() or monitor._sha(path.read_bytes()) != expected_hash:
            raise AuditFailure(f"frozen runtime code changed: {relative}")

    schedule = monitor.build_schedule(config)
    expected = {request.request_id: request for request in schedule}
    if len(expected) != 280:
        raise AuditFailure("independent schedule reconstruction did not produce 280 unique rows")
    progress = _unique(_read_jsonl(run / "progress.jsonl"), "request_id", "progress")
    if set(progress) != set(expected):
        raise AuditFailure("progress ledger does not contain all 280 assigned terminal rows")
    attempts = _read_jsonl(run / "attempts.jsonl")
    starts = _unique([row for row in attempts if row.get("event") == "attempt_started"],
                     "request_id", "attempt starts")
    ends = _unique([row for row in attempts if row.get("event") == "attempt_terminal"],
                   "request_id", "attempt terminals")
    if set(starts) != set(ends) or len(starts) > min(280, config["max_http_attempts"]):
        raise AuditFailure("attempt ledger has retries, missing terminals, or exceeds the 280 cap")
    request_paths = {path.stem: path for path in (run / "requests").glob("*.json")}
    response_paths = {path.stem: path for path in (run / "responses").glob("*.json")}
    if set(request_paths) != set(starts) or set(response_paths) != set(starts):
        raise AuditFailure("raw request/response files do not align exactly with started attempts")

    raw_rows = _unique(_read_jsonl(run / "raw_predictions.jsonl"), "request_id", "raw predictions")
    gated_rows = _unique(_read_jsonl(run / "gated_predictions.jsonl"), "request_id", "gated predictions")
    completed_ids: set[str] = set()
    identities: set[tuple[str, str]] = set()
    input_bytes = 0
    reported_cost = 0.0
    missing_usage_reserve = 0.0
    for request_id, request in expected.items():
        terminal = progress[request_id]
        if request_id not in starts:
            if terminal.get("status") not in {"NOT_SENT_AFTER_STOP", "BUDGET_EXHAUSTED", "COST_BUDGET_EXHAUSTED"}:
                raise AuditFailure("an unstarted row has a status that implies execution")
            if request_id in raw_rows or request_id in gated_rows:
                raise AuditFailure("an unstarted row has a model prediction")
            continue

        start, end = starts[request_id], ends[request_id]
        if (start.get("retry_count") != 0 or end.get("retry_count") != 0
                or start.get("auth_header_saved") is not False
                or end.get("auth_header_saved") is not False
                or start.get("endpoint") != config["endpoint"]
                or start.get("body_sha256") != request.body_sha256
                or end.get("body_sha256") != request.body_sha256
                or end.get("transport_status") != terminal.get("status")):
            raise AuditFailure("attempt receipt differs from frozen request or terminal progress")
        request_bytes = request_paths[request_id].read_bytes()
        if request_bytes != monitor._json_bytes(request.http_payload):
            raise AuditFailure(f"raw HTTP request differs from independently compiled payload: {request_id}")
        if monitor._sha(request_bytes) != request.body_sha256:
            raise AuditFailure("raw request SHA-256 mismatch")
        if b"Authorization" in request_bytes or b"Bearer " in request_bytes:
            raise AuditFailure("provider credential appeared in the raw request body")
        input_bytes += len(request_bytes)

        response_bytes = response_paths[request_id].read_bytes()
        response_hash = monitor._sha(response_bytes)
        if (terminal.get("response_sha256") != response_hash
                or end.get("response_sha256") != response_hash):
            raise AuditFailure("raw response SHA-256 mismatch")
        if b"Authorization" in response_bytes or b"Bearer " in response_bytes:
            raise AuditFailure("provider credential appeared in the raw response")
        try:
            body = json.loads(response_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = None
        usage = body.get("usage") if isinstance(body, dict) else None
        if (isinstance(usage, dict)
                and type(usage.get("prompt_tokens", usage.get("input_tokens"))) is int
                and type(usage.get("completion_tokens", usage.get("output_tokens"))) is int
                and usage.get("prompt_tokens", usage.get("input_tokens")) >= 0
                and usage.get("completion_tokens", usage.get("output_tokens")) >= 0
                and terminal.get("status") != "INVALID_USAGE_ACCOUNTING"):
            reported_cost += (
                usage.get("prompt_tokens", usage.get("input_tokens")) * config["input_usd_per_million_tokens_peak_cache_miss"]
                + usage.get("completion_tokens", usage.get("output_tokens")) * config["output_usd_per_million_tokens_peak"]
            ) / 1_000_000
        else:
            missing_usage_reserve += request.reserve_usd

        if terminal.get("status") != "COMPLETED":
            if request_id in raw_rows or request_id in gated_rows:
                raise AuditFailure("failed response was silently scored or repaired")
            continue
        if not isinstance(body, dict) or body.get("model") not in config["expected_response_models"]:
            raise AuditFailure("completed response lacks an allowed model identity")
        fingerprint = body.get("system_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            raise AuditFailure("completed response lacks a provider system fingerprint")
        identities.add((body["model"], fingerprint))
        choices = body.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or choices[0].get("finish_reason") not in {"stop", "end_turn"}:
            raise AuditFailure("completed response lacks one allowed terminal choice")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise AuditFailure("completed response has no assistant text")
        expected_raw, expected_gated, reference = _expected_predictions(request, content)
        if raw_rows.get(request_id) != expected_raw or gated_rows.get(request_id) != expected_gated:
            raise AuditFailure("saved raw/gated predictions differ from independent rescoring")
        ref_path = run / "analysis" / "references" / f"{request_id}.json"
        # Reference file is researcher-only. Some runtime versions store it in analysis/references;
        # the saved copy, when present, must equal the independently reconstructed reference.
        if ref_path.exists() and _read_json(ref_path) != reference:
            raise AuditFailure("researcher reference artifact differs from independent replay")
        completed_ids.add(request_id)

    if set(raw_rows) != completed_ids or set(gated_rows) != completed_ids:
        raise AuditFailure("raw/gated prediction rows do not reconcile to completed model outputs")
    if len(identities) > 1:
        raise AuditFailure("provider model/fingerprint drift exists in completed responses")

    summary = _read_json(run / "summary.json")
    fake = mode == "live_fake_transport_test"
    expected_physical = 0 if fake else len(starts)
    expected_real_calls = 0 if fake else len(starts)
    cost_total = round(reported_cost + missing_usage_reserve, 12)
    if (summary.get("assigned_rows") != 280 or summary.get("terminal_rows") != 280
            or summary.get("logical_http_requests") != len(starts)
            or summary.get("physical_http_attempts") != expected_physical
            or summary.get("real_model_or_api_calls") != expected_real_calls
            or summary.get("retries") != 0
            or abs(summary.get("conservative_total_peak_cost_usd", -1) - cost_total) > 1e-12
            or cost_total > config["hard_estimated_cost_usd"]):
        raise AuditFailure("run summary differs from independent attempt/cost replay")
    if not fake:
        acl = verify_private_directory_acl(run)
        if acl.get("verified") is not True:
            raise AuditFailure("private run ACL verification failed")
    receipt = {
        "schema_version": "sprint-monitor-live-independent-audit-v1",
        "status": "PASS_FAKE_TRANSPORT_REPLAY_ONLY" if fake else "PASS_LIVE_MONITOR_TRACE_AND_SCORE_REPLAY",
        "mode": mode,
        "assigned_rows": 280,
        "started_attempts": len(starts),
        "completed_predictions_independently_rescored": len(completed_ids),
        "raw_gated_predictions_match": True,
        "provider_identities": [list(value) for value in sorted(identities)],
        "provider_reported_peak_cost_usd": round(reported_cost, 12),
        "missing_usage_reserved_upper_usd": round(missing_usage_reserve, 12),
        "conservative_total_peak_cost_usd": cost_total,
        "hard_cost_ceiling_usd": config["hard_estimated_cost_usd"],
        "raw_request_body_bytes": input_bytes,
        "credential_material_saved": False,
        "real_model_or_api_calls": expected_real_calls,
        "claim_scope": "trace integrity and deterministic rescoring only; no collusion inference",
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=monitor.CONFIG_PATH)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    receipt = audit(args.run, config_path=args.config)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
