"""Freeze deterministic scenario matrices and matched-group splits; no model calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from hashlib import sha256
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from colluscope.m1_100_scenarios import ALGORITHM_ID, select_scenarios  # noqa: E402


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def build_splits() -> dict[str, object]:
    # Scenario families are spread across F1/F2/F3 by a predeclared round-robin
    # assignment. Each (scenario, seed) group keeps all five treatment rows.
    assignments = [
        ("F1", "m1_100_family_1", 100), ("F1", "m1_100_family_1", 101),
        ("F1", "m1_100_family_2", 102), ("F1", "m1_100_family_2", 103),
        ("F1", "m1_100_family_3", 104),
        ("F2", "m1_100_family_1", 105), ("F2", "m1_100_family_2", 106),
        ("F2", "m1_100_family_2", 107), ("F2", "m1_100_family_3", 108),
        ("F2", "m1_100_family_3", 109),
        ("F3", "m1_100_family_1", 110), ("F3", "m1_100_family_1", 111),
        ("F3", "m1_100_family_2", 112), ("F3", "m1_100_family_3", 113),
        ("F3", "m1_100_family_3", 114),
    ]
    groups = []
    for partition, family, seed in assignments:
        seed_block = f"seed-{seed}"
        group_material = f"colluscope-m1-split-v1|{family}|{seed_block}"
        groups.append({"partition": partition, "scenario_family_id": family,
                       "seed_block_id": seed_block,
                       "split_group_id_material": group_material,
                       "split_group_id": sha256(group_material.encode("utf-8")).hexdigest(),
                       "conditions": ["normal_cooperation",
                                      "common_incentive_parallel_behavior",
                                      "coalition_incentive_private_chat",
                                      "coalition_incentive_no_private_chat",
                                      "private_chat_no_side_bonus"]})
    return {
        "schema_version": "m1-100-splits-v1",
        "unit": "scenario_family_id × seed_block_id; all five conditions and all views travel together",
        "F0": {"partition": "development_historical_descriptive_only", "groups": [
            {"scenario_family_id": "icbcmatch_v1", "seed_block_id": f"seed-{seed}",
             "split_group_id": sha256(f"colluscope-m1-split-v1|icbcmatch_v1|seed-{seed}".encode()).hexdigest(),
             "episodes": 5, "source": "runs/m1_p0_local/formal-25ep-pilot-20261019/run",
             "condition_ids": ["normal_cooperation", "common_incentive_parallel_behavior",
                               "coalition_incentive_private_chat", "coalition_incentive_no_private_chat",
                               "private_chat_no_side_bonus"]} for seed in range(5)],
            "episode_count": 25},
        "F1": {"partition": "calibration", "groups": [g for g in groups if g["partition"] == "F1"],
               "episode_count": 25},
        "F2": {"partition": "held_out_evaluation", "groups": [g for g in groups if g["partition"] == "F2"],
               "episode_count": 25},
        "F3": {"partition": "held_out_evaluation", "groups": [g for g in groups if g["partition"] == "F3"],
               "episode_count": 25},
        "leakage_constraints": [
            "all five condition rows per scenario/seed group remain in one partition",
            "all T/B/E, observations, requests, and derived evidence views remain with the same group",
            "F2/F3 are not used to tune scenarios, prompts, labels, thresholds, or model settings",
            "historical F0 is development/descriptive only and is not represented as identically generated",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify checked-in generated files")
    args = parser.parse_args()
    scenario_doc = {"schema_version": "m1-100-scenarios-v1", "algorithm_id": ALGORITHM_ID,
                    "selection_order": [6, 12, 18], "score_range_inclusive": [1, 20],
                    "candidate_order": "candidate_index ascending from zero; each cell is first 8 SHA256 bytes modulo 20 plus 1",
                    "hash_material": "algorithm_id NUL candidate_index NUL row_index NUL column_index; ASCII",
                    "families": select_scenarios()}
    files = {ROOT / "configs" / "m1-100-scenarios.json": canonical_json(scenario_doc),
             ROOT / "configs" / "m1-100-splits.json": canonical_json(build_splits())}
    if args.check:
        failures = [str(path.relative_to(ROOT)) for path, expected in files.items()
                    if not path.is_file() or path.read_bytes() != expected]
        if failures:
            raise SystemExit("frozen design differs from deterministic regeneration: " + ", ".join(failures))
        print(json.dumps({"status": "PASS_FROZEN_DESIGN", "files": len(files),
                          "families": len(scenario_doc["families"]),
                          "groups": sum(len(scenario_doc_split["groups"])
                                        for partition in ("F1", "F2", "F3")
                                        for scenario_doc_split in [build_splits()[partition]])}, sort_keys=True))
    else:
        for path, data in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        print(json.dumps({"status": "WROTE_FROZEN_DESIGN", "files": [str(p.relative_to(ROOT)) for p in files]}, sort_keys=True))


if __name__ == "__main__":
    main()
