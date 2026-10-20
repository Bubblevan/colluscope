#!/usr/bin/env python3
"""Count exact model-visible prompt profiles for the M1 replication drafts.

Only pre-generation message prompts and C ballot prompts are computed. A/B
ballot prompts depend on future message outputs and are deliberately excluded.
The output contains prompt hashes and counts, never prompt or message text.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import replace
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
from colluscope.m1_runtime import (  # noqa: E402
    _chair_for_seed_block,
    _condition_order,
    _observation,
    _render,
    _task_spec,
    load_runtime_config,
)

OLD_DRAFT = ROOT / "research/drafts/m1-replication-candidate-matrices-20261021.json"
NEW_DESIGN = ROOT / "research/drafts/m1-package-24-matrix-scenarios-20261021.json"
CONFIG = ROOT / "configs/m1-r-offline-v2.toml"
DEFAULT_OUT = ROOT / "docs/results/research-sprint-20261021/direction-review-followup/m1-prompt-profile-audit.json"


def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def profile_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    profiles: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        profiles[row["prompt_sha256"]].append({
            key: row[key] for key in ("scenario_family_id", "seed_block_id", "condition_id", "agent_id")
        })
    return {
        "assigned_prompt_count": len(rows),
        "unique_exact_prompt_count": len(profiles),
        "duplicate_assignments": len(rows) - len(profiles),
        "profiles": [
            {"prompt_sha256": prompt_hash, "occurrences": occurrences}
            for prompt_hash, occurrences in sorted(profiles.items())
        ],
    }


def inspect_design(name: str, scenarios: list[dict[str, Any]], group_rows: list[dict[str, Any]], config: Any) -> dict[str, Any]:
    scenario_by_id = {row["scenario_family_id"]: row for row in scenarios}
    message_rows: list[dict[str, Any]] = []
    c_ballot_rows: list[dict[str, Any]] = []
    per_group_c_prompts: dict[str, dict[str, str]] = defaultdict(dict)
    for group in group_rows:
        scenario = scenario_by_id[group["scenario_family_id"]]
        episode_config = replace(config, scenario_family_id=scenario["scenario_family_id"])
        condition_order = _condition_order(episode_config.conditions, group["seed_block_id"])
        if "condition_order" in group and group["condition_order"] != [row["id"] for row in condition_order]:
            raise AssertionError("frozen candidate condition order differs from the existing M1 runtime order")
        chair = _chair_for_seed_block(group["seed_block_id"])
        for condition in condition_order:
            task = _task_spec(condition["public_target_bonus_units"], episode_config)
            task["quality"] = scenario["matrix"]
            task["chair"] = chair
            if condition["private_chat_available"]:
                for agent in ("A", "B"):
                    observation = _observation(agent, task, condition, episode_config)
                    prompt = _render("message", observation, episode_config)
                    message_rows.append({
                        "scenario_family_id": scenario["scenario_family_id"],
                        "seed_block_id": group["seed_block_id"],
                        "condition_id": condition["id"],
                        "agent_id": agent,
                        "prompt_sha256": sha(prompt),
                    })
            observation = _observation("C", task, condition, episode_config)
            prompt_hash = sha(_render("ballot", observation, episode_config))
            row = {
                "scenario_family_id": scenario["scenario_family_id"],
                "seed_block_id": group["seed_block_id"],
                "condition_id": condition["id"],
                "agent_id": "C",
                "prompt_sha256": prompt_hash,
            }
            c_ballot_rows.append(row)
            per_group_c_prompts[group["group_id"]][condition["id"]] = prompt_hash

    no_public_conditions = [
        condition["id"] for condition in config.conditions
        if condition["public_target_bonus_units"] == 0
    ]
    if len(no_public_conditions) != 4:
        raise AssertionError("M1 design expected four conditions without a public target bonus")
    c_private_reward_equivalence = []
    for group in group_rows:
        by_condition = per_group_c_prompts[group["group_id"]]
        hashes = {by_condition[condition_id] for condition_id in no_public_conditions}
        c_private_reward_equivalence.append({
            "group_id": group["group_id"],
            "same_c_prompt_across_four_no_public_bonus_conditions": len(hashes) == 1,
            "condition_count": len(no_public_conditions),
        })
    return {
        "design_id": name,
        "groups": len(group_rows),
        "distinct_matrix_count": len({row["scenario_family_id"] for row in group_rows}),
        "message_stage": profile_summary(message_rows),
        "c_ballot_stage": profile_summary(c_ballot_rows),
        "c_identical_prompt_negative_control": {
            "conditions_compared": no_public_conditions,
            "groups_passing_exact_identity": sum(row["same_c_prompt_across_four_no_public_bonus_conditions"]
                                                  for row in c_private_reward_equivalence),
            "groups_total": len(c_private_reward_equivalence),
            "group_rows": c_private_reward_equivalence,
            "interpretation": "C is not shown private reward or the A/B channel. These repeated same-prompt ballots are an explicit input-invariance control, not independent prompt contexts.",
        },
        "not_compiled_before_generation": [
            "A/B ballot prompts that include future model-authored messages",
            "Any exact response-conditioned prompt profile",
        ],
        "prompt_text_saved": False,
        "request_ids_or_seeds_in_prompt_hash": False,
    }


def build() -> dict[str, Any]:
    config = load_runtime_config(CONFIG)
    old = json.loads(OLD_DRAFT.read_text(encoding="utf-8"))
    new = json.loads(NEW_DESIGN.read_text(encoding="utf-8"))
    old_groups = []
    for family_index, scenario in enumerate(old["families"]):
        for offset in range(8):
            old_groups.append({
                "group_id": f"old-{family_index + 1}-{offset + 1}",
                "scenario_family_id": scenario["scenario_family_id"],
                "seed_block_id": f"seed-{200 + family_index * 8 + offset}",
            })
    new_groups = [
        {"group_id": row["group_id"], "scenario_family_id": row["scenario_family_id"],
         "seed_block_id": row["seed_block_id"]}
        for row in new["groups"]
    ]
    old_result = inspect_design("three_matrices_eight_seeds_each_v2", old["families"], old_groups, config)
    new_result = inspect_design("twenty_four_unique_matrices_one_seed_each_v3", new["scenarios"], new_groups, config)
    if old_result["message_stage"]["unique_exact_prompt_count"] != 36:
        raise AssertionError("expected 36 unique M1 message prompts for the old three-matrix design")
    if old_result["c_ballot_stage"]["unique_exact_prompt_count"] != 18:
        raise AssertionError("expected 18 unique C ballot prompts for the old three-matrix design")
    if new_result["message_stage"]["unique_exact_prompt_count"] != 96:
        raise AssertionError("the 24-matrix design should yield 96 unique message prompts")
    if new_result["c_ballot_stage"]["unique_exact_prompt_count"] != 48:
        raise AssertionError("the 24-matrix design should yield 48 unique C ballot prompts")
    if new_result["c_identical_prompt_negative_control"]["groups_passing_exact_identity"] != 24:
        raise AssertionError("C's four no-public-bonus prompts should be identical within every group")
    return {
        "schema_version": 1,
        "status": "PASS_PREGENERATION_PROMPT_PROFILE_AUDIT",
        "evidence_class": "offline_reanalysis_and_design_preflight",
        "model_calls": 0,
        "source_config_sha256": hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
        "source_old_matrix_draft_sha256": hashlib.sha256(OLD_DRAFT.read_bytes()).hexdigest(),
        "source_new_matrix_design_sha256": hashlib.sha256(NEW_DESIGN.read_bytes()).hexdigest(),
        "designs": [old_result, new_result],
        "conclusion": "The three-matrix v2 schedule offered only 36 unique pre-generation message prompts and 18 exact C-ballot prompts across 24 matched groups. The corrected 24-matrix v3 schedule has 96 unique message prompts and 48 exact C-ballot prompts; C's repeated identical input across four no-public-bonus conditions remains a deliberate matched negative control.",
        "limits": [
            "This is exact for the frozen renderer and initial message/C ballot observations only.",
            "A/B ballot profiles depend on future model-authored messages and are not predicted here.",
            "Unique prompts are not statistically independent model behaviors.",
            "No output, runtime, or behavioral outcome is inferred from this prompt audit.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    raw = payload.encode("utf-8")
    if args.check:
        if not args.out.is_file() or args.out.read_bytes() != raw:
            raise SystemExit("M1_PROMPT_PROFILE_AUDIT_MISMATCH")
        print(json.dumps({"status": "PASS_PROMPT_PROFILE_RECOMPUTE", "model_calls": 0,
                          "designs": 2}, sort_keys=True))
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(raw)
    print(json.dumps({"status": "WROTE_PROMPT_PROFILE_AUDIT", "out": str(args.out),
                      "sha256": hashlib.sha256(raw).hexdigest(), "model_calls": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
