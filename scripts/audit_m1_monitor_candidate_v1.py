"""Offline structural audit for the candidate natural-message Monitor protocol.

This audit reads only committed design inputs. It never loads run data, opens a
network connection, imports credentials, or invokes a model.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "research/drafts/m1-natural-message-monitor-spec-v1.json"
CONTROLS_PATH = ROOT / "research/drafts/m1-natural-message-monitor-controls-v1.json"
KEY_PATH = ROOT / "research/drafts/m1-natural-message-monitor-controls-v1-answer-key.json"
SCHEDULE_PATH = ROOT / "research/drafts/m1-package-24-matrix-scenarios-20261021.json"
CODEBOOK_PATH = ROOT / "research/drafts/m1-natural-message-action-codebook-v1.md"
CAMPAIGN_PATH = ROOT / "research/drafts/m1-package-monitor-campaign-v2.md"
PROJECTION_PATH = ROOT / "src/colluscope/m1_monitor_projection.py"
PROJECTION_TEST_PATH = ROOT / "tests/test_m1_monitor_projection.py"
SCORING_PATH = ROOT / "src/colluscope/m1_monitor_scoring.py"
SCORING_TEST_PATH = ROOT / "tests/test_m1_monitor_scoring.py"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.relative_to(ROOT)}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit() -> dict[str, Any]:
    spec = read_json(SPEC_PATH)
    controls_doc = read_json(CONTROLS_PATH)
    key = read_json(KEY_PATH)
    schedule = read_json(SCHEDULE_PATH)
    codebook = CODEBOOK_PATH.read_text(encoding="utf-8")
    campaign = CAMPAIGN_PATH.read_text(encoding="utf-8")

    controls = controls_doc.get("controls")
    refs = key.get("references")
    if not isinstance(controls, list) or not isinstance(refs, list) or len(controls) != 12 or len(refs) != 12:
        raise ValueError("candidate controls and answer key must each have exactly 12 rows")
    ids = [row.get("control_id") for row in controls]
    ref_ids = [row.get("control_id") for row in refs]
    if len(set(ids)) != 12 or ids != ref_ids:
        raise ValueError("control IDs must be unique and align exactly with the answer key")

    by_control = {row["control_id"]: row for row in controls}
    proposal_counts = {label: 0 for label in ("present", "ambiguous", "absent")}
    concordance_counts = {label: 0 for label in ("concordant", "discordant", "not_assessable")}
    for ref in refs:
        label = ref.get("proposal_status")
        concordance = ref.get("concordance")
        if label not in proposal_counts or concordance not in concordance_counts:
            raise ValueError("answer key contains an unknown label")
        proposal_counts[label] += 1
        concordance_counts[concordance] += 1
        if label == "present":
            allocation = ref.get("allocation")
            if not isinstance(allocation, dict) or set(allocation) != {"A", "B", "C"}:
                raise ValueError(f"present control lacks a complete allocation: {ref['control_id']}")
            if set(allocation.values()) != {"T1", "T2", "T3"}:
                raise ValueError(f"present control allocation is not a task permutation: {ref['control_id']}")
            ballot = by_control[ref["control_id"]].get("recipient_ballot")
            expected = "concordant" if ballot == allocation else "discordant"
            if concordance != expected:
                raise ValueError(f"control concordance does not recompute: {ref['control_id']}")
        else:
            if ref.get("allocation") is not None or concordance != "not_assessable":
                raise ValueError(f"non-present control must be null/not_assessable: {ref['control_id']}")

    if proposal_counts != {"present": 6, "ambiguous": 3, "absent": 3}:
        raise ValueError(f"capability control balance changed: {proposal_counts}")
    if concordance_counts != {"concordant": 3, "discordant": 3, "not_assessable": 6}:
        raise ValueError(f"concordance control balance changed: {concordance_counts}")

    forbidden = set(spec.get("task_p", {}).get("hidden_fields_forbidden", []))
    if forbidden != set(spec.get("task_c", {}).get("hidden_fields_forbidden", [])):
        raise ValueError("P and C hidden-field exclusion lists differ")
    for task_name in ("task_p", "task_c"):
        task = spec.get(task_name, {})
        schema = task.get("output_schema", {})
        if schema.get("additionalProperties") is not False:
            raise ValueError(f"{task_name} output schema permits extra keys")
        if not schema.get("required"):
            raise ValueError(f"{task_name} output schema lacks required fields")
        input_fields = set(task.get("input_fields", []))
        if input_fields & forbidden:
            raise ValueError(f"{task_name} input fields overlap hidden-field exclusions")

    groups = schedule.get("groups", [])
    hashes = {row.get("scenario_sha256") for row in groups}
    if len(groups) != 24 or len(hashes) != 24:
        raise ValueError("the prospective schedule must preserve 24 distinct matrices/groups")
    if schedule.get("design", {}).get("total_local_generations") != 456:
        raise ValueError("M1 assigned generation ceiling changed")
    if spec.get("max_requests") != 216:
        raise ValueError("Monitor request ceiling changed")
    generation_max = 456 + 216
    physical_http_max = 456 + 24 + 216
    if generation_max != 672 or physical_http_max != 696:
        raise ValueError("combined request arithmetic changed")
    if "external transfer" not in codebook.lower() or "external provider" not in codebook.lower():
        raise ValueError("codebook lacks an explicit external private-text transfer gate")
    if "do not calculate a majority label from the evaluation set" not in codebook.lower():
        raise ValueError("baseline design must not fit a majority label on the evaluation rows")
    if not all(path.is_file() for path in (PROJECTION_PATH, PROJECTION_TEST_PATH, SCORING_PATH, SCORING_TEST_PATH)):
        raise ValueError("local projection/scoring implementation or adversarial tests are missing")
    if "696 physical HTTP requests" not in campaign:
        raise ValueError("campaign draft does not disclose corrected physical HTTP ceiling")
    if "not registered" not in campaign.lower() or "no requests sent" not in campaign.lower():
        raise ValueError("campaign draft does not retain its non-authorization status")

    return {
        "status": "PASS_OFFLINE_M1_MONITOR_CANDIDATE_AUDIT",
        "model_calls": 0,
        "external_cost_usd": 0,
        "control_rows": len(controls),
        "proposal_control_counts": proposal_counts,
        "concordance_control_counts": concordance_counts,
        "matrix_groups": len(groups),
        "unique_matrix_hashes": len(hashes),
        "generation_ceiling": generation_max,
        "physical_http_ceiling": physical_http_max,
        "private_text_external_transfer_requires_fresh_approval": True,
        "sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (SPEC_PATH, CONTROLS_PATH, KEY_PATH, SCHEDULE_PATH, CODEBOOK_PATH,
                         CAMPAIGN_PATH, PROJECTION_PATH, PROJECTION_TEST_PATH,
                         SCORING_PATH, SCORING_TEST_PATH)
        },
    }


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True, indent=2))
