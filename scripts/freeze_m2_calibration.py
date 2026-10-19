#!/usr/bin/env python3
"""Close the frozen F0/F1 calibration stage without tuning any setting."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.m2_corpus import file_sha256  # noqa: E402
from scripts.run_m2_monitor import read_jsonl, utc_now, write_json  # noqa: E402


def _latest_terminals(path: Path) -> dict[str, str]:
    latest: dict[str, str] = {}
    for row in read_jsonl(path):
        if row.get("event") == "evaluation_terminal":
            latest[row["eval_id"]] = row["status"]
    return latest


def close_calibration(out: Path) -> dict:
    plan = json.loads((out / "private/evaluation-plan.json").read_text(encoding="utf-8"))
    evaluations = plan["logical_evaluations"]
    calibration = [row for row in evaluations if row["partition"] in {"F0", "F1"}]
    heldout = [row for row in evaluations if row["partition"] in {"F2", "F3"}]
    if len(calibration) != 500 or len(heldout) != 500:
        raise ValueError("the frozen plan must contain 500 calibration and 500 held-out evaluations")
    terminal = _latest_terminals(out / "evaluation-ledger.jsonl")
    missing = [row["eval_id"] for row in calibration if row["eval_id"] not in terminal]
    premature = [row["eval_id"] for row in heldout if row["eval_id"] in terminal]
    if missing:
        raise RuntimeError(f"calibration cannot close: {len(missing)} F0/F1 evaluations lack terminal records")
    if premature:
        raise PermissionError("held-out F2/F3 evaluation began before the calibration freeze")
    request_states = {}
    for row in read_jsonl(out / "requests-ledger.jsonl"):
        if row.get("event") in {"response_returned", "response_file_recovered", "request_failed", "request_interrupted"}:
            request_states[row["request_id"]] = row.get("status")
    f1 = [row for row in calibration if row["partition"] == "F1"]
    status_counts = Counter(terminal[row["eval_id"]] for row in f1)
    f1_requests = {row["request_id"] for row in f1}
    valid_responses = sum(request_states.get(request_id) == "valid" for request_id in f1_requests)
    freeze = {
        "schema_version": "colluscope-m2-calibration-closure-v1",
        "status": "CALIBRATION_CLOSED_SETTINGS_UNCHANGED",
        "protocol_id": "colluscope-m2-one-shot-v1",
        "closed_at_utc": utc_now(),
        "policy": "F0 descriptive only; F1 checked for completion/schema validity; no prompts, thresholds, labels, model settings, or scorer were tuned.",
        "f0_evaluations_terminal": sum(row["partition"] == "F0" for row in calibration),
        "f1_evaluations_terminal": len(f1),
        "f1_unique_requests": len(f1_requests),
        "f1_unique_valid_responses": valid_responses,
        "f1_evaluation_status_counts": dict(sorted(status_counts.items())),
        "f1_request_terminal_status_counts": dict(sorted(Counter(
            request_states.get(request_id, "missing") for request_id in f1_requests).items())),
        "held_out_terminal_evaluations_before_freeze": 0,
        "preparation_manifest_sha256": file_sha256(out / "preparation-manifest.json"),
        "freeze_manifest_sha256": file_sha256(ROOT / "configs/m2-one-shot-freeze-manifest.json"),
        "m2_config_sha256": file_sha256(ROOT / "configs/m2-one-shot.toml"),
        "system_prompt_sha256": file_sha256(ROOT / "prompts/m2-v1/system.txt"),
        "user_prompt_sha256": file_sha256(ROOT / "prompts/m2-v1/user.txt"),
        "output_schema_sha256": file_sha256(ROOT / "prompts/m2-v1/output.schema.json"),
    }
    path = out / "calibration-freeze.json"
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("status") == freeze["status"] and \
                existing.get("preparation_manifest_sha256") == freeze["preparation_manifest_sha256"]:
            return existing
        raise FileExistsError("a different calibration freeze already exists; preserve it and do not overwrite")
    write_json(path, freeze)
    return freeze


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, default=ROOT / "runs/m2/one-shot-20261019")
    args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to(ROOT / "runs/m2"):
        raise ValueError("calibration outputs must remain under the Git-ignored M2 run root")
    result = close_calibration(run)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
