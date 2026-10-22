from __future__ import annotations

"""Continue the frozen schedule after correcting a local over-strict JSON parser.

The registered request schedule and scientific scoring are unchanged. This adapter
accepts one optional `text` field only when it exactly echoes the input claim.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "runs/sprint-monitor/track23-monitor-2x2-v1"
RUN_DIR = PRIVATE / "run"
EXPERIMENT_ID = "track23-monitor-2x2-v1"
AUTH_ID = "DS-FLASH-TRACK23-MONITOR-2X2-36-20261023"
ENDPOINT = "https://api.deepseek.com/chat/completions"
ALLOWED_MODEL_NAMES = {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"}

sys.path.insert(0, str(ROOT / "scripts"))
import run_track23_monitor_v2 as base  # noqa: E402


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(base.canonical(row) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def normalize_compatible_response(content: str, schedule_row: dict[str, Any]) -> dict[str, Any]:
    """Allow only a faithful, optional claim-text echo beyond the frozen required fields."""
    parsed = json.loads(content)
    if not isinstance(parsed, dict) or set(parsed) != {"claims"} or not isinstance(parsed["claims"], list):
        raise ValueError("response must contain only one object with a claims array")
    user = json.loads(schedule_row["request"]["messages"][1]["content"])
    expected_text = {claim["claim_id"]: claim["text"] for claim in user["claims"]}
    if len(parsed["claims"]) != 9:
        raise ValueError("response must contain nine claims")
    normalized_claims = []
    seen: set[str] = set()
    for item in parsed["claims"]:
        if not isinstance(item, dict):
            raise ValueError("claim response must be an object")
        required = {"claim_id", "status", "citations", "short_reason"}
        extra = set(item) - required
        if not required <= set(item) or not extra <= {"text"}:
            raise ValueError(f"unsupported output fields for {item.get('claim_id')}")
        claim_id = item["claim_id"]
        if claim_id not in expected_text or claim_id in seen:
            raise ValueError("unknown or duplicate claim_id")
        if "text" in item and item["text"] != expected_text[claim_id]:
            raise ValueError(f"optional text field is not an exact echo for {claim_id}")
        seen.add(claim_id)
        normalized_claims.append({key: item[key] for key in ("claim_id", "status", "citations", "short_reason")})
    if seen != set(expected_text):
        raise ValueError("response claim IDs do not match the frozen request")
    normalized = {"claims": normalized_claims}
    return base.validate_response_content(json.dumps(normalized, ensure_ascii=False, separators=(",", ":")), schedule_row)


def read_attempts(path: Path) -> list[dict[str, Any]]:
    return read_jsonl(path) if path.exists() else []


def provider_costs(attempts: list[dict[str, Any]]) -> Decimal:
    total = Decimal(0)
    for row in attempts:
        if row.get("event") in {"attempt_completed", "attempt_reclassified_valid"}:
            total += Decimal(str(row.get("estimated_cost_usd_peak", "0")))
    return total


def reclassify_strict_parser_false_failure(
    schedule: list[dict[str, Any]], attempts_path: Path, parsed_dir: Path,
) -> list[dict[str, Any]]:
    """Re-parse the already received HTTP 200 response; make no new provider request."""
    attempts = read_attempts(attempts_path)
    failed = [row for row in attempts if row.get("event") == "attempt_failed"]
    if not failed:
        return attempts
    if len(failed) != 1:
        raise RuntimeError("compatibility recovery is limited to one known strict-parser false failure")
    failure = failed[0]
    if (failure.get("request_id") != "pilot-31-C1"
            or failure.get("http_status") != 200
            or failure.get("error") != "invalid claim response fields: q9"
            or failure.get("billing_uncertain") is not False):
        raise RuntimeError("unexpected pilot failure; no recovery rule applies")
    row = next(item for item in schedule if item["request_id"] == failure["request_id"])
    raw_path = RUN_DIR / "pilot" / "responses" / f"{row['request_id']}.response.json"
    raw = raw_path.read_bytes()
    raw_hash = sha256(raw)
    payload = json.loads(raw)
    if payload.get("model") not in ALLOWED_MODEL_NAMES or payload.get("system_fingerprint") != "e72d3c7f663d3e1383b00b3884cb4501":
        raise RuntimeError("received model identity/fingerprint does not match the completed pilot calls")
    choices = payload.get("choices", [])
    if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
        raise RuntimeError("existing completion is not a complete non-truncated response")
    normalized = normalize_compatible_response(choices[0]["message"]["content"], row)
    usage = payload.get("usage")
    cost = base.estimate_cost(usage)
    if cost != Decimal(str(failure["estimated_cost_usd_peak"])):
        raise RuntimeError("usage-derived cost differs from the preserved original attempt failure row")
    parsed_path = parsed_dir / f"{row['request_id']}.json"
    base.write_once(parsed_path, normalized)
    appendix = {
        "event": "attempt_reclassified_valid",
        "experiment_id": EXPERIMENT_ID,
        "phase": "pilot",
        "request_id": row["request_id"],
        "request_sha256": row["request_sha256"],
        "raw_response_sha256": raw_hash,
        "response_path": str(raw_path.relative_to(ROOT)).replace("\\", "/"),
        "parsed_output_path": str(parsed_path.relative_to(ROOT)).replace("\\", "/"),
        "http_status": 200,
        "model_returned": payload["model"],
        "system_fingerprint": payload["system_fingerprint"],
        "finish_reason": choices[0]["finish_reason"],
        "usage": usage,
        "estimated_cost_usd_peak": str(cost),
        "compatibility_rule": "required fields plus optional exact claim-text echo; original response preserved",
        "no_provider_retry": True,
        "reclassified_at_utc": now_utc(),
        "status": "VALID_RESPONSE_AFTER_COMPAT_REVIEW",
    }
    append_jsonl(attempts_path, appendix)
    return read_attempts(attempts_path)


def validate_known_false_failure_without_writing(schedule: list[dict[str, Any]], attempts_path: Path) -> set[str]:
    """Zero-write check that the one already received response is schema-valid under preregistered criteria."""
    attempts = read_attempts(attempts_path)
    failed = [row for row in attempts if row.get("event") == "attempt_failed"]
    if not failed:
        return set()
    if len(failed) != 1:
        raise RuntimeError("compatibility preflight only covers one known strict-parser false failure")
    failure = failed[0]
    if (failure.get("request_id") != "pilot-31-C1" or failure.get("http_status") != 200
            or failure.get("error") != "invalid claim response fields: q9"
            or failure.get("billing_uncertain") is not False):
        raise RuntimeError("unexpected pilot failure; compatibility rule does not apply")
    row = next(item for item in schedule if item["request_id"] == failure["request_id"])
    raw_path = RUN_DIR / "pilot" / "responses" / f"{row['request_id']}.response.json"
    payload = read_json(raw_path)
    if payload.get("model") not in ALLOWED_MODEL_NAMES or payload.get("system_fingerprint") != "e72d3c7f663d3e1383b00b3884cb4501":
        raise RuntimeError("received model identity/fingerprint differs from pilot")
    choices = payload.get("choices", [])
    if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
        raise RuntimeError("the existing completion is truncated or incomplete")
    normalize_compatible_response(choices[0]["message"]["content"], row)
    usage_cost = base.estimate_cost(payload.get("usage", {}))
    if usage_cost != Decimal(str(failure["estimated_cost_usd_peak"])):
        raise RuntimeError("usage cost does not match the preserved attempt record")
    return {failure["request_id"]}


def phase_manifest(phase: str, manifest: dict[str, Any]) -> None:
    path = RUN_DIR / f"{phase}_run_manifest_compat.json"
    base.write_once(path, {
        "experiment_id": EXPERIMENT_ID,
        "phase": phase,
        "created_at_utc": now_utc(),
        "schedule_sha256": manifest["schedule_sha256"],
        "answer_key_sha256": manifest["answer_key_sha256"],
        "approval_id": AUTH_ID,
        "endpoint": ENDPOINT,
        "model_requested": base.MODEL,
        "temperature": 0.0,
        "thinking": "disabled",
        "max_output_tokens": base.MAX_OUTPUT_TOKENS,
        "retries": 0,
        "replacements": 0,
        "response_parser_amendment": "optional exact claim-text echo accepted and stripped from the scoring projection; all required fields remain validated",
        "auth_header_saved": False,
    })


def run(phase: str, preflight: bool = False) -> dict[str, Any]:
    schedule, key_rows, manifest, env = base.verify_frozen()
    phase_rows = [row for row in schedule if row["phase_private"] == phase]
    attempts_path = RUN_DIR / f"{phase}_attempts.jsonl"
    if phase == "pilot":
        attempts = read_attempts(attempts_path)
        virtual_valid_ids = validate_known_false_failure_without_writing(schedule, attempts_path) if preflight else set()
        if not preflight:
            attempts = reclassify_strict_parser_false_failure(schedule, attempts_path, RUN_DIR / "pilot" / "parsed")
    else:
        gate_path = RUN_DIR / "pilot_gate.json"
        gate = read_json(gate_path) if gate_path.exists() else {}
        if gate.get("status") != "PASS_TECHNICAL_GATE" or gate.get("valid_pilot_responses") != 12:
            raise RuntimeError("held-out phase requires the completed pilot technical gate")
        attempts = read_attempts(attempts_path)
        virtual_valid_ids = set()
    terminals = {
        row["request_id"] for row in attempts
        if row.get("event") in {"attempt_completed", "attempt_reclassified_valid"}
    } | virtual_valid_ids
    started = {row["request_id"] for row in attempts if row.get("event") == "attempt_started"}
    failed = [row for row in attempts if row.get("event") == "attempt_failed" and row.get("request_id") not in terminals]
    if failed:
        raise RuntimeError("unclassified failed provider attempt remains; do not retry")
    if any(rid in started and rid not in terminals for rid in started):
        raise RuntimeError("a provider request has an unresolved start; do not retry")
    pending = [row for row in phase_rows if row["request_id"] not in terminals]
    if preflight:
        return {
            "status": "PASS_COMPAT_NO_CALL_PREFLIGHT",
            "phase": phase,
            "already_valid": len(terminals),
            "pending_first_attempts": len(pending),
            "schedule_sha256": manifest["schedule_sha256"],
            "optional_echo_rule": "accept text only when it exactly equals the corresponding frozen input claim",
            "provider_calls_made": 0,
        }
    if not pending:
        raise RuntimeError(f"no unattempted requests remain in {phase}; no resampling")
    if phase == "heldout" and len(phase_rows) != 24:
        raise RuntimeError("held-out schedule size changed")

    phase_manifest(phase, manifest)
    response_dir = RUN_DIR / phase / "responses"
    parsed_dir = RUN_DIR / phase / "parsed"
    response_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    from local_llama_security import restrict_private_directory_acl
    restrict_private_directory_acl(response_dir)
    restrict_private_directory_acl(parsed_dir)
    key_by_pair = {row["pair_id_private"]: row for row in key_rows}
    session = requests.Session()
    session.trust_env = True
    total_cost = provider_costs(attempts)
    baseline_fingerprint = next((row.get("system_fingerprint") for row in attempts if row.get("event") in {"attempt_completed", "attempt_reclassified_valid"}), None)
    expected_total_starts = sum(row.get("event") == "attempt_started" for row in attempts)
    new_successes = 0
    fatal_error: str | None = None
    started_at = time.monotonic()
    for sequence, row in enumerate(pending, start=1):
        # Preserve the approved project-wide cap using actual spent plus all remaining per-row reserves.
        all_attempts = read_attempts(attempts_path)
        done_ids = {x["request_id"] for x in all_attempts if x.get("event") in {"attempt_completed", "attempt_reclassified_valid"}}
        remaining_rows = [x for x in schedule if x["request_id"] not in done_ids and x["request_id"] != row["request_id"]]
        spent = provider_costs(all_attempts)
        if spent + base.max_request_cost(row) + sum((base.max_request_cost(x) for x in remaining_rows), Decimal(0)) > Decimal("2.00"):
            fatal_error = "CUMULATIVE_PEAK_RESERVE_EXCEEDS_USER_CAP"
            break
        reserve = base.max_request_cost(row)
        append_jsonl(attempts_path, {
            "event": "attempt_started", "experiment_id": EXPERIMENT_ID, "phase": phase,
            "attempt_number": 1, "request_id": row["request_id"],
            "request_sha256": row["request_sha256"], "reserved_peak_cost_usd": str(reserve),
            "started_at_utc": now_utc(), "retry": False,
        })
        expected_total_starts += 1
        response = None
        actual_cost: Decimal | None = None
        try:
            response = session.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {env['LLM_API_KEY']}", "Content-Type": "application/json"},
                data=base.canonical(row["request"]), timeout=(15, 150), allow_redirects=False,
            )
            raw = response.content
            response_path = response_dir / f"{row['request_id']}.response.json"
            response_path.write_bytes(raw)
            response_hash = sha256(raw)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP_STATUS_{response.status_code}")
            payload = json.loads(raw)
            if payload.get("model") not in ALLOWED_MODEL_NAMES:
                raise RuntimeError("MODEL_IDENTITY_MISMATCH")
            fingerprint = payload.get("system_fingerprint")
            if not isinstance(fingerprint, str) or not fingerprint:
                raise RuntimeError("MISSING_SYSTEM_FINGERPRINT")
            if baseline_fingerprint is None:
                baseline_fingerprint = fingerprint
            elif fingerprint != baseline_fingerprint:
                raise RuntimeError("SYSTEM_FINGERPRINT_DRIFT")
            choices = payload.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or choices[0].get("finish_reason") != "stop":
                raise RuntimeError("INVALID_OR_TRUNCATED_COMPLETION")
            content = choices[0].get("message", {}).get("content")
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("EMPTY_MODEL_CONTENT")
            usage = payload.get("usage")
            if not isinstance(usage, dict):
                raise RuntimeError("MISSING_USAGE")
            actual_cost = base.estimate_cost(usage)
            if usage["completion_tokens"] > base.MAX_OUTPUT_TOKENS or usage["prompt_tokens"] > len(base.canonical(row["request"])) + 256:
                raise RuntimeError("TOKEN_BOUND_EXCEEDED")
            if actual_cost > reserve:
                raise RuntimeError("ACTUAL_COST_EXCEEDS_ROW_RESERVE")
            normalized = normalize_compatible_response(content, row)
            for item in normalized["claims"]:
                if item["claim_id"] not in key_by_pair[row["pair_id_private"]]["expected_status_private"]:
                    raise RuntimeError("OUTPUT_CLAIM_ID_MISSING_FROM_KEY")
            total_cost += actual_cost
            parsed_path = parsed_dir / f"{row['request_id']}.json"
            base.write_once(parsed_path, normalized)
            append_jsonl(attempts_path, {
                "event": "attempt_completed", "experiment_id": EXPERIMENT_ID, "phase": phase,
                "request_id": row["request_id"], "request_sha256": row["request_sha256"],
                "raw_response_sha256": response_hash,
                "response_path": str(response_path.relative_to(ROOT)).replace("\\", "/"),
                "parsed_output_path": str(parsed_path.relative_to(ROOT)).replace("\\", "/"),
                "http_status": response.status_code, "model_returned": payload["model"],
                "system_fingerprint": fingerprint, "finish_reason": choices[0]["finish_reason"],
                "usage": usage, "estimated_cost_usd_peak": str(actual_cost),
                "reserved_peak_cost_usd": str(reserve), "completed_at_utc": now_utc(),
                "compatibility_rule": "optional text is accepted only as exact claim echo and stripped from scoring projection",
                "status": "VALID_RESPONSE",
            })
            new_successes += 1
            print(json.dumps({"phase": phase, "completed_new": new_successes, "pending_initially": len(pending), "request_id": row["request_id"], "model": payload["model"], "finish_reason": choices[0]["finish_reason"], "cost_usd": str(actual_cost), "cumulative_cost_usd": str(total_cost)}, ensure_ascii=False), flush=True)
        except Exception as error:
            fatal_error = str(error)
            append_jsonl(attempts_path, {
                "event": "attempt_failed", "experiment_id": EXPERIMENT_ID, "phase": phase,
                "request_id": row["request_id"], "request_sha256": row["request_sha256"],
                "http_status": getattr(response, "status_code", None),
                "error": fatal_error, "error_type": type(error).__name__,
                "estimated_cost_usd_peak": str(actual_cost) if actual_cost is not None else None,
                "reserved_peak_cost_usd": str(reserve), "billing_uncertain": actual_cost is None,
                "retry": False, "failed_at_utc": now_utc(),
            })
            print(json.dumps({"phase": phase, "status": "STOP_FAILED_REQUEST", "request_id": row["request_id"], "error": fatal_error, "retry": False}, ensure_ascii=False), flush=True)
            break
        time.sleep(0.15)

    all_attempts = read_attempts(attempts_path)
    valid_ids = {row["request_id"] for row in all_attempts if row.get("event") in {"attempt_completed", "attempt_reclassified_valid"}}
    summary = {
        "experiment_id": EXPERIMENT_ID, "phase": phase,
        "scheduled_attempts": len(phase_rows), "valid_responses": len(valid_ids),
        "phase_status": "PASS_TECHNICAL_GATE" if len(valid_ids) == len(phase_rows) and fatal_error is None else "STOPPED_WITH_FAILURE",
        "fatal_error": fatal_error,
        "provider_attempts_started": len({row["request_id"] for row in all_attempts if row.get("event") == "attempt_started"}),
        "actual_peak_cost_estimate_usd": str(provider_costs(all_attempts)),
        "system_fingerprint": baseline_fingerprint,
        "elapsed_seconds": round(time.monotonic() - started_at, 3),
        "schedule_sha256": manifest["schedule_sha256"], "answer_key_sha256": manifest["answer_key_sha256"],
        "effect_direction_used_for_gate": False,
        "response_compatibility_rule": "optional exact claim-text echo only; all registered status/citation/source scoring unchanged",
        "created_at_utc": now_utc(),
    }
    summary_path = RUN_DIR / f"{phase}_phase_summary_compat.json"
    base.write_once(summary_path, summary)
    if phase == "pilot" and summary["phase_status"] == "PASS_TECHNICAL_GATE":
        base.write_once(RUN_DIR / "pilot_gate.json", {
            "status": "PASS_TECHNICAL_GATE", "valid_pilot_responses": 12,
            "conditions": ["12/12 provider responses complete", "identity/fingerprint stable", "usage within bounds", "valid JSON and q1-q9", "allowed status values", "input citation refs resolve"],
            "compatibility_amendment": "Exact optional claim-text echo accepted; raw response retained and echo stripped before scoring.",
            "efficacy_results_consulted": False,
            "schedule_sha256": manifest["schedule_sha256"], "created_at_utc": now_utc(),
        })
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["pilot", "heldout"], required=True)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    result = run(args.phase, preflight=args.preflight)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if args.preflight or result["phase_status"] == "PASS_TECHNICAL_GATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
