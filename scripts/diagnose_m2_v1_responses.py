#!/usr/bin/env python3
"""Read-only, per-response diagnosis of the frozen M2-V1 run.

This script never changes the M2-V1 run, its validation states, or its scores.
The only prefix inspection is an anchored, literal <think>...</think> check;
any post-envelope JSON parse is explicitly diagnostic and never upgrades the
stored response status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.m2_monitor import validate_prediction  # noqa: E402
from scripts.run_m2_monitor import _secure_dir  # noqa: E402

DEFAULT_SOURCE = ROOT / "runs/m2/one-shot-20261019"
DEFAULT_OUT = ROOT / "runs/m2-v2/recovery-20261019/diagnosis"
EMPTY_THINK_PREFIX = "<think>\n\n</think>\n\n"
EXPECTED_MODEL_SHA256 = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
EXPECTED_SERVER_BUILD = "b10068-571d0d540"
EXPECTED_TOKENIZER_SHA256 = "06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f"
EXPECTED_TEMPLATE_SHA256 = "57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def inspect_reasoning_envelope(raw: str) -> dict[str, Any]:
    """Inspect a leading reasoning envelope without accepting or rewriting it."""
    if not raw.startswith("<think>"):
        return {
            "kind": "absent",
            "closed": True,
            "inner_trimmed_empty": None,
            "inner_chars": 0,
            "inner_sha256": None,
            "exact_observed_empty_prefix": False,
            "diagnostic_remainder": raw,
        }
    close_at = raw.find("</think>", len("<think>"))
    if close_at < 0:
        inner = raw[len("<think>"):]
        return {
            "kind": "unclosed_leading_think",
            "closed": False,
            "inner_trimmed_empty": not inner.strip(),
            "inner_chars": len(inner),
            "inner_sha256": sha256_bytes(inner.encode("utf-8")),
            "exact_observed_empty_prefix": False,
            "diagnostic_remainder": None,
        }
    inner = raw[len("<think>"):close_at]
    remainder = raw[close_at + len("</think>"):]
    return {
        "kind": "leading_think_envelope",
        "closed": True,
        "inner_trimmed_empty": not inner.strip(),
        "inner_chars": len(inner),
        "inner_sha256": sha256_bytes(inner.encode("utf-8")),
        "exact_observed_empty_prefix": raw.startswith(EMPTY_THINK_PREFIX),
        "diagnostic_remainder": remainder.lstrip(" \t\r\n"),
    }


def _schema_root_fields(schema: dict[str, Any]) -> set[str]:
    required = schema.get("required")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ValueError("frozen output schema has no valid required root-field list")
    return set(required)


def _log_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "lines": 0, "markers": {}}
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "schema_conversion": r"json schema|json_schema|schema converter|converted grammar",
        "grammar_compilation": r"grammar.*(compile|parse|init)|(?:compile|parse|init).*grammar",
        "grammar_rejection": r"failed to parse grammar|invalid grammar|schema.*(?:reject|error)",
        "fallback_or_unconstrained": r"fallback|unconstrained|constraint.*disabled|grammar.*ignored",
        "error_or_warning": r"\b(?:error|warning|failed)\b",
    }
    return {
        "exists": True,
        "sha256": sha256_bytes(text.encode("utf-8")),
        "lines": len(text.splitlines()),
        "markers": {name: len(re.findall(pattern, text, flags=re.IGNORECASE))
                    for name, pattern in patterns.items()},
        "interpretation": "no matching diagnostic marker is not proof that grammar was applied; logger may suppress debug-level schema messages",
    }


def _verify_artifact_inventory(source: Path) -> dict[str, Any]:
    """Re-hash the original inventory without writing into the frozen run."""
    manifest_path = source / "artifact-hashes.json"
    manifest = read_json(manifest_path)
    entries = manifest.get("files")
    if not isinstance(entries, list):
        raise ValueError("frozen artifact manifest has no files array")
    mismatches = []
    expected_paths = set()
    for entry in entries:
        rel = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(rel, str):
            mismatches.append("manifest_entry_without_path")
            continue
        expected_paths.add(rel.replace("\\", "/"))
        path = source / Path(rel)
        if not path.is_file():
            mismatches.append(f"missing:{rel}")
            continue
        data = path.read_bytes()
        if len(data) != entry.get("size_bytes") or sha256_bytes(data) != entry.get("sha256"):
            mismatches.append(f"changed:{rel}")
    actual_paths = {
        path.relative_to(source).as_posix()
        for path in source.rglob("*")
        if path.is_file() and path.name != "artifact-hashes.json"
    }
    extras = sorted(actual_paths - expected_paths)
    missing_entries = sorted(expected_paths - actual_paths)
    return {
        "inventory_manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "expected_manifest_sha256": "6d3f0d552aea565d80416a774d80e64710488318da274ef2053841f140d984b9",
        "manifest_entry_count": len(entries),
        "manifest_entry_count_matches_header": len(entries) == manifest.get("file_count_excluding_this_manifest"),
        "all_entries_match_size_and_sha256": not mismatches,
        "unexpected_files_outside_manifest": extras,
        "manifest_paths_missing_from_run": missing_entries,
        "mismatches": mismatches,
    }
def diagnose(source: Path, out: Path) -> dict[str, Any]:
    if not source.is_dir():
        raise FileNotFoundError(f"frozen M2-V1 run is missing: {source}")
    _secure_dir(out)
    request_dir = source / "requests"
    response_dir = source / "responses"
    schema = read_json(ROOT / "prompts/m2-v1/output.schema.json")
    required_root = _schema_root_fields(schema)
    requests = {path.stem: read_json(path) for path in sorted(request_dir.glob("m2-*.json"))}
    responses = {path.stem: read_json(path) for path in sorted(response_dir.glob("m2-*.json"))}
    if len(requests) != 523 or len(responses) != 517:
        raise ValueError(f"unexpected frozen source inventory: {len(requests)} requests / {len(responses)} responses")

    rows: list[dict[str, Any]] = []
    integrity_errors: list[str] = []
    for request_id, response in responses.items():
        request = requests.get(request_id)
        if request is None:
            integrity_errors.append(f"response_without_request:{request_id}")
            continue
        payload = request.get("payload")
        payload_json = request.get("payload_json")
        if not isinstance(payload, dict) or not isinstance(payload_json, str):
            integrity_errors.append(f"request_payload_missing:{request_id}")
            continue
        payload_bytes = payload_json.encode("utf-8")
        if sha256_bytes(payload_bytes) != request.get("payload_sha256"):
            integrity_errors.append(f"request_payload_hash_mismatch:{request_id}")
        try:
            if json.loads(payload_json) != payload:
                integrity_errors.append(f"request_payload_json_object_mismatch:{request_id}")
        except json.JSONDecodeError:
            integrity_errors.append(f"request_payload_json_invalid:{request_id}")

        raw = response.get("raw_assistant_text")
        body = response.get("raw_response_body")
        if not isinstance(raw, str) or not isinstance(body, str):
            integrity_errors.append(f"response_raw_body_missing:{request_id}")
            continue
        if sha256_bytes(raw.encode("utf-8")) != response.get("raw_assistant_text_sha256"):
            integrity_errors.append(f"assistant_text_hash_mismatch:{request_id}")
        if sha256_bytes(body.encode("utf-8")) != response.get("raw_response_body_sha256"):
            integrity_errors.append(f"response_body_hash_mismatch:{request_id}")

        envelope = inspect_reasoning_envelope(raw)
        remainder = envelope["diagnostic_remainder"]
        parsed: Any = None
        parse_error: str | None = None
        if remainder is not None:
            try:
                parsed = json.loads(remainder)
            except json.JSONDecodeError as exc:
                parse_error = type(exc).__name__
        root_keys = list(parsed.keys()) if isinstance(parsed, dict) else []
        parsed_fields = set(root_keys)
        missing = sorted(required_root - parsed_fields) if isinstance(parsed, dict) else sorted(required_root)
        extra = sorted(parsed_fields - required_root) if isinstance(parsed, dict) else []
        valid_after_diagnostic = False
        validation_after_diagnostic = "not_a_json_object"
        if isinstance(parsed, dict):
            valid_after_diagnostic, validation_after_diagnostic = validate_prediction(
                parsed, set(request.get("visible_event_ids", [])))

        response_format = payload.get("response_format", {})
        transmitted_schema = response_format.get("schema") if isinstance(response_format, dict) else None
        messages = payload.get("messages", [])
        prompt_text = "\n".join(message.get("content", "") for message in messages
                                if isinstance(message, dict) and isinstance(message.get("content"), str))
        visible_names = sorted(name for name in required_root if f'"{name}"' in prompt_text or name in prompt_text)
        usage = response.get("usage", {}) if isinstance(response.get("usage"), dict) else {}
        finish = response.get("finish_reason")
        max_tokens = payload.get("max_tokens")
        completion_tokens = usage.get("completion_tokens")
        prompt_tokens_server = usage.get("prompt_tokens")
        prompt_tokens_local = request.get("input_tokens_local")
        context_limit = 4096
        rows.append({
            "request_id": request_id,
            "phase": response.get("phase"),
            "partition": request.get("partition"),
            "view": request.get("view_name"),
            "permission_profile": request.get("permission_profile"),
            "evaluation_ids_count": len(request.get("evaluation_ids", [])),
            "payload_sha256": request.get("payload_sha256"),
            "assistant_text_sha256": response.get("raw_assistant_text_sha256"),
            "response_body_sha256": response.get("raw_response_body_sha256"),
            "stored_validation_status": response.get("validation_status"),
            "stored_validation_error": response.get("validation_error"),
            "leading_reasoning_envelope": {key: value for key, value in envelope.items()
                                           if key != "diagnostic_remainder"},
            "diagnostic_json_parse_error": parse_error,
            "post_envelope_root_keys_exact_order": root_keys,
            "post_envelope_missing_required_root_fields": missing,
            "post_envelope_extra_root_fields": extra,
            "post_envelope_frozen_semantic_validator_valid": valid_after_diagnostic,
            "post_envelope_frozen_semantic_validator_result": validation_after_diagnostic,
            "diagnostic_only_never_upgrades_stored_status": True,
            "finish_reason": finish,
            "prompt_tokens_server": prompt_tokens_server,
            "prompt_tokens_local": prompt_tokens_local,
            "completion_tokens_server": completion_tokens,
            "max_tokens_request": max_tokens,
            "context_limit_configured": context_limit,
            "truncation_signal": finish == "length" or (
                isinstance(completion_tokens, int) and isinstance(max_tokens, int)
                and completion_tokens >= max_tokens),
            "local_prompt_plus_output_cap_within_context": isinstance(prompt_tokens_local, int)
                and isinstance(max_tokens, int) and prompt_tokens_local + max_tokens <= context_limit,
            "server_prompt_plus_completion_within_context": isinstance(prompt_tokens_server, int)
                and isinstance(completion_tokens, int)
                and prompt_tokens_server + completion_tokens <= context_limit,
            "reasoning_content_metadata_present": response.get("response_metadata", {}).get("reasoning_content_present"),
            "api_response_format_type": response_format.get("type") if isinstance(response_format, dict) else None,
            "api_schema_sha256": sha256_bytes(json.dumps(transmitted_schema, ensure_ascii=False,
                                                         sort_keys=True, separators=(",", ":")).encode("utf-8"))
                if isinstance(transmitted_schema, dict) else None,
            "api_schema_root_fields": sorted(transmitted_schema.get("required", []))
                if isinstance(transmitted_schema, dict) else [],
            "api_schema_matches_frozen_schema": transmitted_schema == schema,
            "model_visible_required_root_field_names": visible_names,
            "model_visible_exact_required_json_shape": all(f'"{name}"' in prompt_text for name in required_root)
                and "evidence_refs" in prompt_text and "abstention_reasons" in prompt_text,
            "server_build": response.get("response_metadata", {}).get("server_build_info_expected"),
            "model_sha256": response.get("response_metadata", {}).get("model_artifact_sha256"),
            "tokenizer_sha256": response.get("response_metadata", {}).get("tokenizer_sha256"),
            "template_sha256": response.get("response_metadata", {}).get("chat_template_sha256"),
        "latency_seconds": response.get("response_metadata", {}).get("latency_seconds"),
        })

    missing_response_ids = sorted(set(requests) - set(responses))
    for request_id, request in requests.items():
        payload_json = request.get("payload_json")
        if not isinstance(payload_json, str) or sha256_bytes(payload_json.encode("utf-8")) != request.get("payload_sha256"):
            integrity_errors.append(f"request_inventory_payload_hash_mismatch:{request_id}")
        payload = request.get("payload", {})
        fmt = payload.get("response_format", {}) if isinstance(payload, dict) else {}
        if not isinstance(fmt, dict) or fmt.get("type") != "json_schema" or fmt.get("schema") != schema:
            integrity_errors.append(f"request_schema_shape_or_hash_mismatch:{request_id}")

    launch_summaries = {}
    for phase, launch_name in (("calibration", "launch-001"), ("held_out", "launch-002")):
        launch_dir = source / "launches" / launch_name
        launch_json = launch_dir / "launch.json"
        launch_info = read_json(launch_json) if launch_json.exists() else {}
        command = launch_info.get("command", [])
        explicit_log_verbosity = None
        if isinstance(command, list):
            for index, token in enumerate(command[:-1]):
                if token in {"--verbosity", "-lv"}:
                    explicit_log_verbosity = command[index + 1]
                    break
        launch_summaries[phase] = {
            "launch_id": launch_name,
            "explicit_log_verbosity_argument": explicit_log_verbosity,
            "pinned_default_log_verbosity_if_unset": 3,
            "stderr": _log_summary(launch_dir / "llama-server.stderr.log"),
            "stdout": _log_summary(launch_dir / "llama-server.stdout.log"),
        }

    def frequency(key: str) -> dict[str, int]:
        return dict(sorted(Counter(str(row.get(key)) for row in rows).items()))

    missing_frequency = Counter(field for row in rows for field in row["post_envelope_missing_required_root_fields"])
    extra_frequency = Counter(field for row in rows for field in row["post_envelope_extra_root_fields"])
    root_shapes = Counter(tuple(row["post_envelope_root_keys_exact_order"]) for row in rows)
    summary = {
        "protocol": "m2-v1-read-only-root-cause-diagnostic",
        "source_run": str(source.resolve()),
        "source_request_count": len(requests),
        "source_response_count": len(responses),
        "requests_without_response_count": len(missing_response_ids),
        "requests_without_response_ids": missing_response_ids,
        "diagnostic_response_rows": len(rows),
        "stored_validation_status_counts": frequency("stored_validation_status"),
        "finish_reason_counts": frequency("finish_reason"),
        "envelope_kind_counts": dict(Counter(row["leading_reasoning_envelope"]["kind"] for row in rows)),
        "envelope_empty_vs_nonempty_counts": dict(Counter(
            str(row["leading_reasoning_envelope"]["inner_trimmed_empty"])
            for row in rows if row["leading_reasoning_envelope"]["kind"] == "leading_think_envelope")),
        "exact_historical_empty_envelope_count": sum(
            row["leading_reasoning_envelope"]["exact_observed_empty_prefix"] for row in rows),
        "post_envelope_json_parse_ok_count": sum(row["diagnostic_json_parse_error"] is None for row in rows),
        "post_envelope_frozen_semantic_valid_count_diagnostic_only": sum(
            row["post_envelope_frozen_semantic_validator_valid"] for row in rows),
        "root_key_shapes": [{"keys_in_order": list(shape), "count": count}
                             for shape, count in sorted(root_shapes.items(), key=lambda item: (-item[1], item[0]))],
        "missing_required_root_field_counts": dict(sorted(missing_frequency.items())),
        "extra_root_field_counts": dict(sorted(extra_frequency.items())),
        "prompt_shape_visibility": {
            "responses_with_exact_required_json_shape_in_model_prompt": sum(
                row["model_visible_exact_required_json_shape"] for row in rows),
            "mean_required_field_names_visible": round(
                sum(len(row["model_visible_required_root_field_names"]) for row in rows) / max(1, len(rows)), 3),
            "field_name_presence_counts": dict(sorted(Counter(
                name for row in rows for name in row["model_visible_required_root_field_names"]).items())),
        },
        "schema_transport": {
            "requests_with_documented_direct_schema_envelope": sum(
                row["api_response_format_type"] == "json_schema" and row["api_schema_matches_frozen_schema"]
                for row in rows),
            "schema_enforced_by_runtime": "NOT ESTABLISHED BY REQUEST BYTES OR HTTP 200 ALONE",
        },
        "token_context": {
            "sum_prompt_tokens_server": sum((row["prompt_tokens_server"] or 0 for row in rows), 0),
            "sum_completion_tokens_server": sum((row["completion_tokens_server"] or 0 for row in rows), 0),
            "max_prompt_tokens_server": max((row["prompt_tokens_server"] or 0 for row in rows), default=0),
            "max_completion_tokens_server": max((row["completion_tokens_server"] or 0 for row in rows), default=0),
            "median_prompt_tokens_server": median([row["prompt_tokens_server"] for row in rows
                                                    if isinstance(row["prompt_tokens_server"], int)]),
            "median_completion_tokens_server": median([row["completion_tokens_server"] for row in rows
                                                        if isinstance(row["completion_tokens_server"], int)]),
            "completion_at_or_over_cap_count": sum(row["truncation_signal"] for row in rows),
            "local_prompt_plus_output_cap_within_context_count": sum(
                row["local_prompt_plus_output_cap_within_context"] for row in rows),
            "server_prompt_plus_completion_within_context_count": sum(
                row["server_prompt_plus_completion_within_context"] for row in rows),
        },
        "runtime_duration": {
            "median_response_latency_seconds": median([row["latency_seconds"] for row in rows
                                                        if isinstance(row["latency_seconds"], (int, float))]),
            "mean_response_latency_seconds": round(mean([row["latency_seconds"] for row in rows
                                                         if isinstance(row["latency_seconds"], (int, float))]), 6),
        },
        "identity_consistency": {
            "all_model_hashes_match_expected": all(row["model_sha256"] == EXPECTED_MODEL_SHA256 for row in rows),
            "all_server_builds_match_expected": all(row["server_build"] == EXPECTED_SERVER_BUILD for row in rows),
            "all_tokenizer_hashes_match_expected": all(row["tokenizer_sha256"] == EXPECTED_TOKENIZER_SHA256 for row in rows),
            "all_template_hashes_match_expected": all(row["template_sha256"] == EXPECTED_TEMPLATE_SHA256 for row in rows),
        },
        "server_logs_by_phase": launch_summaries,
        "original_run_inventory_verification": _verify_artifact_inventory(source),
        "raw_statuses_and_artifacts_modified": False,
        "integrity_errors": integrity_errors,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "m2-v1-response-diagnosis.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
                for row in rows), encoding="utf-8", newline="\n")
    (out / "m2-v1-response-diagnosis-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    if not source.is_relative_to(ROOT / "runs/m2"):
        raise ValueError("diagnostic source must stay inside the local ignored M2 run root")
    if not out.is_relative_to(ROOT / "runs/m2-v2"):
        raise ValueError("diagnostic outputs must stay inside the local ignored M2-V2 run root")
    print(json.dumps(diagnose(source, out), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
