#!/usr/bin/env python3
"""Offline, privacy-preserving forensic summary of the historical M4/Monitor failures."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_M4 = ROOT / "runs/m4/full-research-execution-20261020-run03"
DEFAULT_MONITOR = ROOT / "runs/full-research-execution-20261020/monitor"
DEFAULT_OUT = ROOT / "docs/results/m4-monitor-recovery-20261020/historical_forensic_audit-v2.json"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return False
    return True


def audit_m4(m4_root: Path) -> dict[str, Any]:
    requests = {row["request_id"]: row for row in
                (json.loads(line) for line in (m4_root / "requests.jsonl").read_text(encoding="utf-8").splitlines())}
    attempts = [json.loads(line) for line in (m4_root / "attempts.jsonl").read_text(encoding="utf-8").splitlines()]
    terminal = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_terminal"}
    cases = []
    for path in sorted((m4_root / "responses").glob("*-message-A.body")):
        request_id = path.name[:-len(".body")]
        request = requests.get(request_id)
        if request is None:
            raise ValueError(f"M4 raw response has no request ledger row: {path.name}")
        raw = path.read_bytes()
        response = json.loads(raw)
        choices = response.get("choices")
        message = choices[0].get("message", {}) if isinstance(choices, list) and choices else {}
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            suffix = {"classification": "missing_assistant_content"}
            post_text = ""
        else:
            open_count, close_count = content.count("<think>"), content.count("</think>")
            if open_count == 1 and close_count == 1 and content.startswith("<think>"):
                close = content.find("</think>")
                post_text = content[close + len("</think>"):].strip()
                try:
                    post_value = json.loads(post_text)
                except json.JSONDecodeError:
                    suffix = {"classification": "invalid_json_after_single_wrapper"}
                else:
                    schema = json.loads((m4_root / "requests" / f"{request_id}.json").read_bytes())["response_format"]["schema"]
                    try:
                        import jsonschema
                        jsonschema.validate(post_value, schema)
                    except Exception:
                        suffix = {"classification": "json_after_wrapper_but_schema_invalid"}
                    else:
                        suffix = {"classification": "complete_schema_valid_action_after_wrapper",
                                  "action_type": post_value.get("type", "positive_control"),
                                  "schema_valid": True,
                                  "action_sha256": _sha(post_text.encode("utf-8")),
                                  "action_characters": len(post_text)}
            elif open_count or close_count:
                post_text = ""
                suffix = {"classification": "malformed_or_multiple_reasoning_wrapper"}
            else:
                post_text = content
                suffix = {"classification": "content_without_reasoning_wrapper",
                          "json_valid": _is_json(content)}
        cases.append({
            "request_id_sha256": _sha(request_id.encode("utf-8")),
            "request_body_sha256": request.get("request_body_sha256"),
            "response_body_sha256": _sha(raw),
            "attempt_status": terminal.get(request_id, {}).get("status"),
            "http_status": terminal.get(request_id, {}).get("http_status"),
            "finish_reason": terminal.get(request_id, {}).get("finish_reason"),
            "reasoning_content_field_present": isinstance(message, dict) and "reasoning_content" in message,
            "think_open_count": content.count("<think>") if isinstance(content, str) else None,
            "think_close_count": content.count("</think>") if isinstance(content, str) else None,
            "reasoning_characters": (content[7:content.find("</think>")].__len__()
                                      if isinstance(content, str) and content.startswith("<think>")
                                      and content.count("</think>") == 1 else None),
            **suffix,
        })
    return {
        "source_root": m4_root.relative_to(ROOT).as_posix(),
        "run_manifest_sha256": _sha((m4_root / "run_manifest.json").read_bytes()),
        "assigned_group_count": 24,
        "message_a_response_count": len(cases),
        "historical_status_counts": dict(Counter(row.get("status") for row in terminal.values())),
        "wrapper_classification_counts": dict(Counter(row["classification"] for row in cases)),
        "schema_valid_after_wrapper": sum(row.get("schema_valid") is True for row in cases),
        "action_type_counts_after_wrapper": dict(Counter(row.get("action_type") for row in cases
                                                          if row.get("schema_valid"))),
        "reasoning_content_field_count": sum(row["reasoning_content_field_present"] for row in cases),
        "cases": cases,
    }


def audit_monitor(monitor_root: Path) -> dict[str, Any]:
    phase_rows = []
    totals = Counter()
    for phase in ("scripted_controls", "m4_trace_eval", "matched_worlds"):
        root = monitor_root / phase
        requests_dir, responses_dir = root / "requests", root / "responses"
        attempts = [json.loads(line) for line in (root / "attempts.jsonl").read_text(encoding="utf-8").splitlines()]
        by_request = {}
        for event in attempts:
            by_request.setdefault(event["request_id"], {})[event["event"]] = event
        settings = Counter()
        finish_counts = Counter()
        parseable_by_finish = Counter()
        completion_tokens = []
        json_parseable = 0
        rows = []
        for request_id in sorted(by_request):
            event = by_request[request_id].get("attempt_started", {})
            terminal = by_request[request_id].get("attempt_terminal", {})
            req_path = requests_dir / f"{request_id}.json"
            res_path = responses_dir / f"{request_id}.json"
            req_raw = req_path.read_bytes()
            payload = json.loads(req_raw)
            response_raw = res_path.read_bytes()
            response = json.loads(response_raw)
            choice = response.get("choices", [{}])[0]
            finish = choice.get("finish_reason")
            usage = response.get("usage") or {}
            message = choice.get("message") or {}
            content = message.get("content")
            if isinstance(content, str) and _is_json(content):
                json_parseable += 1
                parseable_by_finish[str(finish)] += 1
            settings["payload_keys=" + ",".join(sorted(payload))] += 1
            settings["thinking=" + str(payload.get("thinking", "OMITTED"))] += 1
            settings["response_format=" + str(payload.get("response_format", "OMITTED"))] += 1
            settings["max_tokens=" + str(payload.get("max_tokens"))] += 1
            settings["temperature=" + str(payload.get("temperature"))] += 1
            finish_counts[str(finish)] += 1
            completion = usage.get("completion_tokens")
            if type(completion) is int:
                completion_tokens.append(completion)
            row = {"request_id_sha256": _sha(request_id.encode("utf-8")),
                   "request_sha256": _sha(req_raw), "response_sha256": _sha(response_raw),
                   "http_status": terminal.get("http_status"),
                   "terminal_status": terminal.get("transport_status"),
                   "finish_reason": finish, "usage_prompt_tokens": usage.get("prompt_tokens"),
                   "usage_completion_tokens": completion,
                   "content_json_parseable": isinstance(content, str) and _is_json(content),
                   "payload_model": payload.get("model"),
                   "payload_settings": {key: payload.get(key, "OMITTED") for key in
                                        ("thinking", "response_format", "max_tokens", "temperature")}}
            rows.append(row)
        totals["requests"] += len(rows)
        totals["completion_length"] += finish_counts.get("length", 0)
        totals["completion_stop"] += finish_counts.get("stop", 0)
        totals["parseable"] += json_parseable
        phase_rows.append({"phase_id": phase, "request_count": len(rows),
                           "request_settings_counts": dict(settings),
                           "finish_reason_counts": dict(finish_counts),
                           "raw_content_json_parseable_count": json_parseable,
                           "raw_content_json_parseable_by_finish": dict(parseable_by_finish),
                           "complete_stop_json_parseable_count": parseable_by_finish.get("stop", 0),
                           "completion_tokens": {"count": len(completion_tokens),
                                                 "minimum": min(completion_tokens) if completion_tokens else None,
                                                 "maximum": max(completion_tokens) if completion_tokens else None,
                                                 "median": sorted(completion_tokens)[len(completion_tokens)//2]
                                                 if completion_tokens else None},
                           "request_response_inventory": rows})
    return {"source_root": monitor_root.relative_to(ROOT).as_posix(),
            "phase_count": len(phase_rows), "total_requests": totals["requests"],
            "total_finish_reason_counts": {"length": totals["completion_length"], "stop": totals["completion_stop"]},
            "total_raw_content_json_parseable": totals["parseable"],
            "total_complete_stop_json_parseable": sum(p["complete_stop_json_parseable_count"] for p in phase_rows),
            "phases": phase_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--m4", type=Path, default=DEFAULT_M4)
    parser.add_argument("--monitor", type=Path, default=DEFAULT_MONITOR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = {"schema_version": "m4-monitor-failure-forensics-v1",
              "historical_artifacts_modified": False,
              "m4": audit_m4(args.m4), "monitor": audit_monitor(args.monitor)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if args.out.exists() and args.out.read_bytes() != data:
        raise SystemExit(f"refusing to overwrite a different forensic report: {args.out}")
    if not args.out.exists():
        args.out.write_bytes(data)
    print(json.dumps({"status": "PASS_OFFLINE_FORENSIC_AUDIT", "out": args.out.relative_to(ROOT).as_posix(),
                      "m4_responses": result["m4"]["message_a_response_count"],
                      "m4_schema_valid_wrapper_actions": result["m4"]["schema_valid_after_wrapper"],
                      "monitor_requests": result["monitor"]["total_requests"],
                      "monitor_length_terminations": result["monitor"]["total_finish_reason_counts"]["length"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
