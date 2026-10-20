#!/usr/bin/env python3
"""Run the preregistered balanced DeepSeek Monitor schedule; zero retries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.deepseek_m4_v1 import (  # noqa: E402
    DeepSeekClient, DeepSeekRequestError, append_jsonl, canonical, now_utc,
    read_jsonl, validate_monitor_arguments, write_once,
)
from colluscope.deepseek_monitor_v1 import verify_plan  # noqa: E402
from scripts.freeze_deepseek_monitor_v1 import (  # noqa: E402
    FREEZE_ROOT, MANIFEST_PATH, MONITOR_ROOT, PLAN_PATH, RUN_ROOT, _acl, verify as verify_freeze,
)
from scripts.local_llama_security import verify_private_directory_acl  # noqa: E402
from scripts.run_m4_deepseek_v1 import _load_key  # noqa: E402

OUT = MONITOR_ROOT
PREDICTIONS = OUT / "predictions.jsonl"
BUDGET = RUN_ROOT / "global_budget_ledger.jsonl"
PHASES = ("m4_six", "m4_remaining", "scripted_controls", "matched_worlds")


def _rows() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    verify_freeze()
    manifest = json.loads(MANIFEST_PATH.read_bytes())
    rows = [json.loads(line) for line in PLAN_PATH.read_text(encoding="utf-8").splitlines() if line]
    return manifest, rows


def _existing_prediction_map() -> dict[str, dict[str, Any]]:
    rows = read_jsonl(PREDICTIONS)
    result = {}
    for row in rows:
        rid = row.get("request_id")
        if rid in result:
            raise RuntimeError(f"duplicate prediction row for {rid}")
        result[rid] = row
    return result


def _already_terminal(rid: str) -> dict[str, Any] | None:
    row = _existing_prediction_map().get(rid)
    if row:
        return row
    return None


def _gate_from_initial_batch(rows: list[dict[str, Any]], predictions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    assessable_pairs = []
    selected = [row for row in rows if row["phase_id"] == "m4_six"]
    by_key: dict[tuple, dict[str, dict[str, Any]]] = {}
    for row in selected:
        key = (row["case_ref"], row["task"], row["permission"])
        by_key.setdefault(key, {})[row["baseline_id"]] = row
    for key, methods in by_key.items():
        if set(methods) != {"B4_raw_fusion", "B5_evidence_aware"}:
            continue
        a, b = methods["B4_raw_fusion"], methods["B5_evidence_aware"]
        if not a["references"][0].get("assessable") or not b["references"][0].get("assessable"):
            continue
        p_a, p_b = predictions.get(a["request_id"]), predictions.get(b["request_id"])
        if p_a and p_b and p_a.get("status") == "VALID" and p_b.get("status") == "VALID":
            assessable_pairs.append({"case_ref": key[0], "task": key[1], "permission": key[2],
                "B4_request_id": a["request_id"], "B5_request_id": b["request_id"],
                "B4_prediction_label": p_a["prediction"]["label"],
                "B5_prediction_label": p_b["prediction"]["label"]})
    return {"schema_version": "deepseek-monitor-initial-pair-gate-v1",
        "status": "PASS" if assessable_pairs else "NO_GO",
        "assigned_initial_rows": 72, "terminal_initial_rows": sum(
            row.get("request_id") in predictions for row in selected),
        "assessable_paired_items": len(assessable_pairs),
        "pairs": assessable_pairs, "no_result_selection": True, "at_utc": now_utc()}


def _require_m4_source() -> None:
    episodes = read_jsonl(RUN_ROOT / "agent/episodes.jsonl")
    if len(episodes) != 24:
        raise RuntimeError("all 24 assigned M4 groups must be terminal before Monitor evaluation")
    if not any(row.get("terminal_status") == "COMPLETED" for row in episodes):
        raise RuntimeError("Monitor dispatch is prohibited because M4 has no complete behavioral episode")


def run(phase: str) -> dict[str, Any]:
    if phase not in PHASES:
        raise ValueError(f"unknown Monitor phase: {phase}")
    manifest, all_rows = _rows()
    selected = json.loads((RUN_ROOT / "pilot/selected_interface.json").read_bytes())
    if manifest.get("interface") != selected.get("selected_interface"):
        raise RuntimeError("Monitor freeze and compatibility-pilot interface differ")
    phase_rows = [row for row in all_rows if row["phase_id"] == phase]
    expected_counts = {"m4_six": 72, "m4_remaining": 216, "scripted_controls": 16, "matched_worlds": 72}
    if len(phase_rows) != expected_counts[phase]:
        raise RuntimeError("phase row count differs from the frozen request plan")
    acl = _acl(OUT)
    if acl.get("verified") is not True:
        raise PermissionError("Monitor raw run ACL is not verified")
    if phase.startswith("m4_"):
        _require_m4_source()
    prediction_map = _existing_prediction_map()
    if phase == "m4_remaining":
        gate_path = OUT / "initial_pair_gate.json"
        if not gate_path.is_file() or json.loads(gate_path.read_bytes()).get("status") != "PASS":
            raise RuntimeError("M4 Monitor scaling is blocked until an assessable initial B4/B5 pair exists")
    if phase in {"scripted_controls", "matched_worlds"}:
        needed = [row for row in all_rows if row["phase_id"] in {"m4_six", "m4_remaining"}]
        if any(row["request_id"] not in prediction_map for row in needed):
            raise RuntimeError("synthetic Monitor populations wait until all 288 natural-trace rows are terminal")
    if phase in {"scripted_controls", "matched_worlds"}:
        m4_terminal = OUT / "m4_trace_terminal.json"
        if not m4_terminal.is_file() or json.loads(m4_terminal.read_bytes()).get("status") != "TERMINAL":
            raise RuntimeError("Monitor controls/worlds require terminal disposition for all M4 trace requests")
    client = DeepSeekClient(run_dir=OUT, budget_ledger=BUDGET, api_key=_load_key(),
                            interface=manifest["interface"])
    fatal_stop = False
    for row in phase_rows:
        if row["request_id"] in prediction_map:
            continue
        try:
            prediction, receipt = client.call(request_id=row["request_id"], role="monitor",
                messages=row["messages"], tool_name=row["tool_name"], schema=row["schema"],
                semantic=lambda value, task=row["task"], labels=row["allowed_labels"]:
                    validate_monitor_arguments(task, labels, value),
                metadata={"phase_id": phase, "population": row["population"],
                          "baseline_id": row["baseline_id"], "task": row["task"],
                          "permission": row["permission"], "case_ref_not_sent": row["case_ref"]},
                expected_request_sha256=row["body_sha256"], run_request_limit=376)
            visible = {e["event_id"] for e in row["evidence"].get("events", [])}
            record = {"request_id": row["request_id"], "phase_id": phase, "status": "VALID",
                "prediction": prediction, "citation_membership_valid": all(
                    ref in visible for ref in prediction["evidence_refs"]),
                "response_sha256": receipt["response_sha256"], "finish_reason": receipt["finish_reason"],
                "returned_model": receipt["returned_model"], "system_fingerprint": receipt["system_fingerprint"],
                "prompt_tokens": receipt["prompt_tokens"], "completion_tokens": receipt["completion_tokens"],
                "estimated_peak_cost_usd": receipt["estimated_peak_cost_usd"],
                "elapsed_seconds": receipt["elapsed_seconds"], "at_utc": now_utc()}
        except DeepSeekRequestError as exc:
            attempts = read_jsonl(OUT / "attempts.jsonl")
            last = next((a for a in reversed(attempts) if a.get("request_id") == row["request_id"]
                         and a.get("event") == "attempt_terminal"), {})
            record = {"request_id": row["request_id"], "phase_id": phase, "status": exc.status,
                "error": str(exc), "fatal": exc.fatal, "finish_reason": last.get("finish_reason"),
                "returned_model": last.get("returned_model"),
                "system_fingerprint": last.get("system_fingerprint"),
                "prompt_tokens": last.get("prompt_tokens"), "completion_tokens": last.get("completion_tokens"),
                "estimated_peak_cost_usd": last.get("estimated_peak_cost_usd"),
                "response_sha256": last.get("response_sha256"), "at_utc": now_utc()}
            fatal_stop = exc.fatal
        append_jsonl(PREDICTIONS, record)
        prediction_map[row["request_id"]] = record
        if fatal_stop:
            break
    if fatal_stop:
        for row in phase_rows:
            if row["request_id"] in prediction_map:
                continue
            record = {"request_id": row["request_id"], "phase_id": phase,
                "status": "NOT_DISPATCHED_FATAL_STOP", "reason": "fatal provider/runtime stop",
                "at_utc": now_utc()}
            append_jsonl(PREDICTIONS, record)
            prediction_map[row["request_id"]] = record
    terminal_count = sum(row["request_id"] in prediction_map for row in phase_rows)
    result = {"phase_id": phase, "assigned_rows": len(phase_rows),
        "terminal_rows": terminal_count, "valid_rows": sum(
            prediction_map.get(row["request_id"], {}).get("status") == "VALID" for row in phase_rows),
        "failed_or_not_dispatched_rows": sum(
            prediction_map.get(row["request_id"], {}).get("status") != "VALID" for row in phase_rows),
        "fatal_stop": fatal_stop, "interface": manifest["interface"], "retry_count": 0,
        "phase_terminal": terminal_count == len(phase_rows), "at_utc": now_utc()}
    from colluscope.deepseek_m4_v1 import write_once
    phase_terminal_path = OUT / f"{phase}-terminal.json"
    if not phase_terminal_path.exists():
        write_once(phase_terminal_path, canonical(result) + b"\n")
    if phase == "m4_six" and result["phase_terminal"]:
        gate = _gate_from_initial_batch(all_rows, prediction_map)
        gate_path = OUT / "initial_pair_gate.json"
        if gate_path.exists():
            if json.loads(gate_path.read_bytes()).get("status") != gate["status"]:
                raise RuntimeError("existing M4 initial-pair gate conflicts with replay")
        else:
            write_once(gate_path, canonical(gate) + b"\n")
        result["initial_pair_gate"] = gate
    if phase in {"m4_six", "m4_remaining"} and result["phase_terminal"]:
        trace_terminal = all(
            prediction_map.get(row["request_id"], {}).get("status") is not None
            for row in all_rows if row["phase_id"] in {"m4_six", "m4_remaining"})
        if trace_terminal:
            fatal_seen = any(
                prediction_map.get(row["request_id"], {}).get("fatal") is True
                or prediction_map.get(row["request_id"], {}).get("status") == "NOT_DISPATCHED_FATAL_STOP"
                for row in all_rows if row["phase_id"] in {"m4_six", "m4_remaining"})
            trace_path = OUT / "m4_trace_terminal.json"
            if not trace_path.exists():
                write_once(trace_path, canonical({"status": "FATAL_STOP" if fatal_seen else "TERMINAL",
                    "request_count": 288, "fatal_stop_seen": fatal_seen,
                    "at_utc": now_utc()}) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=PHASES)
    args = parser.parse_args()
    result = run(args.phase)
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("phase_terminal") and not result.get("fatal_stop") else 2


if __name__ == "__main__":
    raise SystemExit(main())
