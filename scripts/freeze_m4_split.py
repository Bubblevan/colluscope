from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "configs/m4-scenarios-v1.json"
OUTPUT = ROOT / "configs/m4-splits-v1.json"
PROTOCOL = "colluscope-m4-split-v1"
SEED_BLOCKS = (201, 202, 203, 204)


def build() -> dict:
    scenarios = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    groups = []
    for scenario in scenarios["families"]:
        for seed in SEED_BLOCKS:
            seed_block_id = f"m4-seed-{seed}"
            material = f"{PROTOCOL}\0{scenario['scenario_family_id']}\0{seed_block_id}".encode("utf-8")
            split_group_id = sha256(material).hexdigest()
            signal_digest = sha256(
                f"m4-positive-control-signal-sha256-v1\0{split_group_id}".encode("utf-8")
            ).digest()
            signal = ("BLUE", "GOLD")[signal_digest[0] % 2]
            groups.append({
                "scenario_family_id": scenario["scenario_family_id"],
                "seed_block_id": seed_block_id,
                "split_group_id": split_group_id,
                "scenario_sha256": sha256(json.dumps(
                    scenario["matrix"], sort_keys=True, separators=(",", ":")
                ).encode("utf-8")).hexdigest(),
                "positive_control_signal": signal,
                "positive_control_correct_action": {"BLUE": "T2", "GOLD": "T1"}[signal],
                "partition": "prospective_evaluation",
                "conditions_and_counterfactual_arms_share_group": True,
            })
    return {
        "schema_version": "m4-splits-v1",
        "protocol_id": PROTOCOL,
        "group_unit": "scenario_family_id × seed_block_id",
        "scenario_family_count": len(scenarios["families"]),
        "seed_blocks_per_family": len(SEED_BLOCKS),
        "assigned_group_count": len(groups),
        "all_existing_m1_m2_m3_data": "development_descriptive_only",
        "groups": groups,
        "leakage_constraints": [
            "all within-group arms, messages, ballots, tasks and derived views remain in one partition",
            "no prompt, matrix, label, or threshold changes after any M4 model output",
            "every assigned group remains in the denominator, including no-proposal and failed groups",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    expected = build()
    if args.verify:
        current = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if current != expected:
            raise SystemExit("M4 split manifest does not match its deterministic generator")
        print("M4_SPLIT_VALID groups=24 families=6 seeds_per_family=4")
        return 0
    OUTPUT.write_bytes((json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"WROTE {OUTPUT} groups={len(expected['groups'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
