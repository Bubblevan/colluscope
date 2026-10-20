#!/usr/bin/env python3
"""Execute exactly one frozen, user-authorized DeepSeek Monitor phase."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.monitor_aggregate_budget import AggregateBudget  # noqa: E402
from colluscope.recovery_gates import m4_behavior_dependency, monitor_pair_gate  # noqa: E402
from scripts import prepare_full_research_monitor as freeze  # noqa: E402
from scripts import run_sprint_monitor as monitor  # noqa: E402
from scripts.local_llama_security import verify_private_directory_acl  # noqa: E402

RUN_ROOT = ROOT / "runs/full-research-execution-20261020/monitor"
LEDGER_PATH = RUN_ROOT / "global_budget_ledger.jsonl"
M4_SOURCE_RUN = ROOT / "runs/m4/full-research-execution-20261020-run03"
M4_AUDIT = ROOT / "docs/results/full-research-execution-20261020/m4_independent_trace_audit.json"
RECOVERY_MONITOR_SCHEDULE = ROOT / "configs/monitor-recovery-diagnostic-v1.json"
RECOVERY_MONITOR_CERTIFICATE = RUN_ROOT / "recovery_diagnostic/monitor_certificate.json"


def _dependency_result(phase: str) -> dict | None:
    """Fail closed before credential loading or transport on unusable upstream evidence."""
    if phase == "m4_trace_eval":
        if not M4_SOURCE_RUN.is_dir() or not M4_AUDIT.is_file():
            gate = {"status": "NOT_RUN", "failure_reasons": ["independent_m4_trace_audit_missing"]}
            source_hashes = {}
        else:
            episodes = monitor._read_jsonl(M4_SOURCE_RUN / "episodes.jsonl")
            audit = json.loads(M4_AUDIT.read_bytes())
            completed = [row for row in episodes if row.get("terminal_status") == "COMPLETED"
                         and len([ballot for ballot in row.get("researcher_B", {}).get("ballots", [])
                                  if ballot.get("stage") == "baseline"]) == 3
                         and isinstance(row.get("researcher_B", {}).get("settlement"), dict)]
            gate = m4_behavior_dependency(audit, assigned_episode_count=len(episodes),
                                          completed_valid_ballot_episodes=len(completed))
            source_hashes = {"episodes_sha256": __import__("hashlib").sha256(
                (M4_SOURCE_RUN / "episodes.jsonl").read_bytes()).hexdigest(),
                "audit_sha256": __import__("hashlib").sha256(M4_AUDIT.read_bytes()).hexdigest()}
        if gate["status"] != "GO":
            return {"phase_id": phase, "status": "NOT_RUN", "real_model_or_api_calls": 0,
                    "dependency_gate": gate, "source_sha256": source_hashes,
                    "reason": "M4 behavior monitor requires raw linked ballots and independently replayed settlements"}
    elif phase == "matched_worlds":
        if not RECOVERY_MONITOR_CERTIFICATE.is_file():
            return {"phase_id": phase, "status": "NOT_RUN", "real_model_or_api_calls": 0,
                    "dependency_gate": {"status": "NOT_RUN",
                                         "failure_reasons": ["paired_assessable_B4_B5_diagnostic_certificate_missing"]},
                    "reason": "Full B4/B5 comparison requires a completed paired positive and hard-negative diagnostic"}
        schedule = json.loads(RECOVERY_MONITOR_SCHEDULE.read_bytes())
        cert = json.loads(RECOVERY_MONITOR_CERTIFICATE.read_bytes())
        schedule_hash = __import__("hashlib").sha256(RECOVERY_MONITOR_SCHEDULE.read_bytes()).hexdigest()
        gate = monitor_pair_gate(cert, schedule["rows"], schedule_sha256=schedule_hash)
        if gate["status"] != "GO":
            return {"phase_id": phase, "status": "NOT_RUN", "real_model_or_api_calls": 0,
                    "dependency_gate": gate,
                    "reason": "Full B4/B5 comparison remains blocked until paired diagnostic rows pass"}
    return None


def _read_env_file(path: Path) -> dict[str, str]:
    values = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        if item.startswith("export "):
            item = item[len("export "):].lstrip()
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]
        if key in values:
            raise RuntimeError("duplicate key name in local provider environment file")
        values[key] = value
    return values


def _install_secret_in_memory() -> str:
    values = _read_env_file(ROOT / ".env")
    if values.get("LLM_BASE_URL", "").rstrip("/") != "https://api.deepseek.com":
        raise RuntimeError("local .env base URL is not the official DeepSeek API host")
    if values.get("LLM_MODEL_ID") != "deepseek-flash":
        raise RuntimeError("local .env model ID differs from the authorized DeepSeek Flash alias")
    secret = values.get("LLM_API_KEY", "")
    if not secret:
        raise RuntimeError("local .env does not contain the required authorized provider credential")
    ambient = os.environ.get("DEEPSEEK_API_KEY")
    if ambient and ambient != secret:
        raise RuntimeError("ambient DeepSeek credential differs from the local .env credential")
    os.environ["DEEPSEEK_API_KEY"] = secret
    return "loaded"


def execute(phase: str, freeze_dir: Path, out: Path) -> dict:
    config_path = freeze.PHASE_CONFIGS[phase]
    config = monitor._load_config(config_path)
    dependency = _dependency_result(phase)
    if dependency is not None:
        return dependency
    if config["authorization_id"] != freeze.EXECUTION_ID:
        raise RuntimeError("enabled Monitor config does not carry the explicit task authorization ID")
    if not config["live_dispatch_enabled"]:
        raise RuntimeError("phase is not explicitly enabled")
    plan_audit = freeze.verify_plan(freeze_dir, config_path)
    if plan_audit["request_count"] != freeze.PHASE_COUNTS[phase]:
        raise RuntimeError("frozen phase plan request count differs from approved cap")
    root_acl = verify_private_directory_acl(RUN_ROOT)
    if root_acl.get("verified") is not True:
        raise PermissionError("aggregate Monitor run root ACL is not verified")
    ledger = AggregateBudget(LEDGER_PATH, freeze.EXECUTION_ID)
    budget_before = ledger.summary()
    requests = freeze.load_plan(freeze_dir, config_path)
    if len(requests) != freeze.PHASE_COUNTS[phase]:
        raise RuntimeError("loaded frozen schedule differs from the approved phase cap")
    # Fail closed before transport if this phase's remaining full schedule cannot
    # fit the durable aggregate ledger's phase and total reservations.
    existing_phase = budget_before["per_phase"][phase]
    local_attempts = monitor._read_jsonl(out / "attempts.jsonl")
    started_ids = {row["request_id"] for row in local_attempts if row.get("event") == "attempt_started"}
    pending = [request for request in requests if request.request_id not in started_ids]
    if len(existing_phase_reservations := [
            row for row in ledger.rows()
            if row.get("event") == "request_reserved" and row.get("phase_id") == phase
    ]) + len(pending) > config["max_logical_requests"]:
        raise RuntimeError("remaining phase plan exceeds the durable phase request cap")
    pending_reserve = sum(request.reserve_usd for request in pending)
    if existing_phase["reserved_peak_cost_usd"] + pending_reserve > config["hard_estimated_cost_usd"] + 1e-12:
        raise RuntimeError("remaining phase plan exceeds the durable phase cost cap")
    if budget_before["reserved_requests"] + len(pending) > 856:
        raise RuntimeError("remaining phase plan exceeds the global request cap")
    if budget_before["reserved_peak_cost_usd"] + pending_reserve > 3.0 + 1e-12:
        raise RuntimeError("remaining phase plan exceeds the global cost cap")
    credential_status = _install_secret_in_memory()
    try:
        result = monitor.run_schedule(
            out, mode="live", config_path=config_path,
            approval_id=freeze.EXECUTION_ID, secure_storage=True,
            requests_override=requests, budget_ledger=ledger, phase_id=phase,
        )
    finally:
        os.environ.pop("DEEPSEEK_API_KEY", None)
    return {
        "phase_id": phase, "status": result["status"],
        "assigned_rows": result["assigned_rows"],
        "completed_rows": result["completed_rows"],
        "failed_or_unexecuted_rows": result["failed_or_unexecuted_rows"],
        "real_model_or_api_calls": result["real_model_or_api_calls"],
        "retry_count": result["retries"],
        "reserved_peak_cost_usd": result["reserved_peak_cost_usd"],
        "provider_reported_peak_cost_usd": result["provider_reported_peak_cost_usd"],
        "conservative_total_peak_cost_usd": result["conservative_total_peak_cost_usd"],
        "returned_model_identity": result["returned_model_identity"],
        "provider_error_stop_reason": result["provider_error_stop_reason"],
        "aggregate_budget": result["aggregate_budget"],
        "frozen_plan_verified": plan_audit["status"],
        "credential_material_saved": False,
        "credential_source_status": credential_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=tuple(freeze.PHASE_CONFIGS))
    parser.add_argument("--freeze", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    phase = args.phase
    freeze_dir = args.freeze or (freeze.FREEZE_ROOT / phase)
    out = args.out or (RUN_ROOT / phase)
    result = execute(phase, freeze_dir, out)
    print(json.dumps(result, sort_keys=True))
    if result.get("status") == "NOT_RUN":
        return 3
    return 0 if result["failed_or_unexecuted_rows"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
