#!/usr/bin/env python3
"""Record and audit research cycles. This CLI never runs experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
EXPERIMENTS = RESEARCH / "experiments"
STATE_PATH = RESEARCH / "state.json"
BUDGET_PATH = RESEARCH / "budget.json"
FROZEN_EVALUATOR = RESEARCH / "frozen_eval" / "evaluate_cycle.py"
EXPERIMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
PINNED_EVALUATOR_SHA256 = "9ff2caa18abb926251a4cdddefe28c53d472bf8be29d92cc8c878c462c91010b"

actual_evaluator_hash = hashlib.sha256(FROZEN_EVALUATOR.read_bytes()).hexdigest()
if actual_evaluator_hash != PINNED_EVALUATOR_SHA256:
    raise SystemExit(
        "Frozen evaluator hash mismatch. Preserve prior records and version/review any evaluator change before updating its pin."
    )

sys.path.insert(0, str(FROZEN_EVALUATOR.parent))
from evaluate_cycle import validate_closure, validate_handoff_packet, validate_preregistration  # noqa: E402


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def save_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    temporary.replace(path)


def git_head() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def budget_record() -> dict[str, Any]:
    value = load_json(BUDGET_PATH)
    if not isinstance(value, dict) or not isinstance(value.get("authorization"), dict):
        raise ValueError("research/budget.json has an invalid shape")
    auth = value["authorization"]
    status = auth.get("status")
    calls = auth.get("max_model_calls")
    cost = auth.get("max_external_cost_usd")
    ids = auth.get("authorized_experiment_ids")
    if not isinstance(status, str) or status not in {"none", "active"}:
        raise ValueError("budget authorization.status must be none or active")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
        raise ValueError("budget max_model_calls must be a non-negative integer")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        raise ValueError("budget max_external_cost_usd must be finite and non-negative")
    if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
        raise ValueError("budget authorized_experiment_ids must be a string list")
    if status == "none" and (calls != 0 or cost != 0 or auth.get("approval_id") is not None or ids):
        raise ValueError("an unapproved budget must have zero caps and no approval ID/scope")
    if status == "active" and (not auth.get("approval_id") or not auth.get("source") or not ids):
        raise ValueError("an active budget must record approval_id, source, and authorized experiment IDs")
    return value


def cycle_dirs() -> list[Path]:
    if not EXPERIMENTS.exists():
        return []
    return sorted(path for path in EXPERIMENTS.iterdir() if path.is_dir())


def closed_totals(exclude_id: str | None = None) -> tuple[int, float]:
    calls = 0
    cost = 0.0
    for directory in cycle_dirs():
        if exclude_id is not None and directory.name == exclude_id:
            continue
        closure_path = directory / "closure.json"
        if not closure_path.exists():
            continue
        closure = load_json(closure_path)
        local_calls = closure.get("actual_model_calls", 0)
        local_cost = closure.get("actual_external_cost_usd", 0.0)
        if isinstance(local_calls, int) and not isinstance(local_calls, bool) and local_calls >= 0:
            calls += local_calls
        if isinstance(local_cost, (int, float)) and not isinstance(local_cost, bool) and math.isfinite(local_cost) and local_cost >= 0:
            cost += float(local_cost)
    return calls, cost


def update_state(**updates: Any) -> None:
    state = load_json(STATE_PATH)
    state.update(updates)
    state["updated_at"] = datetime.now(timezone.utc).date().isoformat()
    save_json_atomic(STATE_PATH, state)


def command_status(_: argparse.Namespace) -> int:
    state = load_json(STATE_PATH)
    budget = budget_record()
    cycles = []
    open_ids = []
    for directory in cycle_dirs():
        prereg_path = directory / "preregistration.json"
        closure_path = directory / "closure.json"
        if not prereg_path.exists():
            continue
        prereg = load_json(prereg_path)
        closed = closure_path.exists()
        if not closed:
            open_ids.append(prereg.get("experiment_id"))
        cycles.append(
            {
                "experiment_id": prereg.get("experiment_id"),
                "evidence_class": prereg.get("evidence_class"),
                "status": "closed" if closed else "preregistered",
                "decision": load_json(closure_path).get("decision") if closed else None,
            }
        )
    calls, cost = closed_totals()
    result = {
        "program": state.get("program"),
        "status": state.get("status"),
        "current_round": state.get("current_round"),
        "active_experiment_id": state.get("active_experiment_id"),
        "latest_decision": state.get("latest_decision"),
        "next_action": state.get("next_action"),
        "cycles": cycles,
        "imported_handoffs": (
            [
                {"handoff_id": item.stem, "path": str(item.relative_to(ROOT)).replace("\\", "/")}
                for item in sorted((RESEARCH / "handoffs").glob("*.json"))
            ]
            if (RESEARCH / "handoffs").exists()
            else []
        ),
        "new_iteration_usage": {"model_calls": calls, "external_cost_usd": round(cost, 10)},
        "current_authorization": budget.get("authorization"),
        "frozen_evaluator_sha256": actual_evaluator_hash,
        "dispatch_capability": "none; this CLI has no experiment runner",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if len(open_ids) > 1:
        print("ERROR: more than one experiment is open", file=sys.stderr)
        return 1
    return 0


def command_register(args: argparse.Namespace) -> int:
    try:
        record = load_json(args.file.resolve())
    except (OSError, json.JSONDecodeError) as error:
        print(f"ERROR: cannot read preregistration: {error}", file=sys.stderr)
        return 1
    errors = validate_preregistration(record, ROOT)
    if errors:
        print_errors(errors)
        return 1
    experiment_id = record["experiment_id"]
    if not EXPERIMENT_ID_RE.fullmatch(experiment_id):
        print("ERROR: unsafe experiment ID", file=sys.stderr)
        return 1
    target = EXPERIMENTS / experiment_id
    if target.exists():
        print(f"ERROR: experiment is already registered: {experiment_id}", file=sys.stderr)
        return 1
    open_ids = [
        directory.name
        for directory in cycle_dirs()
        if (directory / "preregistration.json").exists() and not (directory / "closure.json").exists()
    ]
    if open_ids:
        print(f"ERROR: close the existing experiment first: {', '.join(open_ids)}", file=sys.stderr)
        return 1

    registered = dict(record)
    registered["registered_at_utc"] = now_utc()
    registered["registered_git_head"] = git_head()
    target.mkdir(parents=True)
    save_json_atomic(target / "preregistration.json", registered)
    update_state(
        status="iteration_preregistered_not_dispatched",
        active_experiment_id=experiment_id,
        latest_decision="PREREGISTERED",
        next_action="Implement and run only through an existing entry point permitted by the current explicit authorization; the harness itself does not dispatch.",
    )
    print(json.dumps({"registered": experiment_id, "dispatched": False, "evidence_class": record["evidence_class"]}, indent=2))
    return 0


def command_import_closeout(args: argparse.Namespace) -> int:
    try:
        packet = load_json(args.file.resolve())
        errors = validate_handoff_packet(packet, ROOT)
        if errors:
            print_errors(errors)
            return 1
        handoff_id = packet["handoff_id"]
        handoffs = RESEARCH / "handoffs"
        target = handoffs / f"{handoff_id}.json"
        if target.exists():
            raise ValueError(f"handoff already imported: {handoff_id}")
        state = load_json(STATE_PATH)
        current_round = state.get("current_round", {})
        if current_round.get("status") != "awaiting terminal result and independent audit":
            raise ValueError("there is no pending current-round handoff to import")
        imported = dict(packet)
        imported["imported_at_utc"] = now_utc()
        imported["imported_git_head"] = git_head()
        save_json_atomic(target, imported)
        update_state(
            status="current_round_closeout_imported",
            current_round={
                "owner": current_round.get("owner"),
                "terminal_artifact": str(target.relative_to(ROOT)).replace("\\", "/"),
                "status": "closeout_imported",
                "terminal_decision": imported["terminal_decision"],
                "evidence_classes": imported["evidence_classes"],
                "historical_model_calls": imported["historical_model_calls"],
                "historical_external_cost_usd": imported["historical_external_cost_usd"],
                "note": "Imported historical usage is not current authorization and does not count toward new-cycle allowance.",
            },
            latest_decision=imported["terminal_decision"],
            next_action="Review the imported sanitized results and limitations, then preregister one new cycle before making any change.",
        )
        print(json.dumps({"imported_handoff": handoff_id, "historical_calls_reauthorized": False, "dispatched": False}, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def command_close(args: argparse.Namespace) -> int:
    try:
        closure = load_json(args.file.resolve())
        experiment_id = closure.get("experiment_id") if isinstance(closure, dict) else None
        if not isinstance(experiment_id, str) or not EXPERIMENT_ID_RE.fullmatch(experiment_id):
            raise ValueError("closure requires a safe experiment_id")
        directory = EXPERIMENTS / experiment_id
        prereg_path = directory / "preregistration.json"
        closure_path = directory / "closure.json"
        if not prereg_path.exists():
            raise ValueError(f"no preregistration found for {experiment_id}")
        if closure_path.exists():
            raise ValueError(f"experiment already has a terminal closure: {experiment_id}")
        prereg = load_json(prereg_path)
        prereg_errors = validate_preregistration(prereg, ROOT)
        if prereg_errors:
            print_errors(prereg_errors)
            return 1
        budget = budget_record()
        prior_calls, prior_cost = closed_totals(exclude_id=experiment_id)
        errors = validate_closure(prereg, closure, ROOT, budget, prior_calls, prior_cost)
        if errors:
            print_errors(errors)
            return 1
        state = load_json(STATE_PATH)
        no_progress = state.get("consecutive_cycles_without_new_uncertainty_reduction", 0)
        if closure["new_uncertainty_reduced"] is True:
            no_progress = 0
        else:
            no_progress += 1
        if no_progress >= 3 and closure["decision"] not in {"PIVOT", "BLOCKED"}:
            print("ERROR: after three low-information cycles, decision must pivot or block", file=sys.stderr)
            return 1
        saved = dict(closure)
        saved["closed_at_utc"] = now_utc()
        saved["closed_git_head"] = git_head()
        save_json_atomic(closure_path, saved)
        update_state(
            status="ready_for_next_cycle",
            active_experiment_id=None,
            latest_closed_experiment_id=experiment_id,
            latest_decision=saved["decision"],
            next_action=saved["next_action"],
            consecutive_cycles_without_new_uncertainty_reduction=no_progress,
            **(
                {"current_round": {"owner": prereg.get("source_task", "imported current round"), "terminal_artifact": f"research/experiments/{experiment_id}/closure.json", "status": "closeout_recorded", "note": "Terminal result and audit references were registered and hash-checked."}}
                if prereg.get("closes_current_handoff") is True
                else {}
            ),
        )
        print(json.dumps({"closed": experiment_id, "decision": saved["decision"], "scientific_result_certified": False}, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def command_audit(_: argparse.Namespace) -> int:
    errors: list[str] = []
    budget = budget_record()
    state = load_json(STATE_PATH)
    handoffs_dir = RESEARCH / "handoffs"
    if handoffs_dir.exists():
        for handoff_path in sorted(handoffs_dir.glob("*.json")):
            packet = load_json(handoff_path)
            errors.extend(f"handoff {handoff_path.stem}: {error}" for error in validate_handoff_packet(packet, ROOT))
            if not isinstance(packet, dict):
                continue
            if packet.get("handoff_id") != handoff_path.stem:
                errors.append(f"handoff {handoff_path.stem}: filename does not match handoff_id")
    open_ids: list[str] = []
    total_calls = 0
    total_cost = 0.0
    for directory in cycle_dirs():
        prereg_path = directory / "preregistration.json"
        closure_path = directory / "closure.json"
        if not prereg_path.exists():
            errors.append(f"{directory.name}: missing preregistration.json")
            continue
        prereg = load_json(prereg_path)
        prereg_errors = validate_preregistration(prereg, ROOT)
        errors.extend(f"{directory.name}: {error}" for error in prereg_errors)
        if prereg_errors or not isinstance(prereg, dict):
            continue
        if prereg.get("experiment_id") != directory.name:
            errors.append(f"{directory.name}: folder name does not match experiment_id")
        if not closure_path.exists():
            open_ids.append(directory.name)
            continue
        closure = load_json(closure_path)
        if not isinstance(closure, dict):
            errors.append(f"{directory.name}: closure must be a JSON object")
            continue
        raw_calls = closure.get("actual_model_calls", 0)
        raw_cost = closure.get("actual_external_cost_usd", 0.0)
        local_calls = raw_calls if isinstance(raw_calls, int) and not isinstance(raw_calls, bool) and raw_calls >= 0 else 0
        local_cost = float(raw_cost) if isinstance(raw_cost, (int, float)) and not isinstance(raw_cost, bool) and math.isfinite(raw_cost) and raw_cost >= 0 else 0.0
        errors.extend(
            f"{directory.name}: {error}"
            for error in validate_closure(prereg, closure, ROOT, budget, total_calls, total_cost)
        )
        total_calls += local_calls
        total_cost += local_cost
    if len(open_ids) > 1:
        errors.append("more than one experiment is open")
    expected_active = open_ids[0] if open_ids else None
    if state.get("active_experiment_id") != expected_active:
        errors.append("research/state.json active_experiment_id disagrees with registry")
    handoff_paths = sorted(handoffs_dir.glob("*.json")) if handoffs_dir.exists() else []
    current_round = state.get("current_round", {})
    if current_round.get("status") == "closeout_imported":
        terminal_path = current_round.get("terminal_artifact")
        if not isinstance(terminal_path, str) or not (ROOT / terminal_path).is_file():
            errors.append("state references a missing imported closeout")
        elif terminal_path not in {str(item.relative_to(ROOT)).replace("\\", "/") for item in handoff_paths}:
            errors.append("state terminal closeout is not one of the validated handoff packets")
    elif handoff_paths:
        errors.append("handoff packet exists but state does not record its import")
    auth = budget.get("authorization", {})
    if total_calls > auth.get("max_model_calls", 0):
        errors.append("cumulative calls exceed research/budget.json authorization")
    if total_cost > auth.get("max_external_cost_usd", 0.0):
        errors.append("cumulative cost exceeds research/budget.json authorization")
    report = {
        "integrity_check": "FAIL" if errors else "PASS",
        "scientific_validity": "NOT_EVALUATED",
        "registered_cycles": len(cycle_dirs()),
        "open_experiments": open_ids,
        "new_iteration_usage": {"model_calls": total_calls, "external_cost_usd": round(total_cost, 10)},
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def print_errors(errors: list[str]) -> None:
    print("RECORD REJECTED:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="ColluScope research registry (record-only; never runs experiments)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status", help="show handoff, registry, and current authorization")
    status_parser.set_defaults(func=command_status)
    register_parser = subparsers.add_parser("register", help="validate and freeze a preregistration JSON file")
    register_parser.add_argument("file", type=Path)
    register_parser.set_defaults(func=command_register)
    close_parser = subparsers.add_parser("close", help="validate and record a terminal closure JSON file")
    close_parser.add_argument("file", type=Path)
    close_parser.set_defaults(func=command_close)
    import_parser = subparsers.add_parser("import-closeout", help="import a completed separate task without retroactive preregistration")
    import_parser.add_argument("file", type=Path)
    import_parser.set_defaults(func=command_import_closeout)
    audit_parser = subparsers.add_parser("audit", help="check registry lifecycle, frozen hashes, and recorded budgets")
    audit_parser.set_defaults(func=command_audit)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
