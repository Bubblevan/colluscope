#!/usr/bin/env python3
"""Create/check the hash-bound M2 preregistration before any monitor call."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m2_corpus import file_sha256  # noqa: E402

MANIFEST = ROOT / "configs/m2-one-shot-freeze-manifest.json"
ATTACHMENT = Path(r"C:\Users\bubblevan\.codex\attachments\55d032a2-7f6e-4fc6-8181-5b554ae3ba30\已粘贴的文本.txt")
ARTIFACTS = (
    ".gitignore",
    "docs/M2_FROZEN_PROTOCOL.md",
    "configs/m2-one-shot.toml",
    "configs/m2-one-shot-splits.json",
    "configs/m1-p0-llama-local-draft.toml",
    "configs/m1-100.toml",
    "configs/m1-100-scenarios.json",
    "configs/m1-100-splits.json",
    "configs/m1-100-f0-split-correction.json",
    "prompts/m2-v1/system.txt",
    "prompts/m2-v1/user.txt",
    "prompts/m2-v1/output.schema.json",
    "scripts/freeze_m2_protocol.py",
    "scripts/freeze_m2_calibration.py",
    "scripts/run_m2_monitor.py",
    "scripts/verify_m2_preparation.py",
    "scripts/score_m2_monitor.py",
    "scripts/audit_m2_outputs.py",
    "scripts/local_llama_security.py",
    "scripts/run_m1_100_extension.py",
    "scripts/run_m1_p0_local_preflight.py",
    "scripts/audit_m1_100.py",
    "scripts/audit_m1_p0_postrun.py",
    "src/colluscope/m2_corpus.py",
    "src/colluscope/m2_monitor.py",
    "src/colluscope/m2_reference.py",
    "src/colluscope/openai_compat_llamacpp.py",
    "src/colluscope/gguf_tokenizer.py",
    "tests/test_m2_monitor.py",
)


def expected_manifest() -> dict:
    config = tomllib.loads((ROOT / "configs/m2-one-shot.toml").read_text(encoding="utf-8"))
    if config["logical_evaluation_cap"] != 1000 or config["physical_http_attempt_cap"] != 2000:
        raise ValueError("M2 protocol caps do not match the user's authorization")
    attachment_hash = file_sha256(ATTACHMENT) if ATTACHMENT.exists() else None
    if attachment_hash is None:
        raise FileNotFoundError("user authorization attachment cannot be hash-verified before freeze")
    return {
        "schema_version": "colluscope-m2-freeze-v1",
        "protocol_id": config["protocol_id"],
        "status": "FROZEN_BEFORE_MONITOR_INFERENCE",
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorization_id": config["authorization_id"],
        "authorization_attachment_sha256": attachment_hash,
        "authorized_source_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "m1_corpus_manifest_sha256": config["source_m1_corpus_manifest_sha256"],
        "logical_evaluation_cap": config["logical_evaluation_cap"],
        "physical_http_attempt_cap": config["physical_http_attempt_cap"],
        "max_attempts_per_unique_request": config["max_attempts_per_unique_request"],
        "api_spend_usd": config["api_spend_usd"],
        "endpoint": config["endpoint"], "offline": config["offline"],
        "third_party_fallback": config["third_party_fallback"],
        "model_sha256": config["model_sha256"], "server_sha256": config["server_sha256"],
        "runtime_bundle_sha256": config["runtime_bundle_sha256"],
        "tokenizer_sha256": config["tokenizer_sha256"],
        "chat_template_sha256": config["chat_template_sha256"],
        "sampling": {key: config[key] for key in (
            "temperature", "top_p", "top_k", "min_p", "sampler_chain", "thinking_mode",
            "context_length", "input_token_cap", "output_token_cap", "timeout_seconds")},
        "views": config["views"], "permission_profiles": config["permission_profiles"],
        "split_manifest_sha256": file_sha256(ROOT / config["split_manifest"]),
        "artifact_hashes": {relative: file_sha256(ROOT / relative) for relative in ARTIFACTS},
    }


def check_manifest() -> dict:
    actual = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if actual.get("status") != "FROZEN_BEFORE_MONITOR_INFERENCE" or \
            actual.get("schema_version") != "colluscope-m2-freeze-v1":
        raise ValueError("unsupported or non-frozen M2 manifest")
    if set(actual.get("artifact_hashes", {})) != set(ARTIFACTS):
        raise ValueError("M2 freeze manifest artifact inventory differs from the required inventory")
    expected = expected_manifest()
    ignored = {"frozen_at_utc", "authorized_source_head", "artifact_hashes"}
    for key, value in expected.items():
        if key not in ignored and actual.get(key) != value:
            raise ValueError(f"M2 freeze manifest field changed: {key}")
    for relative, expected_hash in actual["artifact_hashes"].items():
        if file_sha256(ROOT / relative) != expected_hash:
            raise ValueError(f"M2 frozen artifact changed: {relative}")
    config = tomllib.loads((ROOT / "configs/m2-one-shot.toml").read_text(encoding="utf-8"))
    if (actual.get("authorization_id") != config["authorization_id"] or
            actual.get("logical_evaluation_cap") != config["logical_evaluation_cap"] or
            actual.get("physical_http_attempt_cap") != config["physical_http_attempt_cap"] or
            actual.get("m1_corpus_manifest_sha256") != config["source_m1_corpus_manifest_sha256"]):
        raise ValueError("M2 freeze manifest differs from its authorization/configuration")
    return actual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        if MANIFEST.exists():
            raise FileExistsError("M2 freeze manifest already exists; preserve it and do not overwrite")
        run = ROOT / "runs/m2/one-shot-20261019"
        ledger = run / "requests-ledger.jsonl"
        if (ledger.exists() and ledger.stat().st_size) or any((run / "launches").glob("launch-*")):
            raise PermissionError("cannot freeze after any M2 request or launch has started")
        value = expected_manifest()
        MANIFEST.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8", newline="\n")
    else:
        value = check_manifest()
    digest = file_sha256(MANIFEST)
    print(json.dumps({"status": "PASS_M2_FREEZE_WRITE" if args.write else "PASS_M2_FREEZE_CHECK",
                      "manifest_sha256": digest, "artifact_count": len(value["artifact_hashes"]),
                      "authorized_source_head": value["authorized_source_head"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
