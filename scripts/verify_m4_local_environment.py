#!/usr/bin/env python3
"""Offline identity and exact-tokenizer gate for a future M4 approval.

This script hashes local files, reads embedded GGUF tokenizer metadata and
counts frozen prompts. It does not launch llama.cpp or issue any model call.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tomllib
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from colluscope.openai_compat_llamacpp import llama_runtime_bundle_identity  # noqa: E402
from scripts.run_m4_offline import (  # noqa: E402
    CONFIG_PATH, SYSTEM_PATH, config_positive_prompt, load_documents,
    render_positive_prompt,
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def count_chat(counter: GGUFChatTokenCounter, system: str, user: str) -> int:
    return counter.count_chat_tokens([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])


def verify(output: Path, mock_run: Path | None) -> dict[str, Any]:
    config, _scenarios, splits, positive = load_documents()
    model_cfg, runtime_cfg, tokenizer_cfg = config["model"], config["runtime"], config["tokenizer"]
    model = Path(model_cfg["path"])
    server = Path(runtime_cfg["binary_path"])
    report: dict[str, Any] = {
        "schema_version": "m4-local-environment-verification-v1",
        "checked_at_local": __import__("datetime").datetime.now().astimezone().isoformat(),
        "host": platform.platform(), "python": platform.python_version(),
        "model_path": str(model), "server_path": str(server),
        "model_exists": model.is_file(), "server_exists": server.is_file(),
        "model_expected_sha256": model_cfg["sha256"],
        "server_expected_sha256": runtime_cfg["binary_sha256"],
        "expected_runtime_bundle_sha256": runtime_cfg["bundle_sha256"],
        "tokenizer_expected_sha256": tokenizer_cfg["sha256"],
        "chat_template_expected_sha256": tokenizer_cfg["chat_template_sha256"],
        "real_model_calls": 0, "server_launched": False, "network_calls": 0,
        "positive_control": {"pairs": 24, "token_equality": "NOT_CHECKED"},
        "focal_proposal_neutral": {"pairs": 24, "token_equality": "NOT_CHECKED"},
        "status": "BLOCKED_MISSING_LOCAL_ARTIFACT",
    }
    m3_cfg = tomllib.loads((ROOT / "configs/m3-mechanism.toml").read_text(encoding="utf-8"))
    report["matches_m3_frozen_identity"] = bool(
        m3_cfg["model"]["path"] == model_cfg["path"]
        and m3_cfg["model"]["sha256"] == model_cfg["sha256"]
        and m3_cfg["runtime"]["binary_path"] == runtime_cfg["binary_path"]
        and m3_cfg["runtime"]["binary_sha256"] == runtime_cfg["binary_sha256"]
        and m3_cfg["runtime"]["bundle_sha256"] == runtime_cfg["bundle_sha256"]
        and m3_cfg["tokenizer"]["sha256"] == tokenizer_cfg["sha256"]
        and m3_cfg["tokenizer"]["chat_template_sha256"] == tokenizer_cfg["chat_template_sha256"]
    )
    if not model.is_file() or not server.is_file():
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report
    report["model_size_bytes"] = model.stat().st_size
    report["model_actual_sha256"] = file_sha256(model)
    report["model_hash_matches"] = report["model_actual_sha256"] == model_cfg["sha256"]
    report["server_actual_sha256"] = file_sha256(server)
    report["server_hash_matches"] = report["server_actual_sha256"] == runtime_cfg["binary_sha256"]
    bundle = llama_runtime_bundle_identity(server)
    report["runtime_bundle_actual_sha256"] = bundle["sha256"]
    report["runtime_bundle_file_count"] = bundle["file_count"]
    report["runtime_bundle_matches"] = bundle["sha256"] == runtime_cfg["bundle_sha256"]
    try:
        version = subprocess.run([str(server), "--version"], capture_output=True, text=True,
                                 timeout=20, check=False)
        version_text = (version.stdout + "\n" + version.stderr).strip()
        report["server_version_exit_code"] = version.returncode
        report["server_version_output_sha256"] = hashlib.sha256(version_text.encode("utf-8")).hexdigest()
        report["server_version_output"] = version_text[:1000]
    except Exception as exc:
        report["server_version_error"] = f"{type(exc).__name__}: {exc}"
    try:
        counter = GGUFChatTokenCounter(model, expected_artifact_sha256=model_cfg["sha256"])
        report["tokenizer_actual_sha256"] = counter.tokenizer_sha256
        report["tokenizer_actual_version"] = counter.tokenizers_library_version
        report["jinja2_actual_version"] = counter.jinja2_library_version
        report["chat_template_actual_sha256"] = counter.chat_template_sha256
        report["tokenizer_hash_matches"] = counter.tokenizer_sha256 == tokenizer_cfg["sha256"]
        report["chat_template_hash_matches"] = counter.chat_template_sha256 == tokenizer_cfg["chat_template_sha256"]
        report["tokenizer_library_matches"] = counter.tokenizers_library_version == tokenizer_cfg["tokenizers_version"]
        report["jinja2_library_matches"] = counter.jinja2_library_version == tokenizer_cfg["jinja2_version"]
        system = SYSTEM_PATH.read_text(encoding="utf-8").strip()
        task_prompt = positive["task"]["prompt"]
        neutral = positive["paired_messages"]["neutral_message"]
        messages = []
        for group in splits["groups"]:
            signal = group["positive_control_signal"]
            info = positive["paired_messages"]["information_template"].format(signal=signal)
            info_prompt = render_positive_prompt(task_prompt, info)
            neutral_prompt = render_positive_prompt(task_prompt, neutral)
            info_user = info_prompt.split("\n\n", 1)[1]
            neutral_user = neutral_prompt.split("\n\n", 1)[1]
            information_tokens = count_chat(counter, system, info_user)
            neutral_tokens = count_chat(counter, system, neutral_user)
            messages.append({
                "split_group_id": group["split_group_id"],
                "signal": signal,
                "information_prompt_tokens": information_tokens,
                "neutral_prompt_tokens": neutral_tokens,
                "delta": information_tokens - neutral_tokens,
                "exact_match": information_tokens == neutral_tokens,
            })
        report["positive_control"] = {
            "pairs": len(messages),
            "token_equality": "PASS" if all(row["exact_match"] for row in messages) else "FAIL",
            "all_pairs": messages,
            "information_token_counts": sorted({row["information_prompt_tokens"] for row in messages}),
            "neutral_token_counts": sorted({row["neutral_prompt_tokens"] for row in messages}),
            "paired_deltas": sorted(Counter(row["delta"] for row in messages).items()),
        }
        if mock_run is not None and (mock_run / "episodes.jsonl").is_file():
            episodes = [json.loads(line) for line in (mock_run / "episodes.jsonl").read_text(encoding="utf-8").splitlines()]
            pair_rows = []
            for episode in episodes:
                group_id = episode["researcher_T"]["split_group_id"]
                focal_rows = [row for row in episode["researcher_B"]["ballots"]
                              if row.get("stage") == "focal_counterfactual"]
                if not focal_rows:
                    continue
                receiver = focal_rows[0]["agent"]
                baseline_path = mock_run / "requests" / f"{group_id}-baseline-ballot-{receiver}.json"
                neutral_path = mock_run / "requests" / f"{group_id}-focal-retained_history_neutral.json"
                baseline_request = json.loads(baseline_path.read_text(encoding="utf-8"))
                neutral_request = json.loads(neutral_path.read_text(encoding="utf-8"))
                baseline_count = counter.count_chat_tokens(baseline_request["model_input"]["messages"])
                neutral_count = counter.count_chat_tokens(neutral_request["model_input"]["messages"])
                pair_rows.append({
                    "split_group_id": group_id,
                    "proposal_prompt_tokens": baseline_count,
                    "neutral_prompt_tokens": neutral_count,
                    "delta": neutral_count - baseline_count,
                    "exact_match": neutral_count == baseline_count,
                })
            report["focal_proposal_neutral"] = {
                "pairs": len(pair_rows),
                "token_equality": "PASS" if len(pair_rows) == 24 and all(row["exact_match"] for row in pair_rows) else "FAIL",
                "all_pairs": pair_rows,
                "paired_deltas": sorted(Counter(row["delta"] for row in pair_rows).items()),
            }
    except Exception as exc:
        report["tokenizer_gate_error"] = f"{type(exc).__name__}: {exc}"
    identity_ok = all(report.get(key) is True for key in (
        "matches_m3_frozen_identity", "model_hash_matches", "server_hash_matches",
        "runtime_bundle_matches", "tokenizer_hash_matches", "chat_template_hash_matches",
        "tokenizer_library_matches", "jinja2_library_matches"))
    report["status"] = "PASS_LOCAL_IDENTITY_AND_TOKEN_MATCH" if (
        identity_ok and report.get("positive_control", {}).get("token_equality") == "PASS"
        and (mock_run is None or report.get("focal_proposal_neutral", {}).get("token_equality") == "PASS")
    ) else "NO_GO_LOCAL_IDENTITY_OR_TOKEN_MATCH"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/results/m4-runtime/local-environment.json")
    parser.add_argument("--mock-run", type=Path, default=ROOT / "runs/m4/offline-mock-v2")
    args = parser.parse_args()
    report = verify(args.out, args.mock_run)
    print(json.dumps({key: report.get(key) for key in (
        "status", "model_exists", "server_exists", "matches_m3_frozen_identity",
        "model_hash_matches", "server_hash_matches", "runtime_bundle_matches",
        "tokenizer_hash_matches", "chat_template_hash_matches", "positive_control",
        "focal_proposal_neutral",
        "real_model_calls", "network_calls")}, sort_keys=True))
    return 0 if report["status"] == "PASS_LOCAL_IDENTITY_AND_TOKEN_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
