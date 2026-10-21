"""Create a sanitized, output-independent assignment schedule for B5 diagnostics.

This script reads only the already frozen A2 and M4 repeatability schedules.
It does not read raw responses, labels, or private message payloads and cannot
make provider requests. Exact request-body compilation/hashing remains a later
offline preflight gate before campaign registration or dispatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_ID = "m4-b5-mechanism-factorial-v1"
FACTORIAL_SOURCE = ROOT / "research/drafts/m4-b5-context-sensitivity-campaign-v1-schedule-draft.json"
REPEAT_SOURCE = ROOT / "research/drafts/m4-b5-view-repeatability-v2-schedule.json"
DEFAULT_OUT = ROOT / "research/drafts/m4-b5-mechanism-campaign-v1-schedule.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assignment(row: dict[str, Any]) -> dict[str, Any]:
    row = dict(row)
    row["assignment_id"] = digest({"campaign_id": CAMPAIGN_ID, **row})
    return row


def build() -> dict[str, Any]:
    factorial_source = json.loads(FACTORIAL_SOURCE.read_text(encoding="utf-8"))
    repeat_source = json.loads(REPEAT_SOURCE.read_text(encoding="utf-8"))
    synthetic = [r for r in factorial_source["rows"] if r.get("arm_id") == "A2-PRODUCTION-B5"]
    if len(synthetic) != 40 or len({r["unit_sha256"] for r in synthetic}) != 40:
        raise ValueError("frozen A2 production-B5 source must contain 40 unique units")
    m4_public = [r for r in repeat_source["rows"] if r["view"] == "public_only" and r["repeat"] == 1]
    m4_original = [r for r in repeat_source["rows"] if r["view"] == "privileged_original" and r["repeat"] == 1]
    if len(m4_public) != 24 or len(m4_original) != 24:
        raise ValueError("frozen M4 source must contain 24 public and 24 original-message contexts")

    rows: list[dict[str, Any]] = []
    label_orders = ("canonical", "reversed")
    enum_orders = ("canonical", "reversed")
    arithmetic_forms = ("none", "correct_six_welfare_totals", "length_matched_irrelevant_numbers")
    for source in synthetic:
        base = {
            "phase": "synthetic_factorial",
            "unit_sha256": source["unit_sha256"],
            "group_sha256": source["group_sha256"],
            "trajectory_sha256": source["trajectory_sha256"],
            "source_row_sha256": source["row_sha256"],
            "public_harm_instruction": "historical",
        }
        for label_order in label_orders:
            for enum_order in enum_orders:
                for arithmetic_form in arithmetic_forms:
                    rows.append(assignment({
                        **base,
                        "label_order": label_order,
                        "tool_enum_order": enum_order,
                        "arithmetic_form": arithmetic_form,
                        "replicate": 1,
                    }))
        # Exact duplicate of the canonical, no-aid baseline estimates repeat
        # disagreement on every synthetic unit without selecting cases.
        rows.append(assignment({
            **base,
            "label_order": "canonical",
            "tool_enum_order": "canonical",
            "arithmetic_form": "none",
            "replicate": 2,
        }))
        # A clear operational definition tests whether label/task wording is
        # part of the all-present failure. The output schema stays unchanged.
        rows.append(assignment({
            **base,
            "label_order": "canonical",
            "tool_enum_order": "canonical",
            "arithmetic_form": "none",
            "public_harm_instruction": "explicit_regret_definition",
            "replicate": 1,
        }))

    for source in m4_public:
        rows.append(assignment({
            "phase": "m4_scale_invariance",
            "unit_sha256": source["unit_sha256"],
            "source_row_sha256": source["source_row_sha256"],
            "view": "public_only",
            "payoff_scale_multiplier": 5,
            "replicate": 1,
        }))

    for source in repeat_source["rows"]:
        rows.append(assignment({
            "phase": "m4_view_repeatability",
            "unit_sha256": source["unit_sha256"],
            "source_row_sha256": source["source_row_sha256"],
            "view": source["view"],
            "repeat": source["repeat"],
        }))

    expected = {
        "synthetic_factorial": 480,
        "synthetic_exact_duplicate": 40,
        "synthetic_explicit_definition": 40,
        "m4_scale_invariance": 24,
        "m4_view_repeatability": 144,
    }
    actual = {
        "synthetic_factorial": sum(r["phase"] == "synthetic_factorial" and r["replicate"] == 1 and r["public_harm_instruction"] == "historical" for r in rows),
        "synthetic_exact_duplicate": sum(r["phase"] == "synthetic_factorial" and r["replicate"] == 2 for r in rows),
        "synthetic_explicit_definition": sum(r["phase"] == "synthetic_factorial" and r["public_harm_instruction"] == "explicit_regret_definition" for r in rows),
        "m4_scale_invariance": sum(r["phase"] == "m4_scale_invariance" for r in rows),
        "m4_view_repeatability": sum(r["phase"] == "m4_view_repeatability" for r in rows),
    }
    if actual != expected or len(rows) != 728:
        raise ValueError(f"assignment count mismatch: {actual}, total={len(rows)}")
    if len({r["assignment_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate assignment IDs")

    # Hash-sort gives a deterministic interleaving independent of model output.
    rows.sort(key=lambda r: hashlib.sha256(
        f"{CAMPAIGN_ID}:interleave:{r['assignment_id']}".encode("ascii")).hexdigest())
    payload = {
        "schema_version": "m4-b5-mechanism-campaign-schedule-v1",
        "experiment_id": CAMPAIGN_ID,
        "status": "DESIGN_DRAFT_NOT_REGISTERED_NOT_AUTHORIZED",
        "evidence_class": "offline_assignment_schedule_only",
        "seed": "sha256-hash-order-v1",
        "assignment_count": len(rows),
        "phase_counts": expected,
        "source_hashes": {
            str(FACTORIAL_SOURCE.relative_to(ROOT)).replace("\\", "/"): file_sha(FACTORIAL_SOURCE),
            str(REPEAT_SOURCE.relative_to(ROOT)).replace("\\", "/"): file_sha(REPEAT_SOURCE),
        },
        "contains_request_payloads": False,
        "contains_reference_labels": False,
        "contains_raw_case_ids": False,
        "contains_private_message_text": False,
        "rows": rows,
    }
    payload["schedule_sha256"] = digest(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    encoded = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.check:
        existing = json.loads(args.out.read_text(encoding="utf-8"))
        if existing != result:
            raise SystemExit("FAIL: saved schedule differs from deterministic rebuild")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({
        "status": "PASS_OFFLINE_SCHEDULE_BUILD" if not args.check else "PASS_OFFLINE_SCHEDULE_REBUILD",
        "experiment_id": CAMPAIGN_ID,
        "assigned_rows": result["assignment_count"],
        "phase_counts": result["phase_counts"],
        "schedule_sha256": result["schedule_sha256"],
        "model_calls": 0,
        "private_text_exported": False,
        "registered": False,
        "authorized": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
