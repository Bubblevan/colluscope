#!/usr/bin/env python3
"""Recompute M2-V2 compatibility validity from exact saved HTTP responses."""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import tomllib
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.m2_v2_contract import (
    ContractError, ENUMS, ROOT_FIELDS, parse_raw_output, validate_prediction, validate_usage_limits,
)
from colluscope.m2_corpus import file_sha256
from colluscope.openai_compat_llamacpp import llama_runtime_bundle_identity

CONFIG = ROOT / "configs/m2-v2.toml"
DEFAULT_OUT = ROOT / "runs/m2-v2/recovery-20261019/study"


class AuditError(ValueError):
    pass


def _error_class(error: str | None) -> str:
    if error is None:
        return "contract_valid"
    if error.startswith(("invalid_json:", "nonempty_or_unrecognized_reasoning_prefix",
                         "truncated_finish_reason_length", "assistant_output_not_text")):
        return "syntax_prefix_or_truncation"
    if any(marker in error for marker in (
            "citation", "unknown_evidence_ref", "lacks_multiple_public",
            "lacks_message_and_action", "positive_claim_lacks_source_refs")):
        return "evidence_reference_violation"
    if "abstention" in error or "acceptance_reason" in error or "no_delivered_message" in error:
        return "abstention_semantics_violation"
    if "not_in_view" in error or "without_visible_messages" in error or \
            "private_claim_without_visible" in error:
        return "view_permission_mismatch"
    return "other_contract_violation"


def _model_output_summary(value: Any, visible_ids: set[str]) -> dict[str, Any]:
    fields = ("public_harm", "ballot_disagreement", "message_delivery", "allocation_proposal",
              "action_concordance", "explicit_acceptance", "explicit_commitment", "observable_sequence")
    claims = {field: value[field] if isinstance(value, dict) and isinstance(value.get(field), str)
              and len(value[field]) <= 48 else "missing_or_invalid" for field in fields}
    refs = value.get("evidence_refs") if isinstance(value, dict) else None
    ids: list[str] = []
    claim_ids: dict[str, list[str]] = defaultdict(list)
    if isinstance(refs, dict):
        for claim, items in refs.items():
            if isinstance(items, list):
                valid_items = [item for item in items if isinstance(item, str)]
                ids.extend(valid_items)
                claim_ids[str(claim)].extend(valid_items)
    elif isinstance(refs, list):
        for item in refs:
            if isinstance(item, str) and ":" in item:
                claim, _, event_id = item.partition(":")
                ids.append(event_id)
                claim_ids[claim].append(event_id)
    prefix_counts = Counter(item[:1] if item else "empty" for item in ids)
    unknown_prefix_counts = Counter(item[:1] if item else "empty" for item in ids
                                    if item not in visible_ids)
    prefix_counts_by_claim = {claim: dict(Counter(item[:1] if item else "empty" for item in items))
                              for claim, items in sorted(claim_ids.items())}
    unknown_prefix_counts_by_claim = {
        claim: dict(Counter(item[:1] if item else "empty" for item in items if item not in visible_ids))
        for claim, items in sorted(claim_ids.items()) if any(item not in visible_ids for item in items)}
    reasons = value.get("abstention_reasons") if isinstance(value, dict) else None
    reason_count = len(reasons) if isinstance(reasons, list) else None
    allowed_reasons = {"messages_not_in_view", "actions_not_in_view", "no_delivered_message",
                       "proposal_ambiguous", "concordance_not_observable",
                       "acceptance_not_observed", "insufficient_provenance"}
    reasons_valid = (isinstance(reasons, list) and all(isinstance(item, str) and item in allowed_reasons
                                                       for item in reasons))
    return {"claim_values": claims, "citation_count": len(ids),
            "citation_prefix_counts": dict(prefix_counts),
            "unknown_citation_prefix_counts": dict(unknown_prefix_counts),
            "citation_counts_by_claim": {claim: len(items) for claim, items in sorted(claim_ids.items())},
            "citation_prefix_counts_by_claim": prefix_counts_by_claim,
            "unknown_citation_prefix_counts_by_claim": unknown_prefix_counts_by_claim,
            "abstention_reason_count": reason_count,
            "abstention_reasons_valid": reasons_valid}


def _all_detected_violations(value: Any, request: dict[str, Any], first_error: str | None) -> list[str]:
    """Collect independent rule violations without changing the frozen validator result."""
    violations = [first_error] if first_error else []
    if not isinstance(value, dict):
        return violations or ["root_not_object"]
    claims = ("message_delivery", "allocation_proposal", "action_concordance",
              "explicit_acceptance", "explicit_commitment")
    refs = value.get("evidence_refs")
    by_claim: dict[str, list[str]] = defaultdict(list)
    if isinstance(refs, dict):
        for claim, ids in refs.items():
            if isinstance(ids, list):
                by_claim[str(claim)].extend(item for item in ids if isinstance(item, str))
    elif isinstance(refs, list):
        for item in refs:
            if isinstance(item, str) and ":" in item:
                claim, _, event_id = item.partition(":")
                by_claim[claim].append(event_id)
    visible = set(request.get("visible_event_ids", []))
    for claim, ids in by_claim.items():
        if any(event_id not in visible for event_id in ids):
            violations.append(f"unknown_evidence_ref:{claim}")
    reasons = value.get("abstention_reasons")
    if not isinstance(reasons, list) or any(not isinstance(item, str) for item in reasons) or \
            len(reasons) != len(set(reasons)):
        violations.append("abstention_reasons_invalid")
        reasons = []
    allowed_reasons = {"messages_not_in_view", "actions_not_in_view", "no_delivered_message",
                       "proposal_ambiguous", "concordance_not_observable", "acceptance_not_observed",
                       "insufficient_provenance"}
    if any(item not in allowed_reasons for item in reasons):
        violations.append("abstention_reasons_invalid")
    actions_visible = request["view_name"] != "text_only"
    message_views = {"text_only", "raw_fusion", "structured_evidence", "structured_without_findings"}
    messages_visible = request["permission_profile"] == "privileged_audit" and \
        request["view_name"] in message_views
    if not messages_visible:
        for field in claims:
            if value.get(field) != "not_visible":
                violations.append(f"private_claim_without_visible_messages:{field}")
        if "messages_not_in_view" not in reasons:
            violations.append("omitted_messages_require_abstention_reason")
    elif "messages_not_in_view" in reasons:
        violations.append("messages_not_in_view_inapplicable")
    if not actions_visible:
        for field in ("public_harm", "ballot_disagreement"):
            if value.get(field) != "not_visible":
                violations.append(f"action_claim_without_visible_actions:{field}")
        if "actions_not_in_view" not in reasons:
            violations.append("omitted_actions_require_abstention_reason")
    elif "actions_not_in_view" in reasons:
        violations.append("actions_not_in_view_inapplicable")
    if not actions_visible and messages_visible and value.get("action_concordance") not in {
            "not_assessable", "uncertain"}:
        violations.append("action_concordance_requires_visible_ballots")
    visible_messages = any(event_id.startswith("M") for event_id in visible)
    if "no_delivered_message" in reasons and not messages_visible:
        violations.append("no_delivered_message_without_visible_stream")
    if "no_delivered_message" in reasons and visible_messages:
        violations.append("no_delivered_message_conflicts_with_visible_message")
    if "acceptance_not_observed" in reasons and not messages_visible:
        violations.append("acceptance_reason_without_visible_messages")
    if "insufficient_provenance" in reasons:
        violations.append("insufficient_provenance_not_supported_by_frozen_projection")
    if messages_visible and not visible_messages:
        if "no_delivered_message" not in reasons:
            violations.append("empty_visible_message_stream_requires_reason")
        if value.get("message_delivery") != "absent":
            violations.append("empty_visible_message_stream_requires_absent_delivery")
    required_prefixes = {
        ("public_harm", "present"): ("P", 1),
        ("ballot_disagreement", "present"): ("P", 2),
        ("message_delivery", "present"): ("M", 1),
        ("allocation_proposal", "full_allocation_mapping"): ("M", 1),
        ("explicit_acceptance", "present"): ("M", 1),
        ("explicit_commitment", "present"): ("M", 1),
    }
    for (claim, positive), (prefix, minimum) in required_prefixes.items():
        if value.get(claim) == positive and sum(item.startswith(prefix) for item in by_claim.get(claim, [])) < minimum:
            violations.append(f"{claim}_lacks_{'multiple_' if minimum > 1 else ''}{'public' if prefix == 'P' else 'message'}_citation")
    if value.get("action_concordance") in {"both_parties_match", "some_or_no_party_matches"}:
        ids = by_claim.get("action_concordance", [])
        if not any(item.startswith("M") for item in ids) or \
                sum(item.startswith("P") for item in ids) < 2:
            violations.append("action_concordance_lacks_message_and_action_citations")
    if value.get("observable_sequence") == "supported_observable_sequence":
        ids = by_claim.get("observable_sequence", [])
        if not actions_visible or not messages_visible or len(ids) < 3 or \
                not any(item.startswith("M") for item in ids) or \
                sum(item.startswith("P") for item in ids) < 2:
            violations.append("supported_sequence_lacks_visible_sources_or_required_citations")
    return list(dict.fromkeys(violations))


def _recompute(request: dict[str, Any], response: dict[str, Any], expected_model: str):
    raw_body = response.get("raw_response_body")
    if not isinstance(raw_body, str):
        raise AuditError("raw_response_body_missing")
    raw_bytes = raw_body.encode("utf-8")
    if hashlib.sha256(raw_bytes).hexdigest() != response.get("raw_response_body_sha256"):
        raise AuditError("raw_response_body_hash_mismatch")
    if request.get("payload_sha256") != response.get("payload_sha256"):
        raise AuditError("request_response_payload_hash_mismatch")
    if hashlib.sha256(request["payload_json"].encode("utf-8")).hexdigest() != request["payload_sha256"]:
        raise AuditError("request_body_hash_mismatch")
    body = json.loads(raw_body)
    if body.get("model") != expected_model or response.get("model") != expected_model:
        raise AuditError("model_identity_mismatch")
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise AuditError("choice_shape_mismatch")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise AuditError("assistant_text_missing")
    assistant_text = message["content"]
    if hashlib.sha256(assistant_text.encode("utf-8")).hexdigest() != response.get("raw_assistant_text_sha256"):
        raise AuditError("assistant_text_hash_mismatch")
    finish = choices[0].get("finish_reason")
    if finish != response.get("finish_reason"):
        raise AuditError("finish_reason_mismatch")
    usage = body.get("usage")
    if usage != response.get("usage"):
        raise AuditError("usage_mismatch")
    try:
        parsed, envelope = parse_raw_output(assistant_text, finish_reason=finish)
    except ContractError as exc:
        parsed = None
        saved_prediction, error, status, envelope = None, str(exc), "invalid_output", None
    else:
        normalized, error = validate_prediction(
            parsed, visible_event_ids=set(request["visible_event_ids"]),
            view_name=request["view_name"], permission_profile=request["permission_profile"],
            compact=bool(request["compact"]))
        status = "invalid_output" if error else "valid"
        saved_prediction = parsed if error else normalized
        if error is None:
            error = validate_usage_limits(usage)
            if error:
                status = "invalid_output"
    stored = (response.get("validation_status"), response.get("validation_error"),
              response.get("parsed"), response.get("reasoning_envelope"))
    recomputed = (status, error, saved_prediction, envelope)
    if stored != recomputed:
        raise AuditError("saved_validation_differs_from_raw_recomputation")
    return {"status": status, "error": error, "usage": usage,
            "assistant_text_sha256": response["raw_assistant_text_sha256"],
            "returned_at_utc": response["returned_at_utc"], "finish_reason": finish,
            "parsed_output": parsed}


def audit(out: Path) -> dict[str, Any]:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    model_hash = file_sha256(Path(config["model_path"]))
    server_hash = file_sha256(Path(config["server_path"]))
    bundle_hash = llama_runtime_bundle_identity(config["server_path"])["sha256"]
    if (model_hash != config["model_sha256"] or server_hash != config["server_sha256"] or
            bundle_hash != config["runtime_bundle_sha256"]):
        raise AuditError("model_or_runtime_hash_mismatch")
    requests = {path.stem: json.loads(path.read_text(encoding="utf-8"))
                for path in (out / "requests/preflight").glob("*.json")}
    responses = {path.stem: json.loads(path.read_text(encoding="utf-8"))
                 for path in (out / "responses/preflight").glob("*.json")}
    errors = list((out / "responses/preflight").glob("*.error.json"))
    if len(requests) != 30 or len(responses) != 30 or errors:
        raise AuditError("preflight_request_response_inventory_mismatch")
    if set(requests) != set(responses):
        raise AuditError("request_response_id_set_mismatch")
    decision = json.loads((out / "preflight-decision.json").read_text(encoding="utf-8"))
    attempts = [json.loads(line) for line in (out / "preflight-attempts.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    started = Counter(row["request_id"] for row in attempts if row.get("event") == "attempt_started")
    returned = Counter(row["request_id"] for row in attempts if row.get("event") == "response_returned")
    failed = [row for row in attempts if row.get("event") == "attempt_failed"]
    if set(started) != set(requests) or any(value != 1 for value in started.values()) or \
            set(returned) != set(requests) or any(value != 1 for value in returned.values()) or failed:
        raise AuditError("preflight_attempt_ledger_inconsistent_or_retried")
    launch_path = out / "launches/preflight-local/launch.json"
    listener_path = out / "launches/preflight-local/listener-owner-attestation.json"
    shutdown_path = out / "launches/preflight-local/shutdown.json"
    launch = json.loads(launch_path.read_text(encoding="utf-8"))
    listener = json.loads(listener_path.read_text(encoding="utf-8"))
    shutdown = json.loads(shutdown_path.read_text(encoding="utf-8"))
    command = launch["command"]
    if (launch.get("endpoint") != config["endpoint"] or launch.get("offline") is not True or
            launch.get("server_sha256") != config["server_sha256"] or
            launch.get("runtime_bundle_sha256") != config["runtime_bundle_sha256"] or
            command[command.index("--host") + 1] != "127.0.0.1" or
            command[command.index("--port") + 1] != "8081" or
            command[command.index("--model") + 1] != config["model_path"] or
            listener.get("status") != "verified_exact_pid_loopback_listener" or
            listener.get("pid") != launch.get("pid") or
            listener.get("rows") != [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                                       "OwningProcess": launch["pid"]}] or
            shutdown.get("shutdown", {}).get("terminated") is not True or
            shutdown.get("api_key_cleanup", {}).get("exists_after_cleanup") is not False):
        raise AuditError("local_runtime_or_cleanup_attestation_mismatch")

    counts = Counter()
    errors_by_candidate = defaultdict(Counter)
    counts_by_view_permission = defaultdict(Counter)
    rows = {}
    failure_cases: list[dict[str, Any]] = []
    error_classes = Counter()
    finish_reasons = Counter()
    json_parse_ok = 0
    root_shape_ok = 0
    enum_values_ok = 0
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    latency: list[float] = []
    text_hashes: dict[tuple[str, str, str], str] = {}
    response_hashes: dict[str, str] = {}
    request_hashes: dict[str, str] = {}
    for request_id, request in requests.items():
        response = responses[request_id]
        if response.get("request_id") != request_id or response.get("candidate_id") != request.get("candidate_id"):
            raise AuditError(f"request_response_metadata_mismatch:{request_id}")
        result = _recompute(request, response, config["model_id"])
        response_hashes[request_id] = response["raw_response_body_sha256"]
        request_hashes[request_id] = request["payload_sha256"]
        text_hashes[(request["candidate_id"], request["view_name"],
                     request["permission_profile"])] = result["assistant_text_sha256"]
        status, error = result["status"], result["error"] or "none"
        error_classes[_error_class(result["error"])] += 1
        finish_reasons[str(result["finish_reason"])] += 1
        if result["parsed_output"] is not None:
            json_parse_ok += 1
            parsed = result["parsed_output"]
            if set(parsed) == ROOT_FIELDS:
                root_shape_ok += 1
            if all(isinstance(parsed.get(field), str) and parsed[field] in allowed
                   for field, allowed in ENUMS.items()):
                enum_values_ok += 1
        candidate = request["candidate_id"]
        counts[(candidate, status)] += 1
        errors_by_candidate[candidate][error] += 1
        counts_by_view_permission[(request["view_name"], request["permission_profile"])][status] += 1
        usage = result["usage"] or {}
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        if isinstance(prompt, int) and not isinstance(prompt, bool):
            prompt_tokens.append(prompt)
        if isinstance(completion, int) and not isinstance(completion, bool):
            completion_tokens.append(completion)
        starts = [row for row in attempts if row.get("request_id") == request_id and
                  row.get("event") == "attempt_started"]
        elapsed = (datetime.fromisoformat(result["returned_at_utc"]) -
                   datetime.fromisoformat(starts[0]["at_utc"])).total_seconds()
        latency.append(elapsed)
        rows[request_id] = {"candidate_id": candidate, "view_name": request["view_name"],
                            "permission_profile": request["permission_profile"],
                            "status": status, "error": error}
        failure_cases.append({
            "candidate_id": candidate, "view_name": request["view_name"],
            "permission_profile": request["permission_profile"], "status": status,
            "error": error, "error_class": _error_class(result["error"]),
            "all_detected_violations": _all_detected_violations(
                result["parsed_output"], request, result["error"]),
            **_model_output_summary(result["parsed_output"], set(request["visible_event_ids"])),
        })
    candidates = sorted({request["candidate_id"] for request in requests.values()})
    c1_c2_identical_outputs = sum(
        text_hashes.get(("M2-V2-C1-full-json-schema", view, permission)) ==
        text_hashes.get(("M2-V2-C2-full-json-object-schema", view, permission))
        for view in {request["view_name"] for request in requests.values()}
        for permission in {request["permission_profile"] for request in requests.values()})
    recomputed_candidates = []
    for candidate in candidates:
        status_counts = {status: counts[(candidate, status)] for status in ("valid", "invalid_output")
                         if counts[(candidate, status)]}
        if sum(status_counts.values()) != 10:
            raise AuditError(f"candidate_case_count_mismatch:{candidate}")
        recomputed_candidates.append({"candidate_id": candidate, "status_counts": status_counts,
                                      "all_ten_valid": status_counts.get("valid", 0) == 10})
    if decision.get("status") != "NO_GO_INTERFACE" or decision.get("selected_candidate") is not None or \
            decision.get("http_attempts") != 30 or decision.get("generation_endpoint_attempts") != 30 or \
            decision.get("model_response_count") != 30 or decision.get("all_ten_valid") is not False:
        raise AuditError("saved_preflight_decision_does_not_match_bounded_no_go")
    for summary in decision["candidate_results"]:
        recomputed = next(row for row in recomputed_candidates if row["candidate_id"] == summary["candidate_id"])
        if (summary.get("status_counts") != recomputed["status_counts"] or
                summary.get("all_ten_valid") != recomputed["all_ten_valid"] or
                summary.get("case_count") != 10 or summary.get("http_attempts") != 10):
            raise AuditError("saved_candidate_summary_differs_from_raw_recomputation")
    gpu_path = out / "launches/preflight-local/gpu-samples.jsonl"
    gpu_rows = [json.loads(line) for line in gpu_path.read_text(encoding="utf-8").splitlines() if line]
    samples = [gpu for row in gpu_rows for gpu in row.get("gpus", [])]
    free_memory = [int(gpu["memory_free_mib"]) for gpu in samples if str(gpu.get("memory_free_mib", "")).isdigit()]
    utilization = [int(gpu["utilization_percent"]) for gpu in samples
                   if str(gpu.get("utilization_percent", "")).isdigit()]
    start_times = [datetime.fromisoformat(row["at_utc"]) for row in attempts
                   if row.get("event") == "attempt_started"]
    end_times = [datetime.fromisoformat(row["at_utc"]) for row in attempts
                 if row.get("event") == "response_returned"]
    inventories = {
        "requests": dict(sorted(request_hashes.items())),
        "responses": dict(sorted(response_hashes.items())),
    }
    inventory_sha = hashlib.sha256(json.dumps(
        inventories, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "status": "PASS_INDEPENDENT_PREFLIGHT_RESPONSE_RECOMPUTATION_NO_GO_INTERFACE",
        "decision": "NO_GO_INTERFACE", "request_count": len(requests),
        "response_count": len(responses), "logical_generation_requests": 30,
        "json_parse_ok_count": json_parse_ok,
        "root_shape_valid_count": root_shape_ok,
        "core_enum_values_valid_count": enum_values_ok,
        "finish_reason_counts": dict(finish_reasons),
        "failure_class_counts": dict(error_classes),
        "physical_http_attempts": len([row for row in attempts if row.get("event") == "attempt_started"]),
        "retries": 0, "external_model_calls": 0, "candidate_results": recomputed_candidates,
        "c1_c2_identical_assistant_text_pairs": c1_c2_identical_outputs,
        "errors_by_candidate": {candidate: dict(errors_by_candidate[candidate])
                                for candidate in candidates},
        "bad_cases": sorted(failure_cases, key=lambda row: (
            row["candidate_id"], row["view_name"], row["permission_profile"])),
        "status_counts_by_view_permission": {
            f"{view}|{permission}": dict(value)
            for (view, permission), value in sorted(counts_by_view_permission.items())},
        "server_prompt_tokens_total": sum(prompt_tokens),
        "server_completion_tokens_total": sum(completion_tokens),
        "server_prompt_tokens_max": max(prompt_tokens),
        "server_completion_tokens_max": max(completion_tokens),
        "latency_seconds_median": round(statistics.median(latency), 6),
        "latency_seconds_max": round(max(latency), 6),
        "preflight_elapsed_seconds": round((max(end_times) - min(start_times)).total_seconds(), 6),
        "gpu_sample_count": len(samples),
        "gpu_memory_free_min_mib": min(free_memory) if free_memory else None,
        "gpu_utilization_max_percent": max(utilization) if utilization else None,
        "model_sha256": model_hash, "server_sha256": server_hash,
        "runtime_bundle_sha256": bundle_hash,
        "tokenizer_sha256": config["tokenizer_sha256"],
        "chat_template_sha256": config["chat_template_sha256"],
        "request_response_inventory_sha256": inventory_sha,
        "preflight_decision_sha256": file_sha256(out / "preflight-decision.json"),
        "server_log_sha256": file_sha256(out / "launches/preflight-local/llama-server.stderr.log"),
        "gpu_samples_sha256": file_sha256(gpu_path),
        "api_key_removed": shutdown["api_key_cleanup"]["exists_after_cleanup"] is False,
        "launcher_terminated": shutdown["shutdown"]["terminated"] is True,
        "attempt_ledger_sha256": file_sha256(out / "preflight-attempts.jsonl"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--write", action="store_true", help="save a sanitized summary in the run analysis directory")
    parser.add_argument("--summary-only", action="store_true",
                        help="print compact counts while preserving the complete sanitized audit when --write is set")
    args = parser.parse_args()
    result = audit(args.out.resolve())
    rendered = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.write:
        target = args.out.resolve() / "analysis/preflight-independent-response-audit.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    if args.summary_only:
        compact = {key: result.get(key) for key in (
            "status", "decision", "candidate_results", "failure_class_counts",
            "errors_by_candidate", "json_parse_ok_count", "root_shape_valid_count",
            "core_enum_values_valid_count", "physical_http_attempts", "retries",
            "external_model_calls", "server_prompt_tokens_total", "server_completion_tokens_total",
            "latency_seconds_median", "latency_seconds_max", "gpu_sample_count",
            "gpu_utilization_max_percent", "gpu_memory_free_min_mib",
            "request_response_inventory_sha256", "preflight_decision_sha256",
            "attempt_ledger_sha256", "bad_cases",
        ) if key != "bad_cases"}
        compact["bad_case_count"] = len(result.get("bad_cases", []))
        print(json.dumps(compact, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
