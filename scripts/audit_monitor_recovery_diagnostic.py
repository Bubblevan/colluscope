#!/usr/bin/env python3
"""Independently replay raw bytes for one frozen Monitor recovery diagnostic."""

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

from colluscope.sprint_baselines import parse_model_output, provenance_gate  # noqa: E402
from scripts import run_monitor_recovery_diagnostic as builder  # noqa: E402
from scripts import run_sprint_monitor as transport  # noqa: E402

EXPECTED_OUT = (ROOT / "runs/full-research-execution-20261020/monitor/recovery_diagnostic").resolve()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _http_success(terminal: dict[str, Any]) -> bool:
    """Only HTTP 200 responses may count as completed monitor predictions."""
    return type(terminal.get("http_status")) is int and terminal["http_status"] == 200


def _verify_artifact_hashes(recorded: Any) -> None:
    if recorded != builder._artifact_hashes():
        raise ValueError("Monitor diagnostic source/config artifact hashes differ from the frozen manifest")


def audit(out: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    out = out.resolve()
    if EXPECTED_OUT not in out.parents:
        raise ValueError("diagnostic raw data must remain in the private ignored directory")
    manifest = json.loads((out / "run_manifest.json").read_bytes())
    if (manifest.get("schema_version") != "monitor-recovery-diagnostic-run-v1"
            or manifest.get("protocol_id") != "monitor-recovery-diagnostic-v1"
            or manifest.get("mode") != "live"
            or manifest.get("maximum_physical_requests") != 16
            or manifest.get("retries") != 0 or manifest.get("replacements") != 0):
        raise ValueError("diagnostic manifest is not the frozen real-request protocol")
    if manifest.get("config_sha256") != _sha(builder.CONFIG.read_bytes()) or manifest.get("schedule_sha256") != _sha(builder.SCHEDULE.read_bytes()):
        raise ValueError("diagnostic protocol or schedule changed after freeze")
    _verify_artifact_hashes(manifest.get("artifact_sha256"))
    requests = builder._build_requests()
    request_rows = [json.loads(line) for line in (out / "requests.jsonl").read_text(encoding="utf-8").splitlines()]
    attempts = [json.loads(line) for line in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines()]
    req_map = {row["request_id"]: row for row in request_rows if row.get("event") == "request_frozen"}
    if len(req_map) != len(request_rows) or set(req_map) != {item["schedule"]["request_id"] for item in requests}:
        raise ValueError("frozen request ledger does not exactly match all 16 schedule rows")
    starts = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_started"}
    terminals = {row["request_id"]: row for row in attempts if row.get("event") == "attempt_terminal"}
    if len(starts) != sum(row.get("event") == "attempt_started" for row in attempts) or len(terminals) != sum(row.get("event") == "attempt_terminal" for row in attempts):
        raise ValueError("duplicate request attempt or terminal event")
    if set(starts) != set(terminals) or len(starts) > 16:
        raise ValueError("diagnostic has an unterminalized attempt or exceeds its hard cap")
    item_by_id = {item["schedule"]["request_id"]: item for item in requests}
    cert_rows = []
    detail_rows = []
    for row in json.loads(builder.SCHEDULE.read_bytes())["rows"]:
        rid = row["request_id"]
        item = item_by_id[rid]
        req_path = out / "requests" / f"{rid}.json"
        request_bytes = req_path.read_bytes()
        request_hash = _sha(request_bytes)
        if (request_hash != item["request_sha256"]
                or req_map[rid].get("request_sha256") != request_hash):
            raise ValueError("raw request differs from the frozen payload or request ledger")
        payload = json.loads(request_bytes)
        if (set(payload) != {"model", "messages", "thinking", "temperature", "max_tokens", "response_format", "stream"}
                or payload.get("model") != "deepseek-flash"
                or payload.get("thinking") != {"type": "disabled"}
                or payload.get("response_format") != {"type": "json_object"}
                or payload.get("max_tokens") != 256 or payload.get("temperature") != 0.0):
            raise ValueError("raw request violates the frozen DeepSeek v2 payload contract")
        terminal = terminals.get(rid, {})
        started = starts.get(rid, {})
        response_path = out / "responses" / f"{rid}.json"
        response_hash = _sha(response_path.read_bytes()) if response_path.is_file() else None
        if terminal and terminal.get("response_sha256") != response_hash:
            raise ValueError("raw response hash differs from attempt terminal")
        finish = terminal.get("finish_reason")
        parseable = False
        citation_valid = None
        returned_model = terminal.get("returned_model")
        if response_hash is not None:
            response = json.loads(response_path.read_bytes())
            returned_model = response.get("model")
            choices = response.get("choices")
            message = choices[0].get("message") if isinstance(choices, list) and choices else None
            content = message.get("content") if isinstance(message, dict) else None
            finish = choices[0].get("finish_reason") if isinstance(choices, list) and choices else None
            if response.get("usage") != terminal.get("usage") or finish != terminal.get("finish_reason"):
                raise ValueError("attempt metadata differs from raw response usage or finish reason")
            if returned_model not in builder.ALLOWED_MODELS:
                raise ValueError("raw response model is outside the frozen model allowlist")
            if _http_success(terminal) and finish == "stop" and isinstance(content, str):
                try:
                    prediction = parse_model_output(content, row["task"])
                except Exception:
                    parseable = False
                else:
                    parseable = True
                    citation_valid = provenance_gate(prediction, row["task"], item["evidence"])["citation_membership_valid"]
        eligible = row.get("assessable_reference") is True
        cert_rows.append({"request_id": rid, "case_ref": row["case_ref"], "task": row["task"],
                          "permission": row["permission"], "baseline_id": row["baseline_id"],
                          "view_name": row["view_name"], "assessable": eligible,
                          "complete_parseable": parseable, "finish_reason": finish,
                          "request_sha256": request_hash, "response_sha256": response_hash,
                          "attempted": rid in starts, "returned_model": returned_model})
        detail_rows.append({"request_id": rid, "attempted": rid in starts,
                            "http_status": terminal.get("http_status"),
                            "finish_reason": finish, "returned_model": returned_model,
                            "complete_parseable": parseable, "citation_membership_valid": citation_valid,
                            "request_sha256": request_hash, "response_sha256": response_hash,
                            "input_tokens": (terminal.get("usage") or {}).get("prompt_tokens"),
                            "output_tokens": (terminal.get("usage") or {}).get("completion_tokens"),
                            "auth_header_saved": terminal.get("auth_header_saved", False)})
    parseable_count = sum(row["complete_parseable"] for row in cert_rows)
    length_count = sum(row["finish_reason"] == "length" for row in cert_rows)
    models = Counter(row["returned_model"] for row in cert_rows if row["returned_model"] is not None)
    fingerprints = Counter()
    for rid in starts:
        fingerprints[terminals[rid].get("system_fingerprint")] += 1
    certificate = {"schema_version": "monitor-recovery-pair-certificate-v1",
                   "protocol_id": "monitor-recovery-diagnostic-v1",
                   "schedule_sha256": manifest["schedule_sha256"],
                   "config_sha256": manifest["config_sha256"],
                   "max_requests": 16, "physical_requests": len(starts),
                   "complete_parseable_rows": parseable_count,
                   "length_terminations": length_count,
                   "rows": [{key: value for key, value in row.items()
                             if key not in {"attempted", "returned_model"}} for row in cert_rows]}
    summary = {"schema_version": "monitor-recovery-independent-audit-v1",
               "protocol_id": "monitor-recovery-diagnostic-v1",
               "assigned_rows": 16, "attempted_rows": len(starts), "terminal_rows": len(terminals),
               "parseable_rows": parseable_count, "length_terminations": length_count,
               "citation_valid_rows": sum(row["citation_membership_valid"] is True for row in detail_rows),
               "citation_assessable_rows": sum(row["citation_membership_valid"] is not None for row in detail_rows),
               "returned_model_counts": dict(models), "system_fingerprint_counts": dict(fingerprints),
               "retry_count": sum(row.get("retry") is not False for row in attempts if row.get("event") == "attempt_terminal"),
               "auth_header_saved_count": sum(row["auth_header_saved"] is not False for row in detail_rows),
               "rows": detail_rows, "certificate_sha256_inputs": "raw request/response hashes; no prediction labels included"}
    return summary, certificate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=builder.DEFAULT_OUT)
    args = parser.parse_args()
    summary, certificate = audit(args.run)
    for name, value in (("independent_audit.json", summary), ("monitor_certificate.json", certificate)):
        path = args.run / name
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        if path.exists() and path.read_bytes() != data:
            raise SystemExit(f"refusing to overwrite changed audit evidence: {path.name}")
        if not path.exists():
            path.write_bytes(data)
    print(json.dumps({"status": "AUDIT_COMPLETE", "assigned": 16,
                      "attempted": summary["attempted_rows"], "parseable": summary["parseable_rows"],
                      "length": summary["length_terminations"],
                      "certificate": "monitor_certificate.json"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
