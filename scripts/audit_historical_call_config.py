#!/usr/bin/env python3
"""Read-only, sanitized count/config audit of retained M4 DeepSeek payloads."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


POPULATIONS = {
    "agent": "agent",
    "monitor": "monitor",
    "pilot_agent": "pilot/agent-strict-function-calling",
    "pilot_monitor": "pilot/monitor-strict-function-calling",
}


class AuditFailure(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_json(path: Path, code: str) -> tuple[Any, bytes]:
    try:
        raw = path.read_bytes()
        return json.loads(raw), raw
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditFailure(code) from exc


def audit_population(run_root: Path, name: str, relative: str) -> dict[str, Any]:
    directory = run_root / relative
    request_dir, response_dir = directory / "requests", directory / "responses"
    request_paths = sorted(request_dir.glob("*.bin"))
    response_paths = sorted(response_dir.glob("*.bin"))
    request_ids = {path.stem for path in request_paths}
    response_ids = {path.stem for path in response_paths}
    if request_ids != response_ids:
        raise AuditFailure("REQUEST_RESPONSE_ID_SET_MISMATCH_" + name.upper())

    model_aliases: Counter[str] = Counter()
    thinking_values: Counter[str] = Counter()
    temperatures: Counter[str] = Counter()
    max_tokens: Counter[str] = Counter()
    http_statuses: Counter[str] = Counter()
    finish_reasons: Counter[str] = Counter()
    fingerprints: Counter[str] = Counter()
    for request_path in request_paths:
        request_id = request_path.stem
        request, request_bytes = _load_json(request_path, "REQUEST_JSON_INVALID_" + name.upper())
        request_meta, _ = _load_json(request_dir / f"{request_id}.meta.json",
                                     "REQUEST_META_INVALID_" + name.upper())
        response_path = response_dir / f"{request_id}.bin"
        response, response_bytes = _load_json(response_path, "RESPONSE_JSON_INVALID_" + name.upper())
        response_meta, _ = _load_json(response_dir / f"{request_id}.meta.json",
                                      "RESPONSE_META_INVALID_" + name.upper())
        if (request_meta.get("request_id") != request_id
                or response_meta.get("request_id") != request_id
                or request_meta.get("request_sha256") != _sha(request_bytes)
                or response_meta.get("request_sha256") != _sha(request_bytes)
                or response_meta.get("response_sha256") != _sha(response_bytes)):
            raise AuditFailure("PAYLOAD_HASH_OR_ID_MISMATCH_" + name.upper())
        if request_meta.get("auth_header_saved") is not False or response_meta.get("auth_header_saved") is not False:
            raise AuditFailure("AUTH_HEADER_STORAGE_FLAG_INVALID_" + name.upper())
        if request.get("model") != response_meta.get("returned_model"):
            raise AuditFailure("REQUEST_RESPONSE_MODEL_MISMATCH_" + name.upper())
        choices = response.get("choices")
        if (not isinstance(choices, list) or len(choices) != 1
                or choices[0].get("finish_reason") != response_meta.get("finish_reason")):
            raise AuditFailure("RESPONSE_FINISH_REASON_MISMATCH_" + name.upper())
        model_aliases[str(request.get("model"))] += 1
        thinking_values[json.dumps(request.get("thinking", "<absent>"),
                                   sort_keys=True, separators=(",", ":"))] += 1
        temperatures[str(request.get("temperature", "<absent>"))] += 1
        max_tokens[str(request.get("max_tokens", "<absent>"))] += 1
        http_statuses[str(response_meta.get("http_status", "<absent>"))] += 1
        finish_reasons[str(response_meta.get("finish_reason", "<absent>"))] += 1
        fingerprints[str(response_meta.get("system_fingerprint", "<absent>"))] += 1

    return {
        "request_payload_files": len(request_paths),
        "matched_response_payload_files": len(response_paths),
        "model_aliases": dict(model_aliases),
        "thinking_values": dict(thinking_values),
        "temperatures": dict(temperatures),
        "max_tokens": dict(max_tokens),
        "http_statuses": dict(http_statuses),
        "finish_reasons": dict(finish_reasons),
        "system_fingerprint_count": len(fingerprints),
        "auth_headers_saved": False,
    }


def audit(run_root: Path) -> dict[str, Any]:
    populations = {
        name: audit_population(run_root, name, relative)
        for name, relative in POPULATIONS.items()
    }
    total_requests = sum(row["request_payload_files"] for row in populations.values())
    total_responses = sum(row["matched_response_payload_files"] for row in populations.values())
    return {
        "status": "PASS_HISTORICAL_PAYLOAD_METADATA_AUDIT",
        "populations": populations,
        "total_request_payload_files": total_requests,
        "total_matched_response_payload_files": total_responses,
        "physical_request_response_pairs": total_requests,
        "all_http_responses_200": all(
            set(row["http_statuses"]) == {"200"} for row in populations.values()
            if row["request_payload_files"] > 0),
        "all_finish_reasons_tool_calls": all(
            set(row["finish_reasons"]) == {"tool_calls"} for row in populations.values()
            if row["request_payload_files"] > 0),
        "model_calls_made_by_auditor": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path,
                        help="Local ignored historical run root; read-only")
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.run), sort_keys=True))
        return 0
    except AuditFailure as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
