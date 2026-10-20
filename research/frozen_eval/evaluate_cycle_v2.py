"""Versioned research-cycle gates with typed outcomes and grant-aware ledgers.

This validates record structure and provenance. It does not judge whether a
scientific inference is true, nor does it execute an experiment.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import evaluate_cycle as v1


SCIENTIFIC_OUTCOMES = {
    "SUPPORTED",
    "REFUTED",
    "INCONCLUSIVE",
    "INVALID_EXPERIMENT",
    "EXECUTION_BLOCKED",
    "RESOURCE_BLOCKED",
}
BELIEF_UPDATE_OUTCOMES = {"SUPPORTED", "REFUTED", "INCONCLUSIVE", "UNCHANGED"}
NEXT_ACTION_KINDS = {
    "continue_hypothesis",
    "test_rival",
    "pivot",
    "diagnose_invalid",
    "continue_offline",
    "await_authorization",
    "await_resource",
    "synthesize",
}
SHA256_RE = v1.SHA256_RE
EXPERIMENT_ID_RE = v1.EXPERIMENT_ID_RE
TERMINAL_STATUS_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,40}$")


def parse_utc(value: Any, label: str) -> tuple[datetime | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, f"{label} must be an ISO-8601 UTC timestamp"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None, f"{label} must be an ISO-8601 UTC timestamp"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, f"{label} must include a UTC offset"
    return parsed.astimezone(timezone.utc), None


def validate_authorization_batch(record: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["authorization batch must be a JSON object"]
    required = {
        "schema_version",
        "approval_id",
        "scope",
        "authorized_experiment_ids",
        "max_model_calls",
        "max_external_cost_usd",
        "approved_at_utc",
        "expires_at_utc",
        "source",
    }
    errors.extend(f"missing authorization batch field: {key}" for key in sorted(required - record.keys()))
    if record.get("schema_version") != 1:
        errors.append("authorization batch schema_version must equal 1")
    approval_id = record.get("approval_id")
    if not isinstance(approval_id, str) or not approval_id.strip() or "/" in approval_id or "\\" in approval_id:
        errors.append("approval_id must be a non-empty safe identifier")
    for key in ("scope", "source"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f"authorization batch {key} must be a non-empty string")
    ids = record.get("authorized_experiment_ids")
    if not isinstance(ids, list) or not ids:
        errors.append("authorized_experiment_ids must be a non-empty list")
    elif any(not isinstance(item, str) or not EXPERIMENT_ID_RE.fullmatch(item) for item in ids) or len(set(ids)) != len(ids):
        errors.append("authorized_experiment_ids must contain unique safe experiment IDs")
    calls = record.get("max_model_calls")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls <= 0:
        errors.append("authorization max_model_calls must be a positive integer")
    cost = record.get("max_external_cost_usd")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        errors.append("authorization max_external_cost_usd must be finite and non-negative")
    approved, approved_error = parse_utc(record.get("approved_at_utc"), "approved_at_utc")
    expires, expires_error = parse_utc(record.get("expires_at_utc"), "expires_at_utc")
    if approved_error:
        errors.append(approved_error)
    if expires_error:
        errors.append(expires_error)
    if approved is not None and expires is not None and expires <= approved:
        errors.append("authorization expiry must be later than approval time")
    return errors


def validate_preregistration(record: Any, root: Path) -> list[str]:
    if not isinstance(record, dict):
        return ["preregistration must be a JSON object"]
    errors: list[str] = []
    legacy = dict(record)
    legacy["schema_version"] = 1
    errors.extend(v1.validate_preregistration(legacy, root))
    if record.get("schema_version") != 2:
        errors.append("schema_version must equal 2 for the current preregistration policy")
    for key in ("hypothesis_id", "research_branch_id", "selection_rationale"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key} must be a non-empty string")
    for key in ("hypothesis_id", "research_branch_id"):
        value = record.get(key)
        if isinstance(value, str) and value.strip() and not EXPERIMENT_ID_RE.fullmatch(value):
            errors.append(f"{key} must use 3-64 safe filename characters")
    authorization = record.get("authorization", {})
    planned = record.get("budget", {})
    calls = planned.get("max_model_calls", 0) if isinstance(planned, dict) else 0
    cost = planned.get("max_external_cost_usd", 0) if isinstance(planned, dict) else 0
    paid_scope = (isinstance(calls, int) and not isinstance(calls, bool) and calls > 0) or (
        isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost > 0
    )
    if paid_scope:
        if authorization.get("approval_required") is not True or not authorization.get("approval_id"):
            errors.append("a non-zero model/cost ceiling requires an explicit approval_id")
    elif authorization.get("approval_id") is not None:
        errors.append("zero-call cycles may not carry a historical approval_id")
    return errors


def _validate_request_ledger(
    closure: dict[str, Any],
    preregistration: dict[str, Any],
    root: Path,
    authorization_batch: dict[str, Any] | None,
) -> tuple[list[str], int, Decimal]:
    errors: list[str] = []
    calls = closure.get("actual_model_calls")
    cost_raw = closure.get("actual_external_cost_usd")
    ledger_ref = closure.get("model_request_ledger")
    if not isinstance(calls, int) or isinstance(calls, bool) or calls < 0:
        return ["actual_model_calls must be a non-negative integer"], 0, Decimal("0")
    try:
        claimed_cost = Decimal(str(cost_raw))
    except (InvalidOperation, ValueError):
        claimed_cost = Decimal("NaN")
    if not claimed_cost.is_finite() or claimed_cost < 0:
        errors.append("actual_external_cost_usd must be finite and non-negative")
    if calls == 0:
        if claimed_cost != 0:
            errors.append("zero model/API calls cannot have a non-zero external cost")
        if ledger_ref is not None:
            errors.append("model_request_ledger must be null when actual_model_calls is zero")
        return errors, 0, Decimal("0")
    errors.extend(v1._check_hashed_files([ledger_ref], root, "model_request_ledger", require_one=True))
    if not isinstance(ledger_ref, dict) or not isinstance(ledger_ref.get("path"), str):
        return errors, 0, Decimal("0")
    ledger_path, path_error = v1._safe_file(root, ledger_ref.get("path"))
    if path_error or ledger_path is None:
        return errors, 0, Decimal("0")
    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"model request ledger cannot be read: {error}")
        return errors, 0, Decimal("0")
    rows = ledger.get("requests") if isinstance(ledger, dict) else None
    if not isinstance(ledger, dict) or ledger.get("schema_version") != 1 or not isinstance(rows, list):
        errors.append("model request ledger must contain schema_version 1 and a requests list")
        return errors, 0, Decimal("0")
    ledger_fields = {"schema_version", "experiment_id", "requests"}
    if set(ledger) - ledger_fields:
        errors.append("model request ledger contains unsupported fields; raw payloads are forbidden")
    if ledger.get("experiment_id") != preregistration.get("experiment_id"):
        errors.append("model request ledger experiment_id does not match preregistration")
    if len(rows) != calls:
        errors.append("model request ledger row count must equal actual_model_calls, including failures/retries")
    request_hashes: set[str] = set()
    ledger_cost = Decimal("0")
    approved_at = None
    preregistered_at = None
    expiry = None
    if authorization_batch:
        approved_at, approved_error = parse_utc(authorization_batch.get("approved_at_utc"), "approved_at_utc")
        if approved_error:
            errors.append(approved_error)
        expiry, expiry_error = parse_utc(authorization_batch.get("expires_at_utc"), "expires_at_utc")
        if expiry_error:
            errors.append(expiry_error)
        preregistered_at, preregistered_error = parse_utc(preregistration.get("registered_at_utc"), "registered_at_utc")
        if preregistered_error:
            errors.append(preregistered_error)
    for index, row in enumerate(rows):
        label = f"model_request_ledger.requests[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object")
            continue
        allowed_row_fields = {
            "experiment_id",
            "attempt_id_sha256",
            "started_at_utc",
            "terminal_status",
            "external_cost_usd",
        }
        if set(row) - allowed_row_fields:
            errors.append(f"{label} contains unsupported fields; raw request/response content is forbidden")
        if row.get("experiment_id") != preregistration.get("experiment_id"):
            errors.append(f"{label}.experiment_id does not match preregistration")
        request_hash = row.get("attempt_id_sha256")
        if not isinstance(request_hash, str) or not SHA256_RE.fullmatch(request_hash):
            errors.append(f"{label}.attempt_id_sha256 must be lowercase SHA-256")
        elif request_hash in request_hashes:
            errors.append(f"{label}.attempt_id_sha256 duplicates a physical attempt")
        else:
            request_hashes.add(request_hash)
        started, started_error = parse_utc(row.get("started_at_utc"), f"{label}.started_at_utc")
        if started_error:
            errors.append(started_error)
        if started is not None and approved_at is not None and started < approved_at:
            errors.append(f"{label} started before the approval batch was granted")
        if started is not None and preregistered_at is not None and started < preregistered_at:
            errors.append(f"{label} started before the preregistration was frozen")
        if started is not None and expiry is not None and started > expiry:
            errors.append(f"{label} started after its approval expired")
        status = row.get("terminal_status")
        if not isinstance(status, str) or not TERMINAL_STATUS_RE.fullmatch(status):
            errors.append(f"{label}.terminal_status must be a short sanitized code, including for failures")
        try:
            row_cost = Decimal(str(row.get("external_cost_usd")))
        except (InvalidOperation, ValueError):
            row_cost = Decimal("NaN")
        if not row_cost.is_finite() or row_cost < 0:
            errors.append(f"{label}.external_cost_usd must be finite and non-negative")
        else:
            ledger_cost += row_cost
    if claimed_cost.is_finite() and abs(ledger_cost - claimed_cost) > Decimal("0.0000001"):
        errors.append("request ledger external costs do not sum to actual_external_cost_usd")
    return errors, len(rows), ledger_cost


def validate_closure(
    preregistration: dict[str, Any],
    closure: Any,
    root: Path,
    authorization_batch: dict[str, Any] | None,
    prior_batch_calls: int,
    prior_batch_cost: float,
    project_limits: dict[str, Any],
    prior_project_calls: int,
    prior_project_cost: float,
) -> list[str]:
    if not isinstance(closure, dict):
        return ["closure must be a JSON object"]
    errors: list[str] = []
    required = {
        "scientific_outcome",
        "outcome_rationale",
        "belief_updates",
        "material_update",
        "next_action_kind",
        "authorization_id",
        "model_request_ledger",
    }
    errors.extend(f"missing closure field: {key}" for key in sorted(required - closure.keys()))
    if closure.get("schema_version") != 2:
        errors.append("closure schema_version must equal 2 for the current closure policy")
    if closure.get("scientific_outcome") not in SCIENTIFIC_OUTCOMES:
        errors.append("scientific_outcome must use the typed scientific outcome vocabulary")
    for key in ("outcome_rationale",):
        if not isinstance(closure.get(key), str) or not closure[key].strip():
            errors.append(f"{key} must be a non-empty string")
    action_kind = closure.get("next_action_kind")
    if action_kind not in NEXT_ACTION_KINDS:
        errors.append("next_action_kind is not a registered continuation action")
    outcome = closure.get("scientific_outcome")
    if outcome == "INVALID_EXPERIMENT" and action_kind != "diagnose_invalid":
        errors.append("INVALID_EXPERIMENT must continue with diagnose_invalid")
    if outcome in {"EXECUTION_BLOCKED", "RESOURCE_BLOCKED"} and action_kind not in {
        "continue_offline",
        "await_authorization",
        "await_resource",
    }:
        errors.append("blocked outcomes must preserve a permitted offline step or name the exact boundary to await")

    updates = closure.get("belief_updates")
    claim_updates: dict[str, dict[str, Any]] = {}
    if not isinstance(updates, list):
        errors.append("belief_updates must be a list")
    else:
        seen_claims: set[str] = set()
        for index, update in enumerate(updates):
            label = f"belief_updates[{index}]"
            if not isinstance(update, dict):
                errors.append(f"{label} must be an object")
                continue
            claim_id = update.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id.strip():
                errors.append(f"{label}.claim_id must be a non-empty string")
            elif claim_id in seen_claims:
                errors.append(f"belief_updates contains duplicate claim_id: {claim_id}")
            else:
                seen_claims.add(claim_id)
                claim_updates[claim_id] = update
            if update.get("outcome") not in BELIEF_UPDATE_OUTCOMES:
                errors.append(f"{label}.outcome must be SUPPORTED, REFUTED, INCONCLUSIVE, or UNCHANGED")
            for key in ("statement", "what_changed", "remaining_alternatives"):
                if not isinstance(update.get(key), str) or not update[key].strip():
                    errors.append(f"{label}.{key} must be a non-empty string")
            refs = update.get("evidence_refs")
            if not isinstance(refs, list):
                errors.append(f"{label}.evidence_refs must be a list")
            elif update.get("outcome") in {"SUPPORTED", "REFUTED", "INCONCLUSIVE"} and not refs:
                errors.append(f"{label} needs hash-pinned evidence for a scientific update")
            else:
                errors.extend(v1._check_hashed_files(refs, root, f"{label}.evidence_refs", require_one=False))

    material = closure.get("material_update")
    qualifies_as_progress = False
    if not isinstance(material, dict):
        errors.append("material_update must be a structured object")
    else:
        for key in ("claim_id", "what_changed", "remaining_alternatives"):
            if not isinstance(material.get(key), str) or not material[key].strip():
                errors.append(f"material_update.{key} must be a non-empty string; use an explicit no-change statement")
        refs = material.get("evidence_refs")
        if not isinstance(refs, list):
            errors.append("material_update.evidence_refs must be a list")
        elif refs:
            errors.extend(v1._check_hashed_files(refs, root, "material_update.evidence_refs", require_one=True))
        confirmed = material.get("independent_critic_confirmed")
        if not isinstance(confirmed, bool):
            errors.append("material_update.independent_critic_confirmed must be boolean")
        qualifies_as_progress = (
            confirmed is True
            and bool(refs)
            and closure.get("review_mode") == "independent"
            and isinstance(closure.get("review_artifact"), dict)
        )
        if confirmed is True and not qualifies_as_progress:
            errors.append("credited material progress requires hash-pinned evidence and an independent review artifact")
        if qualifies_as_progress:
            linked_update = claim_updates.get(material.get("claim_id"))
            if linked_update is None or linked_update.get("outcome") == "UNCHANGED":
                errors.append("credited material progress must reference a non-UNCHANGED belief_updates entry")

    ledger_errors, _, _ = _validate_request_ledger(closure, preregistration, root, authorization_batch)
    errors.extend(ledger_errors)
    calls = closure.get("actual_model_calls")
    cost = closure.get("actual_external_cost_usd")
    prereg_auth = preregistration.get("authorization", {})
    expected_approval_id = prereg_auth.get("approval_id") if isinstance(prereg_auth, dict) else None
    if closure.get("authorization_id") != expected_approval_id:
        errors.append("closure authorization_id must match the preregistration snapshot")
    if isinstance(calls, int) and not isinstance(calls, bool) and calls > 0:
        if authorization_batch is None:
            errors.append("non-zero model/API calls require an immutable authorization batch")
        else:
            errors.extend(validate_authorization_batch(authorization_batch))
            if preregistration.get("experiment_id") not in authorization_batch.get("authorized_experiment_ids", []):
                errors.append("authorization batch does not name this experiment")
            scope = prereg_auth.get("scope") if isinstance(prereg_auth, dict) else None
            if scope != authorization_batch.get("scope"):
                errors.append("preregistration scope does not exactly match the approved scope")
            if expected_approval_id != authorization_batch.get("approval_id"):
                errors.append("preregistration approval_id does not match the immutable batch")
            batch_hash = preregistration.get("authorization_batch_sha256")
            if not isinstance(batch_hash, str) or batch_hash != preregistration.get("_resolved_authorization_batch_sha256"):
                errors.append("preregistration approval batch hash is missing or changed")
            max_calls = authorization_batch.get("max_model_calls", 0)
            max_cost = authorization_batch.get("max_external_cost_usd", 0.0)
            if isinstance(max_calls, int) and prior_batch_calls + calls > max_calls:
                errors.append("model calls exceed this approval batch's cumulative ceiling")
            if isinstance(max_cost, (int, float)) and isinstance(cost, (int, float)) and prior_batch_cost + float(cost) > max_cost + 1e-9:
                errors.append("external cost exceeds this approval batch's cumulative ceiling")
    project_calls = project_limits.get("max_model_calls", 0)
    project_cost = project_limits.get("max_external_cost_usd", 0.0)
    if isinstance(calls, int) and not isinstance(calls, bool) and prior_project_calls + calls > project_calls:
        errors.append("cumulative model calls exceed the project-wide lifetime ceiling")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool) and prior_project_cost + float(cost) > project_cost + 1e-9:
        errors.append("cumulative external cost exceeds the project-wide lifetime ceiling")

    legacy_prereg = dict(preregistration)
    legacy_prereg["schema_version"] = 1
    legacy_closure = dict(closure)
    legacy_closure["schema_version"] = 1
    legacy_closure["new_uncertainty_reduced"] = qualifies_as_progress
    synthetic_auth_id = expected_approval_id or "record-only-zero-call"
    legacy_budget = {
        "authorization": {
            "status": "active" if isinstance(calls, int) and calls > 0 else "none",
            "approval_id": synthetic_auth_id,
            "authorized_experiment_ids": [preregistration.get("experiment_id")],
            "max_model_calls": max(1_000_000, (calls if isinstance(calls, int) else 0) + 1),
            "max_external_cost_usd": max(1_000_000.0, (float(cost) if isinstance(cost, (int, float)) and math.isfinite(cost) else 0.0) + 1.0),
        }
    }
    errors.extend(v1.validate_closure(legacy_prereg, legacy_closure, root, legacy_budget, 0, 0.0))
    return errors


validate_handoff_packet = v1.validate_handoff_packet
