#!/usr/bin/env python3
"""Run the frozen 16-row DeepSeek recovery diagnostic after a separate approval."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tomllib
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from colluscope.sprint_baselines import (  # noqa: E402
    BASELINE_VIEWS, TASK_DEFINITIONS, _assert_no_banned_keys,
    build_monitor_payload, canonical_json, parse_model_output, provenance_gate,
)
from scripts import run_sprint_monitor as transport  # noqa: E402

CONFIG = ROOT / "configs/monitor-recovery-v2.toml"
SCHEDULE = ROOT / "configs/monitor-recovery-diagnostic-v1.json"
CONTROLS = ROOT / "data/sprint-baseline-v1/controls.jsonl"
SYSTEM_PROMPT = ROOT / "prompts/sprint-baseline-v2/system.txt"
USER_TEMPLATE = ROOT / "prompts/sprint-baseline-v2/user.txt"
DEFAULT_OUT = ROOT / "runs/full-research-execution-20261020/monitor/recovery_diagnostic"
MAX_REQUESTS = 16
ALLOWED_MODELS = {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"}
ARTIFACT_PATHS = (
    "configs/monitor-recovery-v2.toml",
    "configs/monitor-recovery-diagnostic-v1.json",
    "data/sprint-baseline-v1/controls.jsonl",
    "prompts/sprint-baseline-v2/system.txt",
    "prompts/sprint-baseline-v2/user.txt",
    "prompts/sprint-baseline-v1/tasks.json",
    "src/colluscope/sprint_baselines.py",
    "scripts/run_monitor_recovery_diagnostic.py",
    "scripts/audit_monitor_recovery_diagnostic.py",
    "scripts/run_sprint_monitor.py",
    "scripts/run_full_research_monitor.py",
    "scripts/local_llama_security.py",
)


def _config() -> dict[str, Any]:
    value = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    expected = {"protocol_id": "sprint-monitor-recovery-v2",
                "status": "frozen_offline_separate_approval_required",
                "model_alias": "deepseek-flash", "endpoint": "https://api.deepseek.com/chat/completions",
                "thinking": "disabled", "temperature": 0.0, "max_output_tokens": 256,
                "max_input_utf8_bytes": 8192, "response_format": "json_object",
                "max_logical_requests": 16, "max_http_attempts": 16,
                "max_attempts_per_logical_request": 1, "retries": 0, "replacements": 0,
                "inference_authorized": False}
    if any(value.get(key) != item for key, item in expected.items()):
        raise ValueError("Monitor recovery config differs from its separately approved frozen protocol")
    return value


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifact_hashes() -> dict[str, str]:
    return {relative: _sha((ROOT / relative).read_bytes()) for relative in ARTIFACT_PATHS}


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _approval(path: Path, approval_id: str, config_hash: str, schedule_hash: str) -> dict[str, str]:
    allowed_root = (ROOT / "runs/full-research-execution-20261020/monitor/recovery_diagnostic").resolve()
    path = path.resolve()
    if allowed_root not in path.parents or not path.is_file():
        raise PermissionError("Monitor diagnostic approval receipt must remain in its private run directory")
    receipt = json.loads(path.read_bytes())
    expected_keys = {"schema_version", "authorization_id", "protocol_id", "config_sha256",
                     "schedule_sha256", "max_requests", "retries", "replacements", "external_fallback"}
    if (set(receipt) != expected_keys
            or receipt.get("schema_version") != "monitor-recovery-diagnostic-authorization-v1"
            or receipt.get("authorization_id") != approval_id
            or receipt.get("protocol_id") != "monitor-recovery-diagnostic-v1"
            or receipt.get("config_sha256") != config_hash
            or receipt.get("schedule_sha256") != schedule_hash
            or receipt.get("max_requests") != MAX_REQUESTS
            or receipt.get("retries") != 0 or receipt.get("replacements") != 0
            or receipt.get("external_fallback") is not False):
        raise PermissionError("Monitor diagnostic approval receipt does not match the frozen 16-request scope")
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": _sha(path.read_bytes())}


def _build_requests() -> list[dict[str, Any]]:
    config = _config()
    schedule = json.loads(SCHEDULE.read_bytes())
    controls = {row["case_ref"]: row for row in
                (json.loads(line) for line in CONTROLS.read_text(encoding="utf-8").splitlines())}
    system = SYSTEM_PROMPT.read_text(encoding="utf-8").strip()
    template = USER_TEMPLATE.read_text(encoding="utf-8").rstrip()
    if (schedule.get("protocol_id") != "monitor-recovery-diagnostic-v1"
            or schedule.get("logical_request_limit") != MAX_REQUESTS
            or schedule.get("physical_http_limit") != MAX_REQUESTS
            or len(schedule.get("rows", [])) != MAX_REQUESTS):
        raise ValueError("Monitor diagnostic schedule differs from the 16-request freeze")
    output = []
    for row in schedule["rows"]:
        source = controls.get(row["case_ref"])
        if source is None:
            raise ValueError("diagnostic schedule references a missing frozen scripted control")
        baseline = row["baseline_id"]
        if BASELINE_VIEWS.get(baseline) != row["view_name"]:
            raise ValueError("diagnostic method/view pair differs from the frozen baseline mapping")
        spec = TASK_DEFINITIONS[row["task"]]
        _old_payload, evidence = build_monitor_payload(source, baseline, row["task"], row["permission"])
        if _sha(canonical_json(evidence)) != row["source_evidence_sha256"]:
            raise ValueError("compiled visible evidence differs from the frozen diagnostic input hash")
        _assert_no_banned_keys(evidence)
        user = template.replace("{{question}}", spec["question"])
        user = user.replace("{{allowed_labels}}", ", ".join(spec["allowed_labels"]))
        user = user.replace("{{evidence_json}}", json.dumps(evidence, ensure_ascii=False,
                                                            sort_keys=True, separators=(",", ":")))
        payload = {
            "model": "deepseek-flash",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "thinking": {"type": "disabled"}, "temperature": 0.0,
            "max_tokens": config["max_output_tokens"],
            "response_format": {"type": "json_object"}, "stream": False,
        }
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(body) > config["max_input_utf8_bytes"]:
            raise ValueError("diagnostic request exceeds the frozen UTF-8 input-byte safety bound")
        # Prevent case IDs, reference labels, construction fields or routing data
        # from crossing the evidence projection boundary.
        lowered = body.decode("utf-8").casefold()
        for forbidden in (row["case_ref"], "condition_id", "private_reward_target",
                          "reference_answer", "construction_truth", "welfare_gap", "target_executed"):
            if forbidden.casefold() in lowered:
                raise ValueError("hidden case or reference metadata entered a diagnostic request")
        output.append({"schedule": row, "source": source, "evidence": evidence,
                       "payload": payload, "body": body, "request_sha256": _sha(body),
                       "evidence_sha256": _sha(canonical_json(evidence))})
    if len({row["schedule"]["request_id"] for row in output}) != MAX_REQUESTS:
        raise ValueError("duplicate or missing diagnostic logical request IDs")
    return output


def run(out: Path, *, approval_id: str, approval_receipt: Path) -> dict[str, Any]:
    config = _config()
    config_hash, schedule_hash = _sha(CONFIG.read_bytes()), _sha(SCHEDULE.read_bytes())
    approval = _approval(approval_receipt, approval_id, config_hash, schedule_hash)
    requests = _build_requests()
    out = out.resolve()
    expected_root = (ROOT / "runs/full-research-execution-20261020/monitor/recovery_diagnostic").resolve()
    if expected_root not in out.parents:
        raise PermissionError("Monitor diagnostic raw artifacts must remain in Git-ignored restricted storage")
    if "/runs/full-research-execution-20261020/" not in (ROOT / ".gitignore").read_text(encoding="utf-8").replace("\\", "/"):
        raise PermissionError("Monitor raw output root is not Git-ignored")
    out.mkdir(parents=True, exist_ok=True)
    from scripts.local_llama_security import restrict_private_directory_acl, verify_private_directory_acl
    acl = restrict_private_directory_acl(out) if not any(out.iterdir()) else verify_private_directory_acl(out)
    if acl.get("verified") is not True:
        raise PermissionError("Monitor diagnostic output ACL is not verified")
    manifest = {"schema_version": "monitor-recovery-diagnostic-run-v1",
                "protocol_id": "monitor-recovery-diagnostic-v1", "mode": "live",
                "authorization_id": approval_id, "authorization_receipt": approval,
                "config_sha256": config_hash, "schedule_sha256": schedule_hash,
                "artifact_sha256": _artifact_hashes(),
                "python_version": sys.version,
                "system_prompt_sha256": _sha(SYSTEM_PROMPT.read_bytes()),
                "user_template_sha256": _sha(USER_TEMPLATE.read_bytes()),
                "tasks_sha256": _sha((ROOT / "prompts/sprint-baseline-v1/tasks.json").read_bytes()),
                "model_alias": "deepseek-flash", "expected_response_models": sorted(ALLOWED_MODELS),
                "endpoint": "https://api.deepseek.com/chat/completions",
                "thinking": config["thinking"], "temperature": config["temperature"],
                "max_tokens": config["max_output_tokens"],
                "response_format": {"type": "json_object"}, "assigned_rows": 16,
                "maximum_physical_requests": 16, "maximum_attempts_per_request": 1,
                "retries": 0, "replacements": 0, "external_fallback": False,
                "maximum_peak_cost_reserve_usd": config["budget_basis"]["max_cost_formula_usd"],
                "private_storage_acl_initial": acl}
    manifest_path = out / "run_manifest.json"
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("existing diagnostic run manifest differs; refusing to adopt or mutate")
    if not manifest_path.exists():
        if any(out.iterdir()):
            raise ValueError("refusing to adopt a nonempty output directory without a matching run manifest")
        _write_once(manifest_path, manifest_bytes)

    # Build and freeze every body before loading credentials or dispatching.
    known = {row.get("request_id"): row for row in
             (json.loads(line) for line in (out / "requests.jsonl").read_text(encoding="utf-8").splitlines())} if (out / "requests.jsonl").exists() else {}
    for item in requests:
        rid = item["schedule"]["request_id"]
        path = out / "requests" / f"{rid}.json"
        if path.exists() and _sha(path.read_bytes()) != item["request_sha256"]:
            raise ValueError("existing frozen diagnostic request bytes changed")
        if not path.exists():
            _write_once(path, item["body"])
        if rid not in known:
            _append(out / "requests.jsonl", {"event": "request_frozen", "request_id": rid,
                    "request_sha256": item["request_sha256"], "evidence_sha256": item["evidence_sha256"],
                    "case_ref": item["schedule"]["case_ref"], "task": item["schedule"]["task"],
                    "permission": item["schedule"]["permission"],
                    "baseline_id": item["schedule"]["baseline_id"],
                    "view_name": item["schedule"]["view_name"], "metadata_not_sent": True})
        elif known[rid].get("request_sha256") != item["request_sha256"]:
            raise ValueError("request ledger hash differs from the frozen diagnostic schedule")
    if set(known) - {item["schedule"]["request_id"] for item in requests}:
        raise ValueError("request ledger contains rows outside the frozen diagnostic schedule")

    attempt_path = out / "attempts.jsonl"
    attempt_rows = [json.loads(line) for line in attempt_path.read_text(encoding="utf-8").splitlines()] if attempt_path.exists() else []
    started_ids = {row["request_id"] for row in attempt_rows if row.get("event") == "attempt_started"}
    terminal_ids = {row["request_id"] for row in attempt_rows if row.get("event") == "attempt_terminal"}
    if started_ids - terminal_ids:
        raise ValueError("diagnostic has unresolved requests; never resend an attempted request")
    if len(started_ids) > MAX_REQUESTS or not started_ids <= {r["schedule"]["request_id"] for r in requests}:
        raise ValueError("diagnostic request cap or schedule identity is invalid")

    from scripts.run_full_research_monitor import _read_env_file
    env = _read_env_file(ROOT / ".env")
    if env.get("LLM_BASE_URL", "").rstrip("/") != "https://api.deepseek.com" or env.get("LLM_MODEL_ID") != "deepseek-flash":
        raise PermissionError("local provider configuration does not match the frozen DeepSeek endpoint/model")
    api_key = env.get("LLM_API_KEY", "")
    if not api_key:
        raise PermissionError("local provider credential is missing")
    ambient = os.environ.get("DEEPSEEK_API_KEY")
    if ambient and ambient != api_key:
        raise PermissionError("ambient API credential differs from the local authorized credential")

    # Conservative reserve from the frozen 8,192 input bytes/tokens and 512 output
    # tokens; reserve all 16 rows before the first dispatch, without refund/retry.
    reserve_usd = config["budget_basis"]["max_cost_formula_usd"]
    calculated_reserve = 16 * (config["max_input_tokens"] * config["peak_input_miss_usd_per_million"]
                               + config["max_output_tokens"] * config["peak_output_usd_per_million"]) / 1_000_000
    if abs(reserve_usd - calculated_reserve) > 1e-12 or reserve_usd > config["hard_cost_cap_usd"]:
        raise ValueError("diagnostic peak-price reserve exceeds the hard cost cap")
    os.environ["DEEPSEEK_API_KEY"] = api_key
    errors = []
    try:
        for item in requests:
            row = item["schedule"]
            rid = row["request_id"]
            if rid in started_ids:
                continue
            if len(started_ids) >= MAX_REQUESTS:
                raise RuntimeError("hard 16-request diagnostic cap reached before dispatch")
            _append(attempt_path, {"event": "attempt_started", "request_id": rid,
                    "attempt_index": 1, "request_sha256": item["request_sha256"],
                    "endpoint": manifest["endpoint"], "auth_header_saved": False,
                    "retry": False, "reserved_peak_cost_usd": reserve_usd / MAX_REQUESTS,
                    "started_utc": datetime.now(timezone.utc).isoformat()})
            started_ids.add(rid)
            started = time.perf_counter()
            response_bytes = None
            try:
                result = transport.urllib_transport(manifest["endpoint"], item["body"], api_key, 90)
                response_bytes = result.body
                response_path = out / "responses" / f"{rid}.json"
                _write_once(response_path, response_bytes)
                response = json.loads(response_bytes)
                returned = response.get("model")
                fingerprint = response.get("system_fingerprint")
                choices = response.get("choices")
                finish = choices[0].get("finish_reason") if isinstance(choices, list) and choices else None
                message = choices[0].get("message") if isinstance(choices, list) and choices else None
                content = message.get("content") if isinstance(message, dict) else None
                usage = response.get("usage") if isinstance(response.get("usage"), dict) else None
                parse_status = "not_attempted"
                citation_valid = None
                if result.status == 200 and returned not in ALLOWED_MODELS:
                    raise RuntimeError("returned model identity differs from the frozen allowlist")
                prediction = None
                if result.status == 200 and finish == "stop" and isinstance(content, str):
                    try:
                        prediction = parse_model_output(content, row["task"])
                    except Exception as exc:
                        parse_status = f"invalid_output:{type(exc).__name__}"
                    else:
                        parse_status = "complete_parseable"
                        citation_valid = provenance_gate(prediction, row["task"], item["evidence"])["citation_membership_valid"]
                        _append(out / "raw_predictions.jsonl", {"request_id": rid,
                                "raw_prediction": prediction, "citation_membership_valid": citation_valid,
                                "correctness_not_used_as_interface_gate": True})
                elif finish == "length":
                    parse_status = "truncated_length"
                else:
                    parse_status = "http_or_response_failure"
                response_hash = _sha(response_bytes)
                _append(attempt_path, {"event": "attempt_terminal", "request_id": rid,
                        "http_status": result.status, "response_sha256": response_hash,
                        "returned_model": returned, "system_fingerprint": fingerprint,
                        "finish_reason": finish, "usage": usage,
                        "parse_status": parse_status, "citation_membership_valid": citation_valid,
                        "elapsed_seconds": time.perf_counter() - started,
                        "safe_response_headers": result.safe_headers,
                        "auth_header_saved": False, "retry": False})
                if result.status in {401, 403}:
                    errors.append({"request_id": rid, "status": f"HTTP_ERROR_{result.status}"})
                    break
            except BaseException as exc:
                status = "INTERRUPTED_UNKNOWN" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else type(exc).__name__
                if response_bytes is not None and not (out / "responses" / f"{rid}.json").exists():
                    _write_once(out / "responses" / f"{rid}.json", response_bytes)
                _append(attempt_path, {"event": "attempt_terminal", "request_id": rid,
                        "http_status": None, "response_sha256": _sha(response_bytes) if response_bytes else None,
                        "status": status, "elapsed_seconds": time.perf_counter() - started,
                        "auth_header_saved": False, "retry": False})
                errors.append({"request_id": rid, "status": status})
                if isinstance(exc, (KeyboardInterrupt, SystemExit)) or "identity" in str(exc).casefold():
                    break
    finally:
        os.environ.pop("DEEPSEEK_API_KEY", None)
    attempts_after = [json.loads(line) for line in attempt_path.read_text(encoding="utf-8").splitlines()]
    terminals = [row for row in attempts_after if row.get("event") == "attempt_terminal"]
    parseable = sum(row.get("parse_status") == "complete_parseable" for row in terminals)
    return {"status": "DIAGNOSTIC_COLLECTED" if len(started_ids) == MAX_REQUESTS else "INCOMPLETE_NO_RESAMPLE",
            "assigned_rows": MAX_REQUESTS, "physical_requests": len(started_ids),
            "terminal_rows": len(terminals), "complete_parseable": parseable,
            "hard_request_cap": MAX_REQUESTS, "retries": 0, "replacements": 0,
            "peak_cost_reserve_usd": round(reserve_usd, 8), "errors": errors,
            "real_model_or_api_calls": len(started_ids), "raw_artifacts_private": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="explicit real-call switch; requires separate approval receipt")
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--authorization-receipt", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not args.live:
        raise PermissionError("Monitor recovery diagnostic is offline-by-default; --live and a matching approval are required")
    result = run(args.out, approval_id=args.approval_id, approval_receipt=args.authorization_receipt)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "DIAGNOSTIC_COLLECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
