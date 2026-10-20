from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import freeze_synthetic_invariance_groups as v1
from scripts import freeze_synthetic_invariance_groups_v2 as v2
from scripts.project_monitor_http_request_v2 import (
    ProjectionError,
    project_monitor_http_request,
    project_variant_http_request,
    serialize_http_request,
)


ROOT = Path(__file__).resolve().parents[1]
PROMPT = (ROOT / "prompts/m4-deepseek-agent-v1/monitor-system.txt").read_text(encoding="utf-8")


def _variant() -> dict:
    manifest = v2.build_manifest()
    group = manifest["groups"][0]
    variant = group["trajectories"][0]["variants"][0]
    wrapped = copy.deepcopy(variant)
    wrapped.update({
        "group_id": "SECRET_GROUP_ID",
        "generation_slot": 999,
        "primary_label": "SECRET_PRIMARY_LABEL",
        "split": "SECRET_SPLIT",
        "scoring_reference": "SECRET_SCORING_REFERENCE",
    })
    return wrapped


def _all_keys(value) -> set[str]:
    if isinstance(value, dict):
        result = set(value)
        for child in value.values():
            result.update(_all_keys(child))
        return result
    if isinstance(value, list):
        result: set[str] = set()
        for child in value:
            result.update(_all_keys(child))
        return result
    return set()


def test_projector_only_emits_prompt_and_monitor_input_from_outer_wrapper() -> None:
    variant = _variant()
    request = project_variant_http_request(PROMPT, variant)
    raw = serialize_http_request(request).decode("utf-8")
    body = json.loads(raw)
    assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == variant["projected_http_body_sha256"]
    assert not {"primary_label", "split", "scoring_reference", "group_id", "generation_slot"}.intersection(_all_keys(body))
    for marker in ("SECRET_PRIMARY_LABEL", "SECRET_SPLIT", "SECRET_SCORING_REFERENCE", "SECRET_GROUP_ID"):
        assert marker not in raw
    assert set(request) == {
        "model", "temperature", "max_tokens", "thinking", "messages", "tools", "tool_choice"}
    assert request["messages"][0] == {"role": "system", "content": PROMPT}
    assert request["messages"][1]["content"].endswith(
        json.dumps(variant["monitor_input"], ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")))


def test_scoring_wrapper_mutations_do_not_change_serialized_http_body() -> None:
    manifest_variant = v2.build_manifest()["groups"][0]["trajectories"][0]["variants"][0]
    plain = copy.deepcopy(manifest_variant)
    wrapped = copy.deepcopy(plain)
    wrapped.update({
        "group_id": "OPAQUE_GROUP_SENTINEL",
        "generation_slot": 20,
        "primary_label": "present",
        "split": "held_out",
        "scoring_reference": "absent",
        "variant_id": "B5_evidence_aware",
        "permission_profile": "privileged_audit",
    })
    plain_body = serialize_http_request(project_variant_http_request(PROMPT, plain))
    wrapped_body = serialize_http_request(project_variant_http_request(PROMPT, wrapped))
    assert wrapped_body == plain_body


def test_direct_outer_wrapper_cannot_be_mistaken_for_monitor_input() -> None:
    variant = _variant()
    with pytest.raises(ProjectionError, match="MONITOR_INPUT_OUTER_FIELDS_REJECTED"):
        project_monitor_http_request(PROMPT, variant)


def test_group_wrapper_without_selected_variant_is_rejected() -> None:
    group = v2.build_manifest()["groups"][0]
    with pytest.raises(ProjectionError, match="VARIANT_MONITOR_INPUT_MISSING"):
        project_variant_http_request(PROMPT, group)


@pytest.mark.parametrize(
    "key", ["primary_label", "split", "scoring_reference", "group_id", "generation_slot"])
def test_wrapper_fields_inside_monitor_input_are_rejected(key: str) -> None:
    evidence = copy.deepcopy(_variant()["monitor_input"])
    evidence[key] = "SECRET_DO_NOT_SEND"
    with pytest.raises(ProjectionError, match="MONITOR_INPUT_OUTER_FIELDS_REJECTED"):
        project_monitor_http_request(PROMPT, evidence)


def test_projector_rejects_hidden_wrapper_metadata_in_system_prompt() -> None:
    evidence = _variant()["monitor_input"]
    with pytest.raises(ProjectionError, match="HIDDEN_METADATA_IN_PROMPT"):
        project_monitor_http_request(PROMPT + "\nscoring_reference", evidence)


def test_projector_rejects_unfrozen_system_prompt() -> None:
    evidence = _variant()["monitor_input"]
    with pytest.raises(ProjectionError, match="SYSTEM_PROMPT_HASH_MISMATCH"):
        project_monitor_http_request("A different prompt", evidence)


def test_projector_rejects_permission_or_scoring_marker_in_message_text() -> None:
    message_variant = v2.build_manifest()["groups"][0]["trajectories"][0]["variants"][1]
    evidence = copy.deepcopy(message_variant["monitor_input"])
    evidence["events"][0]["content"]["text"] = "B5_evidence_aware scoring_reference present"
    with pytest.raises(ProjectionError, match="HIDDEN_METADATA_IN_EVIDENCE"):
        project_monitor_http_request(PROMPT, evidence)


@pytest.mark.parametrize(
    "key", ["primary_label", "split", "scoring_reference", "group_id", "generation_slot"])
def test_http_serializer_rejects_outer_wrapper_fields(key: str) -> None:
    request = project_variant_http_request(PROMPT, _variant())
    request[key] = "SECRET_DO_NOT_SEND"
    with pytest.raises(ProjectionError, match="HTTP_REQUEST_TOP_LEVEL_FIELDS_INVALID"):
        serialize_http_request(request)


@pytest.mark.parametrize(
    "key", ["primary_label", "split", "scoring_reference", "group_id"])
def test_http_serializer_rejects_wrapper_inside_serialized_evidence(key: str) -> None:
    request = project_variant_http_request(PROMPT, _variant())
    prefix, encoded_evidence = request["messages"][1]["content"].rsplit("\n", 1)
    evidence = json.loads(encoded_evidence)
    evidence[key] = "SECRET_DO_NOT_SEND"
    request["messages"][1]["content"] = prefix + "\n" + json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with pytest.raises(ProjectionError, match="PUBLIC_EVIDENCE_INVALID_FORBIDDEN_EVIDENCE_KEY|FORBIDDEN_EVIDENCE_KEY|MONITOR_INPUT_OUTER_FIELDS_REJECTED"):
        serialize_http_request(request)


def test_v2_preserves_metalinguistic_control_and_adds_genuinely_task_irrelevant_text() -> None:
    old_short = v1._events(("T1", "T2", "T3"), "irrelevant_short")
    old_long = v1._events(("T1", "T2", "T3"), "irrelevant_long")
    assert v2.METALINGUISTIC_TEXTS["short"] == tuple(
        event["content"]["text"] for event in old_short if event["type"] == "message")
    assert v2.METALINGUISTIC_TEXTS["long"] == tuple(
        event["content"]["text"] for event in old_long if event["type"] == "message")
    for message in sum((list(pair) for pair in v2.TASK_IRRELEVANT_TEXTS.values()), []):
        lowered = message.casefold()
        for term in ("instruction", "task", "matrix", "allocation", "vote", "decision",
                     "enough information", "proposal", "target", "public"):
            assert term not in lowered


def test_v2_opaque_ids_splits_and_row_order_do_not_depend_on_labels() -> None:
    original = v2.build_manifest()["groups"]
    group_ids = [group["group_id"] for group in original]
    assert len(group_ids) == len(set(group_ids)) == 20
    assert set(group_ids) == set(v2.GROUP_ID_TOKENS)
    assert all(len(group_id) == 26 and group_id.startswith("g_")
               and all(char in "0123456789abcdef" for char in group_id[2:])
               for group_id in group_ids)
    assert [group["primary_label"] for group in sorted(original, key=lambda row: row["generation_slot"])] == v2._primary_labels()
    expected_splits = v2._split_map(group_ids)
    expected_order = [group["group_id"] for group in v2._ordered(original)]

    perturbed = copy.deepcopy(original)
    for group in perturbed:
        group["primary_label"] = "absent" if group["primary_label"] == "present" else "present"
        group["split"] = "tampered_split"
        for trajectory in group["trajectories"]:
            trajectory["scoring_reference"] = (
                "absent" if trajectory["scoring_reference"] == "present" else "present")

    assert [group["group_id"] for group in perturbed] == group_ids
    assert {group["group_id"]: group["split"] for group in v2.build_manifest()["groups"]} == expected_splits
    assert [group["group_id"] for group in v2._ordered(perturbed)] == expected_order
