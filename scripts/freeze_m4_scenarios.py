from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m4_scenarios import scenario_document, verify_scenario_document  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "configs/m4-scenarios-v1.json")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    expected = scenario_document(ROOT)
    if args.verify:
        current = json.loads(args.output.read_text(encoding="utf-8"))
        verify_scenario_document(current, ROOT)
        print(f"M4_SCENARIOS_VALID families={len(expected['families'])}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(
        (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    print(f"WROTE {args.output} families={len(expected['families'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
