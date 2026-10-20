#!/usr/bin/env python3
"""Independent no-call audit of a completed M4 v4 interface diagnostic."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from colluscope import m4_live_runtime as live  # noqa: E402
from colluscope.recovery_gates import m4_interface_diagnostic_gate  # noqa: E402
from scripts.run_m4_interface_diagnostic import (  # noqa: E402
    CONFIG, SCHEDULE, _artifact_hashes, _prompts,
)

EXPECTED_ROOT = (ROOT / "runs/m4/recovery-diagnostic-v1").resolve()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _http_success(terminal: dict[str, Any]) -> bool:
    """Independently reject JSON-shaped error pages as successful model actions."""
    return type(terminal.get("http_status")) is int and terminal["http_status"] == 200


def _verify_artifact_hashes(recorded: Any) -> None:
    if recorded != _artifact_hashes():
        raise ValueError("M4 diagnostic source/config artifact hashes differ from the frozen manifest")


def _strict_json(text: str) -> Any:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value
    return json.loads(text, object_pairs_hook=unique)


def _extract_action(message: dict[str, Any]) -> tuple[str, str]:
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("missing content field")
    try:
        _strict_json(content)
        return content, "content_json"
    except (json.JSONDecodeError, ValueError):
        if not content.startswith("<think>") or content.count("<think>") != 1 or content.count("</think>") != 1:
            raise ValueError("content does not match the exact single-wrapper grammar")
        close = content.find("</think>")
        inner = content[len("<think>"):close]
        if "<think>" in inner or "</think>" in inner:
            raise ValueError("nested or repeated reasoning wrapper")
        candidate = content[close + len("</think>"):].strip()
        _strict_json(candidate)
        return candidate, "single_leading_think_wrapper"


def _valid_action(action: Any, kind: str) -> bool:
    if not isinstance(action, dict):
        return False
    if kind == "message":
        return (action == {"type": "no_message"}
                or (set(action) == {"type", "text"} and action.get("type") == "send_message"
                    and isinstance(action.get("text"), str) and 1 <= len(action["text"]) <= 1000))
    if kind == "ballot":
        assignment = action.get("assignment")
        return (set(action) == {"type", "assignment"} and action.get("type") == "ballot"
                and isinstance(assignment, dict) and set(assignment) == {"A", "B", "C"}
                and set(assignment.values()) == {"T1", "T2", "T3"})
    if kind == "positive_control":
        return set(action) == {"choice"} and action.get("choice") in {"T1", "T2"}
    return False


def audit(out: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    out = out.resolve()
    if EXPECTED_ROOT not in out.parents:
        raise ValueError("diagnostic artifacts must remain under the private ignored M4 root")
    manifest = json.loads((out / "diagnostic_manifest.json").read_bytes())
    if (manifest.get("schema_version") != "m4-interface-diagnostic-run-v1"
            or manifest.get("protocol_id") != "m4-interface-diagnostic-v1"
            or manifest.get("execution_mode") != "live_local_llama_cpp"
            or manifest.get("historical_behavioral_episode") is not False
            or manifest.get("generation_attempt_limit") != 18
            or manifest.get("retry_limit") != 0 or manifest.get("replacement_limit") != 0
            or manifest.get("config_sha256") != live.sha_file(CONFIG)
            or manifest.get("schedule_sha256") != live.sha_file(SCHEDULE)):
        raise ValueError("M4 diagnostic manifest differs from the frozen v4 schedule/config")
    _verify_artifact_hashes(manifest.get("artifact_sha256"))
    receipt_ref = manifest.get("authorization_receipt", {})
    receipt_path = (ROOT / receipt_ref.get("path", "")).resolve()
    if not receipt_path.is_file() or live.sha_file(receipt_path) != receipt_ref.get("sha256"):
        raise ValueError("diagnostic approval receipt is missing or changed")
    rows = _prompts()
    schedule = json.loads(SCHEDULE.read_bytes())["rows"]
    expected_prompts = {row["request_id"]: row for row in rows}
    request_events = {row["request_id"]: row for row in live.read_jsonl(out / "requests.jsonl")}
    attempts = live.read_jsonl(out / "attempts.jsonl")
    starts = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_started"}
    terminals = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_terminal"}
    if (set(request_events) != set(expected_prompts) or len(request_events) != len(rows)
            or set(starts) != set(terminals) or set(starts) - set(expected_prompts)):
        raise ValueError("request/attempt ledgers do not exactly match the frozen 18-row schedule")
    audit_rows = []
    response_hashes = {}
    for request in rows:
        rid = request["request_id"]
        request_path = out / "requests" / f"{rid}.json"
        meta_path = out / "requests" / f"{rid}.meta.json"
        request_bytes = request_path.read_bytes()
        body_hash = _sha(request_bytes)
        meta = json.loads(meta_path.read_bytes())
        payload = json.loads(request_bytes)
        if (body_hash != request_events[rid].get("request_body_sha256")
                or live.sha_file(meta_path) != request_events[rid].get("request_metadata_sha256")
                or meta.get("request_body_sha256") != body_hash
                or meta.get("full_rendered_prompt") != request["prompt"]
                or payload.get("messages") != meta.get("messages")
                or meta.get("prompt_sha256") != live.sha(request["prompt"].encode("utf-8"))):
            raise ValueError("frozen request bytes or prompt differ from independent schedule replay")
        if (payload.get("reasoning_format") != "deepseek"
                or payload.get("model") != "colluscope-qwen3-8b-q4km"
                or set(payload) != {"model", "messages", "temperature", "top_p", "top_k", "min_p",
                                    "seed", "max_tokens", "stream", "cache_prompt", "response_format",
                                    "chat_template_kwargs", "reasoning_format"}):
            raise ValueError("raw diagnostic request violates the frozen v4 M4 wire contract")
        terminal = terminals.get(rid, {})
        response_path = out / "responses" / f"{rid}.body"
        response_hash = _sha(response_path.read_bytes()) if response_path.is_file() else None
        response_hashes[rid] = response_hash
        schema_valid = False
        source = None
        parse_error = None
        if terminal:
            if terminal.get("retry") is not False or terminal.get("auth_header_saved") is not False:
                raise ValueError("attempt retry or credential persistence detected")
        if response_hash is not None:
            if response_hash != terminal.get("response_body_sha256"):
                raise ValueError("raw response bytes differ from terminal attempt hash")
            response_meta_path = out / "responses" / f"{rid}.meta.json"
            if (not response_meta_path.is_file()
                    or live.sha_file(response_meta_path) != terminal.get("response_metadata_sha256")):
                raise ValueError("response parser receipt is missing or changed")
            try:
                if terminal.get("status") != "COMPLETED" or not _http_success(terminal):
                    raise ValueError("attempt did not terminalize as COMPLETED")
                response = json.loads(response_path.read_bytes())
                if response.get("model") != manifest["model"].get("id"):
                    raise ValueError("raw response model identity differs from frozen model alias")
                choice = response["choices"][0]
                message = choice["message"]
                action_text, source = _extract_action(message)
                action = _strict_json(action_text)
                if not _valid_action(action, request["action_kind"]):
                    raise ValueError("action has invalid or contradictory fields")
                if choice.get("finish_reason") != "stop":
                    raise ValueError("generation did not stop normally")
                import jsonschema
                jsonschema.validate(action, payload["response_format"]["schema"])
                schema_valid = True
                receipt = json.loads(response_meta_path.read_bytes())
                decision = receipt.get("action_interface", {})
                if (decision.get("source") != source
                        or decision.get("action_text_sha256") != live.sha(action_text.encode("utf-8"))):
                    raise ValueError("stored parser decision differs from independent action extraction")
            except Exception as exc:
                parse_error = type(exc).__name__
                schema_valid = False
        audit_rows.append({"request_id": rid, "action_kind": request["action_kind"],
                           "terminal_status": terminal.get("status", "NOT_ATTEMPTED"),
                           "parse_error_class": parse_error,
                           "schema_valid": schema_valid, "request_sha256": body_hash,
                           "response_sha256": response_hash})
    report = {"schema_version": "m4-interface-diagnostic-independent-audit-v1",
              "protocol_id": "m4-interface-diagnostic-v1", "assigned_generations": 18,
              "physical_requests": len(starts), "terminal_requests": len(terminals),
              "retry_count": sum(row.get("retry") is not False for row in terminals.values()),
              "rows": audit_rows}
    gate = m4_interface_diagnostic_gate(audit_rows, schedule, physical_requests=len(starts),
                                        terminal_requests=len(terminals), retries=report["retry_count"])
    report["gate"] = gate
    cert = {"schema_version": "m4-interface-diagnostic-certificate-v1",
            "protocol_id": "m4-interface-diagnostic-v1",
            "config_sha256": manifest["config_sha256"], "schedule_sha256": manifest["schedule_sha256"],
            "authorized_generation_cap": 18,
            "physical_requests": len(starts), "terminal_requests": len(terminals),
            "schema_valid_counts": gate["schema_valid_by_action_kind"],
            "gate_status": gate["status"],
            "row_hashes": [{"request_id": row["request_id"], "request_sha256": row["request_sha256"],
                            "response_sha256": row["response_sha256"]} for row in audit_rows]}
    return report, cert


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=EXPECTED_ROOT / "run")
    args = parser.parse_args()
    report, cert = audit(args.run)
    for name, value in (("independent_audit.json", report), ("diagnostic_certificate.json", cert)):
        path = args.run / name
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        if path.exists() and path.read_bytes() != data:
            raise SystemExit(f"refusing to overwrite changed evidence: {path.name}")
        if not path.exists():
            path.write_bytes(data)
    print(json.dumps({"status": report["gate"]["status"],
                      "physical_requests": report["physical_requests"],
                      "valid_by_action_kind": report["gate"]["schema_valid_by_action_kind"]}, sort_keys=True))
    return 0 if report["gate"]["status"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
