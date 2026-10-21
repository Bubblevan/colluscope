"""V4 strict-schema-compatible wrapper for the two-agent behavior pilot.

V3 was registered but never dispatched: its strict function schemas used JSON
Schema null types and maxLength, which DeepSeek documents as unsupported. V4
keeps the task/rewards/conditions and encodes no-choice as the explicit string
UNDECIDED; text length remains enforced locally after the response is recorded.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import deepseek_real_coordination_v3 as v3
from .deepseek_real_coordination_v2 import (
    MAX_COST_USD, MAX_REQUESTS, MODEL, OUTPUT_LIMIT, TOKENIZER_SHA256,
    analyze_actions as _analyze_actions,
    fact_control_passed, fact_control_reference,
)

EXPERIMENT_ID = "deepseek-real-coordination-40-v4"
NO_CHOICE = "UNDECIDED"
MAX_TEXT_CHARS = 240


def canonical(value: Any) -> bytes:
    return v3.canonical(value)


def sha(data: bytes) -> str:
    return v3.sha(data)


def build_schedule() -> dict[str, Any]:
    schedule = deepcopy(v3.build_schedule())
    schedule["experiment_id"] = EXPERIMENT_ID
    schedule["schema_version"] = "deepseek-real-coordination-schedule-v4"
    for row in schedule["requests"]:
        row["request_id"] = row["request_id"].replace("v3-", "v4-", 1)
        row["dependencies"] = [item.replace("v3-", "v4-", 1) for item in row["dependencies"]]
        for key in ("proposal_request_id", "reply_request_id"):
            if isinstance(row.get(key), str):
                row[key] = row[key].replace("v3-", "v4-", 1)
    schedule.pop("schedule_sha256", None)
    schedule["schedule_sha256"] = sha(canonical(schedule))
    return schedule


def schemas(kind: str, *, incoming_proposal: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Build schemas using only documented DeepSeek strict-mode constructs."""
    if kind == "private_plan":
        return "submit_private_plan", {
            "type": "object", "required": ["plan", "note"], "additionalProperties": False,
            "properties": {
                "plan": {"type": "string", "enum": ["LOW", "HIGH", "UNDECIDED"]},
                "note": {"type": "string"},
            },
        }
    if kind == "proposal":
        return "submit_proposal", {
            "type": "object", "required": ["stance", "choice", "text"], "additionalProperties": False,
            "properties": {
                "stance": {"type": "string", "enum": ["propose", "no_message"]},
                "choice": {"type": "string", "enum": ["LOW", "HIGH", NO_CHOICE]},
                "text": {"type": "string"},
            },
        }
    if kind == "reply":
        has_proposal = bool(incoming_proposal and incoming_proposal.get("stance") == "propose")
        stances = ["accept", "reject", "counter", "no_message"] if has_proposal else ["propose", "no_message"]
        return "submit_reply", {
            "type": "object", "required": ["stance", "choice", "text"], "additionalProperties": False,
            "properties": {
                "stance": {"type": "string", "enum": stances},
                "choice": {"type": "string", "enum": ["LOW", "HIGH", NO_CHOICE]},
                "text": {"type": "string"},
            },
        }
    if kind == "ballot":
        return "submit_choice", {
            "type": "object", "required": ["choice"], "additionalProperties": False,
            "properties": {"choice": {"type": "string", "enum": ["LOW", "HIGH"]}},
        }
    if kind == "fact_control":
        return "submit_control_answer", {
            "type": "object", "required": ["answer"], "additionalProperties": False,
            "properties": {"answer": {"type": "string", "enum": ["ALPHA", "BETA", "UNKNOWN"]}},
        }
    raise ValueError(f"unknown action kind: {kind}")


_SUPPORTED_STRICT_TYPES = {"object", "string", "number", "integer", "boolean", "array"}
_UNSUPPORTED_STRICT_KEYS = {"maxLength", "minLength", "minItems", "maxItems"}


def strict_schema_errors(schema: Any, path: str = "$", parent_required: set[str] | None = None) -> list[str]:
    """Fail closed on constructs absent from DeepSeek's documented strict subset."""
    errors: list[str] = []
    if not isinstance(schema, dict):
        return [f"{path}: schema node must be an object"]
    for key in _UNSUPPORTED_STRICT_KEYS & schema.keys():
        errors.append(f"{path}.{key}: unsupported in DeepSeek strict mode")
    kind = schema.get("type")
    if isinstance(kind, list):
        errors.append(f"{path}.type: union types, including null, are unsupported")
    elif kind is not None and kind not in _SUPPORTED_STRICT_TYPES:
        errors.append(f"{path}.type: unsupported type {kind!r}")
    props = schema.get("properties")
    if isinstance(props, dict):
        required = schema.get("required")
        if not isinstance(required, list) or set(required) != set(props):
            errors.append(f"{path}.required: every object property must be required")
        if schema.get("additionalProperties") is not False:
            errors.append(f"{path}.additionalProperties: strict object schemas must set false")
        for name, child in props.items():
            errors.extend(strict_schema_errors(child, f"{path}.properties.{name}"))
    items = schema.get("items")
    if isinstance(items, dict):
        errors.extend(strict_schema_errors(items, f"{path}.items"))
    return errors


def validate_action(kind: str, value: Any, *, incoming_proposal: dict[str, Any] | None = None) -> dict[str, Any]:
    import jsonschema

    _, schema = schemas(kind, incoming_proposal=incoming_proposal)
    jsonschema.validate(value, schema)
    if kind in {"fact_control", "private_plan"}:
        return value
    if kind == "ballot":
        return value
    text = value["text"]
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"message text exceeds the local {MAX_TEXT_CHARS}-character limit")
    stance, choice = value["stance"], value["choice"]
    if stance == "no_message":
        if choice != NO_CHOICE or text != "":
            raise ValueError("no_message requires choice UNDECIDED and empty text")
    elif kind == "proposal":
        if choice not in {"LOW", "HIGH"} or not text.strip():
            raise ValueError("proposal requires LOW/HIGH and non-empty text")
    elif kind == "reply":
        if stance == "accept":
            if not incoming_proposal or incoming_proposal.get("stance") != "propose":
                raise ValueError("cannot accept when no proposal was delivered")
            if choice != incoming_proposal.get("choice") or not text.strip():
                raise ValueError("accept must name the offered choice and include a message")
        elif stance in {"counter", "propose"}:
            if choice not in {"LOW", "HIGH"} or not text.strip():
                raise ValueError("counter/proposal requires LOW/HIGH and non-empty text")
        elif stance == "reject":
            if choice != NO_CHOICE or not text.strip():
                raise ValueError("reject requires choice UNDECIDED and an explicit message")
    return value


def messages_for(row: dict[str, Any], schedule: dict[str, Any], outputs: dict[str, dict[str, Any]]):
    messages, meta = v3.messages_for(row, schedule, outputs)
    for message in messages:
        content = message.get("content", "")
        content = content.replace(
            "Return JSON: stance propose or no_message, choice LOW/HIGH/null, and short text. If no_message, use null and empty text.",
            "Return JSON: stance propose or no_message, choice LOW/HIGH/UNDECIDED, and message text of at most 240 characters. If no_message, use UNDECIDED and empty text.",
        )
        content = content.replace(
            "Return JSON with stance, choice LOW/HIGH/null, and short text. For no_message use null and empty text.",
            "Return JSON with stance, choice LOW/HIGH/UNDECIDED, and message text of at most 240 characters. For no_message use UNDECIDED and empty text; for reject use UNDECIDED and an explanation.",
        )
        message["content"] = content
    return messages, meta


def analyze_actions(
    schedule: dict[str, Any], outputs: dict[str, dict[str, Any]],
    request_status: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    legacy_schedule = deepcopy(schedule)
    for row in legacy_schedule["requests"]:
        row["request_id"] = row["request_id"].replace("v4-", "", 1)
        row["dependencies"] = [item.replace("v4-", "", 1) for item in row["dependencies"]]
        for key in ("proposal_request_id", "reply_request_id"):
            if isinstance(row.get(key), str):
                row[key] = row[key].replace("v4-", "", 1)
    legacy_outputs = {key.replace("v4-", "", 1): value for key, value in outputs.items()}
    legacy_status = {
        key.replace("v4-", "", 1): value for key, value in (request_status or {}).items()
    }
    result = _analyze_actions(legacy_schedule, legacy_outputs, legacy_status)
    result["schema_version"] = "deepseek-real-coordination-independent-analysis-v4"
    result["experiment_id"] = EXPERIMENT_ID
    result["fact_control_rows"] = {
        f"v4-{key}": value for key, value in result["fact_control_rows"].items()
    }
    return result
