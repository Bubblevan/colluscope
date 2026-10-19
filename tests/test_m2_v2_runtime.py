from __future__ import annotations

import json
from pathlib import Path

from colluscope.m2_monitor import PERMISSIONS, VIEWS
from colluscope.openai_compat_llamacpp import llama_server_command
from scripts.run_m2_v2 import (
    backend_config, build_payload, load_cases, load_settings, _fixed_preflight_case,
)


class _Counter:
    def encode_chat(self, messages, *, enable_thinking=False):
        assert enable_thinking is False
        return [1] * 100


def test_frozen_runner_builds_exact_three_candidate_by_ten_case_schedule():
    config, registry = load_settings()
    cases = load_cases()
    selected = _fixed_preflight_case(cases)
    counter = _Counter()
    requests = []
    for candidate in registry["candidates"]:
        for view in VIEWS:
            for permission in PERMISSIONS:
                requests.append(build_payload(selected, view, permission, config, candidate, counter))
    assert selected.partition == "F1" and selected.delivered_messages
    assert len(requests) == 30
    assert len({row["payload_sha256"] for row in requests}) == 30
    assert all(row["preparation_status"] == "prepared" for row in requests)
    assert all(row["input_tokens_local"] <= config["input_token_cap"] for row in requests)


def test_only_schema_candidate_payloads_carry_schema_and_all_fit_context():
    config, registry = load_settings()
    case = _fixed_preflight_case(load_cases())
    by_id = {row["candidate_id"]: row for row in registry["candidates"]}
    for candidate in registry["candidates"]:
        prepared = build_payload(case, "raw_fusion", "privileged_audit", config, candidate, _Counter())
        body = json.loads(prepared["payload_json"])
        format_type = candidate["response_format"]["type"]
        assert body["response_format"]["type"] == format_type
        if format_type == "json_schema":
            assert body["response_format"]["schema"] == prepared["schema"]
        else:
            assert body["response_format"] == {"type": "json_object"}
        assert prepared["input_tokens_local"] + config["output_token_cap"] <= config["context_length"]
    assert by_id["M2-V2-C2-full-json-object-schema"]["contract"] == "M2-V2-FULL"


def test_public_projection_payload_never_contains_delivered_private_text():
    config, registry = load_settings()
    case = _fixed_preflight_case(load_cases())
    assert case.delivered_messages
    private_texts = [row["text"] for row in case.delivered_messages]
    prepared = build_payload(case, "raw_fusion", "public_only", config,
                             registry["candidates"][0], _Counter())
    serialized = prepared["payload_json"]
    assert not any(text in serialized for text in private_texts)
    assert prepared["evidence"]["format"] == "raw_ordered_event_stream"


def test_selected_local_backend_command_remains_loopback_and_hard_bounded():
    config, _ = load_settings()
    backend = backend_config(config)
    command = llama_server_command(backend, Path("C:/temporary/m2-v2-api-key"))
    assert backend.base_url == "http://127.0.0.1:8081/v1"
    assert backend.max_logical_requests == 1000
    assert backend.max_total_attempts == 2000
    assert command[command.index("--host") + 1] == "127.0.0.1"
    assert command[command.index("--port") + 1] == "8081"
    assert "--offline" in command
    assert "--api-key-file" in command
