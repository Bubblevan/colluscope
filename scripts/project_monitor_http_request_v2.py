#!/usr/bin/env python3
"""Pure, offline projector for synthetic evidence-invariance Monitor requests.

The only caller-supplied model inputs are the frozen system prompt and the
selected variant's `monitor_input`. Wrapper metadata is intentionally ignored;
passing it as evidence is rejected by the exact schema checks below.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import audit_public_harm_invariance as audit


TASK = "public_harm"
QUESTION = audit.EXPECTED_QUESTION
SYSTEM_PROMPT_SHA256 = "10ba3341c905c87e8334a6dc8426cb05329ce5e675ce337cf2169a6ed9a137dd"
ALLOWED_EVIDENCE_KEYS = {
    "task_spec", "action_record_complete", "events",
    "delivered_message_window_complete",
}
ALLOWED_TASK_KEYS = {
    "agents", "tasks", "chair", "public_objective", "voting_rule", "quality",
}
ALLOWED_ACTION_EVENT_KEYS = {"event_id", "type", "order", "actor", "content"}
ALLOWED_MESSAGE_EVENT_KEYS = ALLOWED_ACTION_EVENT_KEYS | {
    "recipient", "visibility", "sent", "delivered",
}
FORBIDDEN_PROMPT_MARKERS = (
    "primary_label", "scoring_reference", "group_id", "split", "scenario_family_id",
    "case_ref", "reference_label", "gold_label", "public_only", "privileged_audit",
    "B4_raw_fusion", "B5_evidence_aware",
)
FORBIDDEN_INPUT_MARKERS = FORBIDDEN_PROMPT_MARKERS + (
    "primary_label", "scoring_reference", "group_id", "split",
)

TOOL = {
    "type": "function",
    "function": {
        "description": "Submit exactly one validated research action.",
        "name": "report_evidence",
        "parameters": {
            "additionalProperties": False,
            "properties": {
                "evidence_refs": {"items": {"type": "string"}, "type": "array"},
                "label": {
                    "enum": ["present", "absent", "insufficient_evidence", "not_visible", "uncertain"],
                    "type": "string",
                },
            },
            "required": ["label", "evidence_refs"],
            "type": "object",
        },
        "strict": True,
    },
}


class ProjectionError(ValueError):
    """Sanitized failure: error text never includes caller-provided content."""


def _require_exact_keys(value: Any, expected: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ProjectionError(code)
    return value


def _validate_evidence(monitor_input: Any) -> dict[str, Any]:
    if not isinstance(monitor_input, dict):
        raise ProjectionError("MONITOR_INPUT_MUST_BE_OBJECT")
    keys = set(monitor_input)
    if keys not in (ALLOWED_EVIDENCE_KEYS - {"delivered_message_window_complete"},
                    ALLOWED_EVIDENCE_KEYS):
        raise ProjectionError("MONITOR_INPUT_OUTER_FIELDS_REJECTED")
    if audit._find_forbidden_keys(monitor_input):
        raise ProjectionError("FORBIDDEN_EVIDENCE_KEY")
    task = _require_exact_keys(monitor_input.get("task_spec"), ALLOWED_TASK_KEYS,
                               "TASK_SPEC_SCHEMA_INVALID")
    events = monitor_input.get("events")
    if not isinstance(events, list) or not events:
        raise ProjectionError("EVENTS_SCHEMA_INVALID")
    for event in events:
        if not isinstance(event, dict):
            raise ProjectionError("EVENT_SCHEMA_INVALID")
        event_type = event.get("type")
        content = event.get("content")
        if not isinstance(content, dict):
            raise ProjectionError("EVENT_CONTENT_INVALID")
        allowed = ALLOWED_MESSAGE_EVENT_KEYS if event_type == "message" else ALLOWED_ACTION_EVENT_KEYS
        required = allowed if event_type == "message" else ALLOWED_ACTION_EVENT_KEYS
        if set(event) != required:
            raise ProjectionError("EVENT_FIELDS_INVALID")
        if event_type == "message":
            if set(content) != {"text"} or not isinstance(content.get("text"), str):
                raise ProjectionError("MESSAGE_CONTENT_INVALID")
        elif event_type in {"vote", "decision", "outcome"}:
            if set(content) != {"assignment"}:
                raise ProjectionError("ACTION_CONTENT_INVALID")
        else:
            raise ProjectionError("EVENT_TYPE_INVALID")
    if type(monitor_input.get("action_record_complete")) is not bool:
        raise ProjectionError("ACTION_COMPLETENESS_INVALID")
    if ("delivered_message_window_complete" in monitor_input
            and type(monitor_input["delivered_message_window_complete"]) is not bool):
        raise ProjectionError("MESSAGE_COMPLETENESS_INVALID")
    # Verify the evidence is independently scoreable before it can be projected.
    try:
        audit.recompute_public_harm(monitor_input)
    except audit.AuditError as exc:
        raise ProjectionError("PUBLIC_EVIDENCE_INVALID_" + exc.code) from exc
    serialized_evidence = json.dumps(monitor_input, ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":")).casefold()
    if any(marker.casefold() in serialized_evidence for marker in FORBIDDEN_INPUT_MARKERS):
        raise ProjectionError("HIDDEN_METADATA_IN_EVIDENCE")
    return monitor_input


def project_monitor_http_request(system_prompt: str,
                                 monitor_input: Mapping[str, Any]) -> dict[str, Any]:
    """Build the exact fixed request body from a system prompt + evidence only."""
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ProjectionError("SYSTEM_PROMPT_INVALID")
    lowered_prompt = system_prompt.casefold()
    if any(marker.casefold() in lowered_prompt for marker in FORBIDDEN_PROMPT_MARKERS):
        raise ProjectionError("HIDDEN_METADATA_IN_PROMPT")
    if hashlib.sha256(system_prompt.encode("utf-8")).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise ProjectionError("SYSTEM_PROMPT_HASH_MISMATCH")
    evidence = _validate_evidence(monitor_input)
    user_content = (
        f"Task: {TASK}\nQuestion: {QUESTION}\n"
        + json.dumps(evidence, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"))
    )
    return {
        "model": "deepseek-flash",
        "temperature": 0.0,
        "max_tokens": 512,
        "thinking": {"type": "disabled"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "tools": [TOOL],
        "tool_choice": {"type": "function", "function": {"name": "report_evidence"}},
    }


def project_variant_http_request(system_prompt: str,
                                 variant: Mapping[str, Any]) -> dict[str, Any]:
    """Select only `variant.monitor_input`; all adjacent scoring metadata is ignored."""
    if not isinstance(variant, Mapping) or "monitor_input" not in variant:
        raise ProjectionError("VARIANT_MONITOR_INPUT_MISSING")
    return project_monitor_http_request(system_prompt, variant["monitor_input"])


def serialize_http_request(request: Mapping[str, Any]) -> bytes:
    expected = {"model", "temperature", "max_tokens", "thinking", "messages", "tools", "tool_choice"}
    if not isinstance(request, Mapping) or set(request) != expected:
        raise ProjectionError("HTTP_REQUEST_TOP_LEVEL_FIELDS_INVALID")
    messages = request.get("messages")
    if (not isinstance(messages, list) or len(messages) != 2
            or [message.get("role") for message in messages if isinstance(message, Mapping)]
            != ["system", "user"]
            or any(not isinstance(message.get("content"), str) for message in messages)):
        raise ProjectionError("HTTP_REQUEST_MESSAGES_INVALID")
    prefix = f"Task: {TASK}\nQuestion: {QUESTION}\n"
    user_content = messages[1]["content"]
    if not user_content.startswith(prefix):
        raise ProjectionError("HTTP_REQUEST_TASK_PREFIX_INVALID")
    try:
        evidence = json.loads(user_content[len(prefix):])
    except json.JSONDecodeError as exc:
        raise ProjectionError("HTTP_REQUEST_EVIDENCE_JSON_INVALID") from exc
    canonical_projection = project_monitor_http_request(messages[0]["content"], evidence)
    if dict(request) != canonical_projection:
        raise ProjectionError("HTTP_REQUEST_NOT_EXACT_PROJECTION")
    return json.dumps(request, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
