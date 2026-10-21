#!/usr/bin/env python3
"""Independently replay raw request/response evidence for the 40-call study."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.deepseek_m4_v1 import (  # noqa: E402
    append_jsonl, canonical, read_jsonl, sha, write_once,
)
from colluscope.deepseek_real_coordination_v1 import (  # noqa: E402
    EXPERIMENT_ID, MAX_COST_USD, MAX_REQUESTS, MODEL, OUTPUT_LIMIT,
    TOKENIZER_SHA256, analyze_actions,
    build_schedule, messages_for, schemas, validate_action,
)
from colluscope.deepseek_m4_v1 import request_payload  # noqa: E402
from colluscope.deepseek_recipient_mechanism_v1 import render_v41  # noqa: E402

RUN_DIR = ROOT / "runs/deepseek-real-coordination-v1"
ANALYSIS_PATH = RUN_DIR / "independent-analysis.json"
REQUEST_LEDGER_PATH = ROOT / "docs/results/deepseek-real-coordination-v1/model-request-ledger.json"


def _condition_token_profiles(schedule: dict[str, Any], token_counts: dict[str, int]) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for scenario in schedule["scenarios"]:
        sid = scenario["scenario_id"]
        totals: dict[str, int | None] = {}
        per_arm: dict[str, dict[str, Any]] = {}
        for condition in ("shared_bonus_no_delivery", "shared_bonus_neutral_delivery",
                          "shared_bonus_actual_delivery"):
            rows = [row for row in schedule["requests"]
                    if row["scenario_id"] == sid and row["condition_id"] == condition]
            counts = {row["request_id"]: token_counts.get(row["request_id"]) for row in rows}
            complete = len(counts) == 4 and all(type(count) is int for count in counts.values())
            totals[condition] = sum(counts.values()) if complete else None
            per_arm[condition] = {"stage_prompt_tokens_v41": counts,
                                  "total_if_all_four_requests_counted": totals[condition]}
        baseline = totals["shared_bonus_no_delivery"]
        for condition in ("shared_bonus_neutral_delivery", "shared_bonus_actual_delivery"):
            total = totals[condition]
            per_arm[condition]["total_minus_no_delivery"] = (
                total - baseline if total is not None and baseline is not None else None)
        per_arm["shared_bonus_no_delivery"]["total_minus_no_delivery"] = 0 if baseline is not None else None
        profiles.append({"scenario_id": sid, "arms": per_arm})
    return profiles


def _decode_action(response_raw: bytes, *, tool_name: str,
                   kind: str, incoming: dict[str, Any] | None) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key}")
            result[key] = value
        return result

    response = json.loads(response_raw, object_pairs_hook=unique)
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("completion must contain exactly one choice")
    choice = choices[0]
    if choice.get("finish_reason") != "tool_calls":
        raise ValueError("completion did not terminate as a tool call")
    message = choice.get("message")
    if not isinstance(message, dict) or message.get("content") not in (None, ""):
        raise ValueError("tool response contains free text")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        raise ValueError("completion must contain exactly one tool call")
    function = calls[0].get("function")
    if calls[0].get("type") != "function" or not isinstance(function, dict) or function.get("name") != tool_name:
        raise ValueError("tool name mismatch")
    args = json.loads(function.get("arguments", ""), object_pairs_hook=unique)
    return validate_action(kind, args, incoming_proposal=incoming)


def replay(run_dir: Path = RUN_DIR) -> dict[str, Any]:
    schedule = build_schedule()
    attempts = read_jsonl(run_dir / "attempts.jsonl")
    starts: dict[str, list[dict[str, Any]]] = {}
    terminals: dict[str, list[dict[str, Any]]] = {}
    for row in attempts:
        if row.get("event") == "attempt_started":
            starts.setdefault(row["request_id"], []).append(row)
        elif row.get("event") == "attempt_terminal":
            terminals.setdefault(row["request_id"], []).append(row)
    issues: list[str] = []
    for request_id, rows in starts.items():
        if len(rows) != 1:
            issues.append(f"duplicate start:{request_id}")
        if len(terminals.get(request_id, [])) != 1:
            issues.append(f"missing/duplicate terminal:{request_id}")
    if set(terminals) - set(starts):
        issues.append("terminal_without_start")
    if len(starts) > MAX_REQUESTS:
        issues.append("attempt_cap_exceeded")

    actions: dict[str, dict[str, Any]] = {}
    request_status: dict[str, dict[str, Any]] = {}
    request_hashes: dict[str, str] = {}
    response_hashes: dict[str, str | None] = {}
    usage_by_request: dict[str, dict[str, Any]] = {}
    returned_identities: set[tuple[str, str]] = set()
    local_prompt_tokens: dict[str, int] = {}
    tokenizer_path = ROOT / ".cache/deepseek-recipe/tokenizer-v41.json"
    if not tokenizer_path.is_file() or sha(tokenizer_path.read_bytes()) != TOKENIZER_SHA256:
        issues.append("pinned_tokenizer_missing_or_hash_mismatch")
        tokenizer = None
    else:
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
    for request_id, rows in starts.items():
        if len(rows) == 1:
            request_status[request_id] = {"attempt_started": True}
            request_path = run_dir / "requests" / f"{request_id}.bin"
            meta_path = run_dir / "requests" / f"{request_id}.meta.json"
            if not request_path.is_file():
                issues.append(f"missing_request:{request_id}")
                continue
            request_raw = request_path.read_bytes()
            if rows[0].get("request_sha256") != sha(request_raw):
                issues.append(f"start_request_hash_mismatch:{request_id}")
            if b"Authorization" in request_raw or b"Bearer " in request_raw or b"LLM_API_KEY" in request_raw:
                issues.append(f"credential_material_in_request:{request_id}")
            if not meta_path.is_file():
                issues.append(f"request_metadata_missing:{request_id}")
                continue
            try:
                meta = json.loads(meta_path.read_bytes())
                if meta.get("request_sha256") != sha(request_raw) or meta.get("auth_header_saved") is not False:
                    issues.append(f"request_metadata_mismatch_or_auth_saved:{request_id}")
                local_count = meta.get("metadata_not_sent", {}).get("local_prompt_tokens_v41")
                if type(local_count) is not int or local_count < 0:
                    issues.append(f"local_token_count_missing:{request_id}")
                else:
                    local_prompt_tokens[request_id] = local_count
            except Exception as exc:
                issues.append(f"request_metadata_unreadable:{request_id}:{type(exc).__name__}")
    for row in schedule["requests"]:
        request_id = row["request_id"]
        terminal_rows = terminals.get(request_id, [])
        if not terminal_rows:
            continue
        if len(terminal_rows) != 1:
            continue
        terminal = terminal_rows[0]
        request_status[request_id] = {**request_status.get(request_id, {}), **terminal}
        request_path = run_dir / "requests" / f"{request_id}.bin"
        response_path = run_dir / "responses" / f"{request_id}.bin"
        if not request_path.is_file():
            issues.append(f"missing_request:{request_id}")
            continue
        request_raw = request_path.read_bytes()
        request_hashes[request_id] = sha(request_raw)
        if terminal.get("request_sha256") != sha(request_raw):
            issues.append(f"request_hash_mismatch:{request_id}")
            continue
        response_hash = terminal.get("response_sha256")
        response_hashes[request_id] = response_hash
        if response_hash is not None:
            if not response_path.is_file() or sha(response_path.read_bytes()) != response_hash:
                issues.append(f"response_hash_mismatch:{request_id}")
                continue
        try:
            messages, prompt_meta = messages_for(row, schedule, actions)
            tool_name, schema = schemas(row["kind"], incoming_proposal=prompt_meta.get("incoming_proposal"))
            expected = request_payload(interface="strict_function_calling", messages=messages,
                                       tool_name=tool_name, schema=schema, output_limit=OUTPUT_LIMIT)
            if canonical(expected) != request_raw:
                issues.append(f"reconstructed_request_mismatch:{request_id}")
                continue
            if tokenizer is not None:
                rendered_tokens = len(tokenizer.encode(render_v41(messages, json_object=False)).ids)
                if local_prompt_tokens.get(request_id) != rendered_tokens:
                    issues.append(f"independent_local_token_count_mismatch:{request_id}")
            if terminal.get("http_status") != 200 or response_hash is None:
                continue
            response_doc = json.loads(response_path.read_bytes())
            returned_model = response_doc.get("model")
            fingerprint = response_doc.get("system_fingerprint")
            if returned_model not in {MODEL, "DeepSeek-V4.1-Flash-1017"}:
                issues.append(f"returned_model_mismatch:{request_id}")
            if not isinstance(fingerprint, str) or not fingerprint.strip():
                issues.append(f"returned_fingerprint_missing:{request_id}")
            elif returned_model in {MODEL, "DeepSeek-V4.1-Flash-1017"}:
                returned_identities.add((returned_model, fingerprint))
            usage = response_doc.get("usage")
            if isinstance(usage, dict):
                usage_by_request[request_id] = {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "estimated_peak_cost_usd": terminal.get("estimated_peak_cost_usd"),
                }
            action = _decode_action(response_path.read_bytes(), tool_name=tool_name,
                                    kind=row["kind"], incoming=prompt_meta.get("incoming_proposal"))
            actions[request_id] = action
        except Exception as exc:
            # Invalid output is a retained model outcome; it is not repaired or scored.
            if terminal.get("status") == "COMPLETED":
                issues.append(f"independent_replay_failed:{request_id}:{type(exc).__name__}")

    if len(returned_identities) > 1:
        issues.append("returned_provider_identity_drift")
    identity_path = run_dir / "provider_identity.json"
    if returned_identities and identity_path.is_file():
        identity = json.loads(identity_path.read_bytes())
        if returned_identities != {(identity.get("model"), identity.get("system_fingerprint"))}:
            issues.append("provider_identity_file_mismatch")
    elif returned_identities and not identity_path.is_file():
        issues.append("provider_identity_file_missing")

    summary = analyze_actions(schedule, actions, request_status)
    status_counts = Counter(row.get("status", "UNKNOWN") for rows in terminals.values() for row in rows)
    reserved = sum((Decimal(row.get("reserved_peak_cost_usd", "0")) for row in attempts
                    if row.get("event") == "attempt_started"), Decimal("0"))
    provider_prompt_tokens = sum(
        int(item["prompt_tokens"]) for item in usage_by_request.values()
        if type(item.get("prompt_tokens")) is int)
    provider_completion_tokens = sum(
        int(item["completion_tokens"]) for item in usage_by_request.values()
        if type(item.get("completion_tokens")) is int)
    assigned_ids = {row["request_id"] for row in schedule["requests"]}
    missing_assigned = sorted(assigned_ids - set(starts))
    failed_rows = [request_id for request_id, rows in terminals.items()
                   if len(rows) == 1 and rows[0].get("status") != "COMPLETED"]
    analysis = {
        "schema_version": "deepseek-real-coordination-audit-v1",
        "experiment_id": EXPERIMENT_ID,
        "schedule_sha256": schedule["schedule_sha256"],
        "assigned_requests": MAX_REQUESTS,
        "physical_attempts": len(starts),
        "terminal_attempts": sum(len(rows) for rows in terminals.values()),
        "valid_actions_reconstructed": len(actions),
        "invalid_or_failed_attempts": len(failed_rows),
        "unattempted_assigned": len(missing_assigned),
        "unattempted_request_ids": missing_assigned,
        "terminal_status_counts": dict(sorted(status_counts.items())),
        "failed_request_ids": failed_rows,
        "issues": issues,
        "independent_behavioral_analysis": summary,
        "provider_usage": {"requests_with_usage": len(usage_by_request),
                           "prompt_tokens": provider_prompt_tokens,
                           "completion_tokens": provider_completion_tokens,
                           "reported_per_request_usage": usage_by_request},
        "local_prompt_tokens_v41_by_request": local_prompt_tokens,
        "condition_prompt_token_profiles": _condition_token_profiles(schedule, local_prompt_tokens),
        "budget": {"peak_cost_reserved_upper_bound_usd": str(reserved),
                   "per_attempt_cap_usd": MAX_COST_USD,
                   "physical_cap": MAX_REQUESTS},
        "request_sha256_by_id": request_hashes,
        "response_sha256_by_id": response_hashes,
        "claim_boundary": "Observed finite-set behavior only. No latent collusion or intent label; treatment assignment, agreement, chat availability, message content, action, and public welfare are not gold labels for collusion.",
    }
    return analysis


def sanitized_request_ledger(analysis: dict[str, Any], run_dir: Path = RUN_DIR) -> dict[str, Any]:
    attempts = read_jsonl(run_dir / "attempts.jsonl")
    terminals = {row.get("request_id"): row for row in attempts if row.get("event") == "attempt_terminal"}
    starts = [row for row in attempts if row.get("event") == "attempt_started"]
    requests = []
    for start in starts:
        request_id = start["request_id"]
        terminal = terminals.get(request_id, {})
        requests.append({
            "experiment_id": EXPERIMENT_ID,
            "attempt_id_sha256": hashlib.sha256(request_id.encode()).hexdigest(),
            "started_at_utc": start["at_utc"],
            "terminal_status": str(terminal.get("status", "UNKNOWN"))[:40],
            "external_cost_usd": str(terminal.get("estimated_peak_cost_usd", "0")),
        })
    return {"schema_version": 1, "experiment_id": EXPERIMENT_ID, "requests": requests}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write sanitized replay and request ledger")
    args = parser.parse_args()
    analysis = replay()
    print(json.dumps({key: value for key, value in analysis.items()
                      if key not in {"request_sha256_by_id", "response_sha256_by_id", "provider_usage"}},
                     indent=2, sort_keys=True))
    if args.write:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        write_once(ANALYSIS_PATH, canonical(analysis) + b"\n")
        REQUEST_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        ledger = sanitized_request_ledger(analysis)
        REQUEST_LEDGER_PATH.write_bytes(canonical(ledger) + b"\n")
    return 0 if not analysis["issues"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
