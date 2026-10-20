"""Strict, versioned action extraction for the prospective M4 v4 interface.

This parser does not repair arbitrary model output. It accepts either a JSON
action in the assistant content field or exactly one leading ``<think>...</think>``
wrapper followed by a JSON action. A separately returned reasoning_content field
is recorded by hash only; it is never considered an action source.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


class ActionInterfaceError(ValueError):
    pass


@dataclass(frozen=True)
class Extraction:
    action_text: str
    source: str
    wrapper_count: int
    reasoning_text: str | None


def _sha(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_action_text(message: dict[str, Any]) -> Extraction:
    """Extract a candidate action using the exact v4 rules; never regex-repair."""
    content = message.get("content")
    if not isinstance(content, str):
        raise ActionInterfaceError("assistant content must be a string")
    reasoning = message.get("reasoning_content")
    if reasoning is not None and not isinstance(reasoning, str):
        raise ActionInterfaceError("reasoning_content, when present, must be a string")

    # Prefer the protocol's explicit content/action field. reasoning_content is
    # intentionally not parsed as an action, even if it happens to contain JSON.
    if _is_complete_json_value(content):
        return Extraction(content, "content_json", 0, reasoning)

    # Historical llama.cpp `reasoning_format=none` wrapper compatibility:
    # exact beginning, exactly one opening/closing tag, and the entire suffix
    # after the close must be one JSON value. No preamble, nesting, or trailing
    # prose is accepted. JSON/action semantics are validated by the caller.
    if not content.startswith("<think>"):
        raise ActionInterfaceError("content is neither complete JSON nor an exact leading think wrapper")
    if content.count("<think>") != 1 or content.count("</think>") != 1:
        raise ActionInterfaceError("think wrapper must contain exactly one opening and closing tag")
    close = content.find("</think>")
    if close < len("<think>"):
        raise ActionInterfaceError("think wrapper close precedes its body")
    inner = content[len("<think>"):close]
    action_text = content[close + len("</think>"):].strip()
    if "<think>" in inner or "</think>" in inner or not _is_complete_json_value(action_text):
        raise ActionInterfaceError("think wrapper must be followed by exactly one complete JSON value")
    return Extraction(action_text, "single_leading_think_wrapper", 1,
                      reasoning if reasoning is not None else inner)


def _is_complete_json_value(text: str) -> bool:
    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    try:
        json.loads(text, object_pairs_hook=unique_object)
    except (json.JSONDecodeError, TypeError, ValueError):
        return False
    return True


def parse_action(message: dict[str, Any], action_kind: str, validator) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract, validate, and return a privacy-safe parser receipt."""
    extracted = extract_action_text(message)
    action = validator(extracted.action_text, action_kind)
    receipt = {
        "interface_version": "m4-action-interface-v4",
        "source": extracted.source,
        "wrapper_count": extracted.wrapper_count,
        "action_text_sha256": _sha(extracted.action_text),
        "action_text_characters": len(extracted.action_text),
        "reasoning_content_present": extracted.reasoning_text is not None,
        "reasoning_content_sha256": _sha(extracted.reasoning_text),
        "reasoning_content_characters": len(extracted.reasoning_text) if extracted.reasoning_text is not None else None,
    }
    return action, receipt
