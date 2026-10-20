"""Write the response-independent M3 group and arm-order schedule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m3_mechanism import PROTOCOL_ID, build_schedule, canonical_sha256  # noqa: E402


def freeze(output_path: Path) -> dict[str, object]:
    scenarios_path = ROOT / "configs/m1-100-scenarios.json"
    splits_path = ROOT / "configs/m1-100-splits.json"
    scenarios = json.loads(scenarios_path.read_text(encoding="utf-8"))
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    groups = build_schedule(scenarios, splits)
    document = {
        "schema_version": "colluscope-m3-schedule-v1",
        "protocol_id": PROTOCOL_ID,
        "generation_method": "four sequential fresh numeric seed blocks per existing M1-100 payoff family; seed range 115-126; no model output input",
        "scenario_source_sha256": canonical_sha256(scenarios),
        "split_source_sha256": canonical_sha256(splits),
        "group_count": len(groups),
        "groups": groups,
    }
    document["schedule_sha256"] = canonical_sha256(groups)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8", newline="\n")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "configs/m3-mechanism-schedule.json")
    args = parser.parse_args()
    document = freeze(args.out.resolve())
    print(json.dumps({"path": str(args.out.resolve()), "groups": document["group_count"],
                      "schedule_sha256": document["schedule_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
