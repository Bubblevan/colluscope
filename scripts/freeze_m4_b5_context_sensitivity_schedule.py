#!/usr/bin/env python3
"""Freeze a sanitized, researcher-only schedule for the M4/B5 campaign.

This script only reads the tracked score table and synthetic fixture manifest.
It emits hashed unit identifiers and arm IDs; it never emits private text,
reference labels, model inputs, or request bodies, and it never dispatches.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCORES = Path("docs/results/deepseek-first-m4/audit/monitor_per_reference_scores.csv")
SYNTHETIC = Path("docs/results/evidence-invariance/synthetic-invariance-groups-v2.json")
EXPERIMENT_ID = "m4-b5-context-sensitivity-campaign-v1"
SHUFFLE_SEED = 20261021
A1_ARMS = ("A1-PUBLIC", "A1-PRIVILEGED-NEUTRAL", "A1-PRIVILEGED-ORIGINAL")
A2_ARMS = ("A2-V2-DIRECT", "A2-PRODUCTION-B5", "A2-PRODUCTION-ARITHMETIC", "A2-REVERSED-LABEL-ORDER")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def file_hash(path: Path) -> str:
    return sha((ROOT / path).read_bytes())


def a1_units() -> list[str]:
    score_path = ROOT / SCORES
    with score_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    selected = [
        row
        for row in rows
        if row.get("population") == "m4_natural_traces"
        and row.get("baseline_id") == "B5_evidence_aware"
        and row.get("task") == "public_harm"
    ]
    by_case: dict[str, Counter[str]] = {}
    for row in selected:
        case_ref = row.get("case_ref")
        permission = row.get("permission")
        if not case_ref or permission not in {"public_only", "privileged_audit"}:
            raise ValueError("A1_SOURCE_ROW_SHAPE_INVALID")
        by_case.setdefault(case_ref, Counter())[permission] += 1

    expected_permissions = Counter({"public_only": 1, "privileged_audit": 1})
    if len(by_case) != 24 or any(counts != expected_permissions for counts in by_case.values()):
        raise ValueError("A1_EXPECTED_24_EXACTLY_PAIRED_CASES")

    # Real case references stay local to this function and are never written.
    return sorted(sha(case_ref.encode("utf-8")) for case_ref in by_case)


def a2_units() -> list[tuple[str, str]]:
    manifest_path = ROOT / SYNTHETIC
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    groups = manifest.get("groups") if isinstance(manifest, dict) else None
    if not isinstance(groups, list) or len(groups) != 20:
        raise ValueError("A2_EXPECTED_20_SYNTHETIC_GROUPS")

    group_ids: set[str] = set()
    units: list[tuple[str, str]] = []
    trajectory_refs = Counter()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("group_id"), str):
            raise ValueError("A2_GROUP_ID_INVALID")
        group_id = group["group_id"]
        if group_id in group_ids:
            raise ValueError("A2_DUPLICATE_GROUP_ID")
        group_ids.add(group_id)
        trajectories = group.get("trajectories")
        if not isinstance(trajectories, list) or len(trajectories) != 2:
            raise ValueError("A2_EXPECTED_TWO_TRAJECTORIES_PER_GROUP")
        trajectory_ids: set[str] = set()
        for trajectory in trajectories:
            trajectory_id = trajectory.get("trajectory_id") if isinstance(trajectory, dict) else None
            reference = trajectory.get("scoring_reference") if isinstance(trajectory, dict) else None
            if not isinstance(trajectory_id, str) or trajectory_id in trajectory_ids:
                raise ValueError("A2_TRAJECTORY_ID_INVALID_OR_DUPLICATE")
            if reference not in {"present", "absent"}:
                raise ValueError("A2_REFERENCE_NOT_BINARY")
            trajectory_ids.add(trajectory_id)
            trajectory_refs[reference] += 1
            units.append((sha(group_id.encode("utf-8")), sha(trajectory_id.encode("utf-8"))))

    if trajectory_refs != Counter({"present": 20, "absent": 20}):
        raise ValueError("A2_REFERENCE_BALANCE_MISMATCH")
    return sorted(units)


def build_schedule() -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for case_hash in a1_units():
        for arm in A1_ARMS:
            material = {"experiment_id": EXPERIMENT_ID, "block": "A1", "unit_hash": case_hash, "arm": arm}
            rows.append({"block": "A1", "unit_sha256": case_hash, "arm_id": arm, "row_sha256": sha(canonical(material))})

    for group_hash, trajectory_hash in a2_units():
        unit_hash = sha(canonical({"group_hash": group_hash, "trajectory_hash": trajectory_hash}))
        for arm in A2_ARMS:
            material = {
                "experiment_id": EXPERIMENT_ID,
                "block": "A2",
                "group_sha256": group_hash,
                "trajectory_sha256": trajectory_hash,
                "unit_hash": unit_hash,
                "arm": arm,
            }
            rows.append({
                "block": "A2",
                "group_sha256": group_hash,
                "trajectory_sha256": trajectory_hash,
                "unit_sha256": unit_hash,
                "arm_id": arm,
                "row_sha256": sha(canonical(material)),
            })

    if len(rows) != 232 or len({row["row_sha256"] for row in rows}) != 232:
        raise ValueError("CAMPAIGN_EXPECTED_232_UNIQUE_REQUEST_ROWS")

    random.Random(SHUFFLE_SEED).shuffle(rows)
    arm_counts = Counter(row["arm_id"] for row in rows)
    expected_counts = Counter({arm: 24 for arm in A1_ARMS}) + Counter({arm: 40 for arm in A2_ARMS})
    if arm_counts != expected_counts:
        raise ValueError("CAMPAIGN_ARM_COUNTS_MISMATCH")

    body: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "status": "FROZEN_ASSIGNMENT_SCHEDULE_NOT_A_DISPATCH_AUTHORIZATION",
        "evidence_class": "monitor_evaluation",
        "shuffle_seed": SHUFFLE_SEED,
        "denominators": {
            "a1_m4_contexts": 24,
            "a1_requests": 72,
            "a2_synthetic_groups": 20,
            "a2_trajectory_rows": 40,
            "a2_requests": 160,
            "total_assigned_requests": 232,
            "max_physical_attempts": 232,
        },
        "arm_counts": dict(sorted(arm_counts.items())),
        "source_hashes": {str(SCORES).replace("\\", "/"): file_hash(SCORES), str(SYNTHETIC).replace("\\", "/"): file_hash(SYNTHETIC)},
        "model_visible_payloads_included": False,
        "reference_labels_included": False,
        "raw_case_or_group_ids_included": False,
        "rows": rows,
    }
    body["schedule_sha256"] = sha(canonical(body))
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("research/schedules/m4-b5-context-sensitivity-campaign-v1.json"),
    )
    args = parser.parse_args()
    output = args.out if args.out.is_absolute() else ROOT / args.out
    result = build_schedule()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "assigned_rows": result["denominators"]["total_assigned_requests"],
        "a1_contexts": result["denominators"]["a1_m4_contexts"],
        "a2_groups": result["denominators"]["a2_synthetic_groups"],
        "arm_counts": result["arm_counts"],
        "schedule_sha256": result["schedule_sha256"],
        "output": str(output.relative_to(ROOT)).replace("\\", "/") if output.is_relative_to(ROOT) else "OUTSIDE_REPO",
        "dispatched": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
