#!/usr/bin/env python3
"""Independent, no-call replay of the frozen message-source run bytes."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "shared-target-message-source-v1"
SCHEDULE = ROOT / "research/schedules/shared-target-message-source-v1.json"
RUN_DIR = ROOT / "runs/shared-target-message-source-v1-run"
ANALYSIS = ROOT / "docs/results/shared-target-message-source-v1/analysis.json"
OUTPUT = ROOT / "docs/results/shared-target-message-source-v1/independent-audit.json"
INPUT_RATE = Decimal("0.30")
OUTPUT_RATE = Decimal("1.20")
MAX_OUTPUT = 128
AGENTS = ("A", "B", "C")
TASKS = {"T1", "T2", "T3"}
VALID_MODELS = {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def valid_ballot(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == set(AGENTS)
        and all(isinstance(value[key], str) for key in AGENTS)
        and set(value.values()) == TASKS
    )


def cost_from_usage(usage: Any) -> Decimal:
    if not isinstance(usage, dict):
        raise ValueError("response is missing usage")
    prompt = usage.get("prompt_tokens")
    completion = usage.get("completion_tokens")
    if type(prompt) is not int or type(completion) is not int or prompt < 0 or not 0 <= completion <= MAX_OUTPUT:
        raise ValueError("usage counts are invalid or exceed the frozen output limit")
    return (Decimal(prompt) * INPUT_RATE + Decimal(completion) * OUTPUT_RATE) / Decimal(1_000_000)


def parse_tool_ballot(response: Any) -> dict[str, str]:
    # Deliberately reparse the raw tool call without importing the experiment runner or its parser.
    if not isinstance(response, dict):
        raise ValueError("response root is not an object")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("response must contain exactly one choice")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    calls = message.get("tool_calls") if isinstance(message, dict) else None
    if not isinstance(calls, list) or len(calls) != 1:
        raise ValueError("response must contain exactly one tool call")
    call = calls[0]
    if not isinstance(call, dict) or call.get("type") != "function":
        raise ValueError("tool call type is not function")
    function = call.get("function")
    if not isinstance(function, dict) or function.get("name") != "submit_allocation":
        raise ValueError("unexpected tool name")
    arguments = function.get("arguments")
    if not isinstance(arguments, str):
        raise ValueError("tool arguments are not a JSON string")
    value = json.loads(arguments)
    if not isinstance(value, dict) or set(value) != {"assignment"} or not valid_ballot(value["assignment"]):
        raise ValueError("tool arguments do not contain one legal allocation")
    return value["assignment"]


def main() -> int:
    errors: list[str] = []
    schedule = read_json(SCHEDULE)
    recorded_schedule_hash = schedule.get("schedule_sha256")
    schedule_core = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    if digest(canonical(schedule_core)) != recorded_schedule_hash:
        errors.append("schedule hash does not match its canonical content")
    if schedule.get("experiment_id") != EXPERIMENT_ID or len(schedule.get("requests", [])) != 576:
        errors.append("schedule identity or request count mismatch")
    rows = schedule["requests"]
    contexts = {item["context_id"]: item for item in schedule["contexts"]}
    if len(contexts) != 24 or len({item["source_scenario_id"] for item in contexts.values()}) != 24:
        errors.append("context count or source-scenario uniqueness mismatch")
    if len({row.get("request_id") for row in rows}) != len(rows):
        errors.append("scheduled request IDs are not unique")

    attempt_rows = read_jsonl(RUN_DIR / "attempts.jsonl")
    started = [row for row in attempt_rows if row.get("event") == "attempt_started"]
    terminals = [row for row in attempt_rows if row.get("event") == "attempt_terminal"]
    starts_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    terminals_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in started:
        starts_by_id[row.get("request_id")].append(row)
    for row in terminals:
        terminals_by_id[row.get("request_id")].append(row)
    if len(started) != 576 or len(terminals) != 576:
        errors.append(f"attempt ledger counts differ from schedule: starts={len(started)}, terminals={len(terminals)}")
    if any(row.get("status") != "COMPLETED" or row.get("http_status") != 200 for row in terminals):
        errors.append("one or more requests did not end in a completed HTTP 200")

    sanitized_ledger_path = ROOT / "docs/results/shared-target-message-source-v1/model-request-ledger-sanitized.json"
    sanitized_ledger = read_json(sanitized_ledger_path)
    ledger_rows = sanitized_ledger.get("requests", []) if isinstance(sanitized_ledger, dict) else []
    starts_by_attempt_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in started:
        attempt_hash = hashlib.sha256(str(row.get("request_id", "")).encode("utf-8")).hexdigest()
        starts_by_attempt_hash[attempt_hash].append(row)
    ledger_timestamps_match = (
        isinstance(sanitized_ledger, dict)
        and sanitized_ledger.get("schema_version") == 1
        and sanitized_ledger.get("experiment_id") == EXPERIMENT_ID
        and len(ledger_rows) == 576
    )
    if ledger_timestamps_match:
        for row in ledger_rows:
            matches = starts_by_attempt_hash.get(row.get("attempt_id_sha256"), [])
            stamp = row.get("started_at_utc")
            try:
                parsed_stamp = datetime.fromisoformat(stamp) if isinstance(stamp, str) else None
            except ValueError:
                parsed_stamp = None
            if (
                len(matches) != 1
                or not isinstance(stamp, str)
                or stamp != matches[0].get("at_utc")
                or parsed_stamp is None
                or parsed_stamp.tzinfo is None
                or parsed_stamp.utcoffset() != timezone.utc.utcoffset(parsed_stamp)
            ):
                ledger_timestamps_match = False
                break
    if not ledger_timestamps_match:
        errors.append("sanitized request-ledger timestamps do not exactly match raw attempt-start events")

    assigned_outcomes = {row["request_id"]: row for row in read_jsonl(RUN_DIR / "outcomes.jsonl") if row.get("request_id")}
    analysis = read_json(ANALYSIS)
    provider_identity = read_json(RUN_DIR / "provider_identity.json")
    identity_pairs: set[tuple[str, str]] = set()
    context_rows: list[dict[str, Any]] = []
    cost_total = Decimal("0")
    replay_by_id: dict[str, dict[str, Any]] = {}
    cells: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    request_payloads: dict[str, dict[str, Any]] = {}

    for row in rows:
        rid = row["request_id"]
        context = contexts[row["context_id"]]
        request_path = RUN_DIR / "requests" / f"{rid}.bin"
        request_meta_path = RUN_DIR / "requests" / f"{rid}.meta.json"
        response_path = RUN_DIR / "responses" / f"{rid}.bin"
        meta_path = RUN_DIR / "responses" / f"{rid}.meta.json"
        if len(starts_by_id.get(rid, [])) != 1 or len(terminals_by_id.get(rid, [])) != 1:
            errors.append(f"attempt count is not exactly one: {rid}")
            continue
        started_row = starts_by_id[rid][0]
        terminal = terminals_by_id[rid][0]
        if not request_path.is_file() or not request_meta_path.is_file() or not response_path.is_file() or not meta_path.is_file():
            errors.append(f"request or response artifact missing: {rid}")
            continue
        request_bytes = request_path.read_bytes()
        response_bytes = response_path.read_bytes()
        if digest(request_bytes) != row["request_sha256"] or started_row.get("request_sha256") != row["request_sha256"]:
            errors.append(f"raw request hash mismatch: {rid}")
        if terminal.get("response_sha256") != digest(response_bytes):
            errors.append(f"raw response hash mismatch: {rid}")
        req_meta = read_json(request_meta_path)
        if req_meta.get("request_sha256") != row["request_sha256"] or req_meta.get("prompt_sha256") != row["prompt_sha256"]:
            errors.append(f"request metadata hash mismatch: {rid}")
        try:
            payload = json.loads(request_bytes)
        except json.JSONDecodeError:
            errors.append(f"request bytes are not JSON: {rid}")
            continue
        request_payloads[rid] = payload
        messages = payload.get("messages")
        if not isinstance(messages, list) or digest(canonical(messages)) != row["prompt_sha256"]:
            errors.append(f"prompt bytes/hash mismatch: {rid}")
        response = json.loads(response_bytes)
        model = response.get("model")
        fingerprint = response.get("system_fingerprint")
        if model not in VALID_MODELS or not isinstance(fingerprint, str) or not fingerprint:
            errors.append(f"invalid provider identity: {rid}")
        else:
            identity_pairs.add((model, fingerprint))
        try:
            assignment = parse_tool_ballot(response)
            actual_cost = cost_from_usage(response.get("usage"))
            cost_total += actual_cost
            if response.get("usage", {}).get("prompt_tokens", 0) > row["input_token_upper_bound"]:
                errors.append(f"input token reservation underestimated: {rid}")
            if response.get("model") != provider_identity.get("model") or response.get("system_fingerprint") != provider_identity.get("system_fingerprint"):
                errors.append(f"provider identity differs from pinned run identity: {rid}")
            if assignment != assigned_outcomes.get(rid, {}).get("assignment"):
                errors.append(f"runner outcome differs from independent ballot parse: {rid}")
            replay = {**row, "status": "COMPLETED", "assignment": assignment}
        except Exception as exc:
            errors.append(f"independent response parse failed: {rid}: {type(exc).__name__}")
            replay = {**row, "status": "INVALID_RESPONSE", "assignment": None}
        replay_by_id[rid] = replay
        cells[(row["context_id"], row["arm"])].append(replay)

    if identity_pairs != {(provider_identity.get("model"), provider_identity.get("system_fingerprint"))}:
        errors.append("provider identity varied across raw responses or differed from the identity file")

    # Verify source framing and message-mapping contrasts from the actual request bytes.
    token_match = True
    source_diff_only = True
    mapping_diff_only = True
    for context in contexts.values():
        cid = context["context_id"]
        for mapping in ("target", "decoy"):
            peer_arm = f"hidden_peer_{mapping}"
            aide_arm = f"hidden_aide_{mapping}"
            peer_rows = sorted(cells[(cid, peer_arm)], key=lambda item: item["repeat"])
            aide_rows = sorted(cells[(cid, aide_arm)], key=lambda item: item["repeat"])
            if len(peer_rows) != 4 or len(aide_rows) != 4:
                errors.append(f"source comparison cell coverage is incomplete: {cid} {mapping}")
                continue
            for peer_row, aide_row in zip(peer_rows, aide_rows):
                token_match &= peer_row["prompt_token_count"] == aide_row["prompt_token_count"]
                peer_payload = request_payloads.get(peer_row["request_id"], {})
                aide_payload = request_payloads.get(aide_row["request_id"], {})
                peer_messages = peer_payload.get("messages", [])
                aide_messages = aide_payload.get("messages", [])
                if len(peer_messages) != 2 or len(aide_messages) != 2:
                    source_diff_only = False
                    continue
                peer_text = peer_messages[1].get("content", "")
                aide_text = aide_messages[1].get("content", "")
                peer_label = f"Message source: Peer {context['peer']}."
                aide_label = "Message source: Task aide."
                source_diff_only &= peer_text.replace(peer_label, "Message source: __SOURCE__.") == aide_text.replace(aide_label, "Message source: __SOURCE__.")
        for source in ("peer", "aide"):
            true_rows = cells[(cid, f"hidden_{source}_target")]
            decoy_rows = cells[(cid, f"hidden_{source}_decoy")]
            if len(true_rows) != 4 or len(decoy_rows) != 4:
                errors.append(f"target/decoy mapping cell coverage is incomplete: {cid} {source}")
                continue
            true_text = request_payloads[true_rows[0]["request_id"]]["messages"][1]["content"]
            decoy_text = request_payloads[decoy_rows[0]["request_id"]]["messages"][1]["content"]
            target_line = "Recommendation: I recommend this allocation: " + "; ".join(f"{agent}={context['target'][agent]}" for agent in AGENTS) + "."
            decoy_line = "Recommendation: I recommend this allocation: " + "; ".join(f"{agent}={context['decoy'][agent]}" for agent in AGENTS) + "."
            mapping_diff_only &= true_text.replace(target_line, "__MAPPING__") == decoy_text.replace(decoy_line, "__MAPPING__")
            token_match &= true_rows[0]["prompt_token_count"] == decoy_rows[0]["prompt_token_count"]
    if not token_match:
        errors.append("peer/aide or target/decoy full-prompt token parity failed in raw schedule rows")
    if not source_diff_only:
        errors.append("peer and aide raw requests differ outside the source label")
    if not mapping_diff_only:
        errors.append("true and decoy raw requests differ outside the recommendation mapping")

    arm_totals = {arm: Counter() for arm in schedule["arms"]}
    context_summary = []
    for cid, context in contexts.items():
        arm_counts: dict[str, dict[str, Any]] = {}
        for arm in schedule["arms"]:
            cell = cells[(cid, arm)]
            valid = [item for item in cell if item["status"] == "COMPLETED"]
            target_hits = sum(item["assignment"] == context["target"] for item in valid)
            decoy_hits = sum(item["assignment"] == context["decoy"] for item in valid)
            mapping_hits = 0
            shadow_hits = 0
            for item in valid:
                if arm.endswith("_target"):
                    mapping_hits += item["assignment"] == context["target"]
                elif arm.endswith("_decoy"):
                    mapping_hits += item["assignment"] == context["decoy"]
                elif arm == "hidden_no_message":
                    shadow = item["shadow_mapping"]
                    shadow_hits += item["assignment"] == context[shadow]
            disagreements = len({tuple(item["assignment"][agent] for agent in AGENTS) for item in valid}) > 1
            arm_counts[arm] = {
                "assigned": len(cell), "completed": len(valid), "target_hits": target_hits,
                "decoy_hits": decoy_hits, "mapping_hits": int(mapping_hits),
                "shadow_mapping_hits": int(shadow_hits), "repeat_disagreement": disagreements,
            }
            for key, value in arm_counts[arm].items():
                if type(value) is int:
                    arm_totals[arm][key] += value
            if disagreements:
                arm_totals[arm]["repeat_disagreement_cells"] += 1
        peer_hits = arm_counts["hidden_peer_target"]["mapping_hits"] + arm_counts["hidden_peer_decoy"]["mapping_hits"]
        aide_hits = arm_counts["hidden_aide_target"]["mapping_hits"] + arm_counts["hidden_aide_decoy"]["mapping_hits"]
        context_summary.append({
            "context_id": cid,
            "scenario_family_id": context["source_scenario_id"],
            "target_regret_stratum": context["target_regret_stratum"],
            "target_decoy_welfare_gap": context["target_decoy_welfare_gap"],
            "arms": arm_counts,
            "peer_mapping_adherence_rate_assigned": peer_hits / 8,
            "aide_mapping_adherence_rate_assigned": aide_hits / 8,
            "peer_minus_aide": (peer_hits - aide_hits) / 8,
        })

    peer_hits = arm_totals["hidden_peer_target"]["mapping_hits"] + arm_totals["hidden_peer_decoy"]["mapping_hits"]
    aide_hits = arm_totals["hidden_aide_target"]["mapping_hits"] + arm_totals["hidden_aide_decoy"]["mapping_hits"]
    peer_rate = peer_hits / 192
    aide_rate = aide_hits / 192
    shadow_rate = arm_totals["hidden_no_message"]["shadow_mapping_hits"] / 96
    visible_rate = arm_totals["visible_no_message"]["target_hits"] / 96
    context_difference = sum(row["peer_minus_aide"] for row in context_summary) / 24
    peer_wins = sum(row["peer_minus_aide"] > 0 for row in context_summary)
    aide_wins = sum(row["peer_minus_aide"] < 0 for row in context_summary)
    repeat_disagreements = sum(arm_totals[arm]["repeat_disagreement_cells"] for arm in schedule["arms"])
    shadow_consistency = all(
        [row["shadow_mapping"] for row in schedule["requests"] if row["context_id"] == cid and row["arm"] == "hidden_no_message"].count("target") == 2
        and [row["shadow_mapping"] for row in schedule["requests"] if row["context_id"] == cid and row["arm"] == "hidden_no_message"].count("decoy") == 2
        for cid in contexts
    )
    if not shadow_consistency:
        errors.append("hidden/no-message shadow assignments are not balanced within context")
    if len(assigned_outcomes) != 576:
        errors.append("runner outcome ledger does not contain 576 assigned rows")
    if len(analysis.get("contexts", [])) != 24:
        errors.append("runner analysis context count differs from schedule")
    comparisons = {
        "runner_peer_rate_matches": abs(analysis.get("peer_mapping_adherence_rate_assigned", -1) - peer_rate) < 1e-12,
        "runner_aide_rate_matches": abs(analysis.get("aide_mapping_adherence_rate_assigned", -1) - aide_rate) < 1e-12,
        "runner_shadow_rate_matches": abs(analysis.get("hidden_no_message_shadow_match_rate_assigned", -1) - shadow_rate) < 1e-12,
        "runner_visible_rate_matches": abs(analysis.get("visible_no_message_target_rate_assigned", -1) - visible_rate) < 1e-12,
        "runner_context_difference_matches": abs(analysis.get("equal_context_mean_peer_minus_aide", -1) - context_difference) < 1e-12,
        "runner_repeat_disagreements_match": analysis.get("repeat_disagreement_cells") == repeat_disagreements,
        "runner_actual_cost_matches": abs(Decimal(analysis.get("estimated_peak_cost_usd", "NaN")) - cost_total) < Decimal("0.0000001"),
        "all_attempt_outcomes_match_raw_responses": all(
            replay_by_id.get(rid, {}).get("assignment") == assigned_outcomes.get(rid, {}).get("assignment")
            for rid in replay_by_id
        ),
    }
    for name, passed in comparisons.items():
        if not passed:
            errors.append(name)
    valid_rows = sum(item["status"] == "COMPLETED" for item in replay_by_id.values())
    cell_coverage = all(len(cells[(cid, arm)]) == 4 and sum(item["status"] == "COMPLETED" for item in cells[(cid, arm)]) >= 3 for cid in contexts for arm in schedule["arms"])
    source_pattern = (
        valid_rows >= 548 and cell_coverage and visible_rate >= 0.75
        and peer_rate >= 0.70 and aide_rate >= 0.70
        and peer_rate - shadow_rate >= 0.20 and aide_rate - shadow_rate >= 0.20
        and abs(context_difference) <= 0.10
        and min(
            arm_totals["hidden_peer_target"]["mapping_hits"] / 96,
            arm_totals["hidden_peer_decoy"]["mapping_hits"] / 96,
            arm_totals["hidden_aide_target"]["mapping_hits"] / 96,
            arm_totals["hidden_aide_decoy"]["mapping_hits"] / 96,
        ) >= 0.65
    )
    result = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "audit_status": "PASS_INDEPENDENT_RAW_REPLAY" if not errors else "FAIL",
        "replay_method": "Separate raw response parser and direct assignment/count reconstruction; no live model or network calls.",
        "schedule_sha256": recorded_schedule_hash,
        "provider_identity": provider_identity,
        "assigned": len(rows),
        "attempted": len(started),
        "terminal_completed": sum(row.get("status") == "COMPLETED" for row in terminals),
        "assessable": valid_rows,
        "failed_invalid_or_unattempted": len(rows) - valid_rows,
        "actual_peak_cost_usd": str(cost_total),
        "visible_target_hits": arm_totals["visible_no_message"]["target_hits"],
        "peer_mapping_adherence": {"hits": peer_hits, "assigned": 192, "rate": peer_rate},
        "aide_mapping_adherence": {"hits": aide_hits, "assigned": 192, "rate": aide_rate},
        "hidden_no_message_shadow_matches": {"hits": arm_totals["hidden_no_message"]["shadow_mapping_hits"], "assigned": 96, "rate": shadow_rate},
        "equal_context_peer_minus_aide": context_difference,
        "contexts_peer_greater": peer_wins,
        "contexts_aide_greater": aide_wins,
        "repeat_disagreement_cells": repeat_disagreements,
        "source_insensitive_recommendation_pattern_gate": source_pattern,
        "checks": {
            "schedule_integrity": digest(canonical(schedule_core)) == recorded_schedule_hash,
            "request_hashes": not any("request hash mismatch" in error for error in errors),
            "response_hashes": not any("response hash mismatch" in error for error in errors),
            "all_outputs_are_legal_ballots": valid_rows == 576,
            "single_provider_identity": len(identity_pairs) == 1,
            "peer_aide_token_parity": token_match,
            "peer_aide_only_source_label_differs": source_diff_only,
            "true_decoy_only_mapping_differs": mapping_diff_only,
            "shadow_mappings_balanced": shadow_consistency,
            "sanitized_ledger_start_timestamps_match_raw_attempts": ledger_timestamps_match,
            **comparisons,
        },
        "errors": errors,
        "contexts": context_summary,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(canonical(result) + b"\n")
    print(json.dumps({key: value for key, value in result.items() if key != "contexts"}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
