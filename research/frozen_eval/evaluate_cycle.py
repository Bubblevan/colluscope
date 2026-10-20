"""Frozen integrity gates for ColluScope preregistration/closure records.

This checks protocol compliance, not scientific validity or collusion.
"""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any


EVIDENCE_CLASSES = {
    "scripted_mock",
    "live_engineering_preflight",
    "real_llm_behavior",
    "monitor_evaluation",
    "offline_reanalysis",
}
DECISIONS = {"PASS", "FAIL", "AMBIGUOUS", "BLOCKED", "PIVOT"}
HANDOFF_DECISIONS = DECISIONS | {"GO", "NO-GO"}
REVIEW_MODES = {"independent", "adversarial_self_review", "not_run"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPERIMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


def _safe_file(root: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "path must be a non-empty repository-relative string"
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        return None, f"unsafe repository path: {value}"
    if candidate.parts and candidate.parts[0].lower() in {"runs", "logs", "reference", ".git", ".aws", ".codex"}:
        return None, f"private or local-only path cannot be registered: {value}"
    if value.lower() == ".env" or value.lower().endswith("/.env"):
        return None, f"secret-bearing path cannot be registered: {value}"
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        return None, f"path escapes repository: {value}"
    if not resolved.is_file():
        return None, f"registered file does not exist: {value}"
    return resolved, None


def _check_hashed_files(
    entries: Any, root: Path, label: str, *, require_one: bool
) -> list[str]:
    errors: list[str] = []
    if not isinstance(entries, list) or (require_one and not entries):
        return [f"{label} must be a non-empty list" if require_one else f"{label} must be a list"]
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"{label}[{index}] must be an object")
            continue
        path_text = entry.get("path")
        path, path_error = _safe_file(root, path_text)
        if path_error:
            errors.append(f"{label}[{index}]: {path_error}")
            continue
        assert path is not None
        if path_text in seen:
            errors.append(f"{label} contains duplicate path: {path_text}")
            continue
        seen.add(path_text)
        expected = entry.get("sha256")
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            errors.append(f"{label}[{index}].sha256 must be lowercase SHA-256")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(f"{label}[{index}] hash mismatch: {path_text}")
    return errors


def validate_preregistration(record: Any, root: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["preregistration must be a JSON object"]
    required = {
        "schema_version",
        "experiment_id",
        "title",
        "evidence_class",
        "research_question",
        "hypothesis",
        "competing_explanations",
        "prior_evidence",
        "protocol",
        "budget",
        "authorization",
    }
    errors.extend(f"missing preregistration field: {key}" for key in sorted(required - record.keys()))
    if isinstance(record.get("schema_version"), bool) or record.get("schema_version") != 1:
        errors.append("schema_version must equal 1")
    experiment_id = record.get("experiment_id")
    if not isinstance(experiment_id, str) or not EXPERIMENT_ID_RE.fullmatch(experiment_id):
        errors.append("experiment_id must be 3-64 safe filename characters")
    if not isinstance(record.get("evidence_class"), str) or record.get("evidence_class") not in EVIDENCE_CLASSES:
        errors.append("evidence_class is not one of the registered evidence levels")
    for key in ("title", "research_question", "hypothesis"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append(f"{key} must be a non-empty string")
    alternatives = record.get("competing_explanations")
    if not isinstance(alternatives, list) or not alternatives or any(not isinstance(x, str) or not x.strip() for x in alternatives):
        errors.append("competing_explanations must contain at least one concrete alternative")

    prior = record.get("prior_evidence")
    if not isinstance(prior, list) or not prior:
        errors.append("prior_evidence must be a non-empty list")
    else:
        for index, item in enumerate(prior):
            if not isinstance(item, dict) or not isinstance(item.get("claim"), str) or not item["claim"].strip():
                errors.append(f"prior_evidence[{index}] must contain path, sha256, and claim")
        errors.extend(_check_hashed_files(prior, root, "prior_evidence", require_one=True))

    protocol = record.get("protocol")
    protocol_fields = {
        "sample_selection",
        "intervention",
        "held_constant",
        "primary_outcome",
        "denominator",
        "success_gate",
        "failure_gate",
        "ambiguous_gate",
        "analysis_plan",
        "reproduction_command",
        "runtime_identity",
        "frozen_inputs",
    }
    if not isinstance(protocol, dict):
        errors.append("protocol must be an object")
    else:
        errors.extend(f"missing protocol field: {key}" for key in sorted(protocol_fields - protocol.keys()))
        for key in ("sample_selection", "intervention", "primary_outcome", "denominator", "success_gate", "failure_gate", "ambiguous_gate", "analysis_plan", "reproduction_command", "runtime_identity"):
            if not isinstance(protocol.get(key), str) or not protocol[key].strip():
                errors.append(f"protocol.{key} must be a non-empty string")
        held = protocol.get("held_constant")
        if not isinstance(held, list) or not held or any(not isinstance(x, str) or not x.strip() for x in held):
            errors.append("protocol.held_constant must be a non-empty list")
        errors.extend(_check_hashed_files(protocol.get("frozen_inputs"), root, "protocol.frozen_inputs", require_one=True))

    budget = record.get("budget")
    if not isinstance(budget, dict):
        errors.append("budget must be an object")
    else:
        calls = budget.get("max_model_calls")
        minutes = budget.get("max_wallclock_minutes")
        cost = budget.get("max_external_cost_usd")
        if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
            errors.append("budget.max_model_calls must be a non-negative integer")
        if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
            errors.append("budget.max_wallclock_minutes must be a non-negative integer")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
            errors.append("budget.max_external_cost_usd must be a finite non-negative number")

    authorization = record.get("authorization")
    if not isinstance(authorization, dict):
        errors.append("authorization must be an object")
    else:
        if authorization.get("approval_id") is not None and not isinstance(authorization.get("approval_id"), str):
            errors.append("authorization.approval_id must be a string or null")
        if not isinstance(authorization.get("approval_required"), bool):
            errors.append("authorization.approval_required must be boolean")
        if not isinstance(authorization.get("scope"), str) or not authorization["scope"].strip():
            errors.append("authorization.scope must describe the approval boundary or state none")
    if "closes_current_handoff" in record and not isinstance(record["closes_current_handoff"], bool):
        errors.append("closes_current_handoff must be boolean when supplied")
    return errors


def validate_closure(
    preregistration: dict[str, Any],
    closure: Any,
    root: Path,
    budget_record: dict[str, Any],
    prior_model_calls: int,
    prior_external_cost_usd: float,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(closure, dict):
        return ["closure must be a JSON object"]
    required = {
        "schema_version",
        "experiment_id",
        "evidence_class",
        "decision",
        "results_summary",
        "denominator_summary",
        "scientific_update",
        "actual_model_calls",
        "actual_external_cost_usd",
        "actual_wallclock_minutes",
        "failures_retained",
        "review_mode",
        "review_finding",
        "review_artifact",
        "outputs",
        "next_action",
        "next_action_evidence_class",
        "next_action_max_model_calls",
        "next_action_max_external_cost_usd",
        "new_uncertainty_reduced",
        "approval_required_for_next_action",
    }
    errors.extend(f"missing closure field: {key}" for key in sorted(required - closure.keys()))
    if isinstance(closure.get("schema_version"), bool) or closure.get("schema_version") != 1:
        errors.append("closure schema_version must equal 1")
    if closure.get("experiment_id") != preregistration.get("experiment_id"):
        errors.append("closure experiment_id does not match preregistration")
    if closure.get("evidence_class") != preregistration.get("evidence_class"):
        errors.append("closure evidence_class drift; evidence levels cannot be promoted")
    if not isinstance(closure.get("decision"), str) or closure.get("decision") not in DECISIONS:
        errors.append("decision must be PASS, FAIL, AMBIGUOUS, BLOCKED, or PIVOT")
    if not isinstance(closure.get("next_action_evidence_class"), str) or closure.get("next_action_evidence_class") not in EVIDENCE_CLASSES:
        errors.append("next_action_evidence_class must be a registered evidence class")
    for key in ("results_summary", "denominator_summary", "scientific_update", "review_finding", "next_action"):
        if not isinstance(closure.get(key), str) or not closure[key].strip():
            errors.append(f"{key} must be a non-empty string")
    calls = closure.get("actual_model_calls")
    cost = closure.get("actual_external_cost_usd")
    minutes = closure.get("actual_wallclock_minutes")
    planned = preregistration.get("budget", {})
    if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
        errors.append("actual_model_calls must be a non-negative integer")
    elif isinstance(planned.get("max_model_calls"), int) and calls > planned["max_model_calls"]:
        errors.append("actual model calls exceed preregistered cap")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        errors.append("actual_external_cost_usd must be a finite non-negative number")
    elif isinstance(planned.get("max_external_cost_usd"), (int, float)) and cost > planned["max_external_cost_usd"]:
        errors.append("actual external cost exceeds preregistered cap")
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 0:
        errors.append("actual_wallclock_minutes must be a non-negative integer")
    elif isinstance(planned.get("max_wallclock_minutes"), int) and minutes > planned["max_wallclock_minutes"]:
        errors.append("actual wall-clock time exceeds preregistered cap")
    if closure.get("failures_retained") is not True:
        errors.append("failures_retained must be true")
    if not isinstance(closure.get("review_mode"), str) or closure.get("review_mode") not in REVIEW_MODES:
        errors.append("review_mode must identify independent, adversarial_self_review, or not_run")
    if closure.get("review_mode") == "not_run" and closure.get("decision") == "PASS":
        errors.append("a PASS decision requires an adversarial review")
    if closure.get("review_mode") == "independent":
        errors.extend(_check_hashed_files([closure.get("review_artifact")], root, "review_artifact", require_one=True))
    elif closure.get("review_artifact") not in (None, {}):
        errors.append("review_artifact is only accepted when review_mode is independent")
    auth = budget_record.get("authorization", {})
    if (isinstance(calls, int) and calls > 0) or (isinstance(cost, (int, float)) and cost > 0):
        exp_id = preregistration.get("experiment_id")
        if auth.get("status") != "active" or exp_id not in auth.get("authorized_experiment_ids", []):
            errors.append("non-zero model calls/cost lack a current matching authorization in research/budget.json")
        if not auth.get("approval_id") or preregistration.get("authorization", {}).get("approval_id") != auth.get("approval_id"):
            errors.append("authorization ID does not match the current approved budget")
    auth = budget_record.get("authorization", {})
    max_calls = auth.get("max_model_calls", 0)
    max_cost = auth.get("max_external_cost_usd", 0.0)
    if isinstance(calls, int) and prior_model_calls + calls > max_calls:
        errors.append("cumulative model calls exceed current project authorization")
    if isinstance(cost, (int, float)) and prior_external_cost_usd + cost > max_cost:
        errors.append("cumulative external cost exceeds current project authorization")
    next_calls = closure.get("next_action_max_model_calls")
    next_cost = closure.get("next_action_max_external_cost_usd")
    if isinstance(next_calls, bool) or not isinstance(next_calls, int) or next_calls < 0:
        errors.append("next_action_max_model_calls must be a non-negative integer")
    if isinstance(next_cost, bool) or not isinstance(next_cost, (int, float)) or not math.isfinite(next_cost) or next_cost < 0:
        errors.append("next_action_max_external_cost_usd must be finite and non-negative")
    if (isinstance(next_calls, int) and next_calls > 0 or isinstance(next_cost, (int, float)) and next_cost > 0) and closure.get("approval_required_for_next_action") is not True:
        errors.append("a next action with non-zero model/cost budget must require new user approval")
    if not isinstance(closure.get("new_uncertainty_reduced"), bool):
        errors.append("new_uncertainty_reduced must be boolean")
    if not isinstance(closure.get("approval_required_for_next_action"), bool):
        errors.append("approval_required_for_next_action must be boolean")
    if not isinstance(closure.get("outputs"), list) or not closure["outputs"]:
        errors.append("outputs must contain at least one sanitized, hash-pinned artifact")
    else:
        errors.extend(_check_hashed_files(closure["outputs"], root, "outputs", require_one=True))
    return errors


def validate_handoff_packet(packet: Any, root: Path) -> list[str]:
    """Validate a completed external task import without calling it preregistered."""
    errors: list[str] = []
    if not isinstance(packet, dict):
        return ["handoff packet must be a JSON object"]
    required = {
        "schema_version",
        "handoff_id",
        "title",
        "terminal_decision",
        "evidence_classes",
        "evidence_summaries",
        "terminal_summary",
        "preregistration_refs",
        "sanitized_artifacts",
        "historical_model_calls",
        "historical_external_cost_usd",
        "authorization_status",
        "raw_data_local_only",
        "limitations",
        "recommended_next_action",
    }
    errors.extend(f"missing handoff field: {key}" for key in sorted(required - packet.keys()))
    if isinstance(packet.get("schema_version"), bool) or packet.get("schema_version") != 1:
        errors.append("handoff schema_version must equal 1")
    handoff_id = packet.get("handoff_id")
    if not isinstance(handoff_id, str) or not EXPERIMENT_ID_RE.fullmatch(handoff_id):
        errors.append("handoff_id must be 3-64 safe filename characters")
    if not isinstance(packet.get("terminal_decision"), str) or packet.get("terminal_decision") not in HANDOFF_DECISIONS:
        errors.append("terminal_decision must preserve PASS/FAIL/AMBIGUOUS/BLOCKED/PIVOT or GO/NO-GO")
    for key in ("title", "terminal_summary", "recommended_next_action"):
        if not isinstance(packet.get(key), str) or not packet[key].strip():
            errors.append(f"{key} must be a non-empty string")
    evidence = packet.get("evidence_classes")
    if not isinstance(evidence, list) or not evidence or any(not isinstance(item, str) or item not in EVIDENCE_CLASSES for item in evidence):
        errors.append("evidence_classes must list one or more registered evidence levels")
    summaries = packet.get("evidence_summaries")
    if not isinstance(summaries, list) or not summaries:
        errors.append("evidence_summaries must keep results separated by evidence class")
    else:
        summary_classes: list[str] = []
        for index, summary in enumerate(summaries):
            if not isinstance(summary, dict):
                errors.append(f"evidence_summaries[{index}] must be an object")
                continue
            level = summary.get("evidence_class")
            if not isinstance(level, str) or level not in EVIDENCE_CLASSES:
                errors.append(f"evidence_summaries[{index}] has an unknown evidence class")
            else:
                summary_classes.append(level)
            for key in ("summary", "denominator"):
                if not isinstance(summary.get(key), str) or not summary[key].strip():
                    errors.append(f"evidence_summaries[{index}].{key} must be a non-empty string")
        if isinstance(evidence, list) and all(isinstance(item, str) for item in evidence) and set(summary_classes) != set(evidence):
            errors.append("evidence_summaries must cover exactly the listed evidence_classes")
    calls = packet.get("historical_model_calls")
    cost = packet.get("historical_external_cost_usd")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
        errors.append("historical_model_calls must be a non-negative integer")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0:
        errors.append("historical_external_cost_usd must be finite and non-negative")
    if not isinstance(packet.get("authorization_status"), str) or packet.get("authorization_status") not in {"consumed", "not_used", "not_authorized", "unknown"}:
        errors.append("authorization_status must describe the historical run")
    if isinstance(calls, int) and calls > 0 and packet.get("authorization_status") == "not_authorized":
        errors.append("a non-zero historical run cannot be recorded as not_authorized")
    if packet.get("raw_data_local_only") is not True:
        errors.append("raw_data_local_only must be true")
    limitations = packet.get("limitations")
    if not isinstance(limitations, list) or not limitations or any(not isinstance(item, str) or not item.strip() for item in limitations):
        errors.append("limitations must retain at least one explicit limitation")
    errors.extend(_check_hashed_files(packet.get("preregistration_refs"), root, "preregistration_refs", require_one=True))
    artifacts = packet.get("sanitized_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("sanitized_artifacts must contain a terminal summary and audit artifact")
    else:
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict) or not isinstance(artifact.get("role"), str) or not artifact["role"].strip():
                errors.append(f"sanitized_artifacts[{index}] must include a role")
        errors.extend(_check_hashed_files(artifacts, root, "sanitized_artifacts", require_one=True))
    return errors
