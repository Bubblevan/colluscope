#!/usr/bin/env python3
"""Read-only validator for the frozen v2 synthetic manifest/projector."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import audit_public_harm_invariance as audit
from scripts import freeze_synthetic_invariance_groups_v2 as generator
from scripts import project_monitor_http_request_v2 as projector
from scripts.project_monitor_http_request_v2 import (
    ProjectionError,
    project_variant_http_request,
    serialize_http_request,
)


PROMPT_PATH = ROOT / "prompts/m4-deepseek-agent-v1/monitor-system.txt"
PROMPT_SHA256 = "10ba3341c905c87e8334a6dc8426cb05329ce5e675ce337cf2169a6ed9a137dd"
MANIFEST_PATH = generator.OUT
V1_MANIFEST_PATH = ROOT / "docs/results/evidence-invariance/synthetic-invariance-groups-v1.json"


class ValidationError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _all_keys(value: Any) -> set[str]:
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


def _load_manifest() -> tuple[dict[str, Any], bytes]:
    try:
        raw = MANIFEST_PATH.read_bytes()
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError("MANIFEST_UNAVAILABLE_OR_INVALID") from exc
    canonical = generator._canonical(value) + b"\n"
    expected = generator._canonical(generator.build_manifest()) + b"\n"
    if raw != canonical or raw != expected:
        raise ValidationError("MANIFEST_BYTES_DIFFER_FROM_FROZEN_GENERATOR")
    return value, raw


def validate() -> dict[str, Any]:
    manifest, manifest_bytes = _load_manifest()
    if sha(V1_MANIFEST_PATH.read_bytes()) != generator.LEGACY_V1_MANIFEST_SHA256:
        raise ValidationError("PRESERVED_V1_MANIFEST_HASH_MISMATCH")
    prompt_bytes = PROMPT_PATH.read_bytes()
    if sha(prompt_bytes) != PROMPT_SHA256:
        raise ValidationError("SYSTEM_PROMPT_HASH_MISMATCH")
    prompt = prompt_bytes.decode("utf-8")
    request_contract = manifest.get("request_contract")
    if not isinstance(request_contract, dict):
        raise ValidationError("REQUEST_CONTRACT_MISSING")
    expected_contract = {
        "projector_sha256": sha((ROOT / "scripts/project_monitor_http_request_v2.py").read_bytes()),
        "system_prompt_sha256": PROMPT_SHA256,
        "tool_schema_sha256": generator._sha(generator._canonical(projector.TOOL)),
        "model_alias": "deepseek-flash",
        "temperature": 0.0,
        "max_tokens": 512,
        "thinking": "disabled",
        "tool_name": "report_evidence",
        "planned_logical_requests_if_dispatched": 200,
        "dispatch_authorized": False,
        "excluded_wrapper_fields": [
            "primary_label", "split", "scoring_reference", "group_id", "generation_slot",
        ],
    }
    if any(request_contract.get(key) != value for key, value in expected_contract.items()):
        raise ValidationError("REQUEST_CONTRACT_DRIFT")
    groups = manifest.get("groups")
    if (manifest.get("schema_version") != "branch-a-synthetic-evidence-invariance-v2"
            or not isinstance(groups, list) or len(groups) != 20):
        raise ValidationError("V2_MANIFEST_SHAPE_INVALID")
    ids = [group.get("group_id") for group in groups]
    if len(ids) != len(set(ids)):
        raise ValidationError("OPAQUE_GROUP_ID_DUPLICATE")
    if any(not isinstance(value, str) or len(value) != 26 or not value.startswith("g_")
           or any(char not in "0123456789abcdef" for char in value[2:]) for value in ids):
        raise ValidationError("OPAQUE_GROUP_ID_FORMAT_INVALID")
    expected_ids = [generator._opaque_group_id(group["generation_slot"]) for group in groups]
    if ids != expected_ids:
        raise ValidationError("OPAQUE_GROUP_ID_NOT_FIXED_RANDOM_TOKEN")
    if groups != generator._ordered(groups):
        raise ValidationError("ROW_ORDER_NOT_OPAQUE_HASH_ORDER")
    split_map = generator._split_map(ids)
    if any(group.get("split") != split_map[group["group_id"]] for group in groups):
        raise ValidationError("SPLIT_NOT_OPAQUE_ID_HASH_ASSIGNED")
    split_counts = {split: sum(group["split"] == split for group in groups)
                    for split in ("calibration", "validation", "held_out")}
    if split_counts != {"calibration": 4, "validation": 4, "held_out": 12}:
        raise ValidationError("SPLIT_COUNTS_INVALID")

    reference_counts = {label: 0 for label in ("present", "absent")}
    primary_counts = {label: 0 for label in ("present", "absent")}
    projected_requests = 0
    for group in groups:
        slot = group.get("generation_slot")
        if type(slot) is not int or not 1 <= slot <= 20:
            raise ValidationError("GENERATION_SLOT_INVALID")
        if group.get("primary_label") != generator._primary_labels()[slot - 1]:
            raise ValidationError("PRIMARY_LABEL_ASSIGNMENT_DRIFT")
        primary_counts[group["primary_label"]] += 1
        trajectories = group.get("trajectories")
        if (not isinstance(trajectories, list) or len(trajectories) != 2
                or [item.get("trajectory_id") for item in trajectories]
                != ["primary", "label_flip_positive_control"]):
            raise ValidationError("TRAJECTORY_SET_INVALID")
        if trajectories[0]["scoring_reference"] == trajectories[1]["scoring_reference"]:
            raise ValidationError("POSITIVE_CONTROL_FAILED_TO_FLIP_LABEL")
        for trajectory in trajectories:
            reference = trajectory.get("scoring_reference")
            reference_counts[reference] += 1
            if reference not in {"present", "absent"}:
                raise ValidationError("SCORING_REFERENCE_INVALID")
            if len(trajectory.get("variants", [])) != 5:
                raise ValidationError("VARIANT_COUNT_INVALID")
            for variant in trajectory["variants"]:
                evidence = variant.get("monitor_input")
                if not isinstance(evidence, dict):
                    raise ValidationError("MONITOR_INPUT_MISSING")
                if generator._sha(generator._canonical(evidence)) != variant.get("monitor_input_sha256"):
                    raise ValidationError("MONITOR_INPUT_HASH_MISMATCH")
                if audit._find_forbidden_keys(evidence):
                    raise ValidationError("HIDDEN_SCORING_FIELD_IN_MONITOR_INPUT")
                result = audit.recompute_public_harm(evidence)
                if (result["reference_label"] != reference
                        or variant.get("scoring_reference") != reference):
                    raise ValidationError("TRUTH_NOT_INVARIANT_OR_WRONG")
                expected_permission = "public_only" if variant["variant_id"] == "public_canonical" else "privileged_audit"
                if variant.get("permission_profile") != expected_permission:
                    raise ValidationError("PERMISSION_PROFILE_DRIFT")
                request = project_variant_http_request(prompt, variant)
                serialized = serialize_http_request(request)
                if sha(serialized) != variant.get("projected_http_body_sha256"):
                    raise ValidationError("PROJECTED_HTTP_BODY_HASH_MISMATCH")
                body = json.loads(serialized)
                projected_requests += 1
                if set(body) != {"model", "temperature", "max_tokens", "thinking", "messages", "tools", "tool_choice"}:
                    raise ValidationError("PROJECTED_BODY_FIELDS_INVALID")
                forbidden_keys = {"primary_label", "split", "scoring_reference", "group_id"}
                if forbidden_keys.intersection(_all_keys(body)):
                    raise ValidationError("WRAPPER_METADATA_KEY_LEAKED")
                forbidden_values = (
                    group["group_id"], "SECRET_PRIMARY_LABEL", "SECRET_SPLIT",
                    "SECRET_SCORING_REFERENCE", "SECRET_GROUP_ID",
                )
                if any(marker in serialized.decode("utf-8") for marker in forbidden_values):
                    raise ValidationError("WRAPPER_METADATA_LEAKED")
    if reference_counts != {"present": 20, "absent": 20}:
        raise ValidationError("POSITIVE_CONTROL_REFERENCE_COUNTS_INVALID")
    return {
        "status": "PASS_SYNTHETIC_V2_VALIDATION",
        "manifest_sha256": sha(manifest_bytes),
        "preserved_v1_manifest_sha256": sha(V1_MANIFEST_PATH.read_bytes()),
        "generator_sha256": sha(Path(generator.__file__).read_bytes()),
        "projector_sha256": sha((ROOT / "scripts/project_monitor_http_request_v2.py").read_bytes()),
        "system_prompt_sha256": sha(prompt_bytes),
        "groups": len(groups),
        "primary_label_counts": primary_counts,
        "trajectory_reference_counts": reference_counts,
        "split_counts": split_counts,
        "projected_requests_checked_offline": projected_requests,
        "planned_logical_requests_if_dispatched": request_contract["planned_logical_requests_if_dispatched"],
        "model_calls": 0,
    }


def main() -> int:
    try:
        print(json.dumps(validate(), sort_keys=True))
        return 0
    except ValidationError as exc:
        print(json.dumps({"status": "FAIL", "error_code": exc.code}, sort_keys=True))
        return 2
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error_code": "UNEXPECTED_" + type(exc).__name__}, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
