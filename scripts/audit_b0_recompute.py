#!/usr/bin/env python3
"""Quantify the retained pre-fix versus reference-blind B0 replay delta."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "docs/results/sprint-execution-readiness/superseded-b0-before-v2"
NEW = ROOT / "docs/results/sprint-baseline-v1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[tuple[str, str, str, str, str], dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return {
        (row["baseline_id"], row["case_ref"], row["task"], row["view"], row["permission"]): row
        for row in rows
    }


def audit() -> dict[str, Any]:
    old_path = OLD / "offline_baseline_scores.jsonl"
    new_path = NEW / "offline_baseline_scores.jsonl"
    old_csv, new_csv = OLD / "main_results_table.csv", NEW / "main_results_table.csv"
    old, new = _read(old_path), _read(new_path)
    if set(old) != set(new):
        raise ValueError("superseded and current summary row identities differ")
    b0_changed = [
        {"case_ref": key[1], "task": key[2], "view": key[3], "permission": key[4],
         "superseded_prediction": old[key]["prediction_label"],
         "current_prediction": new[key]["prediction_label"],
         "superseded_exact_correct": old[key]["exact_correct"],
         "current_exact_correct": new[key]["exact_correct"]}
        for key in sorted(old)
        if key[0] == "B0_always_negative" and old[key]["prediction_label"] != new[key]["prediction_label"]
    ]
    b1_changed = [key for key in sorted(old) if key[0] == "B1_deterministic_replay"
                  and (old[key]["prediction_label"], old[key]["exact_correct"])
                  != (new[key]["prediction_label"], new[key]["exact_correct"])]
    if len(b0_changed) != 2 or b1_changed:
        raise ValueError("unexpected B0 delta or B1 drift")
    aggregate = {}
    for key in sorted(old):
        if key[0] != "B0_always_negative":
            continue
        permission = key[4]
        row = aggregate.setdefault(permission, {"superseded_assessable": 0, "superseded_correct": 0,
                                                "current_assessable": 0, "current_correct": 0})
        row["superseded_assessable"] += int(old[key]["assessable"] is True)
        row["superseded_correct"] += int(old[key]["exact_correct"] is True)
        row["current_assessable"] += int(new[key]["assessable"] is True)
        row["current_correct"] += int(new[key]["exact_correct"] is True)
    b0_old_json = [row for row in old.values() if row.get("baseline_id") == "B0_always_negative"]
    b0_new_json = [row for row in new.values() if row.get("baseline_id") == "B0_always_negative"]
    return {
        "schema_version": "b0-reference-blind-recompute-audit-v1",
        "status": "PASS_B0_LABEL_BLINDNESS_COUNTEREXAMPLE_REPLAY",
        "superseded_scores_sha256": _sha(old_path),
        "current_scores_sha256": _sha(new_path),
        "superseded_summary_sha256": _sha(old_csv),
        "current_summary_sha256": _sha(new_csv),
        "superseded_b0_rows": sum(row.get("baseline_id") == "B0_always_negative" for row in b0_old_json),
        "current_b0_rows": sum(row.get("baseline_id") == "B0_always_negative" for row in b0_new_json),
        "changed_b0_predictions": b0_changed,
        "changed_b1_predictions": 0,
        "b0_by_permission": aggregate,
        "summary_table_files_exist": old_csv.is_file() and new_csv.is_file(),
        "interpretation": "Two former matches on ambiguous positive-reference rows came from reference-label mirroring. The current B0 uses only evidence completeness and frozen negative labels; these are now errors. B1 is unchanged.",
        "historical_failure_artifacts_preserved": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/results/sprint-execution-readiness/b0-score-delta.json")
    args = parser.parse_args()
    report = audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
