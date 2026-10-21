#!/usr/bin/env python3
"""Run the frozen 40-attempt DeepSeek two-agent coordination study."""
from __future__ import annotations

import argparse
from decimal import Decimal
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokenizers import Tokenizer  # noqa: E402
from colluscope.deepseek_m4_v1 import (  # noqa: E402
    DeepSeekClient, DeepSeekRequestError, append_jsonl, canonical, now_utc,
    read_jsonl, request_cost_bound, request_payload, sha, write_once,
)
from colluscope.deepseek_real_coordination_v1 import (  # noqa: E402
    EXPERIMENT_ID, MAX_COST_USD, MAX_REQUESTS, MODEL, OUTPUT_LIMIT,
    TOKENIZER_SHA256, build_schedule, fact_control_passed,
    fact_control_reference, messages_for,
    schemas, validate_action,
)
from colluscope.deepseek_recipient_mechanism_v1 import render_v41  # noqa: E402
from colluscope.m2_v3_deepseek import (  # noqa: E402
    API_BASE, _dotenv_secret, apply_private_acl,
)

SCHEDULE_PATH = ROOT / "research/schedules/deepseek-real-coordination-v1.json"
CONFIG_PATH = ROOT / "configs/deepseek-real-coordination-v1.json"
AUTH_PATH = ROOT / "research/authorizations/DS-FLASH-REAL-COORD-40-20261021.json"
PREREG_PATH = ROOT / "research/experiments/deepseek-real-coordination-v1/preregistration.json"
REGISTRATION_PATH = ROOT / "research/experiments/deepseek-real-coordination-v1/registration.json"
RUN_DIR = ROOT / "runs/deepseek-real-coordination-v1"
PROJECT_CALL_CAP = 1200
PROJECT_COST_CAP = Decimal("2.50")
CRITICAL_PREFIXES = (
    "HTTP_", "TRANSPORT_ERROR", "INTERRUPTED_UNKNOWN", "PROVIDER_",
    "GLOBAL_", "RUN_REQUEST_CAP", "INPUT_BOUND", "FROZEN_REQUEST_HASH",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def event(path: Path, name: str, **fields: Any) -> None:
    append_jsonl(path, {"event": name, "at_utc": now_utc(), **fields})


def verify_freeze() -> tuple[dict[str, Any], dict[str, Any], Tokenizer, dict[str, Any], str]:
    schedule = load_json(SCHEDULE_PATH)
    config = load_json(CONFIG_PATH)
    prereg = load_json(PREREG_PATH)
    auth = load_json(AUTH_PATH)
    registration = load_json(REGISTRATION_PATH)
    if schedule.get("experiment_id") != EXPERIMENT_ID or len(schedule.get("requests", [])) != MAX_REQUESTS:
        raise RuntimeError("frozen schedule ID/request count mismatch")
    schedule_core = {k: v for k, v in schedule.items() if k != "schedule_sha256"}
    if sha(canonical(schedule_core)) != schedule.get("schedule_sha256"):
        raise RuntimeError("frozen schedule digest mismatch")
    rebuilt = build_schedule()
    if canonical(rebuilt) != canonical(schedule):
        raise RuntimeError("frozen schedule differs from source-code reconstruction")
    config_core = {k: v for k, v in config.items() if k != "config_sha256"}
    if sha(canonical(config_core)) != config.get("config_sha256"):
        raise RuntimeError("frozen configuration digest mismatch")
    if (config.get("model_requested") != MODEL
            or config.get("endpoint") != "https://api.deepseek.com/chat/completions"
            or config.get("interface") != "strict_function_calling"
            or config.get("temperature") != 0.0
            or config.get("thinking") != "disabled"
            or config.get("max_output_tokens") != OUTPUT_LIMIT
            or config.get("retry_limit") != 0
            or config.get("replacement_limit") != 0
            or Decimal(str(config.get("max_peak_reserved_cost_usd"))) != Decimal(MAX_COST_USD)):
        raise RuntimeError("runtime configuration differs from the freeze")
    tokenizer_path = ROOT / config["tokenizer_path"]
    if file_sha(tokenizer_path) != TOKENIZER_SHA256 or config.get("tokenizer_sha256") != TOKENIZER_SHA256:
        raise RuntimeError("pinned tokenizer digest mismatch")
    for item in prereg["protocol"]["frozen_inputs"]:
        path = ROOT / item["path"]
        if not path.is_file() or file_sha(path) != item["sha256"]:
            raise RuntimeError(f"registered source hash mismatch: {item['path']}")
    if registration.get("preregistration_sha256") != file_sha(PREREG_PATH):
        raise RuntimeError("registered preregistration hash mismatch")
    if prereg.get("schedule_sha256") != schedule["schedule_sha256"]:
        raise RuntimeError("schedule differs from preregistration")
    auth_sha = file_sha(AUTH_PATH)
    if prereg.get("authorization_batch_sha256") != auth_sha:
        raise RuntimeError("immutable authorization batch hash mismatch")
    if (auth.get("approval_id") != "DS-FLASH-REAL-COORD-40-20261021"
            or auth.get("authorized_experiment_ids") != [EXPERIMENT_ID]
            or auth.get("max_model_calls") != MAX_REQUESTS
            or Decimal(str(auth.get("max_external_cost_usd"))) != Decimal(MAX_COST_USD)):
        raise RuntimeError("authorization scope/cap mismatch")
    budget = load_json(ROOT / "research/budget.json")
    current = budget.get("authorization", {})
    if (current.get("status") != "active"
            or current.get("approval_id") != auth["approval_id"]
            or current.get("authorized_experiment_ids") != [EXPERIMENT_ID]
            or current.get("max_model_calls") != MAX_REQUESTS
            or Decimal(str(current.get("max_external_cost_usd"))) != Decimal(MAX_COST_USD)):
        raise RuntimeError("active budget authorization differs from the frozen batch")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    key, env_values = _dotenv_secret(ROOT / ".env")
    if not key:
        raise RuntimeError("DeepSeek credential is not configured locally")
    if env_values.get("LLM_BASE_URL", API_BASE) != API_BASE or env_values.get("LLM_MODEL_ID", MODEL) != MODEL:
        raise RuntimeError("local provider configuration differs from official DeepSeek Flash")
    return schedule, config, tokenizer, prereg, key


def _attempt_rows() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = read_jsonl(RUN_DIR / "attempts.jsonl")
    starts: dict[str, int] = {}
    terminals: dict[str, dict[str, Any]] = {}
    for row in rows:
        request_id = row.get("request_id")
        if row.get("event") == "attempt_started":
            starts[request_id] = starts.get(request_id, 0) + 1
        elif row.get("event") == "attempt_terminal":
            if request_id in terminals:
                raise RuntimeError(f"duplicate terminal attempt record for {request_id}")
            terminals[request_id] = row
    if any(count != 1 for count in starts.values()):
        raise RuntimeError("duplicate physical attempt found; stop without dispatch")
    if not set(terminals).issubset(starts):
        raise RuntimeError("terminal attempt has no matching start")
    if set(starts) != set(terminals):
        raise RuntimeError("a prior request lacks a terminal record; billing is ambiguous, so resume stops")
    for request_id, terminal in terminals.items():
        request_path = RUN_DIR / "requests" / f"{request_id}.bin"
        if not request_path.is_file() or sha(request_path.read_bytes()) != terminal.get("request_sha256"):
            raise RuntimeError(f"raw request missing or hash-mismatched for {request_id}")
        response_hash = terminal.get("response_sha256")
        if response_hash is not None:
            response_path = RUN_DIR / "responses" / f"{request_id}.bin"
            if not response_path.is_file() or sha(response_path.read_bytes()) != response_hash:
                raise RuntimeError(f"raw response missing or hash-mismatched for {request_id}")
    return rows, terminals


def _check_remaining_budget(auth: dict[str, Any], run_attempts: list[dict[str, Any]]) -> None:
    starts = [row for row in run_attempts if row.get("event") == "attempt_started"]
    if len(starts) > MAX_REQUESTS:
        raise RuntimeError("per-experiment physical attempt ceiling reached")
    reserved = sum((Decimal(row.get("reserved_peak_cost_usd", "0")) for row in starts), Decimal(0))
    if reserved > Decimal(MAX_COST_USD):
        raise RuntimeError("per-experiment peak-rate cost reservation exceeded")
    state = load_json(ROOT / "research/state.json")
    usage = state.get("new_iteration_usage", {})
    project_calls = int(usage.get("model_calls", 0))
    project_cost = Decimal(str(usage.get("external_cost_usd", "0")))
    if project_calls + len(starts) >= PROJECT_CALL_CAP:
        raise RuntimeError("cumulative project model-call ceiling would be exceeded")
    if project_cost + reserved > PROJECT_COST_CAP:
        raise RuntimeError("cumulative project cost ceiling would be exceeded")
    expiry = datetime.fromisoformat(auth["expires_at_utc"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expiry:
        raise RuntimeError("authorization batch has expired")


def _critical(status: str, fatal: bool) -> bool:
    return fatal or status.startswith(CRITICAL_PREFIXES)


def run(*, check_only: bool = False) -> dict[str, Any]:
    schedule, config, tokenizer, prereg, api_key = verify_freeze()
    if check_only:
        return {"status": "PASS_OFFLINE_PREFLIGHT", "model_calls": 0,
                "assigned_requests": MAX_REQUESTS, "schedule_sha256": schedule["schedule_sha256"],
                "tokenizer_sha256": TOKENIZER_SHA256,
                "approved_attempt_cap": MAX_REQUESTS, "peak_reserved_cost_cap_usd": MAX_COST_USD,
                "endpoint": config["endpoint"], "model_alias": MODEL}
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    apply_private_acl(RUN_DIR)
    manifest_path = RUN_DIR / "manifest.json"
    config_sha = file_sha(CONFIG_PATH)
    prereg_sha = file_sha(PREREG_PATH)
    if not manifest_path.exists():
        write_once(manifest_path, canonical({
            "experiment_id": EXPERIMENT_ID, "schedule_sha256": schedule["schedule_sha256"],
            "config_sha256": config_sha, "preregistration_sha256": prereg_sha,
            "model_requested": MODEL, "endpoint": config["endpoint"],
            "tokenizer_sha256": TOKENIZER_SHA256, "temperature": 0.0,
            "thinking": "disabled", "max_output_tokens": OUTPUT_LIMIT,
            "assigned_requests": MAX_REQUESTS, "physical_attempt_cap": MAX_REQUESTS,
            "peak_reserved_cost_cap_usd": MAX_COST_USD,
            "retries": 0, "replacements": 0, "raw_private_data_gitignored": True,
            "auth_header_saved": False, "created_at_utc": now_utc(),
        }) + b"\n")
    else:
        manifest = load_json(manifest_path)
        if (manifest.get("schedule_sha256") != schedule["schedule_sha256"]
                or manifest.get("config_sha256") != config_sha
                or manifest.get("preregistration_sha256") != prereg_sha):
            raise RuntimeError("existing local run manifest differs from frozen inputs")
    attempts_path = RUN_DIR / "attempts.jsonl"
    progress_path = RUN_DIR / "progress.jsonl"
    client = DeepSeekClient(run_dir=RUN_DIR, budget_ledger=RUN_DIR / "global_budget_ledger.jsonl",
                            api_key=api_key, interface="strict_function_calling", timeout=90)
    attempts, terminals = _attempt_rows()
    initial_attempt_count = sum(row.get("event") == "attempt_started" for row in attempts)
    _check_remaining_budget(load_json(AUTH_PATH), attempts)
    prior_progress = read_jsonl(progress_path)
    terminalized = {row.get("request_id") for row in prior_progress
                    if row.get("event") in {"request_success", "request_failure", "request_unattempted"}}
    outputs: dict[str, dict[str, Any]] = {}
    request_status: dict[str, dict[str, Any]] = {}
    fatal_stop = None
    for row in schedule["requests"]:
        rid = row["request_id"]
        attempts, terminals = _attempt_rows()
        if rid in terminals and terminals[rid].get("status") != "COMPLETED":
            terminal = terminals[rid]
            status = str(terminal.get("status", "UNKNOWN"))
            request_status[rid] = terminal
            if rid not in terminalized:
                event(progress_path, "request_failure", request_id=rid, status=status,
                      http_status=terminal.get("http_status"), resumed=True)
                terminalized.add(rid)
            if row["kind"] == "fact_control" or status.startswith(CRITICAL_PREFIXES):
                fatal_stop = f"prior terminal failure {rid}:{status}"
                break
            continue
        missing = [dependency for dependency in row["dependencies"] if dependency not in outputs]
        if missing:
            request_status[rid] = {"status": "NOT_ATTEMPTED_DEPENDENCY_FAILED", "http_status": None}
            if rid not in terminalized:
                event(progress_path, "request_unattempted", request_id=rid, kind=row["kind"],
                      reason="DEPENDENCY_INVALID_OR_UNAVAILABLE", dependencies=missing)
                terminalized.add(rid)
            continue
        try:
            messages, prompt_meta = messages_for(row, schedule, outputs)
            local_tokens = len(tokenizer.encode(render_v41(messages, json_object=False)).ids)
            tool_name, schema = schemas(row["kind"], incoming_proposal=prompt_meta.get("incoming_proposal"))
            payload = request_payload(interface="strict_function_calling", messages=messages,
                                      tool_name=tool_name, schema=schema, output_limit=OUTPUT_LIMIT)
            body = canonical(payload)
            _, reserve = request_cost_bound(body, OUTPUT_LIMIT)
            attempts, terminals = _attempt_rows()
            _check_remaining_budget(load_json(AUTH_PATH), attempts)
            prior_reserved = sum((Decimal(item.get("reserved_peak_cost_usd", "0"))
                                  for item in attempts if item.get("event") == "attempt_started"), Decimal(0))
            if prior_reserved + reserve > Decimal(MAX_COST_USD):
                raise RuntimeError("next request exceeds the frozen $0.50 peak-rate reservation")
        except Exception as exc:
            reason = f"PRE_REQUEST_FAILURE:{type(exc).__name__}"
            event(progress_path, "request_unattempted", request_id=rid, kind=row["kind"],
                  reason=reason, detail=str(exc)[:240], model_request_started=False)
            terminalized.add(rid)
            fatal_stop = f"{rid}:{reason}"
            break

        def semantic(value: Any) -> dict[str, Any]:
            try:
                return validate_action(row["kind"], value,
                                       incoming_proposal=prompt_meta.get("incoming_proposal"))
            except Exception as exc:
                raise DeepSeekRequestError("INVALID_ACTION", str(exc), fatal=False) from exc

        try:
            action, metadata = client.call(
                request_id=rid, role="agent", messages=messages,
                tool_name=tool_name, schema=schema, semantic=semantic,
                metadata={"scenario_id": row["scenario_id"], "condition_id": row["condition_id"],
                          "kind": row["kind"], "dependencies": row["dependencies"],
                          "local_prompt_tokens_v41": local_tokens,
                          "metadata_not_sent_to_model": True},
                output_limit=OUTPUT_LIMIT, run_request_limit=MAX_REQUESTS,
            )
        except DeepSeekRequestError as exc:
            _, terminal_rows = _attempt_rows()
            terminal = terminal_rows.get(rid, {"status": exc.status, "http_status": None})
            request_status[rid] = terminal
            if rid not in terminalized:
                event(progress_path, "request_failure", request_id=rid,
                      status=terminal.get("status", exc.status),
                      http_status=terminal.get("http_status"), fatal=exc.fatal)
                terminalized.add(rid)
            if row["kind"] == "fact_control" or _critical(str(terminal.get("status", exc.status)), exc.fatal):
                fatal_stop = f"{rid}:{terminal.get('status', exc.status)}"
                break
            continue
        outputs[rid] = action
        request_status[rid] = {**metadata, "status": "COMPLETED", "http_status": metadata.get("http_status", 200)}
        if rid not in terminalized:
            event(progress_path, "request_success", request_id=rid,
                  action=action, request_sha256=metadata["request_sha256"],
                  response_sha256=metadata["response_sha256"],
                  finish_reason=metadata["finish_reason"],
                  prompt_tokens_provider=metadata["prompt_tokens"],
                  completion_tokens_provider=metadata["completion_tokens"],
                  local_prompt_tokens_v41=local_tokens,
                  estimated_peak_cost_usd=metadata["estimated_peak_cost_usd"])
            terminalized.add(rid)
        if row["kind"] == "fact_control":
            correct = fact_control_passed(row, action)
            event(progress_path, "fact_control_result", request_id=rid,
                  correct=correct, expected_reference=fact_control_reference(row),
                  observed_answer=action.get("answer"))
            if not correct:
                fatal_stop = f"POSITIVE_CONTROL_FAILED:{rid}"
                event(progress_path, "control_gate_failed", request_id=rid,
                      stop_reason=fatal_stop, remaining_model_requests_stopped=True)
                break
    if fatal_stop:
        started_ids = {row.get("request_id") for row in read_jsonl(attempts_path)
                       if row.get("event") == "attempt_started"}
        for row in schedule["requests"]:
            rid = row["request_id"]
            if rid not in started_ids and rid not in terminalized:
                event(progress_path, "request_unattempted", request_id=rid, kind=row["kind"],
                      reason="FATAL_BATCH_STOP", stop_reason=fatal_stop,
                      dependencies=row["dependencies"])
                terminalized.add(rid)
    attempts, terminals = _attempt_rows()
    started_count = sum(row.get("event") == "attempt_started" for row in attempts)
    statuses = {row.get("request_id"): row for row in terminals.values()}
    return {"experiment_id": EXPERIMENT_ID, "assigned_requests": MAX_REQUESTS,
            "physical_attempts": started_count, "new_model_calls": started_count - initial_attempt_count,
            "actions_reconstructed": len(outputs),
            "terminal_requests": len(terminals), "unattempted_assigned": MAX_REQUESTS - started_count,
            "stop_status": fatal_stop or "SCHEDULE_EXHAUSTED_OR_ALL_TERMINAL",
            "attempt_statuses": {key: value.get("status") for key, value in statuses.items()},
            "raw_dir": str(RUN_DIR)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    result = run(check_only=args.check_only)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("stop_status") != "SCHEDULE_EXHAUSTED_OR_ALL_TERMINAL":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
