#!/usr/bin/env python3
"""Offline exact-tokenizer audit for the prospective M4 positive-control v2 pair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from scripts.run_m4_offline import SYSTEM_PATH, load_documents, render_positive_prompt  # noqa: E402

BASELINE_PATH = ROOT / "configs/m4-positive-control-v1.json"
CANDIDATE_PATH = ROOT / "configs/m4-positive-control-v2.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_user(task: str, message: str) -> str:
    rendered = render_positive_prompt(task, message)
    parts = rendered.split("\n\n", 1)
    if len(parts) != 2:
        raise ValueError("positive-control prompt did not preserve the frozen system/user boundary")
    return parts[1]


def verify(output: Path) -> dict[str, Any]:
    runtime_config, _scenarios, splits, _frozen_positive = load_documents()
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    model_cfg = runtime_config["model"]
    system = SYSTEM_PATH.read_text(encoding="utf-8").strip()
    task = candidate["task"]["prompt"]
    signal_to_action = candidate["signal_assignment"]["mapping"]
    if baseline["task"] != candidate["task"]:
        raise ValueError("candidate changed the frozen positive-control task or action schema")
    if baseline["signal_assignment"] != candidate["signal_assignment"]:
        raise ValueError("candidate changed the frozen signal assignment")
    neutral = candidate["paired_messages"]["neutral_message"]
    if neutral == baseline["paired_messages"]["neutral_message"]:
        raise ValueError("candidate did not change the known-mismatched neutral code")
    if neutral.split(":", 1)[-1].strip(" .") in signal_to_action:
        raise ValueError("neutral code aliases a valid task signal")

    model = Path(model_cfg["path"])
    if not model.is_file():
        raise FileNotFoundError(f"frozen GGUF model is unavailable: {model}")
    counter = GGUFChatTokenCounter(model, expected_artifact_sha256=model_cfg["sha256"])
    if len(splits["groups"]) != 24:
        raise ValueError("frozen M4 split no longer contains exactly 24 groups")

    rows = []
    for group in splits["groups"]:
        signal = group["positive_control_signal"]
        if signal not in signal_to_action:
            raise ValueError(f"unexpected signal in frozen split: {signal}")
        info_message = candidate["paired_messages"]["information_template"].format(signal=signal)
        info_tokens = len(counter.encode_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": render_user(task, info_message)},
        ]))
        old_neutral = baseline["paired_messages"]["neutral_message"]
        old_tokens = len(counter.encode_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": render_user(task, old_neutral)},
        ]))
        new_tokens = len(counter.encode_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": render_user(task, neutral)},
        ]))
        rows.append({
            "split_group_id": group["split_group_id"],
            "signal": signal,
            "information_tokens": info_tokens,
            "v1_neutral_tokens": old_tokens,
            "v2_neutral_tokens": new_tokens,
            "v1_delta_neutral_minus_information": old_tokens - info_tokens,
            "v2_delta_neutral_minus_information": new_tokens - info_tokens,
            "v1_exact": old_tokens == info_tokens,
            "v2_exact": new_tokens == info_tokens,
        })

    v1_matches = sum(row["v1_exact"] for row in rows)
    v2_matches = sum(row["v2_exact"] for row in rows)
    expected_v1_failure_reproduced = v1_matches == 0 and all(
        row["v1_delta_neutral_minus_information"] == 1 for row in rows
    )
    status = "PASS_POSITIVE_CONTROL_V2_LOCAL_TOKEN_MATCH" if (
        v2_matches == 24 and expected_v1_failure_reproduced
    ) else "NO_GO_POSITIVE_CONTROL_TOKEN_MATCH"
    result = {
        "schema_version": "m4-positive-control-token-audit-v2",
        "status": status,
        "claim_scope": "exact local GGUF tokenizer and frozen chat-template count only; no model behavior or live server parity claim",
        "real_model_calls": 0,
        "server_launched": False,
        "network_calls": 0,
        "model_sha256": counter.artifact_sha256,
        "tokenizer_sha256": counter.tokenizer_sha256,
        "chat_template_sha256": counter.chat_template_sha256,
        "tokenizers_library_version": counter.tokenizers_library_version,
        "jinja2_library_version": counter.jinja2_library_version,
        "system_prompt_sha256": sha256(SYSTEM_PATH),
        "positive_control_prompt_sha256": sha256(ROOT / "prompts/m4-v1/positive_control.txt"),
        "baseline_v1_config_sha256": sha256(BASELINE_PATH),
        "candidate_v2_config_sha256": sha256(CANDIDATE_PATH),
        "split_manifest_sha256": sha256(ROOT / "configs/m4-splits-v1.json"),
        "groups": len(rows),
        "v1_exact_matches": v1_matches,
        "v1_known_failure_reproduced": expected_v1_failure_reproduced,
        "v2_exact_matches": v2_matches,
        "information_token_counts": sorted({row["information_tokens"] for row in rows}),
        "v1_neutral_token_counts": sorted({row["v1_neutral_tokens"] for row in rows}),
        "v2_neutral_token_counts": sorted({row["v2_neutral_tokens"] for row in rows}),
        "group_results": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "docs/results/sprint-execution-readiness/m4-positive-control-v2-token-match.json")
    args = parser.parse_args()
    result = verify(args.out)
    print(json.dumps({key: result[key] for key in (
        "status", "groups", "v1_exact_matches", "v1_known_failure_reproduced",
        "v2_exact_matches", "information_token_counts", "v1_neutral_token_counts",
        "v2_neutral_token_counts", "real_model_calls", "server_launched", "network_calls",
    )}, sort_keys=True))
    return 0 if result["status"] == "PASS_POSITIVE_CONTROL_V2_LOCAL_TOKEN_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
