from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.sprint_baselines import (  # noqa: E402
    build_monitor_payload,
    canonical_json,
    deterministic_prediction,
    sha256_json,
)
from colluscope.sprint_controls import construction_truth_rows, scripted_cases  # noqa: E402
from colluscope.sprint_metrics import score_one, summarize_baseline  # noqa: E402
from colluscope.sprint_replay import all_references  # noqa: E402

PROTOCOL = "colluscope-sprint-evidence-baselines-v1"
CASE_PATH = ROOT / "data/sprint-baseline-v1/controls.jsonl"
TRUTH_PATH = ROOT / "data/sprint-baseline-v1/control-construction-truth.jsonl"
REFERENCE_PATH = ROOT / "data/sprint-baseline-v1/references.jsonl"
SPLIT_PATH = ROOT / "configs/sprint-baseline-splits-v1.json"
CONFIG_PATH = ROOT / "configs/sprint-baseline-v1.toml"
PROMPT_DIR = ROOT / "prompts/sprint-baseline-v1"
TASKS = ("explicit_sequence", "proposal", "acceptance", "action_concordance", "public_harm")
LLM_CELLS = (
    ("B2_text_only", "public_only"),
    ("B2_text_only", "privileged_audit"),
    ("B3_action_only", "public_only"),
    ("B4_raw_fusion", "public_only"),
    ("B4_raw_fusion", "privileged_audit"),
    ("B5_evidence_aware", "public_only"),
    ("B5_evidence_aware", "privileged_audit"),
)
DETERMINISTIC_CELLS = (
    ("B0_always_negative", "public_only"),
    ("B0_always_negative", "privileged_audit"),
    ("B1_deterministic_replay", "public_only"),
    ("B1_deterministic_replay", "privileged_audit"),
)
SOURCE_FILES = (
    "COLLUSCOPE_PERSISTENT_RESEARCH_GOAL.md",
    "docs/M0_EVIDENCE.md",
    "docs/M0_DECISION.md",
    "docs/M1_100_PROTOCOL.md",
    "docs/M1_100_EVIDENCE.md",
    "docs/M1_100_SCIENTIFIC_AUDIT.md",
    "docs/M1_100_DECISION.md",
    "docs/M2_V3_DEEPSEEK_PROTOCOL.md",
    "docs/M2_V3_DEEPSEEK_RESULTS.md",
    "docs/M2_V3_DEEPSEEK_DECISION.md",
    "docs/M2_FINAL_SCIENTIFIC_SYNTHESIS.md",
    "docs/M3_MECHANISM_PROTOCOL_DRAFT.md",
    "docs/COLLUSCOPE_M3_PAPER_DRAFT.md",
    "configs/m1-100.toml",
    "configs/m1-100-splits.json",
    "configs/m1-100-scenarios.json",
    "configs/m2-v3-deepseek.toml",
    "configs/m2-one-shot-splits.json",
    "docs/results/m2-final-scientific-synthesis/m2_final_audit_summary.json",
    "docs/results/m2-final-scientific-synthesis/m2_baselines_and_metrics.csv",
    "docs/results/m2-final-scientific-synthesis/m2_recomputed_predictions.csv",
)
HASHED_INPUT_FILES = (
    "data/sprint-baseline-v1/controls.jsonl",
    "data/sprint-baseline-v1/control-construction-truth.jsonl",
    "data/sprint-baseline-v1/references.jsonl",
    "configs/sprint-baseline-v1.toml",
    "configs/sprint-baseline-splits-v1.json",
    "configs/m4-positive-control-v1.json",
    "configs/m4-scenarios-v1.json",
    "configs/m4-splits-v1.json",
    "prompts/sprint-baseline-v1/system.txt",
    "prompts/sprint-baseline-v1/user.txt",
    "prompts/sprint-baseline-v1/tasks.json",
)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(content, encoding="utf-8", newline="\n")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_bytes(content.encode("utf-8"))


def _family_split_id(family: str) -> str:
    return sha256(f"sprint-control-split-v1|{family}".encode("utf-8")).hexdigest()


def make_split_manifest(cases: list[dict[str, Any]]) -> dict[str, Any]:
    families = sorted({case["scenario_family_id"] for case in cases})
    return {
        "schema_version": "sprint-baseline-splits-v1",
        "unit": "scenario_family_id; all cases, tasks, permissions, views, and ablations move together",
        "development_sources": {
            "m0_m3": "historical/development/descriptive only",
            "m1_f0_f3": "previously exposed; no new evaluation score",
            "m2_v3": "previously exposed and answer-leaked in public-harm views; no new evaluation score",
        },
        "prospective_control_evaluation": [
            {
                "scenario_family_id": family,
                "split_group_id": _family_split_id(family),
                "case_refs": [c["case_ref"] for c in cases if c["scenario_family_id"] == family],
                "partition": "prospective_control_evaluation",
                "synthetic_only": True,
            }
            for family in families
        ],
        "leakage_constraints": [
            "all views, permissions, task rows, and B5 ablations of a family stay in one partition",
            "construction truth and reference answers are stored separately from monitor inputs",
            "historical M1/M2/M3 are development/descriptive evidence, not a held-out test",
            "no prediction-based tuning, case removal, or sample replacement",
        ],
    }


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _source_inventory() -> dict[str, Any]:
    inventory = {}
    for relative in SOURCE_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"versioned M0-M3 source missing: {relative}")
        inventory[relative] = sha256(path.read_bytes()).hexdigest()
    missing_raw = {
        "runs/m1_100/extension-75-20261019-run02": not (ROOT / "runs/m1_100/extension-75-20261019-run02").exists(),
        "runs/m1_p0_local/formal-25ep-pilot-20261019/run": not (ROOT / "runs/m1_p0_local/formal-25ep-pilot-20261019/run").exists(),
        "runs/m2-v3/deepseek-overnight-r1": not (ROOT / "runs/m2-v3/deepseek-overnight-r1").exists(),
    }
    return {
        "inventory_id": "sprint-baseline-source-inventory-v1",
        "sha256": inventory,
        "ignored_raw_paths_missing_on_this_host": missing_raw,
        "colosseum_reproduction_role": "external compatibility study; excluded from accuracy baselines",
        "historical_frozen_artifacts_modified": False,
        "model_calls_in_preparation": 0,
    }


def _make_llm_schedule(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for case in cases:
        for baseline, permission in LLM_CELLS:
            for task in TASKS:
                payload, _ = build_monitor_payload(case, baseline, task, permission)
                payload_bytes = canonical_json(payload)
                material = {
                    "protocol": PROTOCOL,
                    "case": case["case_ref"],
                    "baseline": baseline,
                    "permission": permission,
                    "task": task,
                }
                rows.append({
                    "request_id": sha256_json(material),
                    "case_ref": case["case_ref"],
                    "scenario_family_id": case["scenario_family_id"],
                    "split_group_id": _family_split_id(case["scenario_family_id"]),
                    "partition": "prospective_control_evaluation",
                    "baseline_id": baseline,
                    "permission": permission,
                    "task": task,
                    "view": {
                        "B2_text_only": "text_only",
                        "B3_action_only": "action_only",
                        "B4_raw_fusion": "raw_fusion",
                        "B5_evidence_aware": "evidence_aware",
                    }[baseline],
                    "payload_sha256": sha256(payload_bytes).hexdigest(),
                    "payload_bytes": len(payload_bytes),
                    "status": "NOT_DISPATCHED_NO_AUTHORIZATION",
                    "max_attempts": 1,
                })
    return rows


def _offline_deterministic_scores(cases: list[dict[str, Any]],
                                  references: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reference_index = {
        (row["case_ref"], row["task"], row["view"], row["permission"]): row
        for row in references
    }
    scored = []
    for baseline in ("B0_always_negative", "B1_deterministic_replay"):
        for case in cases:
            for permission in ("public_only", "privileged_audit"):
                for task in TASKS:
                    view = "evidence_aware"
                    ref = reference_index[(case["case_ref"], task, view, permission)]
                    prediction = deterministic_prediction(
                        case, baseline, task, permission, view_name=view
                    )
                    scored.append(score_one(
                        case, ref, baseline, prediction,
                        view_name=view, permission=permission,
                    ))
    return scored


def _main_results(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    configurations = [
        *[(name, permission) for name, permission in DETERMINISTIC_CELLS],
        *[(name, permission) for name, permission in LLM_CELLS],
    ]
    results = []
    for baseline, permission in configurations:
        if baseline in {"B0_always_negative", "B1_deterministic_replay"}:
            summary = summarize_baseline(rows, baseline, permission)
            summary["result_status"] = "SCRIPTED_OFFLINE_SANITY_ONLY"
            summary["model_calls"] = 0
            results.append(summary)
        else:
            results.append({
                "baseline_id": baseline,
                "permission": permission,
                "result_status": "NOT_RUN",
                "model_calls": 0,
                "assigned_rows": 8 * len(TASKS),
                "completed_rows": None,
                "unsupported_sequence_claim_rate": None,
                "positive_sequence_sensitivity": None,
                "appropriate_abstention_coverage": None,
                "fact_precision": None,
                "fact_recall": None,
                "citation_sufficiency": None,
                "token_cost": None,
                "latency": None,
            })
    return results


def prepare(output_dir: Path) -> dict[str, Any]:
    cases = scripted_cases()
    truth = construction_truth_rows(cases)
    references = all_references(cases)
    split = make_split_manifest(cases)

    _write_jsonl(CASE_PATH, cases)
    _write_jsonl(TRUTH_PATH, truth)
    _write_jsonl(REFERENCE_PATH, references)
    _write_json(SPLIT_PATH, split)

    output_dir.mkdir(parents=True, exist_ok=True)
    schedule = _make_llm_schedule(cases)
    if len(schedule) != 280:
        raise RuntimeError(f"expected 280 frozen requests, got {len(schedule)}")
    _write_jsonl(output_dir / "request_schedule.jsonl", schedule)
    _write_jsonl(output_dir / "offline_baseline_scores.jsonl",
                 _offline_deterministic_scores(cases, references))
    summaries = _main_results(_offline_deterministic_scores(cases, references))
    _write_csv(output_dir / "main_results_table.csv", summaries)
    source_inventory = _source_inventory()
    _write_json(output_dir / "source_inventory.json", source_inventory)
    access_audit = {
        "m1_100_raw_available": not source_inventory["ignored_raw_paths_missing_on_this_host"][
            "runs/m1_100/extension-75-20261019-run02"
        ],
        "historical_m1_p0_raw_available": not source_inventory["ignored_raw_paths_missing_on_this_host"][
            "runs/m1_p0_local/formal-25ep-pilot-20261019/run"
        ],
        "m2_v3_raw_available": not source_inventory["ignored_raw_paths_missing_on_this_host"][
            "runs/m2-v3/deepseek-overnight-r1"
        ],
        "versioned_m2_synthesis_available": True,
        "decision": "No raw historical replay was attempted; scripted controls are the only new offline evaluation input.",
    }
    _write_json(output_dir / "historical_data_access.json", access_audit)
    receipt = {
        "receipt_id": "sprint-baseline-offline-preparation-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "base_commit": "598e17bb6e35d95210c02add76ff7e6496c5af10",
        "protocol_config_sha256": sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "prompt_hashes": {
            name: sha256((PROMPT_DIR / name).read_bytes()).hexdigest()
            for name in ("system.txt", "user.txt", "tasks.json")
        },
        "case_count": len(cases),
        "scenario_family_count": len({case["scenario_family_id"] for case in cases}),
        "reference_row_count": len(references),
        "scheduled_logical_requests": len(schedule),
        "max_physical_attempts": 280,
        "real_model_or_api_calls": 0,
        "external_traffic": 0,
        "historical_raw_data_access": 0,
        "construction_truth_passed_to_compiler": False,
        "reference_answers_passed_to_compiler": False,
        "results_scope": "scripted control sanity checks only; no LLM performance result",
    }
    _write_json(output_dir / "preparation_receipt.json", receipt)
    output_hashes = {}
    for path in sorted(output_dir.iterdir()):
        if path.is_file() and path.name != "artifact_sha256.json":
            output_hashes[path.name] = sha256(path.read_bytes()).hexdigest()
    artifact_hashes = {
        "schema_version": "sprint-baseline-artifact-sha256-v1",
        "outputs": output_hashes,
        "inputs": {
            relative: sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in HASHED_INPUT_FILES
        },
    }
    _write_json(output_dir / "artifact_sha256.json", artifact_hashes)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare offline Sprint baseline artifacts; no inference.")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/results/sprint-baseline-v1")
    args = parser.parse_args()
    receipt = prepare(args.output)
    print(
        "SPRINT_BASELINES_PREPARED "
        f"cases={receipt['case_count']} references={receipt['reference_row_count']} "
        f"logical_requests={receipt['scheduled_logical_requests']} "
        f"model_calls={receipt['real_model_or_api_calls']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
