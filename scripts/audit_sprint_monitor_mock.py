#!/usr/bin/env python3
"""Independently verify the saved B2-B5 offline Mock dispatch artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts import run_sprint_monitor as monitor  # noqa: E402
from scripts.local_llama_security import verify_private_directory_acl  # noqa: E402


class AuditFailure(RuntimeError):
    pass


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise AuditFailure(f"blank JSONL row at {path}:{number}")
        rows.append(json.loads(line))
    return rows


def audit(run: Path, *, output: Path | None = None) -> dict[str, Any]:
    schedule = monitor.build_schedule()
    expected = {row.request_id: row for row in schedule}
    progress = _read_jsonl(run / "progress.jsonl")
    attempts = _read_jsonl(run / "attempts.jsonl")
    starts = [row for row in attempts if row.get("event") == "attempt_started"]
    ends = [row for row in attempts if row.get("event") == "attempt_terminal"]
    progress_by_id = {row["request_id"]: row for row in progress}
    start_by_id = {row["request_id"]: row for row in starts}
    end_by_id = {row["request_id"]: row for row in ends}
    request_files = {path.stem: path for path in (run / "requests").glob("*.json")}
    response_files = {path.stem: path for path in (run / "responses").glob("*.json")}
    if not (len(expected) == len(progress_by_id) == len(start_by_id) == len(end_by_id)
            == len(request_files) == len(response_files) == 280):
        raise AuditFailure("frozen schedule, progress, attempts, requests or responses do not reconcile to 280 rows")
    if set(expected) != set(progress_by_id) or set(expected) != set(request_files) or set(expected) != set(response_files):
        raise AuditFailure("saved logical request IDs differ from frozen schedule")
    total_bytes = 0
    for request_id, built in expected.items():
        request_bytes = request_files[request_id].read_bytes()
        response_bytes = response_files[request_id].read_bytes()
        request_json = json.loads(request_bytes)
        response_json = json.loads(response_bytes)
        if request_bytes != monitor._json_bytes(built.http_payload):
            raise AuditFailure(f"request bytes differ from the frozen payload: {request_id}")
        if monitor._sha(request_bytes) != built.body_sha256:
            raise AuditFailure(f"payload hash mismatch: {request_id}")
        if b"Authorization" in request_bytes or b"Bearer " in request_bytes or b"Authorization" in response_bytes:
            raise AuditFailure("authentication material is present in a raw request/response")
        if progress_by_id[request_id]["status"] != "COMPLETED":
            raise AuditFailure("offline mock row is not terminal-completed")
        if start_by_id[request_id]["body_sha256"] != built.body_sha256 or end_by_id[request_id]["body_sha256"] != built.body_sha256:
            raise AuditFailure("attempt ledger body hash does not link to the frozen request")
        if start_by_id[request_id]["auth_header_saved"] is not False or end_by_id[request_id]["auth_header_saved"] is not False:
            raise AuditFailure("attempt ledger does not attest auth-header exclusion")
        if response_json.get("choices", [{}])[0].get("finish_reason") not in {"stop", "end_turn"}:
            raise AuditFailure("mock response does not have an allowed terminal reason")
        if response_json.get("system_fingerprint") != "offline-mock-not-a-model":
            raise AuditFailure("mock response identity marker differs")
        if progress_by_id[request_id]["response_sha256"] != monitor._sha(response_bytes):
            raise AuditFailure("response hash does not match its progress receipt")
        if request_json != built.http_payload:
            raise AuditFailure("decoded raw HTTP body differs from scheduled request")
        total_bytes += len(request_bytes)
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    if (summary["real_model_or_api_calls"] != 0 or summary["retries"] != 0
            or summary["logical_http_requests"] != 280 or summary["physical_http_attempts"] != 280
            or summary["mock_is_behavior_evidence"] is not False
            or summary["reserved_peak_cost_usd"] > 1.0):
        raise AuditFailure("run summary violates offline, retry, count, cost or evidence scope")
    if summary["request_body_bytes_total"] != total_bytes:
        raise AuditFailure("summary request byte total differs from raw request files")
    acl = verify_private_directory_acl(run)
    inventory = []
    for path in sorted(run.rglob("*")):
        if path.is_file():
            inventory.append((path.relative_to(run).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    inventory_material = "\n".join(f"{path}\0{digest}" for path, digest in inventory).encode("utf-8")
    receipt = {
        "schema_version": "sprint-monitor-mock-independent-audit-v1",
        "status": "PASS_OFFLINE_MOCK_DISPATCH_REPLAY_ONLY",
        "assigned_rows": 280, "terminal_rows": 280,
        "request_response_attempt_links_verified": 280,
        "raw_request_files": len(request_files), "raw_response_files": len(response_files),
        "request_body_bytes_replayed": total_bytes,
        "reserved_peak_cost_usd": summary["reserved_peak_cost_usd"],
        "hard_cost_ceiling_usd": 1.0,
        "real_model_or_api_calls": 0, "external_network_calls": 0,
        "retries": 0, "auth_headers_saved": False,
        "raw_private_tree_acl_verified": acl.get("verified") is True,
        "artifact_file_count": len(inventory),
        "artifact_inventory_sha256": hashlib.sha256(inventory_material).hexdigest(),
        "claim_scope": "runtime and artifact integrity only; Mock responses are not monitor evidence",
    }
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "runs/sprint-monitor/mock-e2e-v1")
    parser.add_argument("--out", type=Path, default=ROOT / "docs/results/sprint-execution-readiness/sprint-monitor-mock-audit.json")
    args = parser.parse_args()
    print(json.dumps(audit(args.run, output=args.out), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
