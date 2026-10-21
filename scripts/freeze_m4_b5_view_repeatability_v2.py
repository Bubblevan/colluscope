#!/usr/bin/env python3
"""Freeze a hash-only, no-payload schedule for the M4 B5 repeatability screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/schedules/m4-b5-context-sensitivity-campaign-v1.json"
DEFAULT_OUT = ROOT / "research/drafts/m4-b5-view-repeatability-v2-schedule.json"
EXPERIMENT_ID = "m4-b5-view-repeatability-v2"
SHUFFLE_SEED = 20261022
EXPECTED_CONTEXTS = 24
VIEWS = ("public_only", "privileged_original")
REPEATS = (1, 2, 3)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def schedule_object() -> dict[str, Any]:
    source_bytes = SOURCE.read_bytes()
    source = json.loads(source_bytes)
    rows = source.get("rows")
    if not isinstance(rows, list):
        raise ValueError("SOURCE_ROWS_INVALID")

    arm_to_view = {
        "A1-PUBLIC": "public_only",
        "A1-PRIVILEGED-ORIGINAL": "privileged_original",
    }
    by_view: dict[str, dict[str, dict[str, str]]] = {view: {} for view in VIEWS}
    for row in rows:
        if not isinstance(row, dict) or row.get("arm_id") not in arm_to_view:
            continue
        view = arm_to_view[row["arm_id"]]
        unit = row.get("unit_sha256")
        row_hash = row.get("row_sha256")
        if not isinstance(unit, str) or not isinstance(row_hash, str):
            raise ValueError("SOURCE_A1_ROW_SHAPE_INVALID")
        if unit in by_view[view]:
            raise ValueError("DUPLICATE_SOURCE_CONTEXT_VIEW")
        by_view[view][unit] = {"source_row_sha256": row_hash}

    units = sorted(by_view[VIEWS[0]])
    if len(units) != EXPECTED_CONTEXTS or set(units) != set(by_view[VIEWS[1]]):
        raise ValueError("SOURCE_A1_PAIRING_MISMATCH")

    assignments: list[dict[str, Any]] = []
    for unit in units:
        for view in VIEWS:
            for repeat in REPEATS:
                material = {
                    "experiment_id": EXPERIMENT_ID,
                    "unit_sha256": unit,
                    "view": view,
                    "repeat": repeat,
                }
                assignments.append({
                    "assignment_id": sha(canonical(material)),
                    "unit_sha256": unit,
                    "view": view,
                    "repeat": repeat,
                    "source_row_sha256": by_view[view][unit]["source_row_sha256"],
                })

    if len(assignments) != 144 or len({row["assignment_id"] for row in assignments}) != 144:
        raise ValueError("EXPECTED_144_UNIQUE_ASSIGNMENTS")
    random.Random(SHUFFLE_SEED).shuffle(assignments)

    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "draft_not_registered_not_authorized",
        "experiment_id": EXPERIMENT_ID,
        "evidence_class": "monitor_evaluation",
        "question": "For these 24 fixed M4 contexts, do Public-only versus Privileged-original majority-label differences exceed within-view label variation across identical repeated requests?",
        "source_schedule_sha256": sha(source_bytes),
        "shuffle_seed": SHUFFLE_SEED,
        "denominators": {
            "contexts": EXPECTED_CONTEXTS,
            "views_per_context": len(VIEWS),
            "repeats_per_context_view": len(REPEATS),
            "assigned_physical_attempts": 144,
        },
        "model_visible_payloads_included": False,
        "reference_labels_included": False,
        "raw_case_or_group_ids_included": False,
        "private_message_text_included": False,
        "rows": assignments,
    }
    result["schedule_sha256"] = sha(canonical(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.out.resolve()
    if ROOT.resolve() not in out.parents:
        raise ValueError("OUTPUT_MUST_STAY_WITHIN_REPOSITORY")

    payload = json.dumps(schedule_object(), indent=2, ensure_ascii=False) + "\n"
    if out.exists():
        if out.read_text(encoding="utf-8") != payload:
            raise ValueError("REFUSE_TO_OVERWRITE_DIFFERENT_FROZEN_SCHEDULE")
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload.encode("utf-8"))

    schedule = json.loads(payload)
    print(json.dumps({
        "status": schedule["status"],
        "experiment_id": EXPERIMENT_ID,
        "schedule_sha256": schedule["schedule_sha256"],
        "source_schedule_sha256": schedule["source_schedule_sha256"],
        "assigned_physical_attempts": schedule["denominators"]["assigned_physical_attempts"],
        "private_message_text_included": False,
        "path": str(out.relative_to(ROOT.resolve())),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # explicit freeze failure, never repair silently
        print(f"FREEZE_ERROR:{type(exc).__name__}:{exc}", file=sys.stderr)
        raise
