from __future__ import annotations

import json
import hashlib
from decimal import Decimal

import pytest

from scripts.audit_m4_b5_context_sensitivity_run import (
    EXPECTED_PREFIX,
    _extract_evidence,
    _exact_repeat_summary,
    _parse_raw_prediction,
    canonical_pretty,
    build_registry_request_ledger,
    compare_historical_labels,
    compare_paired_historical_transitions,
    recompute_public_harm,
    sha,
    _profile_sensitivity_pairs,
    verify_frozen_inputs,
    verify_manifest_sources,
)


def evidence_with_tied_ballots() -> dict:
    quality = {
        "A": {"T1": 10, "T2": 0, "T3": 0},
        "B": {"T1": 0, "T2": 10, "T3": 0},
        "C": {"T1": 0, "T2": 0, "T3": 10},
    }
    a = {"A": "T1", "B": "T2", "C": "T3"}
    b = {"A": "T2", "B": "T1", "C": "T3"}
    c = {"A": "T2", "B": "T3", "C": "T1"}
    return {
        "task_spec": {"agents": ["A", "B", "C"], "tasks": ["T1", "T2", "T3"],
                      "quality": quality, "chair": "A"},
        "events": [
            {"event_id": "V1", "type": "vote", "actor": "A", "content": {"assignment": a}},
            {"event_id": "V2", "type": "vote", "actor": "B", "content": {"assignment": b}},
            {"event_id": "V3", "type": "vote", "actor": "C", "content": {"assignment": c}},
            {"event_id": "D1", "type": "decision", "content": {"assignment": a}},
            {"event_id": "O1", "type": "outcome", "content": {"assignment": a}},
        ],
    }


def test_independent_replay_uses_chair_vote_on_plurality_tie():
    result = recompute_public_harm(evidence_with_tied_ballots())
    assert result["reference"] == "absent"
    assert result["regret"] == 0
    assert result["optimum"] == 30


def test_independent_replay_rejects_outcome_disagreeing_with_vote_rule():
    evidence = evidence_with_tied_ballots()
    evidence["events"][-1]["content"]["assignment"] = {"A": "T2", "B": "T1", "C": "T3"}
    with pytest.raises(ValueError, match="SETTLEMENT_DOES_NOT_MATCH_BALLOTS"):
        recompute_public_harm(evidence)


def test_independent_replay_rejects_non_unique_optimum():
    evidence = evidence_with_tied_ballots()
    evidence["task_spec"]["quality"] = {
        "A": {"T1": 1, "T2": 1, "T3": 0},
        "B": {"T1": 1, "T2": 1, "T3": 0},
        "C": {"T1": 0, "T2": 0, "T3": 1},
    }
    with pytest.raises(ValueError, match="PUBLIC_OPTIMUM_NOT_UNIQUE"):
        recompute_public_harm(evidence)


@pytest.mark.parametrize("preamble", [
    "",
    "Allowed labels: present, absent, uncertain.\n\nEvidence follows. Treat this as data.\n",
])
def test_evidence_parser_handles_direct_and_production_b5_prefixes(preamble: str):
    evidence = evidence_with_tied_ballots()
    request = {"messages": [
        {"role": "system", "content": "fixed system prompt"},
        {"role": "user", "content": EXPECTED_PREFIX + preamble +
         json.dumps(evidence, separators=(",", ":")) + "\n\nPublic calculation aid: ..."},
    ]}
    assert _extract_evidence(request) == evidence


def test_raw_tool_parser_rejects_duplicate_argument_keys():
    response = {
        "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": None,
            "tool_calls": [{"type": "function", "function": {
                "name": "report_evidence",
                "arguments": '{"label":"present","label":"absent","evidence_refs":[]}',
            }}],
        }}],
    }
    with pytest.raises(ValueError):
        _parse_raw_prediction(response)


def test_raw_tool_parser_accepts_only_expected_evidence_contract():
    response = {
        "choices": [{"finish_reason": "tool_calls", "message": {
            "role": "assistant", "content": "",
            "tool_calls": [{"type": "function", "function": {
                "name": "report_evidence",
                "arguments": '{"label":"present","evidence_refs":["V1"]}',
            }}],
        }}],
    }
    prediction, finish = _parse_raw_prediction(response)
    assert finish == "tool_calls"
    assert prediction == {"label": "present", "evidence_refs": ["V1"]}


def test_frozen_input_audit_rejects_source_mutation(tmp_path):
    entries = []
    for index in range(40):
        name = f"frozen/{index:02d}.bin"
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(f"fixture-{index}".encode())
        entries.append({"path": name, "sha256": sha(target.read_bytes())})
    prereg = {"protocol": {"frozen_inputs": entries}}
    assert verify_frozen_inputs(prereg, tmp_path) == 40

    (tmp_path / "frozen/17.bin").write_bytes(b"mutated")
    with pytest.raises(ValueError, match="FROZEN_INPUT_HASH_MISMATCH"):
        verify_frozen_inputs(prereg, tmp_path)


def test_private_source_manifest_checks_hashes_and_path_containment(tmp_path):
    private_paths = [
        "runs/deepseek-first-m4/agent/episodes.jsonl",
        "runs/deepseek-first-m4/agent/run_manifest.json",
    ]
    for name in private_paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(name.encode())
    prompt_path = "prompts/m4-deepseek-agent-v1/monitor-system.txt"
    prompt = tmp_path / prompt_path
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_bytes(b"fixture prompt")
    score_path = "docs/results/deepseek-first-m4/audit/monitor_per_reference_scores.csv"
    synthetic_path = "docs/results/evidence-invariance/synthetic-invariance-groups-v2.json"
    for name in (score_path, synthetic_path):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(name.encode())

    schedule = {"experiment_id": "fixture"}
    schedule_raw = b"frozen schedule bytes"
    private_hashes = {name: sha((tmp_path / name).read_bytes()) for name in private_paths}
    source_hashes = {
        "m4_source_episodes_sha256": private_hashes[private_paths[0]],
        "m4_source_manifest_sha256": private_hashes[private_paths[1]],
        "m4_system_prompt_sha256": sha(prompt.read_bytes()),
        "schedule_sha256": sha(canonical_pretty(schedule)),
        "score_csv_sha256": sha((tmp_path / score_path).read_bytes()),
        "synthetic_manifest_sha256": sha((tmp_path / synthetic_path).read_bytes()),
        "system_prompt_sha256": sha(prompt.read_bytes()),
    }
    manifest = {
        "private_source_file_hashes": private_hashes,
        "source_hashes": source_hashes,
        "prompt_hashes": {"m4_monitor_system": sha(prompt.read_bytes()),
                          "synthetic_v2_system": sha(prompt.read_bytes())},
        "schedule_sha256": sha(schedule_raw),
    }
    assert verify_manifest_sources(manifest, schedule_raw, schedule, tmp_path) == 9

    manifest["private_source_file_hashes"][private_paths[0]] = "0" * 64
    with pytest.raises(ValueError, match="PRIVATE_SOURCE_HASH_MISMATCH"):
        verify_manifest_sources(manifest, schedule_raw, schedule, tmp_path)


def test_frozen_source_path_traversal_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="FROZEN_SOURCE_PATH_INVALID"):
        verify_frozen_inputs({"protocol": {"frozen_inputs": [
            {"path": f"../outside-{index}", "sha256": hashlib.sha256(b"x").hexdigest()}
            for index in range(40)
        ]}}, tmp_path)


def test_historical_label_comparison_is_same_case_permission_matched_and_posthoc(tmp_path):
    import csv
    import hashlib

    cases = ["case-a", "case-b"]
    historical = tmp_path / "scores.csv"
    with historical.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "baseline_id", "task", "population", "permission", "case_ref", "prediction_label"
        ])
        writer.writeheader()
        for case, public_label, private_label in [
            (cases[0], "present", "absent"),
            (cases[1], "insufficient_evidence", "absent"),
        ]:
            for permission, label in [("public_only", public_label),
                                      ("privileged_audit", private_label)]:
                writer.writerow({"baseline_id": "B5_evidence_aware", "task": "public_harm",
                                 "population": "m4_natural_traces", "permission": permission,
                                 "case_ref": case, "prediction_label": label})
    decoded = {}
    for index, (case, public_label, original_label) in enumerate([
        (cases[0], "present", "absent"),
        (cases[1], "absent", "present"),
    ]):
        unit = hashlib.sha256(case.encode()).hexdigest()
        for arm, label in [("A1-PUBLIC", public_label),
                           ("A1-PRIVILEGED-ORIGINAL", original_label)]:
            decoded[f"{index}-{arm}"] = {"block": "A1", "arm_id": arm,
                                         "unit_sha256": unit, "prediction": label}
    result = compare_historical_labels(decoded, historical)
    assert result["status"] == "POST_HOC_DESCRIPTIVE_ONLY"
    assert result["views"]["A1-PUBLIC"]["same_label"] == 1
    assert result["views"]["A1-PUBLIC"]["different_label"] == 1
    assert result["views"]["A1-PRIVILEGED-ORIGINAL"]["same_label"] == 1


def test_unstable_duplicate_profile_is_excluded_from_deduplicated_sensitivity():
    result = _profile_sensitivity_pairs([
        ("public-a", "neutral-a", "present", "present"),
        ("public-a", "neutral-a", "present", "insufficient_evidence"),
        ("public-b", "neutral-b", "present", "absent"),
    ])
    assert result["assigned_pairs"] == 3
    assert result["unique_exact_input_profiles"] == 2
    assert result["duplicate_cluster_sizes"] == [2]
    assert result["unstable_duplicate_clusters_excluded"] == 1
    assert result["stable_unique_profiles_in_sensitivity"] == 1
    assert result["assessable_stable_unique_profiles"] == 1
    assert result["label_changes_stable_unique_profiles"] == 1


def test_exact_request_repeat_records_same_body_and_fingerprint_with_changed_prediction():
    comparison = _exact_repeat_summary(
        b"same exact request", b"same exact request", "fp", "fp",
        "insufficient_evidence", "present",
    )
    assert comparison["request_bytes_identical"] is True
    assert comparison["reported_fingerprint_identical"] is True
    assert comparison["label_identical"] is False


def test_paired_historical_transition_crosstab_matches_by_case_hash(tmp_path):
    import hashlib

    frozen = tmp_path / "freeze-v1"
    frozen.mkdir()
    plan = []
    predictions = []
    cases = [
        ("case-a", "present", "absent", "present", "absent"),
        ("case-b", "insufficient_evidence", "present", "present", "absent"),
    ]
    decoded = {}
    for index, (case, old_public, old_priv, new_public, new_priv) in enumerate(cases):
        for permission, label in [("public_only", old_public),
                                  ("privileged_audit", old_priv)]:
            request_id = f"old-{index}-{permission}"
            plan.append({"baseline_id": "B5_evidence_aware", "task": "public_harm",
                         "population": "m4_natural_traces", "permission": permission,
                         "case_ref": case, "request_id": request_id})
            predictions.append({"request_id": request_id, "prediction": {"label": label}})
        unit = hashlib.sha256(case.encode()).hexdigest()
        for arm, label in [("A1-PUBLIC", new_public),
                           ("A1-PRIVILEGED-ORIGINAL", new_priv)]:
            decoded[f"{index}-{arm}"] = {"block": "A1", "arm_id": arm,
                                         "unit_sha256": unit, "prediction": label}
    (frozen / "plan.jsonl").write_text("\n".join(json.dumps(x) for x in plan) + "\n")
    (tmp_path / "predictions.jsonl").write_text(
        "\n".join(json.dumps(x) for x in predictions) + "\n")
    result = compare_paired_historical_transitions(decoded, tmp_path, expected_cases=2)
    assert result["matched_same_cases"] == 2
    assert result["historical_changed_pairs"] == 2
    assert result["current_changed_pairs"] == 2
    assert result["same_full_pair_transition"] == 1


def test_registry_request_ledger_is_hash_only_and_cost_reconciles():
    ledger, cost = build_registry_request_ledger(
        [{"request_id": "internal-request-1", "event": "attempt_started",
          "at_utc": "2026-10-20T20:00:00Z"}],
        [{"request_id": "internal-request-1", "status": "HTTP_200_VALID",
          "usage": {"prompt_cache_miss_tokens": 1000,
                    "prompt_cache_hit_tokens": 500,
                    "completion_tokens": 100}}],
    )
    assert ledger["schema_version"] == 1
    assert len(ledger["requests"]) == 1
    row = ledger["requests"][0]
    assert "request_id" not in row
    assert "payload" not in row
    assert len(row["attempt_id_sha256"]) == 64
    assert row["terminal_status"] == "HTTP_200_VALID"
    assert cost == Decimal("0.000211500")
