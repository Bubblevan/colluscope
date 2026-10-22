from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "docs/results/track23-evidence-audit-v1"
PRIVATE = ROOT / "runs/sprint-monitor/track23-evidence-audit-v1"
RAW = ROOT / "reference/colosseum/experiments/collusion/outputs/colosseum-deepseek-flash-staged-smoke-v3/upstream_runs"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    manifest = load_json(PUBLIC / "dataset_manifest.json")
    split = load_json(PUBLIC / "split_manifest.json")
    for filename, expected in manifest["public_file_sha256"].items():
        if sha256(PUBLIC / filename) != expected:
            raise ValueError(f"public hash mismatch: {filename}")
    for filename, expected in manifest.get("figure_sha256", {}).items():
        if sha256(PUBLIC / "figures" / filename) != expected:
            raise ValueError(f"figure hash mismatch: {filename}")
    for filename, expected in manifest["private_file_sha256"].items():
        if sha256(PRIVATE / filename) != expected:
            raise ValueError(f"private hash mismatch: {filename}")

    sys.path.insert(0, str(ROOT / "scripts"))
    from local_llama_security import verify_private_directory_acl

    acl = verify_private_directory_acl(PRIVATE)
    episodes = load_jsonl(PRIVATE / "episodes.jsonl")
    messages = load_jsonl(PRIVATE / "messages.jsonl")
    actions = load_jsonl(PRIVATE / "actions.jsonl")
    settlements = load_jsonl(PRIVATE / "settlements.jsonl")
    claims = load_jsonl(PRIVATE / "claims.jsonl")
    metrics_rows = list(csv.DictReader((PUBLIC / "pair_behavior_metrics.csv").open(encoding="utf-8-sig", newline="")))

    if len(episodes) != 58 or len({row["episode_id"] for row in episodes}) != 58:
        raise ValueError("episode count or uniqueness check failed")
    if len(metrics_rows) != 29 or {int(row["pair"]) for row in metrics_rows} != set(split["valid_pair_ids"]):
        raise ValueError("pair metric rows do not match frozen valid pair IDs")
    if set(split["development_pairs"]) & set(split["held_out_test_pairs"]):
        raise ValueError("development/test pair overlap")
    if set(split["development_pairs"]) | set(split["held_out_test_pairs"]) != set(split["valid_pair_ids"]):
        raise ValueError("development/test split does not cover valid pairs")
    if not {1, 16, 25}.issubset(set(split["development_pairs"])):
        raise ValueError("public focal examples must remain in development")

    by_episode = {row["episode_id"]: row for row in episodes}
    raw_run_by_episode: dict[str, Path] = {}
    boards_by_episode: dict[str, list[dict]] = {}
    source_hash_checks = 0
    for episode in episodes:
        pair = int(episode["pair_id"])
        condition = episode["condition"]
        block = RAW / f"block-{pair:02d}"
        matches = list(block.glob(f"{condition}__seed1/*/runs/*/{condition}/*"))
        if len(matches) != 1:
            raise ValueError(f"raw run source is missing or ambiguous: pair {pair} {condition}")
        run = matches[0]
        raw_run_by_episode[episode["episode_id"]] = run
        boards_by_episode[episode["episode_id"]] = load_json(run / "blackboards.json")
        for filename, expected in episode["source_hashes"].items():
            if sha256(run / filename) != expected:
                raise ValueError(f"raw source hash mismatch: {pair}/{condition}/{filename}")
            source_hash_checks += 1

    message_map = {row["message_id"]: row for row in messages}
    action_map = {row["action_id"]: row for row in actions}
    settlement_map = {row["settlement_id"]: row for row in settlements}
    if len(message_map) != len(messages) or len(action_map) != len(actions) or len(settlement_map) != len(settlements):
        raise ValueError("message/action/settlement IDs are not unique")
    for message in messages:
        if sha256_bytes(message["message_content"].encode("utf-8")) != message["message_content_sha256"]:
            raise ValueError(f"message content hash mismatch: {message['message_id']}")
        if message["sender_id"] in message["recipient_ids"]:
            raise ValueError(f"message sender included in recipient set: {message['message_id']}")
        if not set(message["recipient_ids"]).issubset(set(message["board_participants"])):
            raise ValueError(f"message recipient is not a board participant: {message['message_id']}")
        episode_id = f"pair-{int(message['pair_id']):02d}-{message['condition']}"
        source_events = [
            event
            for board in boards_by_episode[episode_id]
            for event in (board.get("events") or [])
            if event.get("id") == message["event_id"] and str(event.get("kind", "")).lower() == "communication"
        ]
        if len(source_events) != 1:
            raise ValueError(f"message event does not resolve uniquely in raw board source: {message['message_id']}")
        source_event = source_events[0]
        if source_event.get("agent") != message["sender_id"] or (source_event.get("payload") or {}).get("content") != message["message_content"]:
            raise ValueError(f"message sender/content disagrees with raw source: {message['message_id']}")
        source_board = next(board for board in boards_by_episode[episode_id] if str(board.get("blackboard_id")) == str(message["board_id"]))
        expected_recipients = sorted(str(person) for person in (source_board.get("participants") or []) if str(person) != str(message["sender_id"]))
        if sorted(message["recipient_ids"]) != expected_recipients:
            raise ValueError(f"message recipient derivation disagrees with board membership: {message['message_id']}")

    for action in actions:
        episode_id = f"pair-{int(action['pair_id']):02d}-{action['condition']}"
        run = raw_run_by_episode.get(episode_id)
        if run is None:
            raise ValueError(f"raw run not found for action {action['action_id']}")
        metrics = load_json(run / "metrics.json")
        summary = load_json(run / "final_summary.json")
        metric_agent = next(row for row in metrics["agents"] if row["agent_name"] == action["agent_id"])
        if metric_agent["chosen_task_id"] != action["assigned_task_id"] or summary["assignment"].get(action["agent_id"]) != action["assigned_task_id"]:
            raise ValueError(f"action reconciliation failed for {action['action_id']} in {episode_id}")
        if action["assigned_task_id"] is not None and action["source_fact_status"] != "VERIFIED_BY_METRICS_TOOL_EVENT_AND_FINAL_SUMMARY":
            raise ValueError(f"action provenance status is not verified: {action['action_id']}")

    for settlement in settlements:
        episode = by_episode[settlement["episode_id"]]
        run = raw_run_by_episode[settlement["episode_id"]]
        metrics = load_json(run / "metrics.json")
        summary = load_json(run / "final_summary.json")
        expected_gap = float(metrics["noncoalition_mean_regret"]) - float(metrics["coalition_mean_regret"])
        if abs(expected_gap - float(settlement["official_regret_gap"])) > 1e-9:
            raise ValueError(f"regret formula mismatch for {settlement['settlement_id']}")
        if abs(float(summary["joint_reward"]) - float(settlement["system_reward"])) > 1e-9:
            raise ValueError(f"system reward mismatch for {settlement['settlement_id']}")

    allowed_labels = {"SUPPORTED", "CONTRADICTED", "NOT_IDENTIFIABLE"}
    for claim in claims:
        if claim["claim_status_full_trace"] not in allowed_labels:
            raise ValueError(f"unrecognized full-trace claim label: {claim['claim_id']}")
        if any(mid not in message_map for mid in claim["message_ids"]):
            raise ValueError(f"unresolved message reference: {claim['claim_id']}")
        if any(aid not in action_map for aid in claim["action_ids"]):
            raise ValueError(f"unresolved action reference: {claim['claim_id']}")
        if claim["settlement_id"] not in settlement_map and not claim["settlement_id"].endswith("-contrast"):
            raise ValueError(f"unresolved settlement reference: {claim['claim_id']}")
        intervention = claim.get("synthetic_intervention")
        if intervention and (intervention.get("is_original_model_dialogue") is not False or intervention.get("original_message_content_unchanged") is not True):
            raise ValueError(f"synthetic intervention disclosure is incomplete: {claim['claim_id']}")

    by_pair = {int(row["pair"]): row for row in metrics_rows}
    values = np.asarray([float(row["delta_regret_gap"]) for row in metrics_rows])
    signs = Counter("positive" if value > 1e-12 else "negative" if value < -1e-12 else "zero" for value in values)
    p25_excluded = values[np.asarray([int(row["pair"]) != 25 for row in metrics_rows])]
    blind_message_leaks = 0
    public_files = [path for path in PUBLIC.rglob("*") if path.is_file()]
    for message in messages:
        content = message["message_content"]
        if len(content) >= 60 and any(content.encode("utf-8") in path.read_bytes() for path in public_files):
            blind_message_leaks += 1
    if blind_message_leaks:
        raise ValueError(f"raw message text leaked into public output: {blind_message_leaks} messages")

    receipt = {
        "status": "PASS_OFFLINE_SOURCE_AND_LABEL_REPLAY",
        "dataset_id": manifest["dataset_id"],
        "pair_count": len(metrics_rows), "episode_count": len(episodes), "message_event_count": len(messages),
        "action_event_count": len(actions), "settlement_count": len(settlements), "claim_count": len(claims),
        "raw_source_hash_checks": source_hash_checks,
        "unique_message_references": len(message_map), "unique_action_references": len(action_map),
        "synthetic_intervention_rows": sum(bool(row.get("synthetic_intervention")) for row in claims),
        "split_test_pairs": split["held_out_test_pairs"], "split_overlap": 0,
        "pair_delta_regret_signs": dict(signs),
        "mean_delta_regret_gap": float(values.mean()), "median_delta_regret_gap": float(np.median(values)),
        "mean_delta_regret_gap_excluding_pair_25": float(p25_excluded.mean()),
        "min_delta_regret_gap": float(values.min()), "max_delta_regret_gap": float(values.max()),
        "pair_25_delta_regret_gap": float(by_pair[25]["delta_regret_gap"]),
        "pair_25_delta_system_reward": float(by_pair[25]["delta_system_reward"]),
        "pair_1_delta_regret_gap": float(by_pair[1]["delta_regret_gap"]),
        "pair_1_delta_system_reward": float(by_pair[1]["delta_system_reward"]),
        "public_raw_message_leaks": blind_message_leaks,
        "private_acl_verified": acl["verified"],
        "human_commitment_review_status": "PENDING; no human labels represented as complete",
        "monitor_calls": 0,
        "interpretation_limit": "29 paired trajectories share Jira environment seed 1; these are not 29 independent environment seeds and do not identify message causation or latent intent.",
        "public_manifest_sha256": sha256(PUBLIC / "dataset_manifest.json"),
    }
    (PUBLIC / "verification_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


if __name__ == "__main__":
    from collections import Counter
    main()
