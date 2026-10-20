"""Freeze proposed Sprint validation groups without invoking any model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "configs/sprint-validation-scenarios.json"
OUTPUT = ROOT / "configs/sprint-validation-groups.json"
FAMILIES = (
    "sprint_validation_family_1",
    "sprint_validation_family_2",
    "sprint_validation_family_3",
)
ARMS = ("neutral", "masked", "no_delivery")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    scenario_config = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    actual_families = [row["scenario_family_id"] for row in scenario_config["families"]]
    if tuple(actual_families) != FAMILIES:
        raise ValueError(f"unexpected scenario family order: {actual_families}")

    groups = []
    chairs = ("A", "B", "C")
    global_index = 0
    for family_index, family in enumerate(FAMILIES):
        for offset in range(8):
            group_id = f"sprint-m3-validation-f{family_index + 1}-seed-{200 + family_index * 8 + offset}"
            digest = hashlib.sha256(
                f"colluscope-sprint-self-history-validation-v1|arm-order|{group_id}".encode("ascii")
            ).digest()
            order = sorted(ARMS, key=lambda arm: hashlib.sha256(digest + b"|" + arm.encode("ascii")).digest())
            groups.append({
                "group_id": group_id,
                "scenario_family_id": family,
                "seed": 200 + family_index * 8 + offset,
                "chair": chairs[global_index % len(chairs)],
                "condition_id": "coalition_incentive_private_chat",
                "counterfactual_order": order,
            })
            global_index += 1

    return {
        "schema_version": "colluscope-sprint-self-history-validation-groups-v1",
        "protocol_id": "colluscope-sprint-self-history-validation-v1",
        "model_calls_authorized": False,
        "scenario_config_sha256": sha256(SCENARIOS),
        "assignment_rule": "three frozen new families x eight consecutive seeds; globally cyclic A/B/C chair; no response-dependent selection or replacement",
        "counterfactual_order_rule": "sort neutral, masked, no_delivery by SHA256(SHA256(protocol_id|arm-order|group_id) || '|' || arm); no model output used",
        "assigned_group_count": len(groups),
        "groups": groups,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(build_manifest(), indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("frozen validation groups do not match deterministic generator")
        print(f"PASS groups=24 sha256={sha256(OUTPUT)} model_calls=0")
    else:
        OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
        print(f"wrote={OUTPUT}")
        print(f"sha256={sha256(OUTPUT)}")
        print("model_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
