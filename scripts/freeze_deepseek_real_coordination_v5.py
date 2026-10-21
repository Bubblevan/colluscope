#!/usr/bin/env python3
"""Create or verify the exact schedule/config freeze for the 40-call pilot."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.deepseek_real_coordination_v5 import (  # noqa: E402
    EXPERIMENT_ID, MAX_COST_USD, MAX_REQUESTS, MODEL, OUTPUT_LIMIT,
    TOKENIZER_SHA256, build_schedule, canonical, schemas, sha, strict_schema_errors,
)

SCHEDULE_PATH = ROOT / "research/schedules/deepseek-real-coordination-v5.json"
CONFIG_PATH = ROOT / "configs/deepseek-real-coordination-v5.json"
TOKENIZER_PATH = ROOT / ".cache/deepseek-recipe/tokenizer-v41.json"
FROZEN_PATHS = (
    "docs/DEEPSEEK_REAL_COORDINATION_V5_PROTOCOL.md",
    "docs/results/deepseek-real-coordination-v5/official_api_preflight.json",
    "docs/DEEPSEEK_REAL_COORDINATION_V3_PROTOCOL.md",
    "docs/DEEPSEEK_REAL_COORDINATION_V2_PROTOCOL.md",
    "scripts/freeze_deepseek_real_coordination_v5.py",
    "scripts/run_deepseek_real_coordination_v5.py",
    "scripts/analyze_deepseek_real_coordination_v5.py",
    "src/colluscope/deepseek_real_coordination_v5.py",
    "src/colluscope/deepseek_real_coordination_v3.py",
    "src/colluscope/deepseek_real_coordination_v2.py",
    "src/colluscope/deepseek_m4_v1.py",
    "src/colluscope/deepseek_recipient_mechanism_v1.py",
    "src/colluscope/m2_v3_deepseek.py",
    "tests/test_deepseek_real_coordination_v5.py",
    "tests/test_deepseek_real_coordination_v2.py",
    "tests/test_deepseek_real_coordination_analysis_v2.py",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def build_config(schedule: dict) -> dict:
    if digest(TOKENIZER_PATH) != TOKENIZER_SHA256:
        raise RuntimeError("pinned DeepSeek tokenizer hash mismatch")
    for kind, incoming in (
        ("fact_control", None), ("proposal", None), ("reply", None),
        ("reply", {"stance": "propose", "choice": "HIGH", "text": "test"}),
        ("ballot", None),
    ):
        _, schema = schemas(kind, incoming_proposal=incoming)
        errors = strict_schema_errors(schema)
        if errors:
            raise RuntimeError(f"schema for {kind} is outside the documented strict subset: {errors}")
    code_hashes = {relative: digest(ROOT / relative) for relative in FROZEN_PATHS}
    core = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "schedule_sha256": schedule["schedule_sha256"],
        "model_requested": MODEL,
        "endpoint": "https://api.deepseek.com/beta/chat/completions",
        "interface": "strict_function_calling",
        "temperature": 0.0,
        "thinking": "disabled",
        "stream": False,
        "max_output_tokens": OUTPUT_LIMIT,
        "timeout_seconds": 90,
        "retry_limit": 0,
        "replacement_limit": 0,
        "physical_request_cap": MAX_REQUESTS,
        "max_peak_reserved_cost_usd": MAX_COST_USD,
        "tokenizer_path": ".cache/deepseek-recipe/tokenizer-v41.json",
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizer_source_commit": "935817c66f5d6e64838f419692545f06787e485f",
        "chat_template_renderer": "deepseek_recipient_mechanism_v1.render_v41",
        "chat_template_renderer_source_sha256": code_hashes["src/colluscope/deepseek_recipient_mechanism_v1.py"],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {name: package_version(name) for name in ("tokenizers", "jsonschema", "pytest")},
        },
        "code_sha256": code_hashes,
        "network_policy": {
            "endpoint_host_allowlist": ["api.deepseek.com"],
            "proxy_disabled": True,
            "redirects_disabled": True,
            "third_party_fallback": False,
            "credential_saved": False,
        },
        "request_graph": {"fact_controls": 4, "game_requests": 36,
                          "message_stage_calls_per_arm": 2, "ballot_calls_per_arm": 2,
                          "arms_per_scenario": 3, "scenarios": 3},
    }
    return {**core, "config_sha256": sha(canonical(core))}


def write_or_check(path: Path, expected: bytes, check_only: bool) -> None:
    if check_only:
        if not path.is_file() or path.read_bytes() != expected:
            raise RuntimeError(f"frozen artifact differs: {path.relative_to(ROOT)}")
        return
    if path.exists():
        if path.read_bytes() != expected:
            raise RuntimeError(f"refusing to overwrite frozen artifact: {path.relative_to(ROOT)}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(expected)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    schedule = build_schedule()
    config = build_config(schedule)
    write_or_check(SCHEDULE_PATH, canonical(schedule) + b"\n", args.check)
    write_or_check(CONFIG_PATH, canonical(config) + b"\n", args.check)
    print(json.dumps({"status": "PASS_FREEZE_CHECK" if args.check else "FROZEN",
                      "schedule_sha256": schedule["schedule_sha256"],
                      "config_sha256": config["config_sha256"],
                      "assigned_requests": MAX_REQUESTS,
                      "physical_attempt_cap": MAX_REQUESTS,
                      "peak_cost_cap_usd": MAX_COST_USD}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
