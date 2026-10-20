#!/usr/bin/env python3
"""Explicitly authorized local Qwen/llama.cpp executor for the frozen M4-v2 schedule."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.m4_live_runtime import LIVE_CONFIG, M4AuthorizationRequired, run_live  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=LIVE_CONFIG)
    parser.add_argument("--out", type=Path, required=True,
                        help="new run directory beneath runs/m4; raw artifacts stay local and ACL-restricted")
    parser.add_argument("--execute-live", action="store_true",
                        help="required explicit live-inference switch; omitted by default")
    parser.add_argument("--approval-id", default=None,
                        help="operator's separate approval reference; does not itself authorize a future run")
    args = parser.parse_args()
    try:
        result = run_live(args.out, config_path=args.config, approval_id=args.approval_id,
                          execute_live=args.execute_live)
    except M4AuthorizationRequired as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["unstarted_groups_remaining"] == 0 and result["failed_groups"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
