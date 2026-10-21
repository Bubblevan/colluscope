from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.deepseek_real_coordination_v4 import EXPERIMENT_ID, build_schedule


def test_v4_schedule_has_namespaced_ids_and_closed_dependency_references():
    schedule = build_schedule()
    assert schedule["experiment_id"] == EXPERIMENT_ID == "deepseek-real-coordination-40-v4"
    assert len(schedule["requests"]) == 40
    ids = {row["request_id"] for row in schedule["requests"]}
    assert len(ids) == 40
    assert all(request_id.startswith("v4-") for request_id in ids)
    for row in schedule["requests"]:
        assert set(row["dependencies"]) <= ids
        for key in ("proposal_request_id", "reply_request_id"):
            if row.get(key):
                assert row[key] in ids
    core = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    from colluscope.deepseek_real_coordination_v4 import canonical, sha
    assert schedule["schedule_sha256"] == sha(canonical(core))


def test_all_runtime_schemas_use_documented_deepseek_strict_subset():
    from colluscope.deepseek_real_coordination_v4 import schemas, strict_schema_errors

    cases = [
        ("fact_control", None), ("proposal", None), ("reply", None),
        ("reply", {"stance": "propose", "choice": "HIGH", "text": "test"}),
        ("ballot", None),
    ]
    for kind, incoming in cases:
        _, schema = schemas(kind, incoming_proposal=incoming)
        assert strict_schema_errors(schema) == []


def test_frozen_endpoint_matches_strict_function_calling_client():
    from colluscope.deepseek_m4_v1 import STRICT_ENDPOINT

    assert STRICT_ENDPOINT == "https://api.deepseek.com/beta/chat/completions"


@pytest.mark.parametrize("schema,fragment", [
    ({"type": "string", "maxLength": 240}, "maxLength"),
    ({"type": ["string", "null"]}, "union types"),
    ({"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}, "additionalProperties"),
])
def test_strict_schema_gate_rejects_known_unsupported_constructs(schema, fragment):
    from colluscope.deepseek_real_coordination_v4 import strict_schema_errors

    assert fragment in " ".join(strict_schema_errors(schema))


def test_no_message_uses_explicit_string_sentinel_and_local_text_limit():
    from colluscope.deepseek_real_coordination_v4 import validate_action

    valid = {"stance": "no_message", "choice": "UNDECIDED", "text": ""}
    assert validate_action("proposal", valid) == valid
    with pytest.raises(Exception):
        validate_action("proposal", {"stance": "no_message", "choice": None, "text": ""})
    with pytest.raises(ValueError, match="240-character"):
        validate_action("proposal", {"stance": "propose", "choice": "HIGH", "text": "x" * 241})


def test_prompt_does_not_request_json_null_for_no_message():
    from colluscope.deepseek_real_coordination_v4 import messages_for

    schedule = build_schedule()
    proposal = next(row for row in schedule["requests"] if row["kind"] == "proposal")
    messages, _ = messages_for(proposal, schedule, {})
    text = "\n".join(message["content"] for message in messages)
    assert "UNDECIDED" in text
    assert "choice LOW/HIGH/null" not in text
    assert "at most 240 characters" in text


def test_every_stage_prompt_renders_v4_sentinels_without_json_null():
    from colluscope.deepseek_real_coordination_v4 import messages_for

    schedule = build_schedule()
    outputs = {}
    for row in schedule["requests"]:
        if row["kind"] in {"proposal", "reply"}:
            outputs[row["request_id"]] = {"stance": "no_message", "choice": "UNDECIDED", "text": ""}
        elif row["kind"] == "ballot":
            outputs[row["request_id"]] = {"choice": "LOW"}
    for row in schedule["requests"]:
        messages, _ = messages_for(row, schedule, outputs)
        prompt = "\n".join(message["content"] for message in messages)
        assert "choice LOW/HIGH/null" not in prompt
        assert "use null and empty text" not in prompt


def test_independent_analysis_reconstructs_prefixed_v4_request_ids():
    from colluscope.deepseek_real_coordination_v4 import analyze_actions, fact_control_reference

    schedule = build_schedule()
    actions, statuses = {}, {}
    for row in schedule["requests"]:
        rid = row["request_id"]
        statuses[rid] = {"http_status": 200}
        if row["kind"] == "fact_control":
            actions[rid] = {"answer": fact_control_reference(row)}
        elif row["kind"] in {"proposal", "reply"}:
            actions[rid] = {"stance": "no_message", "choice": "UNDECIDED", "text": ""}
        else:
            high_arm = row["condition_id"] == "shared_bonus_actual_delivery"
            actions[rid] = {"choice": "HIGH" if high_arm else "LOW"}
    result = analyze_actions(schedule, actions, statuses)
    assert result["experiment_id"] == EXPERIMENT_ID
    assert result["fact_control_assigned"] == 4
    assert result["fact_control_correct"] == 4
    s1 = [row for row in result["main_group_rows"] if row["scenario_id"] == "S1"]
    no_delivery = next(row for row in s1 if row["condition_id"] == "shared_bonus_no_delivery")
    actual = next(row for row in s1 if row["condition_id"] == "shared_bonus_actual_delivery")
    assert no_delivery["choice_A"] == "LOW"
    assert actual["choice_A"] == "HIGH"


def test_transport_terminal_without_hash_reconciles_to_matching_start_row(tmp_path, monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v4")
    monkeypatch.setattr(runner, "RUN_DIR", tmp_path)
    (tmp_path / "requests").mkdir()
    (tmp_path / "responses").mkdir()
    body = b'{"frozen":"request"}'
    digest = hashlib.sha256(body).hexdigest()
    (tmp_path / "requests" / "v4-C1-delivered.bin").write_bytes(body)
    rows = [
        {"event": "attempt_started", "request_id": "v4-C1-delivered", "request_sha256": digest},
        {"event": "attempt_terminal", "request_id": "v4-C1-delivered",
         "status": "TRANSPORT_ERROR", "http_status": None, "response_sha256": None},
    ]
    (tmp_path / "attempts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    actual, terminals = runner._attempt_rows()
    assert len(actual) == 2
    assert terminals["v4-C1-delivered"]["status"] == "TRANSPORT_ERROR"


def test_transport_terminal_rejects_tampered_request_even_with_start_hash(tmp_path, monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v4")
    monkeypatch.setattr(runner, "RUN_DIR", tmp_path)
    (tmp_path / "requests").mkdir()
    (tmp_path / "responses").mkdir()
    (tmp_path / "requests" / "v4-C1-delivered.bin").write_bytes(b"tampered")
    rows = [
        {"event": "attempt_started", "request_id": "v4-C1-delivered", "request_sha256": "a" * 64},
        {"event": "attempt_terminal", "request_id": "v4-C1-delivered",
         "status": "TRANSPORT_ERROR", "http_status": None, "response_sha256": None},
    ]
    (tmp_path / "attempts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(RuntimeError, match="raw request missing or hash-mismatched"):
        runner._attempt_rows()


def test_runner_is_offline_without_explicit_execute_flag(monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v4")
    calls = []
    monkeypatch.setattr(sys, "argv", ["run_deepseek_real_coordination_v4"])
    monkeypatch.setattr(runner, "run", lambda *, check_only: calls.append(check_only) or {
        "status": "PASS_OFFLINE_PREFLIGHT", "model_calls": 0,
    })
    assert runner.main() == 0
    assert calls == [True]


def test_transport_failure_terminalizes_batch_and_never_dispatches_descendants(tmp_path, monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v4")
    schedule = build_schedule()

    class FakeTokenizer:
        def encode(self, _text):
            return SimpleNamespace(ids=[1, 2, 3])

    class FakeClient:
        calls = []

        def __init__(self, *, run_dir, budget_ledger, **_kwargs):
            self.run_dir = run_dir
            self.budget_ledger = budget_ledger

        def call(self, *, request_id, messages, tool_name, schema, output_limit, metadata, **_kwargs):
            self.calls.append(request_id)
            payload = runner.request_payload(
                interface="strict_function_calling", messages=messages,
                tool_name=tool_name, schema=schema, output_limit=output_limit,
            )
            body = runner.canonical(payload)
            (self.run_dir / "requests").mkdir(exist_ok=True)
            (self.run_dir / "responses").mkdir(exist_ok=True)
            request_hash = runner.sha(body)
            runner.write_once(self.run_dir / "requests" / f"{request_id}.bin", body)
            runner.append_jsonl(self.run_dir / "attempts.jsonl", {
                "event": "attempt_started", "request_id": request_id,
                "request_sha256": request_hash, "auth_header_saved": False,
            })
            runner.append_jsonl(self.budget_ledger, {
                "event": "physical_request_started", "request_id": request_id,
                "request_sha256": request_hash, "auth_header_saved": False,
            })
            # Reproduce the shared client defect: the transport terminal omits the hash.
            terminal = {"event": "attempt_terminal", "request_id": request_id,
                        "status": "TRANSPORT_ERROR", "http_status": None,
                        "response_sha256": None, "retry": False,
                        "auth_header_saved": False}
            runner.append_jsonl(self.run_dir / "attempts.jsonl", terminal)
            runner.append_jsonl(self.budget_ledger, {
                **terminal, "event": "physical_request_terminal",
            })
            raise runner.DeepSeekRequestError("TRANSPORT_ERROR", "simulated DNS failure", fatal=False)

    FakeClient.calls = []
    monkeypatch.setattr(runner, "verify_freeze", lambda: (
        schedule, {"endpoint": "https://api.deepseek.com/chat/completions"},
        FakeTokenizer(), {}, "fake-key"))
    monkeypatch.setattr(runner, "RUN_DIR", tmp_path / "run")
    monkeypatch.setattr(runner, "DeepSeekClient", FakeClient)
    monkeypatch.setattr(runner, "apply_private_acl", lambda _path: None)
    monkeypatch.setattr(runner, "_check_remaining_budget", lambda *_args: None)
    monkeypatch.setattr(runner, "load_json", lambda _path: {})
    monkeypatch.setattr(runner, "file_sha", lambda _path: "frozen-hash")

    result = runner.run()

    assert FakeClient.calls == ["v4-C1-delivered"]
    assert result["physical_attempts"] == 1
    assert result["unattempted_assigned"] == 39
    assert result["stop_status"] == "v4-C1-delivered:TRANSPORT_ERROR"
    progress = [json.loads(line) for line in
                (tmp_path / "run" / "progress.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(row["event"] == "request_failure" and row["request_id"] == "v4-C1-delivered"
               for row in progress)
    assert sum(row["event"] == "request_unattempted" for row in progress) == 39
