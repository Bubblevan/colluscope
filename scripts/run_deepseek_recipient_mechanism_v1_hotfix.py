#!/usr/bin/env python3
"""Versioned metadata-only launcher for the frozen recipient mechanism run.

Amendment 1 maps the already-frozen nested tokenizer repository commit into the
run manifest field expected by the base runner. It does not change any prompt,
request, schedule, model setting, response parsing, retry, or analysis behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_deepseek_recipient_mechanism_v1 as base  # noqa: E402
from colluscope.deepseek_m4_v1 import canonical, write_once  # noqa: E402
from colluscope.m2_v3_deepseek import apply_private_acl  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _install_manifest_metadata_fix() -> None:
    original = base.verify_frozen_inputs

    def verified_with_source_commit():
        schedule, config, tokenizer, parity = original()
        # Hash verification happened in original(); this is a derived manifest
        # field already pinned by config['tokenizer']['repository_commit'].
        config["tokenizer_source_commit"] = config["tokenizer"]["repository_commit"]
        return schedule, config, tokenizer, parity

    base.verify_frozen_inputs = verified_with_source_commit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if not args.check_only:
        base.RUN_DIR.mkdir(parents=True, exist_ok=True)
        apply_private_acl(base.RUN_DIR)
        amendment = {
            "amendment_id": "recipient-mechanism-v1-launcher-metadata-01",
            "reason": "The frozen base launcher expected tokenizer_source_commit at the config top level, while the frozen config stores the same value under tokenizer.repository_commit. The first launch stopped before manifest creation or HTTP dispatch.",
            "intervention_changed": False,
            "model_requests_before_amendment": 0,
            "base_runner_sha256": _sha(Path(base.__file__)),
            "launcher_sha256": _sha(Path(__file__)),
            "frozen_config_sha256": _sha(base.CONFIG_PATH),
            "frozen_schedule_sha256": base._load(base.SCHEDULE_PATH)["schedule_sha256"],
            "tokenizer_source_commit": base._load(base.CONFIG_PATH)["tokenizer"]["repository_commit"],
            "mapping": "verified config['tokenizer']['repository_commit'] -> manifest-only config['tokenizer_source_commit']",
            "created_at_utc": base.now_utc(),
        }
        write_once(base.RUN_DIR / "runtime-amendment-01.json", canonical(amendment) + b"\n")
    _install_manifest_metadata_fix()
    result = base.run(check_only=args.check_only)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") in {"PASS_OFFLINE_PREFLIGHT", "COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
