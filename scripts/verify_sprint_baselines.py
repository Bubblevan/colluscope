from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.sprint_baselines import build_monitor_payload, canonical_json  # noqa: E402
from colluscope.sprint_controls import construction_truth_rows, scripted_cases  # noqa: E402
from colluscope.sprint_replay import all_references  # noqa: E402
from prepare_sprint_baselines import (  # noqa: E402
    CONFIG_PATH,
    HASHED_INPUT_FILES,
    LLM_CELLS,
    PROMPT_DIR,
    PROTOCOL,
    SOURCE_FILES,
    TASKS,
    _family_split_id,
    _make_llm_schedule,
    make_split_manifest,
)
from colluscope.m4_scenarios import verify_scenario_document  # noqa: E402
from freeze_m4_split import build as build_m4_split  # noqa: E402


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _same_json(path: Path, expected: Any, label: str) -> None:
    actual = json.loads(path.read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError(f"{label} differs from its deterministic reconstruction")


def verify(output_dir: Path) -> dict[str, Any]:
    data_dir = ROOT / "data/sprint-baseline-v1"
    cases = scripted_cases()
    truth = construction_truth_rows(cases)
    references = all_references(cases)
    schedule = _read_jsonl(output_dir / "request_schedule.jsonl")

    if _read_jsonl(data_dir / "controls.jsonl") != cases:
        raise ValueError("control cases differ from deterministic reconstruction")
    if _read_jsonl(data_dir / "control-construction-truth.jsonl") != truth:
        raise ValueError("construction truth differs from deterministic reconstruction")
    if _read_jsonl(data_dir / "references.jsonl") != references:
        raise ValueError("observable references differ from independent replay")
    _same_json(ROOT / "configs/sprint-baseline-splits-v1.json",
               make_split_manifest(cases), "baseline split manifest")

    expected_schedule = _make_llm_schedule(cases)
    if schedule != expected_schedule:
        raise ValueError("request schedule differs from payload/hash reconstruction")
    request_ids = [row["request_id"] for row in schedule]
    if len(schedule) != 280 or len(set(request_ids)) != len(request_ids):
        raise ValueError("schedule must contain exactly 280 unique logical requests")
    if any(row["status"] != "NOT_DISPATCHED_NO_AUTHORIZATION" or row["max_attempts"] != 1
           for row in schedule):
        raise ValueError("schedule contains a dispatched row or retry allowance")

    case_by_ref = {case["case_ref"]: case for case in cases}
    for row in schedule:
        case = case_by_ref[row["case_ref"]]
        payload, _ = build_monitor_payload(
            case, row["baseline_id"], row["task"], row["permission"]
        )
        encoded = canonical_json(payload)
        if sha256(encoded).hexdigest() != row["payload_sha256"]:
            raise ValueError(f"payload hash mismatch for {row['request_id']}")
        if len(encoded) != row["payload_bytes"]:
            raise ValueError(f"payload byte count mismatch for {row['request_id']}")
        if row["split_group_id"] != _family_split_id(row["scenario_family_id"]):
            raise ValueError(f"split-group hash mismatch for {row['request_id']}")

    grouped: dict[tuple[str, str], int] = {}
    for row in schedule:
        key = row["baseline_id"], row["permission"]
        grouped[key] = grouped.get(key, 0) + 1
    expected_cells = {
        (baseline, permission): len(cases) * len(TASKS)
        for baseline, permission in LLM_CELLS
    }
    if grouped != expected_cells:
        raise ValueError(f"baseline/permission cell counts differ: {grouped}")

    receipt = json.loads((output_dir / "preparation_receipt.json").read_text(encoding="utf-8"))
    config = CONFIG_PATH.read_bytes()
    prompt_hashes = {
        name: sha256((PROMPT_DIR / name).read_bytes()).hexdigest()
        for name in ("system.txt", "user.txt", "tasks.json")
    }
    if receipt["protocol_config_sha256"] != sha256(config).hexdigest():
        raise ValueError("receipt config hash does not match current config")
    if receipt["prompt_hashes"] != prompt_hashes:
        raise ValueError("receipt prompt hashes do not match current prompt files")
    if any(receipt[key] != 0 for key in (
        "real_model_or_api_calls", "external_traffic", "historical_raw_data_access"
    )):
        raise ValueError("receipt claims a prohibited inference, egress, or raw-data access")
    if receipt["scheduled_logical_requests"] != len(schedule) or receipt["max_physical_attempts"] != 280:
        raise ValueError("receipt request budget differs from schedule")

    source_inventory = json.loads((output_dir / "source_inventory.json").read_text(encoding="utf-8"))
    actual_source_hashes = {
        relative: sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in SOURCE_FILES
    }
    if source_inventory["sha256"] != actual_source_hashes:
        raise ValueError("historical M0-M3 source inventory changed")
    if source_inventory["historical_frozen_artifacts_modified"] is not False:
        raise ValueError("source inventory does not preserve frozen artifact status")

    expected_files = {
        path.name: sha256(path.read_bytes()).hexdigest()
        for path in output_dir.iterdir()
        if path.is_file() and path.name != "artifact_sha256.json"
    }
    saved_artifacts = json.loads((output_dir / "artifact_sha256.json").read_text(encoding="utf-8"))
    expected_inputs = {
        relative: sha256((ROOT / relative).read_bytes()).hexdigest()
        for relative in HASHED_INPUT_FILES
    }
    if saved_artifacts != {
        "schema_version": "sprint-baseline-artifact-sha256-v1",
        "outputs": expected_files,
        "inputs": expected_inputs,
    }:
        raise ValueError("prepared artifact hash inventory mismatch")

    with (output_dir / "main_results_table.csv").open(newline="", encoding="utf-8") as handle:
        result_rows = list(csv.DictReader(handle))
    offline = [row for row in result_rows if row["result_status"] == "SCRIPTED_OFFLINE_SANITY_ONLY"]
    not_run = [row for row in result_rows if row["result_status"] == "NOT_RUN"]
    if len(offline) != 4 or len(not_run) != 7:
        raise ValueError("results table must keep four deterministic rows and seven LLM rows")
    if any(row["model_calls"] != "0" for row in result_rows):
        raise ValueError("results table implies model calls")
    if any(row["exact_accuracy"] != "" for row in not_run):
        raise ValueError("unrun LLM baseline contains a fabricated metric")

    scenario_doc = json.loads((ROOT / "configs/m4-scenarios-v1.json").read_text(encoding="utf-8"))
    verify_scenario_document(scenario_doc, ROOT)
    _same_json(ROOT / "configs/m4-splits-v1.json", build_m4_split(), "M4 group split")
    m4_groups = json.loads((ROOT / "configs/m4-splits-v1.json").read_text(encoding="utf-8"))["groups"]
    if len(m4_groups) != 24 or len({row["split_group_id"] for row in m4_groups}) != 24:
        raise ValueError("M4 split does not contain 24 unique matched groups")

    return {
        "status": "PASS_OFFLINE_ARTIFACT_REPLAY_ONLY",
        "cases": len(cases),
        "reference_rows": len(references),
        "scheduled_requests": len(schedule),
        "dispatched_requests": 0,
        "model_calls": 0,
        "historical_source_files_hash_verified": len(actual_source_hashes),
        "m4_scenarios": len(scenario_doc["families"]),
        "m4_groups": len(m4_groups),
        "claim_scope": "scripted controls and deterministic artifact integrity only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only offline verification; never dispatches requests.")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/results/sprint-baseline-v1")
    args = parser.parse_args()
    report = verify(args.output)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
