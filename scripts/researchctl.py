#!/usr/bin/env python3
"""Record and audit research cycles. This CLI never runs experiments."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research"
EXPERIMENTS = RESEARCH / "experiments"
STATE_PATH = RESEARCH / "state.json"
BUDGET_PATH = RESEARCH / "budget.json"
AUTHORIZATIONS = RESEARCH / "authorizations"
MEMORY_PATH = RESEARCH / "memory.json"
HYPOTHESES_PATH = RESEARCH / "hypotheses.json"
FROZEN_EVALUATOR_V1 = RESEARCH / "frozen_eval" / "evaluate_cycle.py"
FROZEN_EVALUATOR_V2 = RESEARCH / "frozen_eval" / "evaluate_cycle_v2.py"
EXPERIMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")
PINNED_EVALUATOR_V1_SHA256 = "9ff2caa18abb926251a4cdddefe28c53d472bf8be29d92cc8c878c462c91010b"
PINNED_EVALUATOR_V2_SHA256 = "e7b563b1a149a8c770a56728a4d13abcc53e8a12080866a1adfad03b2d234f6d"

actual_evaluator_v1_hash = hashlib.sha256(FROZEN_EVALUATOR_V1.read_bytes()).hexdigest()
actual_evaluator_v2_hash = hashlib.sha256(FROZEN_EVALUATOR_V2.read_bytes()).hexdigest()
if actual_evaluator_v1_hash != PINNED_EVALUATOR_V1_SHA256:
    raise SystemExit(
        "Frozen v1 evaluator hash mismatch. Preserve prior records and do not rewrite the original evaluator."
    )
if actual_evaluator_v2_hash != PINNED_EVALUATOR_V2_SHA256:
    raise SystemExit("Current v2 evaluator hash mismatch. Review the versioned evaluator before updating its pin.")

sys.path.insert(0, str(FROZEN_EVALUATOR_V1.parent))
import evaluate_cycle as v1  # noqa: E402
from evaluate_cycle_v2 import (  # noqa: E402
    parse_utc,
    validate_authorization_batch,
    validate_closure,
    validate_handoff_packet,
    validate_preregistration,
)


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


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_registration_manifest(directory: Path, preregistration: dict[str, Any]) -> list[str]:
    manifest_path = directory / "registration.json"
    if not manifest_path.is_file():
        return [f"{directory.name}: missing immutable registration.json manifest"]
    manifest = load_json(manifest_path)
    errors: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return [f"{directory.name}: registration.json must be schema_version 1"]
    if manifest.get("experiment_id") != directory.name:
        errors.append(f"{directory.name}: registration manifest experiment_id mismatch")
    expected = manifest.get("preregistration_sha256")
    if not isinstance(expected, str) or expected != file_sha256(directory / "preregistration.json"):
        errors.append(f"{directory.name}: preregistration changed after registration")
    if manifest.get("evaluator_v2_sha256") != actual_evaluator_v2_hash:
        errors.append(f"{directory.name}: registration evaluator hash mismatch")
    if manifest.get("authorization_batch_sha256") != preregistration.get("authorization_batch_sha256"):
        errors.append(f"{directory.name}: registration authorization hash disagrees with preregistration")
    closure_path = directory / "closure.json"
    if closure_path.exists():
        closure_hash = manifest.get("closure_sha256")
        if not isinstance(closure_hash, str) or closure_hash != file_sha256(closure_path):
            errors.append(f"{directory.name}: closure changed after it was sealed")
    return errors


def registry_locked(function: Any) -> Any:
    @wraps(function)
    def wrapped(args: argparse.Namespace) -> int:
        lock_path = RESEARCH / ".registry.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+b") as stream:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                return function(args)
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    return wrapped


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
    if status == "none" and (
        calls != 0
        or cost != 0
        or auth.get("approval_id") is not None
        or auth.get("scope") is not None
        or auth.get("source") is not None
        or auth.get("approved_at_utc") is not None
        or auth.get("expires_at_utc") is not None
        or ids
    ):
        raise ValueError("an unapproved budget must have zero caps and no approval ID/scope")
    if status == "active" and (not auth.get("approval_id") or not auth.get("source") or not ids):
        raise ValueError("an active budget must record approval_id, source, and authorized experiment IDs")
    project_limits = value.get("project_limits")
    if not isinstance(project_limits, dict):
        raise ValueError("budget project_limits must be an object")
    project_calls = project_limits.get("max_model_calls")
    project_cost = project_limits.get("max_external_cost_usd")
    if isinstance(project_calls, bool) or not isinstance(project_calls, int) or project_calls < 0:
        raise ValueError("project max_model_calls must be a non-negative integer")
    if isinstance(project_cost, bool) or not isinstance(project_cost, (int, float)) or not math.isfinite(project_cost) or project_cost < 0:
        raise ValueError("project max_external_cost_usd must be finite and non-negative")
    if status == "active":
        batch = authorization_batch(auth.get("approval_id"))
        if batch is None:
            raise ValueError("active budget snapshot has no immutable research/authorizations batch")
        for key in ("approval_id", "scope", "authorized_experiment_ids", "max_model_calls", "max_external_cost_usd", "source", "approved_at_utc", "expires_at_utc"):
            if auth.get(key) != batch.get(key):
                raise ValueError(f"active budget snapshot disagrees with immutable authorization batch field {key}")
        value["authorization_expired"] = authorization_expired(batch)
    return value


def cycle_dirs() -> list[Path]:
    if not EXPERIMENTS.exists():
        return []
    return sorted(path for path in EXPERIMENTS.iterdir() if path.is_dir())


def authorization_batch(approval_id: Any) -> dict[str, Any] | None:
    if not isinstance(approval_id, str) or not EXPERIMENT_ID_RE.fullmatch(approval_id):
        return None
    path = AUTHORIZATIONS / f"{approval_id}.json"
    if not path.is_file():
        return None
    value = load_json(path)
    errors = validate_authorization_batch(value)
    if errors:
        raise ValueError("invalid authorization batch " + approval_id + ": " + "; ".join(errors))
    if value.get("approval_id") != approval_id:
        raise ValueError("authorization filename does not match approval_id")
    return value


def authorization_expired(batch: dict[str, Any]) -> bool:
    expiry, error = parse_utc(batch.get("expires_at_utc"), "expires_at_utc")
    if error or expiry is None:
        return True
    return datetime.now(timezone.utc) > expiry


def usage_totals(exclude_id: str | None = None) -> tuple[dict[str, tuple[int, float]], int, float]:
    by_approval: dict[str, tuple[int, float]] = {}
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
        approval_id = closure.get("authorization_id")
        if isinstance(approval_id, str):
            prior_calls, prior_cost = by_approval.get(approval_id, (0, 0.0))
            if isinstance(local_calls, int) and not isinstance(local_calls, bool) and local_calls >= 0:
                prior_calls += local_calls
            if isinstance(local_cost, (int, float)) and not isinstance(local_cost, bool) and math.isfinite(local_cost) and local_cost >= 0:
                prior_cost += float(local_cost)
            by_approval[approval_id] = (prior_calls, prior_cost)
    return by_approval, calls, cost


def closed_totals(exclude_id: str | None = None) -> tuple[int, float]:
    _, calls, cost = usage_totals(exclude_id)
    return calls, cost


def preregistration_budget_errors(record: dict[str, Any], budget: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    errors: list[str] = []
    experiment_id = record.get("experiment_id")
    plan = record.get("budget", {})
    authorization = record.get("authorization", {})
    calls = plan.get("max_model_calls", 0)
    cost = float(plan.get("max_external_cost_usd", 0.0))
    if calls == 0 and cost == 0:
        return errors, None
    approval_id = authorization.get("approval_id") if isinstance(authorization, dict) else None
    snapshot = budget.get("authorization", {})
    batch = authorization_batch(approval_id)
    if not batch:
        return ["non-zero experiment budget has no immutable approval batch"], None
    if snapshot.get("status") != "active" or snapshot.get("approval_id") != approval_id:
        errors.append("the approval batch is not the current authorization snapshot")
    approved_at, approved_error = parse_utc(batch.get("approved_at_utc"), "approved_at_utc")
    if approved_error:
        errors.append(approved_error)
    elif approved_at is not None and datetime.now(timezone.utc) < approved_at:
        errors.append("the approval batch is not effective yet")
    if authorization_expired(batch):
        errors.append("the approval batch has expired; it cannot authorize a new cycle")
    if experiment_id not in batch.get("authorized_experiment_ids", []):
        errors.append("approval batch does not name this experiment ID")
    if authorization.get("scope") != batch.get("scope"):
        errors.append("preregistration scope must exactly match the approved scope")
    by_approval, project_calls_used, project_cost_used = usage_totals()
    grant_calls_used, grant_cost_used = by_approval.get(approval_id, (0, 0.0))
    if grant_calls_used + calls > batch.get("max_model_calls", 0):
        errors.append("preregistered model-call reserve exceeds remaining approval-batch calls")
    if grant_cost_used + cost > batch.get("max_external_cost_usd", 0.0) + 1e-9:
        errors.append("preregistered cost reserve exceeds remaining approval-batch budget")
    project_limits = budget.get("project_limits", {})
    if project_calls_used + calls > project_limits.get("max_model_calls", 0):
        errors.append("preregistered model-call reserve exceeds the project-wide lifetime ceiling")
    if project_cost_used + cost > project_limits.get("max_external_cost_usd", 0.0) + 1e-9:
        errors.append("preregistered cost reserve exceeds the project-wide lifetime ceiling")
    return errors, batch


def update_state(**updates: Any) -> None:
    state = load_json(STATE_PATH)
    state.update(updates)
    state["updated_at"] = datetime.now(timezone.utc).date().isoformat()
    save_json_atomic(STATE_PATH, state)


def continuation_plan(state: dict[str, Any], open_ids: list[str]) -> dict[str, str]:
    if state.get("program_status") == "complete":
        return {
            "action_type": "program_complete",
            "next_action": "No further cycle is scheduled; the program completion review is recorded.",
        }
    if open_ids:
        return {
            "action_type": "resume_or_close_registered_cycle",
            "next_action": f"Inspect the frozen preregistration for {open_ids[0]}, then use only its existing permitted entry point or record the exact execution boundary; do not dispatch from this CLI.",
        }
    outcome = state.get("latest_scientific_outcome")
    if outcome == "INVALID_EXPERIMENT":
        return {
            "action_type": "diagnose_invalid",
            "next_action": "Trace the invalid result to its cause, preserve every failed row, and preregister a bounded repair or redesigned evaluation.",
        }
    if outcome in {"EXECUTION_BLOCKED", "RESOURCE_BLOCKED"}:
        return {
            "action_type": "continue_offline_or_wait",
            "next_action": "Continue the highest-value independent offline work; record the exact authorization or resource boundary before any blocked execution.",
        }
    return {
        "action_type": "select_and_preregister",
        "next_action": "Review the scientific memory and up to three competing candidate hypotheses, select one, and preregister the smallest discriminating cycle.",
    }


@registry_locked
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
                "hypothesis_id": prereg.get("hypothesis_id"),
                "evidence_class": prereg.get("evidence_class"),
                "status": "closed" if closed else "preregistered",
                "decision": load_json(closure_path).get("decision") if closed else None,
                "scientific_outcome": load_json(closure_path).get("scientific_outcome") if closed else None,
            }
        )
    by_approval, calls, cost = usage_totals()
    continuation = continuation_plan(state, open_ids)
    hypotheses = load_json(HYPOTHESES_PATH) if HYPOTHESES_PATH.exists() else {"candidates": []}
    memory = load_json(MEMORY_PATH) if MEMORY_PATH.exists() else {"beliefs": [], "cycle_updates": []}
    result = {
        "program": state.get("program"),
        "program_status": state.get("program_status", "active"),
        "status": state.get("status"),
        "current_round": state.get("current_round"),
        "active_experiment_id": state.get("active_experiment_id"),
        "latest_decision": state.get("latest_decision"),
        "latest_decision_type": state.get("latest_decision_type", "operational"),
        "latest_scientific_outcome": state.get("latest_scientific_outcome"),
        "next_action": state.get("next_action"),
        "continuation": continuation,
        "cycles": cycles,
        "candidate_hypotheses": [item.get("hypothesis_id") for item in hypotheses.get("candidates", []) if item.get("status") in {"candidate", "selected"}],
        "research_memory": {"historical_beliefs": len(memory.get("beliefs", [])), "cycle_updates": len(memory.get("cycle_updates", []))},
        "imported_handoffs": (
            [
                {"handoff_id": item.stem, "path": str(item.relative_to(ROOT)).replace("\\", "/")}
                for item in sorted((RESEARCH / "handoffs").glob("*.json"))
            ]
            if (RESEARCH / "handoffs").exists()
            else []
        ),
        "new_iteration_usage": {"model_calls": calls, "external_cost_usd": round(cost, 10)},
        "usage_by_approval_id": {key: {"model_calls": value[0], "external_cost_usd": round(value[1], 10)} for key, value in by_approval.items()},
        "current_authorization": budget.get("authorization"),
        "authorization_expired": budget.get("authorization_expired", False),
        "project_limits": budget.get("project_limits"),
        "frozen_evaluator_sha256": {"v1": actual_evaluator_v1_hash, "v2": actual_evaluator_v2_hash},
        "dispatch_capability": "none; Codex Goal is the continuation driver, and this CLI never executes registered commands",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if len(open_ids) > 1:
        print("ERROR: more than one experiment is open", file=sys.stderr)
        return 1
    return 0


@registry_locked
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

    budget = budget_record()
    budget_errors, batch = preregistration_budget_errors(record, budget)
    if budget_errors:
        print_errors(budget_errors)
        return 1
    hypotheses = load_json(HYPOTHESES_PATH)
    candidates = hypotheses.get("candidates", []) if isinstance(hypotheses, dict) else []
    candidate = next((item for item in candidates if item.get("hypothesis_id") == record.get("hypothesis_id")), None)
    if candidate is None:
        print("ERROR: hypothesis_id must name a registered candidate in research/hypotheses.json", file=sys.stderr)
        return 1
    if candidate.get("status") not in {"candidate", "selected"}:
        print("ERROR: selected research hypothesis is no longer an open candidate", file=sys.stderr)
        return 1
    if record.get("hypothesis") != candidate.get("hypothesis"):
        print("ERROR: preregistered hypothesis text must match the selected candidate", file=sys.stderr)
        return 1

    registered = dict(record)
    registered["registered_at_utc"] = now_utc()
    registered["registered_git_head"] = git_head()
    registered["evaluator_version"] = 2
    registered["authorization_batch_sha256"] = hashlib.sha256(
        (AUTHORIZATIONS / f"{record['authorization']['approval_id']}.json").read_bytes()
    ).hexdigest() if batch else None
    target.mkdir(parents=True)
    save_json_atomic(target / "preregistration.json", registered)
    save_json_atomic(
        target / "registration.json",
        {
            "schema_version": 1,
            "experiment_id": experiment_id,
            "registered_at_utc": registered["registered_at_utc"],
            "registered_git_head": registered["registered_git_head"],
            "evaluator_v2_sha256": actual_evaluator_v2_hash,
            "preregistration_sha256": file_sha256(target / "preregistration.json"),
            "authorization_batch_sha256": registered["authorization_batch_sha256"],
            "closure_sha256": None,
        },
    )
    for item in candidates:
        if item.get("status") == "selected":
            item["status"] = "candidate"
    candidate["status"] = "selected"
    hypotheses["selected_hypothesis_id"] = candidate["hypothesis_id"]
    save_json_atomic(HYPOTHESES_PATH, hypotheses)
    update_state(
        status="iteration_preregistered",
        active_experiment_id=experiment_id,
        active_hypothesis_id=candidate["hypothesis_id"],
        latest_decision="PREREGISTERED",
        latest_decision_type="operational",
        next_action="Implement the frozen protocol and proceed only through an existing entry point within current authorization; the CLI does not dispatch.",
    )
    print(json.dumps({"registered": experiment_id, "dispatched": False, "evidence_class": record["evidence_class"], "hypothesis_id": candidate["hypothesis_id"], "budget_reserved_at_preregistration": record["budget"]}, indent=2))
    return 0


@registry_locked
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
            status="ready_for_hypothesis_selection",
            current_round={
                "owner": current_round.get("owner"),
                "terminal_artifact": str(target.relative_to(ROOT)).replace("\\", "/"),
                "status": "terminal_historical_closeout_reconciled",
                "integrity_decision": imported["terminal_decision"],
                "evidence_classes": imported["evidence_classes"],
                "historical_model_calls": imported["historical_model_calls"],
                "historical_external_cost_usd": imported["historical_external_cost_usd"],
                "note": "Imported historical usage is not current authorization and does not count toward new-cycle allowance.",
            },
            latest_decision=imported["terminal_decision"],
            latest_decision_type="historical_integrity",
            latest_scientific_outcome=None,
            next_action=imported["recommended_next_action"],
        )
        print(json.dumps({"imported_handoff": handoff_id, "historical_calls_reauthorized": False, "dispatched": False}, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def expected_cycle_memory() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for directory in cycle_dirs():
        closure_path = directory / "closure.json"
        if not closure_path.exists():
            continue
        closure = load_json(closure_path)
        updates = closure.get("belief_updates", []) if isinstance(closure, dict) else []
        if not isinstance(updates, list):
            continue
        for update in updates:
            if not isinstance(update, dict):
                continue
            entries.append(
                {
                    "experiment_id": closure.get("experiment_id"),
                    "scientific_outcome": closure.get("scientific_outcome"),
                    **update,
                }
            )
    return entries


def sync_cycle_memory() -> None:
    memory = load_json(MEMORY_PATH)
    memory["cycle_updates"] = expected_cycle_memory()
    memory["updated_at"] = datetime.now(timezone.utc).date().isoformat()
    save_json_atomic(MEMORY_PATH, memory)


@registry_locked
def command_sync_memory(_: argparse.Namespace) -> int:
    sync_cycle_memory()
    print(json.dumps({"cycle_memory_entries": len(expected_cycle_memory()), "source": "closed cycle records", "scientific_validity": "not_assessed_by_sync"}, indent=2))
    return 0


@registry_locked
def command_next(_: argparse.Namespace) -> int:
    state = load_json(STATE_PATH)
    open_ids = [
        directory.name
        for directory in cycle_dirs()
        if (directory / "preregistration.json").exists() and not (directory / "closure.json").exists()
    ]
    continuation = continuation_plan(state, open_ids)
    result = {
        **continuation,
        "goal_should_continue": state.get("program_status") != "complete",
        "dispatched": False,
        "reason": "Scientific outcomes and phase gates do not complete the program Goal; only a separate completion review can do so.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


@registry_locked
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
        manifest_errors = verify_registration_manifest(directory, prereg)
        if manifest_errors:
            print_errors(manifest_errors)
            return 1
        budget = budget_record()
        prereg = dict(prereg)
        approval_id = prereg.get("authorization", {}).get("approval_id")
        batch = authorization_batch(approval_id) if approval_id else None
        if batch:
            prereg["_resolved_authorization_batch_sha256"] = hashlib.sha256(
                (AUTHORIZATIONS / f"{approval_id}.json").read_bytes()
            ).hexdigest()
            if prereg.get("authorization_batch_sha256") != prereg["_resolved_authorization_batch_sha256"]:
                raise ValueError("immutable authorization batch hash changed after preregistration")
        by_approval, prior_project_calls, prior_project_cost = usage_totals(exclude_id=experiment_id)
        prior_batch_calls, prior_batch_cost = by_approval.get(approval_id, (0, 0.0)) if approval_id else (0, 0.0)
        errors = validate_closure(
            prereg,
            closure,
            ROOT,
            batch,
            prior_batch_calls,
            prior_batch_cost,
            budget.get("project_limits", {}),
            prior_project_calls,
            prior_project_cost,
        )
        if errors:
            print_errors(errors)
            return 1
        state = load_json(STATE_PATH)
        no_progress = state.get("consecutive_cycles_without_new_uncertainty_reduction", 0)
        material = closure.get("material_update", {})
        credited_update = (
            isinstance(material, dict)
            and material.get("independent_critic_confirmed") is True
            and closure.get("review_mode") == "independent"
            and bool(material.get("evidence_refs"))
        )
        if credited_update:
            no_progress = 0
        else:
            no_progress += 1
        if no_progress >= 3 and closure["decision"] not in {"PIVOT", "BLOCKED"}:
            print("ERROR: after three cycles without an independently reviewed material update, decision must pivot or block", file=sys.stderr)
            return 1
        saved = dict(closure)
        saved["authorization_id"] = approval_id
        saved["closed_at_utc"] = now_utc()
        saved["closed_git_head"] = git_head()
        save_json_atomic(closure_path, saved)
        registration_manifest = load_json(directory / "registration.json")
        registration_manifest["closure_sha256"] = file_sha256(closure_path)
        registration_manifest["closed_at_utc"] = saved["closed_at_utc"]
        registration_manifest["closed_git_head"] = saved["closed_git_head"]
        save_json_atomic(directory / "registration.json", registration_manifest)
        hypotheses = load_json(HYPOTHESES_PATH)
        terminal_hypothesis_status = {
            "SUPPORTED": "supported",
            "REFUTED": "refuted",
        }.get(saved["scientific_outcome"], "candidate")
        for hypothesis in hypotheses.get("candidates", []):
            if hypothesis.get("hypothesis_id") == prereg.get("hypothesis_id"):
                hypothesis["status"] = terminal_hypothesis_status
        hypotheses["selected_hypothesis_id"] = None
        save_json_atomic(HYPOTHESES_PATH, hypotheses)
        sync_cycle_memory()
        update_state(
            status=(
                "diagnosing_invalid_experiment"
                if saved["scientific_outcome"] == "INVALID_EXPERIMENT"
                else "continuing_after_execution_boundary"
                if saved["scientific_outcome"] in {"EXECUTION_BLOCKED", "RESOURCE_BLOCKED"}
                else "ready_for_next_cycle"
            ),
            active_experiment_id=None,
            active_hypothesis_id=None,
            latest_closed_experiment_id=experiment_id,
            latest_decision=saved["decision"],
            latest_decision_type="operational",
            latest_scientific_outcome=saved["scientific_outcome"],
            next_action=saved["next_action"],
            consecutive_cycles_without_new_uncertainty_reduction=no_progress,
            **(
                {"current_round": {"owner": prereg.get("source_task", "imported current round"), "terminal_artifact": f"research/experiments/{experiment_id}/closure.json", "status": "closeout_recorded", "note": "Terminal result and audit references were registered and hash-checked."}}
                if prereg.get("closes_current_handoff") is True
                else {}
            ),
        )
        print(json.dumps({"closed": experiment_id, "decision": saved["decision"], "scientific_outcome": saved["scientific_outcome"], "material_update_credited": credited_update, "program_goal_complete": False, "scientific_result_certified": False}, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


def validate_hypothesis_registry(root: Path) -> list[str]:
    errors: list[str] = []
    if not HYPOTHESES_PATH.exists():
        return ["research/hypotheses.json is missing"]
    registry = load_json(HYPOTHESES_PATH)
    if not isinstance(registry, dict) or registry.get("schema_version") != 1:
        return ["research/hypotheses.json must be schema_version 1"]
    candidates = registry.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 3:
        return ["hypotheses.json candidates must be a list of at most three candidates"]
    seen: set[str] = set()
    selected: list[str] = []
    for index, item in enumerate(candidates):
        label = f"hypotheses.candidates[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object")
            continue
        hypothesis_id = item.get("hypothesis_id")
        if not isinstance(hypothesis_id, str) or not EXPERIMENT_ID_RE.fullmatch(hypothesis_id):
            errors.append(f"{label}.hypothesis_id must be a safe identifier")
        elif hypothesis_id in seen:
            errors.append(f"duplicate hypothesis_id: {hypothesis_id}")
        else:
            seen.add(hypothesis_id)
        if item.get("status") not in {"candidate", "selected", "supported", "refuted", "retired"}:
            errors.append(f"{label}.status is not registered")
        if item.get("status") == "selected":
            selected.append(hypothesis_id)
        for key in ("title", "hypothesis", "discriminating_prediction", "selection_note"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{label}.{key} must be a non-empty string")
        rivals = item.get("competing_explanations")
        if not isinstance(rivals, list) or len(rivals) < 2 or any(not isinstance(x, str) or not x.strip() for x in rivals):
            errors.append(f"{label}.competing_explanations must contain at least two alternatives")
        errors.extend(v1._check_hashed_files(item.get("evidence_refs"), root, f"{label}.evidence_refs", require_one=True))
    if len(selected) > 1:
        errors.append("at most one formal hypothesis may be selected")
    if registry.get("selected_hypothesis_id") not in (None, *selected):
        errors.append("selected_hypothesis_id disagrees with candidate status")
    return errors


def validate_memory(root: Path) -> list[str]:
    errors: list[str] = []
    if not MEMORY_PATH.exists():
        return ["research/memory.json is missing"]
    memory = load_json(MEMORY_PATH)
    if not isinstance(memory, dict) or memory.get("schema_version") != 1:
        return ["research/memory.json must be schema_version 1"]
    beliefs = memory.get("beliefs")
    if not isinstance(beliefs, list):
        errors.append("research/memory.json beliefs must be a list")
    else:
        seen: set[str] = set()
        for index, belief in enumerate(beliefs):
            label = f"memory.beliefs[{index}]"
            if not isinstance(belief, dict):
                errors.append(f"{label} must be an object")
                continue
            claim_id = belief.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id.strip():
                errors.append(f"{label}.claim_id must be a non-empty string")
            elif claim_id in seen:
                errors.append(f"duplicate memory claim_id: {claim_id}")
            else:
                seen.add(claim_id)
            if belief.get("outcome") not in {"SUPPORTED", "REFUTED", "INCONCLUSIVE", "INVALID_EXPERIMENT", "EXECUTION_BLOCKED", "RESOURCE_BLOCKED"}:
                errors.append(f"{label}.outcome must use the scientific outcome vocabulary")
            for key in ("claim", "interpretation", "scope"):
                if not isinstance(belief.get(key), str) or not belief[key].strip():
                    errors.append(f"{label}.{key} must be a non-empty string")
            errors.extend(v1._check_hashed_files(belief.get("evidence_refs"), root, f"{label}.evidence_refs", require_one=True))
    cycle_updates = memory.get("cycle_updates")
    if not isinstance(cycle_updates, list):
        errors.append("research/memory.json cycle_updates must be a list")
    elif cycle_updates != expected_cycle_memory():
        errors.append("research/memory.json cycle_updates do not match closed experiment records; run researchctl.py sync-memory")
    return errors


@registry_locked
def command_audit(_: argparse.Namespace) -> int:
    errors: list[str] = []
    budget = budget_record()
    state = load_json(STATE_PATH)
    errors.extend(validate_hypothesis_registry(ROOT))
    errors.extend(validate_memory(ROOT))
    if AUTHORIZATIONS.exists():
        for batch_path in sorted(AUTHORIZATIONS.glob("*.json")):
            batch = load_json(batch_path)
            errors.extend(f"authorization {batch_path.stem}: {error}" for error in validate_authorization_batch(batch))
            if isinstance(batch, dict) and batch.get("approval_id") != batch_path.stem:
                errors.append(f"authorization {batch_path.stem}: filename does not match approval_id")
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
    by_approval: dict[str, tuple[int, float]] = {}
    for directory in cycle_dirs():
        prereg_path = directory / "preregistration.json"
        closure_path = directory / "closure.json"
        if not prereg_path.exists():
            errors.append(f"{directory.name}: missing preregistration.json")
            continue
        prereg = load_json(prereg_path)
        prereg_errors = validate_preregistration(prereg, ROOT)
        errors.extend(f"{directory.name}: {error}" for error in prereg_errors)
        errors.extend(verify_registration_manifest(directory, prereg) if isinstance(prereg, dict) else [])
        if prereg_errors or not isinstance(prereg, dict):
            continue
        if prereg.get("experiment_id") != directory.name:
            errors.append(f"{directory.name}: folder name does not match experiment_id")
        approval_id = prereg.get("authorization", {}).get("approval_id")
        batch = authorization_batch(approval_id) if approval_id else None
        if batch:
            batch_hash = hashlib.sha256((AUTHORIZATIONS / f"{approval_id}.json").read_bytes()).hexdigest()
            if prereg.get("authorization_batch_sha256") != batch_hash:
                errors.append(f"{directory.name}: authorization batch hash changed after registration")
            prereg["_resolved_authorization_batch_sha256"] = batch_hash
        elif prereg.get("budget", {}).get("max_model_calls", 0) or prereg.get("budget", {}).get("max_external_cost_usd", 0):
            errors.append(f"{directory.name}: non-zero preregistered budget has no immutable authorization batch")
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
        prior_batch_calls, prior_batch_cost = by_approval.get(approval_id, (0, 0.0)) if approval_id else (0, 0.0)
        errors.extend(f"{directory.name}: {error}" for error in validate_closure(
            prereg,
            closure,
            ROOT,
            batch,
            prior_batch_calls,
            prior_batch_cost,
            budget.get("project_limits", {}),
            total_calls,
            total_cost,
        ))
        total_calls += local_calls
        total_cost += local_cost
        if isinstance(approval_id, str):
            by_approval[approval_id] = (prior_batch_calls + local_calls, prior_batch_cost + local_cost)
    if len(open_ids) > 1:
        errors.append("more than one experiment is open")
    expected_active = open_ids[0] if open_ids else None
    if state.get("active_experiment_id") != expected_active:
        errors.append("research/state.json active_experiment_id disagrees with registry")
    active_hypothesis = state.get("active_hypothesis_id")
    if expected_active is None and active_hypothesis is not None:
        errors.append("research/state.json has an active hypothesis without an open experiment")
    if expected_active is not None:
        open_prereg = load_json(EXPERIMENTS / expected_active / "preregistration.json")
        if active_hypothesis != open_prereg.get("hypothesis_id"):
            errors.append("research/state.json active_hypothesis_id disagrees with the open preregistration")
    handoff_paths = sorted(handoffs_dir.glob("*.json")) if handoffs_dir.exists() else []
    current_round = state.get("current_round", {})
    if current_round.get("status") in {"closeout_imported", "terminal_historical_closeout_reconciled"}:
        terminal_path = current_round.get("terminal_artifact")
        if not isinstance(terminal_path, str) or not (ROOT / terminal_path).is_file():
            errors.append("state references a missing imported closeout")
        elif terminal_path not in {str(item.relative_to(ROOT)).replace("\\", "/") for item in handoff_paths}:
            errors.append("state terminal closeout is not one of the validated handoff packets")
    elif handoff_paths:
        errors.append("handoff packet exists but state does not record its import")
    project_limits = budget.get("project_limits", {})
    reserved_calls = sum(
        load_json(EXPERIMENTS / experiment_id / "preregistration.json").get("budget", {}).get("max_model_calls", 0)
        for experiment_id in open_ids
    )
    reserved_cost = sum(
        float(load_json(EXPERIMENTS / experiment_id / "preregistration.json").get("budget", {}).get("max_external_cost_usd", 0.0))
        for experiment_id in open_ids
    )
    if total_calls + reserved_calls > project_limits.get("max_model_calls", 0):
        errors.append("actual plus reserved model calls exceed the project-wide lifetime ceiling")
    if total_cost + reserved_cost > project_limits.get("max_external_cost_usd", 0.0) + 1e-9:
        errors.append("actual plus reserved cost exceeds the project-wide lifetime ceiling")
    for approval_id, (used_calls, used_cost) in by_approval.items():
        batch = authorization_batch(approval_id)
        if batch and used_calls > batch.get("max_model_calls", 0):
            errors.append(f"authorization {approval_id}: cumulative calls exceed its immutable cap")
        if batch and used_cost > batch.get("max_external_cost_usd", 0.0) + 1e-9:
            errors.append(f"authorization {approval_id}: cumulative cost exceeds its immutable cap")
    report = {
        "integrity_check": "FAIL" if errors else "PASS",
        "scientific_validity": "NOT_EVALUATED",
        "registered_cycles": len(cycle_dirs()),
        "open_experiments": open_ids,
        "new_iteration_usage": {"model_calls": total_calls, "external_cost_usd": round(total_cost, 10)},
        "usage_by_approval_id": {key: {"model_calls": value[0], "external_cost_usd": round(value[1], 10)} for key, value in by_approval.items()},
        "project_limits": project_limits,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


def print_errors(errors: list[str]) -> None:
    print("RECORD REJECTED:", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="ColluScope research coordinator (records and gates cycles; never executes experiments)")
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
    next_parser = subparsers.add_parser("next", help="show the next continuation step without dispatching work")
    next_parser.set_defaults(func=command_next)
    memory_parser = subparsers.add_parser("sync-memory", help="rebuild the cycle-memory projection from closed records")
    memory_parser.set_defaults(func=command_sync_memory)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
