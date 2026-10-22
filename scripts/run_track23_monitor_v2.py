from __future__ import annotations

"""Execute exactly one frozen Track 2.3 monitor phase, with no retries."""

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "runs/sprint-monitor/track23-monitor-2x2-v1"
RUN_DIR = PRIVATE / "run"
EXPERIMENT_ID = "track23-monitor-2x2-v1"
MODEL = "deepseek-flash"
ALLOWED_MODEL_NAMES = {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"}
ENDPOINT = "https://api.deepseek.com/chat/completions"
AUTH_ID = "DS-FLASH-TRACK23-MONITOR-2X2-36-20261023"
MAX_OUTPUT_TOKENS = 2048
INPUT_MISS_RATE = Decimal("0.30")
INPUT_HIT_RATE = Decimal("0.006")
OUTPUT_RATE = Decimal("1.32")
PHASES = {"pilot", "heldout"}
ALLOWED_STATES = {"SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "NOT_IDENTIFIABLE"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(canonical(row) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_once(path: Path, value: Any) -> None:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if path.exists():
        if path.read_bytes() != data:
            raise RuntimeError(f"refusing to overwrite frozen run artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def load_local_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.exists():
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            values[name.strip()] = value.strip().strip('"').strip("'")
    return values


def verify_frozen() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    schedule_path = PRIVATE / "frozen_schedule.jsonl"
    key_path = PRIVATE / "answer_key.jsonl"
    manifest_path = ROOT / "docs/results/track23-monitor-2x2-v1/monitor_schedule_manifest.json"
    schedule = read_jsonl(schedule_path)
    key = read_jsonl(key_path)
    manifest = read_json(manifest_path)
    registration_dir = ROOT / "research/experiments" / EXPERIMENT_ID
    prereg = read_json(registration_dir / "preregistration.json")
    registration = read_json(registration_dir / "registration.json")
    errors: list[str] = []
    if sha256(schedule_path.read_bytes()) != manifest.get("schedule_sha256"):
        errors.append("frozen schedule hash mismatch")
    if sha256(key_path.read_bytes()) != manifest.get("answer_key_sha256"):
        errors.append("answer key hash mismatch")
    if prereg.get("experiment_id") != EXPERIMENT_ID or registration.get("experiment_id") != EXPERIMENT_ID:
        errors.append("research registry identity mismatch")
    if registration.get("preregistration_sha256") != sha256((registration_dir / "preregistration.json").read_bytes()):
        errors.append("registered preregistration hash mismatch")
    if prereg.get("protocol", {}).get("frozen_schedule_sha256") != manifest.get("schedule_sha256"):
        errors.append("preregistration schedule hash mismatch")
    if prereg.get("protocol", {}).get("answer_key_sha256") != manifest.get("answer_key_sha256"):
        errors.append("preregistration answer key hash mismatch")
    if len(schedule) != 36 or len(key) != 9:
        errors.append("frozen denominator must be 36 requests and 9 pair keys")
    if Decimal(str(manifest.get("peak_all_cache_miss_cost_upper_bound_usd", "999"))) > Decimal("2.00"):
        errors.append("frozen all-miss peak cost bound exceeds the user-authorized $2 cap")
    if sum(row.get("phase_private") == "pilot" for row in schedule) != 12:
        errors.append("pilot schedule does not contain 12 requests")
    if sum(row.get("phase_private") == "heldout" for row in schedule) != 24:
        errors.append("held-out schedule does not contain 24 requests")
    for row in schedule:
        req = row.get("request", {})
        if (req.get("model") != MODEL or req.get("temperature") != 0.0
                or req.get("max_tokens") != MAX_OUTPUT_TOKENS
                or req.get("response_format") != {"type": "json_object"}
                or req.get("thinking") != {"type": "disabled"}):
            errors.append(f"request parameter mismatch: {row.get('request_id')}")
        if sha256(canonical(req)) != row.get("request_sha256"):
            errors.append(f"request body hash mismatch: {row.get('request_id')}")
    auth_record = read_json(ROOT / "research/authorizations" / f"{AUTH_ID}.json")
    budget = read_json(ROOT / "research/budget.json")["authorization"]
    if (auth_record.get("approval_id") != AUTH_ID
            or EXPERIMENT_ID not in auth_record.get("authorized_experiment_ids", [])
            or auth_record.get("max_model_calls") != 36
            or Decimal(str(auth_record.get("max_external_cost_usd"))) != Decimal("2.0")):
        errors.append("immutable authorization does not match the 36-call/$2 scope")
    if budget.get("approval_id") != AUTH_ID or budget.get("status") != "active":
        errors.append("current budget snapshot is not this experiment's fresh authorization")
    if prereg.get("authorization", {}).get("approval_id") != AUTH_ID:
        errors.append("preregistration does not cite the current authorization")
    env = load_local_env()
    if not env.get("LLM_API_KEY"):
        errors.append("DeepSeek credential is unavailable")
    if env.get("LLM_MODEL_ID") != MODEL or env.get("LLM_BASE_URL", "").rstrip("/") != "https://api.deepseek.com":
        errors.append("local model configuration is not the authorized official DeepSeek endpoint and alias")
    if errors:
        raise RuntimeError("offline execution gate failed: " + "; ".join(errors))
    return schedule, key, manifest, env


def max_request_cost(row: dict[str, Any]) -> Decimal:
    request_bytes = len(canonical(row["request"]))
    input_tokens_bound = request_bytes + 256
    return (Decimal(input_tokens_bound) * INPUT_MISS_RATE + Decimal(MAX_OUTPUT_TOKENS) * OUTPUT_RATE) / Decimal(1_000_000)


def estimate_cost(usage: dict[str, Any]) -> Decimal:
    hit = usage.get("prompt_cache_hit_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    output = usage.get("completion_tokens")
    prompt = usage.get("prompt_tokens")
    values = (hit, miss, output, prompt)
    if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in values):
        raise ValueError("usage counts are missing or invalid")
    if hit + miss != prompt:
        raise ValueError("prompt token/cache count mismatch")
    return (Decimal(miss) * INPUT_MISS_RATE + Decimal(hit) * INPUT_HIT_RATE + Decimal(output) * OUTPUT_RATE) / Decimal(1_000_000)


def validate_response_content(content: str, row: dict[str, Any]) -> dict[str, Any]:
    parsed = json.loads(content)
    if not isinstance(parsed, dict) or set(parsed) != {"claims"} or not isinstance(parsed["claims"], list):
        raise ValueError("response must be an object with only a claims array")
    claim_ids = [item.get("claim_id") for item in parsed["claims"] if isinstance(item, dict)]
    if len(parsed["claims"]) != 9 or len(claim_ids) != 9 or set(claim_ids) != {f"q{i}" for i in range(1, 10)}:
        raise ValueError("response claim IDs must contain q1-q9 exactly once")
    allowed_refs = set(row["evidence_refs_private"])
    for item in parsed["claims"]:
        if set(item) != {"claim_id", "status", "citations", "short_reason"}:
            raise ValueError(f"invalid claim response fields: {item.get('claim_id')}")
        if item["status"] not in ALLOWED_STATES:
            raise ValueError(f"invalid status for {item['claim_id']}")
        if not isinstance(item["citations"], list) or any(not isinstance(ref, str) or ref not in allowed_refs for ref in item["citations"]):
            raise ValueError(f"invalid citation reference for {item['claim_id']}")
        if not isinstance(item["short_reason"], str):
            raise ValueError(f"invalid short_reason for {item['claim_id']}")
    return parsed


def run_phase(phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise ValueError(f"phase must be one of {sorted(PHASES)}")
    schedule, keys, manifest, env = verify_frozen()
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "scripts"))
    from local_llama_security import restrict_private_directory_acl
    acl = restrict_private_directory_acl(RUN_DIR)
    if not acl.get("verified"):
        raise RuntimeError("private run directory ACL could not be verified")
    attempts_path = RUN_DIR / f"{phase}_attempts.jsonl"
    if attempts_path.exists() and attempts_path.stat().st_size:
        raise RuntimeError("this experiment already has a physical attempt; no rerun or retry is allowed")
    if phase == "heldout":
        gate_path = RUN_DIR / "pilot_gate.json"
        gate = read_json(gate_path) if gate_path.exists() else {}
        if gate.get("status") != "PASS_TECHNICAL_GATE" or gate.get("valid_pilot_responses") != 12:
            raise RuntimeError("held-out phase requires a complete, technically valid 12-call pilot")

    phase_rows = [row for row in schedule if row["phase_private"] == phase]
    if phase == "pilot" and [row["pair_id_private"] for row in phase_rows if row["arm_private"] == "C0"] != [31, 20, 32]:
        raise RuntimeError("pilot pair assignment changed")
    if phase == "heldout" and [row["pair_id_private"] for row in phase_rows if row["arm_private"] == "C0"] != [4, 5, 12, 17, 23, 28]:
        raise RuntimeError("held-out pair assignment changed")
    run_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "phase": phase,
        "created_at_utc": now_utc(),
        "schedule_sha256": manifest["schedule_sha256"],
        "answer_key_sha256": manifest["answer_key_sha256"],
        "registered_preregistration_sha256": sha256((ROOT / "research/experiments" / EXPERIMENT_ID / "preregistration.json").read_bytes()),
        "approval_id": AUTH_ID,
        "endpoint": ENDPOINT,
        "model_requested": MODEL,
        "temperature": 0.0,
        "thinking": "disabled",
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "scheduled_attempts_in_phase": len(phase_rows),
        "retries": 0,
        "replacements": 0,
        "auth_header_saved": False,
        "private_directory_acl_verified": True,
        "transport": "HTTPS requests with standard TLS verification; redirects disabled; no retry adapter",
    }
    phase_manifest_path = RUN_DIR / f"{phase}_run_manifest.json"
    write_once(phase_manifest_path, run_manifest)
    response_dir = RUN_DIR / phase / "responses"
    parsed_dir = RUN_DIR / phase / "parsed"
    response_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    restrict_private_directory_acl(response_dir)
    restrict_private_directory_acl(parsed_dir)
    key_by_pair = {row["pair_id_private"]: row for row in keys}
    api_key = env["LLM_API_KEY"]
    session = requests.Session()
    session.trust_env = True
    results: list[dict[str, Any]] = []
    total_actual_cost = Decimal(0)
    baseline_fingerprint: str | None = None
    started = time.monotonic()
    fatal_error: str | None = None
    for index, row in enumerate(phase_rows, start=1):
        reserve = max_request_cost(row)
        response = None
        actual_cost: Decimal | None = None
        append_jsonl(attempts_path, {
            "event": "attempt_started",
            "experiment_id": EXPERIMENT_ID,
            "phase": phase,
            "attempt_number": 1,
            "request_id": row["request_id"],
            "request_sha256": row["request_sha256"],
            "reserved_peak_cost_usd": str(reserve),
            "started_at_utc": now_utc(),
            "retry": False,
        })
        try:
            response = session.post(
                ENDPOINT,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                data=canonical(row["request"]),
                timeout=(15, 150),
                allow_redirects=False,
            )
            raw_response = response.content
            response_path = response_dir / f"{row['request_id']}.response.json"
            response_path.write_bytes(raw_response)
            restrict_private_directory_acl(response_dir)
            response_hash = sha256(raw_response)
            if response.status_code != 200:
                raise RuntimeError(f"HTTP_STATUS_{response.status_code}")
            payload = json.loads(raw_response)
            if payload.get("model") not in ALLOWED_MODEL_NAMES:
                raise RuntimeError(f"MODEL_IDENTITY_MISMATCH:{payload.get('model')}")
            fingerprint = payload.get("system_fingerprint")
            if not isinstance(fingerprint, str) or not fingerprint:
                raise RuntimeError("MISSING_SYSTEM_FINGERPRINT")
            if baseline_fingerprint is None:
                baseline_fingerprint = fingerprint
            elif fingerprint != baseline_fingerprint:
                raise RuntimeError("SYSTEM_FINGERPRINT_DRIFT")
            choices = payload.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise RuntimeError("INVALID_CHOICES_SHAPE")
            finish_reason = choices[0].get("finish_reason")
            if finish_reason != "stop":
                raise RuntimeError(f"INVALID_FINISH_REASON:{finish_reason}")
            content = choices[0].get("message", {}).get("content")
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError("EMPTY_MODEL_CONTENT")
            usage = payload.get("usage")
            if not isinstance(usage, dict):
                raise RuntimeError("MISSING_USAGE")
            actual_cost = estimate_cost(usage)
            total_actual_cost += actual_cost
            if usage["completion_tokens"] > MAX_OUTPUT_TOKENS:
                raise RuntimeError("ACTUAL_OUTPUT_TOKENS_EXCEED_FROZEN_CAP")
            if usage["prompt_tokens"] > len(canonical(row["request"])) + 256:
                raise RuntimeError("ACTUAL_INPUT_TOKENS_EXCEED_CONSERVATIVE_BYTE_BOUND")
            if actual_cost > reserve:
                raise RuntimeError("ACTUAL_COST_EXCEEDS_CONSERVATIVE_REQUEST_RESERVE")
            parsed = validate_response_content(content, row)
            pair_key = key_by_pair[row["pair_id_private"]]
            for item in parsed["claims"]:
                # Check that every claim ID is present in the private key; no gold enters the prompt.
                if item["claim_id"] not in pair_key["expected_status_private"]:
                    raise RuntimeError("OUTPUT_CLAIM_ID_MISSING_FROM_PRIVATE_KEY")
            parsed_path = parsed_dir / f"{row['request_id']}.json"
            write_once(parsed_path, parsed)
            ledger = {
                "event": "attempt_completed",
                "experiment_id": EXPERIMENT_ID,
                "phase": phase,
                "request_id": row["request_id"],
                "request_sha256": row["request_sha256"],
                "raw_response_sha256": response_hash,
                "response_path": str(response_path.relative_to(ROOT)).replace("\\", "/"),
                "parsed_output_path": str(parsed_path.relative_to(ROOT)).replace("\\", "/"),
                "http_status": response.status_code,
                "model_returned": payload["model"],
                "system_fingerprint": fingerprint,
                "finish_reason": finish_reason,
                "usage": usage,
                "estimated_cost_usd_peak": str(actual_cost),
                "reserved_peak_cost_usd": str(reserve),
                "completed_at_utc": now_utc(),
                "status": "VALID_RESPONSE",
            }
            append_jsonl(attempts_path, ledger)
            results.append(ledger)
            print(json.dumps({"phase": phase, "completed": index, "scheduled": len(phase_rows), "request_id": row["request_id"], "model": payload["model"], "finish_reason": finish_reason, "cost_usd": str(actual_cost), "cumulative_cost_usd": str(total_actual_cost)}, ensure_ascii=False), flush=True)
        except Exception as error:
            fatal_error = str(error)
            error_row = {
                "event": "attempt_failed",
                "experiment_id": EXPERIMENT_ID,
                "phase": phase,
                "request_id": row["request_id"],
                "request_sha256": row["request_sha256"],
                "error_type": type(error).__name__,
                "error": fatal_error,
                "reserved_peak_cost_usd": str(reserve),
                "estimated_cost_usd_peak": str(actual_cost) if actual_cost is not None else None,
                "billing_uncertain": actual_cost is None,
                "http_status": getattr(response, "status_code", None),
                "failed_at_utc": now_utc(),
                "retry": False,
            }
            append_jsonl(attempts_path, error_row)
            print(json.dumps({"phase": phase, "status": "STOP_FAILED_REQUEST", "request_id": row["request_id"], "error": fatal_error, "retry": False}, ensure_ascii=False), flush=True)
            break
        time.sleep(0.15)

    phase_summary = {
        "experiment_id": EXPERIMENT_ID,
        "phase": phase,
        "scheduled_attempts": len(phase_rows),
        "valid_responses": len(results),
        "phase_status": "PASS_TECHNICAL_GATE" if len(results) == len(phase_rows) and not fatal_error else "STOPPED_WITH_FAILURE",
        "fatal_error": fatal_error,
        "model_calls_started": sum(row.get("event") == "attempt_started" for row in read_jsonl(attempts_path)),
        "actual_peak_cost_estimate_usd": str(total_actual_cost),
        "system_fingerprint": baseline_fingerprint,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "schedule_sha256": manifest["schedule_sha256"],
        "answer_key_sha256": manifest["answer_key_sha256"],
        "results_direction_used_for_gate": False,
        "created_at_utc": now_utc(),
    }
    summary_path = RUN_DIR / f"{phase}_phase_summary.json"
    write_once(summary_path, phase_summary)
    if phase == "pilot" and phase_summary["phase_status"] == "PASS_TECHNICAL_GATE":
        gate = {
            "status": "PASS_TECHNICAL_GATE",
            "valid_pilot_responses": len(results),
            "conditions": ["12/12 HTTP 200", "model/fingerprint stable", "finish_reason=stop", "usage present and within reserve", "valid JSON schema", "all citation refs resolve to input records"],
            "efficacy_results_consulted": False,
            "schedule_sha256": manifest["schedule_sha256"],
            "created_at_utc": now_utc(),
        }
        write_once(RUN_DIR / "pilot_gate.json", gate)
    return phase_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    args = parser.parse_args()
    summary = run_phase(args.phase)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["phase_status"] == "PASS_TECHNICAL_GATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
