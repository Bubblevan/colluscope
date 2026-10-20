#!/usr/bin/env python3
"""Run the authorized DeepSeek-first bounded research sequence, fail-closed."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from scripts import run_deepseek_first_pilot as pilot  # noqa: E402
from scripts import run_m4_deepseek_v1 as agent  # noqa: E402
from scripts import freeze_deepseek_monitor_v1 as monitor_freeze  # noqa: E402
from scripts import run_deepseek_monitor_v1 as monitor  # noqa: E402
from scripts.audit_deepseek_first_research import (  # noqa: E402
    audit_agent_run, audit_monitor_run,
)
from colluscope.deepseek_m4_v1 import canonical, now_utc, write_once  # noqa: E402
from colluscope.deepseek_m4_v1 import read_jsonl  # noqa: E402
from decimal import Decimal

RUN_ROOT = ROOT / "runs/deepseek-first-m4"
JOURNAL = RUN_ROOT / "orchestrator-events.jsonl"
SUMMARY = RUN_ROOT / "final-run-summary.json"


def _event(event: str, status: str, details: dict[str, Any] | None = None) -> None:
    from colluscope.deepseek_m4_v1 import append_jsonl
    append_jsonl(JOURNAL, {"event": event, "status": status, "details": details or {}, "at_utc": now_utc()})


def run() -> dict[str, Any]:
    if SUMMARY.exists():
        return json.loads(SUMMARY.read_bytes())
    result: dict[str, Any] = {"schema_version": "deepseek-first-research-run-v1",
        "status": "IN_PROGRESS", "inference_authorized_by_user": True,
        "official_provider_only": True, "new_weights_downloaded": False,
        "fine_tuning": False, "m2_additional_model": False, "phases": {}}

    pilot_result = pilot.run()
    result["phases"]["compatibility_pilot"] = pilot_result
    _event("compatibility_pilot", pilot_result.get("status", "UNKNOWN"), pilot_result)
    if pilot_result.get("status") != "PASS":
        result["status"] = "STOP_PILOT_NO_GO"
        return _finish(result)

    gate = agent.run("gate")
    result["phases"]["agent_gate"] = gate
    _event("agent_gate", gate.get("status", "UNKNOWN"), gate)
    if gate.get("status") != "PASS":
        result["status"] = "STOP_AGENT_GATE_NO_GO"
        return _finish(result)

    bulk = agent.run("bulk")
    result["phases"]["agent_bulk"] = bulk
    _event("agent_bulk", bulk.get("status", "UNKNOWN"), bulk)
    if bulk.get("status") != "COMPLETE" or bulk.get("terminal_groups") != 24 or bulk.get("failed_groups"):
        result["status"] = "STOP_AGENT_BULK_INCOMPLETE"
        result["phases"]["agent_audit"] = audit_agent_run()
        return _finish(result)

    agent_audit = audit_agent_run()
    result["phases"]["agent_audit"] = agent_audit
    _event("agent_independent_audit", agent_audit.get("status", "UNKNOWN"), agent_audit)
    if agent_audit.get("status") != "PASS_INDEPENDENT_AGENT_REPLAY":
        result["status"] = "STOP_AGENT_AUDIT_NO_GO"
        return _finish(result)

    frozen = monitor_freeze.freeze()
    result["phases"]["monitor_freeze"] = frozen
    _event("monitor_freeze", frozen.get("status", "UNKNOWN"), frozen)
    verified = monitor_freeze.verify()
    result["phases"]["monitor_freeze_verify"] = verified
    _event("monitor_freeze_verify", verified.get("status", "UNKNOWN"), verified)
    if frozen.get("status") != "PASS_FROZEN" or verified.get("status") != "PASS_INPUTS_FROZEN":
        result["status"] = "STOP_MONITOR_FREEZE_NO_GO"
        return _finish(result)

    first = monitor.run("m4_six")
    result["phases"]["monitor_m4_six"] = first
    _event("monitor_m4_six", "PASS" if first.get("phase_terminal") and not first.get("fatal_stop") else "NO_GO", first)
    gate_record = first.get("initial_pair_gate", {})
    if (not first.get("phase_terminal") or first.get("fatal_stop")
            or gate_record.get("status") != "PASS"):
        result["status"] = "STOP_MONITOR_SCALE_GATE_NO_GO"
        result["phases"]["monitor_audit"] = audit_monitor_run()
        return _finish(result)

    remaining = monitor.run("m4_remaining")
    result["phases"]["monitor_m4_remaining"] = remaining
    _event("monitor_m4_remaining", "PASS" if remaining.get("phase_terminal") and not remaining.get("fatal_stop") else "NO_GO", remaining)
    if not remaining.get("phase_terminal") or remaining.get("fatal_stop"):
        result["status"] = "STOP_MONITOR_M4_TRACE_NO_GO"
        result["phases"]["monitor_audit"] = audit_monitor_run()
        return _finish(result)

    controls = monitor.run("scripted_controls")
    result["phases"]["monitor_scripted_controls"] = controls
    _event("monitor_scripted_controls", "PASS" if controls.get("phase_terminal") and not controls.get("fatal_stop") else "NO_GO", controls)
    if not controls.get("phase_terminal") or controls.get("fatal_stop"):
        result["status"] = "STOP_MONITOR_CONTROL_NO_GO"
        result["phases"]["monitor_audit"] = audit_monitor_run()
        return _finish(result)

    worlds = monitor.run("matched_worlds")
    result["phases"]["monitor_matched_worlds"] = worlds
    _event("monitor_matched_worlds", "PASS" if worlds.get("phase_terminal") and not worlds.get("fatal_stop") else "NO_GO", worlds)
    result["phases"]["monitor_audit"] = audit_monitor_run()
    result["status"] = "COMPLETE" if worlds.get("phase_terminal") and not worlds.get("fatal_stop") else "PARTIAL_MONITOR_RUN"
    return _finish(result)


def _finish(result: dict[str, Any]) -> dict[str, Any]:
    result["finished_utc"] = now_utc()
    ledger = read_jsonl(RUN_ROOT / "global_budget_ledger.jsonl")
    starts = [row for row in ledger if row.get("event") == "physical_request_started"]
    terminals = [row for row in ledger if row.get("event") == "physical_request_terminal"]
    result["global_physical_requests"] = len(starts)
    result["global_http_200_responses"] = sum(row.get("http_status") == 200 for row in terminals)
    result["global_non_200_http_responses"] = sum(
        type(row.get("http_status")) is int and row.get("http_status") != 200 for row in terminals)
    result["global_attempts_without_http_response"] = sum(row.get("http_status") is None for row in terminals)
    result["global_unterminalized_started_requests"] = len({r.get("request_id") for r in starts}
        - {r.get("request_id") for r in terminals})
    result["provider_reported_input_tokens"] = sum(
        row.get("prompt_tokens", 0) for row in terminals if row.get("http_status") == 200
        and type(row.get("prompt_tokens")) is int)
    result["provider_reported_output_tokens"] = sum(
        row.get("completion_tokens", 0) for row in terminals if row.get("http_status") == 200
        and type(row.get("completion_tokens")) is int)
    actual = sum((Decimal(row.get("estimated_peak_cost_usd", "0")) for row in terminals
                  if row.get("http_status") == 200), Decimal(0))
    reserved = sum((Decimal(row.get("reserved_peak_cost_usd", "0")) for row in starts), Decimal(0))
    result["provider_usage_cost_usd"] = str(actual)
    result["global_reserved_peak_cost_usd"] = str(reserved)
    result["global_request_cap"] = 900
    result["global_cost_cap_usd"] = "5.00"
    result["new_model_weights_or_training"] = False
    if SUMMARY.exists():
        old = json.loads(SUMMARY.read_bytes())
        if old != result:
            raise RuntimeError("final run summary already exists and differs; preserve it")
        return old
    write_once(SUMMARY, canonical(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = run()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
