#!/usr/bin/env python3
"""Independently replay live M4 settlements and raw request/response links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.m4_live_runtime import load_live_config, verify_frozen_assets, verify_live_run  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None,
                        help="optional frozen live runtime config; defaults to checked-in v3")
    args = parser.parse_args()
    live, _base, scenarios, splits, _positive = load_live_config(args.config) if args.config else load_live_config()
    identity = verify_frozen_assets(live)
    receipt = verify_live_run(args.run, scenarios, splits, token_counter=identity["token_counter"])
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
