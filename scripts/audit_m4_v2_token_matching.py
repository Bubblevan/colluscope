#!/usr/bin/env python3
"""Independently audit M4 v1 failures and the prospective v2 token-match candidate.

This audit consumes only saved offline Mock requests. It does not call a model,
launch llama.cpp, or issue an HTTP request. Counts include the frozen Qwen3
chat template and embedded GGUF tokenizer.
"""

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
from scripts.run_m4_offline import load_documents  # noqa: E402

V1_CONFIG = ROOT / "configs/m4-runtime-v1.json"
V2_CONFIG = ROOT / "configs/m4-runtime-v2.json"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _requests(run: Path) -> dict[str, dict[str, Any]]:
    root = run / "requests"
    if not root.is_dir():
        raise FileNotFoundError(f"offline Mock request directory not found: {root}")
    rows = {}
    for path in root.glob("*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        rows[item["request_id"]] = item
    return rows


def _focal_receiver(run: Path, group_id: str) -> str:
    for line in (run / "episodes.jsonl").read_text(encoding="utf-8").splitlines():
        episode = json.loads(line)
        if episode["researcher_T"]["split_group_id"] != group_id:
            continue
        for ballot in episode["researcher_B"]["ballots"]:
            if ballot.get("stage") == "focal_counterfactual":
                return ballot["agent"]
        raise ValueError(f"no focal counterfactual was assigned for {group_id}")
    raise ValueError(f"group missing from episode ledger: {group_id}")


def _count(counter: GGUFChatTokenCounter, request: dict[str, Any]) -> tuple[int, str]:
    messages = request["model_input"]["messages"]
    ids = counter.encode_chat(messages)
    return len(ids), hashlib.sha256(",".join(map(str, ids)).encode("ascii")).hexdigest()


def audit(v1_run: Path, v2_run: Path, output: Path) -> dict[str, Any]:
    v1_config, _scenarios, splits, v1_positive = load_documents(V1_CONFIG)
    v2_config, _scenarios2, splits2, v2_positive = load_documents(V2_CONFIG)
    if splits != splits2 or len(splits["groups"]) != 24:
        raise ValueError("v1/v2 candidate must retain the same 24 frozen groups")
    if v1_config["schedule"]["positive_control"] != "configs/m4-positive-control-v1.json":
        raise ValueError("v1 positive-control path was changed")
    if v2_config["schedule"]["positive_control"] != "configs/m4-positive-control-v2.json":
        raise ValueError("v2 positive-control candidate is not wired into runtime v2")
    model_cfg = v2_config["model"]
    counter = GGUFChatTokenCounter(Path(model_cfg["path"]), expected_artifact_sha256=model_cfg["sha256"])
    old_requests, new_requests = _requests(v1_run), _requests(v2_run)
    focal_rows, positive_rows = [], []
    for group in splits["groups"]:
        group_id = group["split_group_id"]
        receiver_v1 = _focal_receiver(v1_run, group_id)
        receiver_v2 = _focal_receiver(v2_run, group_id)
        if receiver_v1 != receiver_v2:
            raise ValueError("candidate changed the pre-frozen focal receiver")
        baseline_id = f"{group_id}-baseline-ballot-{receiver_v2}"
        neutral_id = f"{group_id}-focal-retained_history_neutral"
        proposal = new_requests[baseline_id]
        neutral = new_requests[neutral_id]
        proposal_count, proposal_ids_sha = _count(counter, proposal)
        neutral_count, neutral_ids_sha = _count(counter, neutral)
        # The immutable prompt itself is audited below; treatment metadata is
        # not allowed into the model input and must remain outside its hash.
        model_text = json.dumps(proposal["model_input"], ensure_ascii=False)
        if any(secret in model_text for secret in (group_id, "retained_history_neutral", "scenario_family_id")):
            raise ValueError("research group or counterfactual arm metadata leaked into the model prompt")
        focal_rows.append({
            "split_group_id": group_id,
            "receiver": receiver_v2,
            "proposal_prompt_tokens": proposal_count,
            "neutral_prompt_tokens": neutral_count,
            "neutral_minus_proposal_tokens": neutral_count - proposal_count,
            "proposal_token_ids_sha256": proposal_ids_sha,
            "neutral_token_ids_sha256": neutral_ids_sha,
            "exact_count_match": proposal_count == neutral_count,
        })

        information_id = f"{group_id}-positive-information"
        positive_neutral_id = f"{group_id}-positive-neutral"
        old_info, old_neutral = old_requests[information_id], old_requests[positive_neutral_id]
        new_info, new_neutral = new_requests[information_id], new_requests[positive_neutral_id]
        old_info_count, _ = _count(counter, old_info)
        old_neutral_count, _ = _count(counter, old_neutral)
        new_info_count, new_info_sha = _count(counter, new_info)
        new_neutral_count, new_neutral_sha = _count(counter, new_neutral)
        positive_rows.append({
            "split_group_id": group_id,
            "v1_information_tokens": old_info_count,
            "v1_neutral_tokens": old_neutral_count,
            "v1_neutral_minus_information_tokens": old_neutral_count - old_info_count,
            "v2_information_tokens": new_info_count,
            "v2_neutral_tokens": new_neutral_count,
            "v2_neutral_minus_information_tokens": new_neutral_count - new_info_count,
            "v2_information_token_ids_sha256": new_info_sha,
            "v2_neutral_token_ids_sha256": new_neutral_sha,
            "v2_exact_count_match": new_info_count == new_neutral_count,
        })

    old_focal = []
    for group in splits["groups"]:
        group_id = group["split_group_id"]
        receiver = _focal_receiver(v1_run, group_id)
        proposal_id = f"{group_id}-baseline-ballot-{receiver}"
        neutral_id = f"{group_id}-focal-retained_history_neutral"
        proposal_count, _ = _count(counter, old_requests[proposal_id])
        neutral_count, _ = _count(counter, old_requests[neutral_id])
        old_focal.append(neutral_count - proposal_count)

    v1_focal_failure_reproduced = len(old_focal) == 24 and set(old_focal) == {-1}
    v2_focal_matches = sum(row["exact_count_match"] for row in focal_rows)
    v1_positive_deltas = [row["v1_neutral_minus_information_tokens"] for row in positive_rows]
    v1_positive_failure_reproduced = len(positive_rows) == 24 and set(v1_positive_deltas) == {1}
    v2_positive_matches = sum(row["v2_exact_count_match"] for row in positive_rows)
    status = "PASS_M4_V2_LOCAL_TOKEN_MATCH" if (
        v1_focal_failure_reproduced and v1_positive_failure_reproduced
        and v2_focal_matches == 24 and v2_positive_matches == 24
    ) else "NO_GO_M4_V2_LOCAL_TOKEN_MATCH"
    result = {
        "schema_version": "m4-v2-token-match-audit-v1",
        "status": status,
        "scope": "exact full-chat token counts under embedded GGUF tokenizer and frozen chat template; offline Mock inputs only",
        "real_model_generations": 0,
        "server_launched": False,
        "http_requests": 0,
        "network_requests": 0,
        "model_sha256": counter.artifact_sha256,
        "tokenizer_sha256": counter.tokenizer_sha256,
        "chat_template_sha256": counter.chat_template_sha256,
        "tokenizers_version": counter.tokenizers_library_version,
        "jinja2_version": counter.jinja2_library_version,
        "v1_runtime_config_sha256": file_sha256(V1_CONFIG),
        "v2_runtime_config_sha256": file_sha256(V2_CONFIG),
        "v1_positive_config_sha256": file_sha256(ROOT / v1_config["schedule"]["positive_control"]),
        "v2_positive_config_sha256": file_sha256(ROOT / v2_config["schedule"]["positive_control"]),
        "split_manifest_sha256": file_sha256(ROOT / v2_config["schedule"]["split_manifest"]),
        "v1_focal_neutral_minus_proposal_deltas": sorted(set(old_focal)),
        "v1_focal_known_failure_reproduced": v1_focal_failure_reproduced,
        "v2_focal_exact_matches": v2_focal_matches,
        "v1_positive_neutral_minus_information_deltas": sorted(set(v1_positive_deltas)),
        "v1_positive_known_failure_reproduced": v1_positive_failure_reproduced,
        "v2_positive_exact_matches": v2_positive_matches,
        "focal_pairs": focal_rows,
        "positive_control_pairs": positive_rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-mock-run", type=Path, default=ROOT / "runs/m4/offline-mock-v2")
    parser.add_argument("--v2-mock-run", type=Path, default=ROOT / "runs/m4/offline-mock-v3-candidate")
    parser.add_argument("--out", type=Path, default=ROOT / "docs/results/sprint-execution-readiness/m4-v2-token-match-audit.json")
    args = parser.parse_args()
    result = audit(args.v1_mock_run, args.v2_mock_run, args.out)
    print(json.dumps({key: result[key] for key in (
        "status", "v1_focal_known_failure_reproduced", "v2_focal_exact_matches",
        "v1_positive_known_failure_reproduced", "v2_positive_exact_matches",
        "real_model_generations", "http_requests", "network_requests",
    )}, sort_keys=True))
    return 0 if result["status"] == "PASS_M4_V2_LOCAL_TOKEN_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
