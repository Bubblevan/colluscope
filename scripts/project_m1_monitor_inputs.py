#!/usr/bin/env python3
"""Compile a local, restricted M1 privileged-audit projection; never dispatches."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m1_monitor_projection import compile_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--write-local", action="store_true",
                        help="write a Git-ignored, ACL-restricted projection under the run's private/ directory")
    args = parser.parse_args()
    result = compile_run(args.run_dir, write=args.write_local)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
