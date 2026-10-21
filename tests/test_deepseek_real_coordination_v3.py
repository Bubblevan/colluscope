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

from colluscope.deepseek_real_coordination_v3 import EXPERIMENT_ID, build_schedule


def test_v3_schedule_has_namespaced_ids_and_closed_dependency_references():
    schedule = build_schedule()
    assert schedule["experiment_id"] == EXPERIMENT_ID == "deepseek-real-coordination-40-v3"
    assert len(schedule["requests"]) == 40
    ids = {row["request_id"] for row in schedule["requests"]}
    assert len(ids) == 40
    assert all(request_id.startswith("v3-") for request_id in ids)
    for row in schedule["requests"]:
        assert set(row["dependencies"]) <= ids
        for key in ("proposal_request_id", "reply_request_id"):
            if row.get(key):
                assert row[key] in ids
    core = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    from colluscope.deepseek_real_coordination_v3 import canonical, sha
    assert schedule["schedule_sha256"] == sha(canonical(core))


def test_transport_terminal_without_hash_reconciles_to_matching_start_row(tmp_path, monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v3")
    monkeypatch.setattr(runner, "RUN_DIR", tmp_path)
    (tmp_path / "requests").mkdir()
    (tmp_path / "responses").mkdir()
    body = b'{"frozen":"request"}'
    digest = hashlib.sha256(body).hexdigest()
    (tmp_path / "requests" / "v3-C1-delivered.bin").write_bytes(body)
    rows = [
        {"event": "attempt_started", "request_id": "v3-C1-delivered", "request_sha256": digest},
        {"event": "attempt_terminal", "request_id": "v3-C1-delivered",
         "status": "TRANSPORT_ERROR", "http_status": None, "response_sha256": None},
    ]
    (tmp_path / "attempts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    actual, terminals = runner._attempt_rows()
    assert len(actual) == 2
    assert terminals["v3-C1-delivered"]["status"] == "TRANSPORT_ERROR"


def test_transport_terminal_rejects_tampered_request_even_with_start_hash(tmp_path, monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v3")
    monkeypatch.setattr(runner, "RUN_DIR", tmp_path)
    (tmp_path / "requests").mkdir()
    (tmp_path / "responses").mkdir()
    (tmp_path / "requests" / "v3-C1-delivered.bin").write_bytes(b"tampered")
    rows = [
        {"event": "attempt_started", "request_id": "v3-C1-delivered", "request_sha256": "a" * 64},
        {"event": "attempt_terminal", "request_id": "v3-C1-delivered",
         "status": "TRANSPORT_ERROR", "http_status": None, "response_sha256": None},
    ]
    (tmp_path / "attempts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(RuntimeError, match="raw request missing or hash-mismatched"):
        runner._attempt_rows()


def test_runner_is_offline_without_explicit_execute_flag(monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v3")
    calls = []
    monkeypatch.setattr(sys, "argv", ["run_deepseek_real_coordination_v3"])
    monkeypatch.setattr(runner, "run", lambda *, check_only: calls.append(check_only) or {
        "status": "PASS_OFFLINE_PREFLIGHT", "model_calls": 0,
    })
    assert runner.main() == 0
    assert calls == [True]


def test_transport_failure_terminalizes_batch_and_never_dispatches_descendants(tmp_path, monkeypatch):
    runner = importlib.import_module("scripts.run_deepseek_real_coordination_v3")
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

    assert FakeClient.calls == ["v3-C1-delivered"]
    assert result["physical_attempts"] == 1
    assert result["unattempted_assigned"] == 39
    assert result["stop_status"] == "v3-C1-delivered:TRANSPORT_ERROR"
    progress = [json.loads(line) for line in
                (tmp_path / "run" / "progress.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(row["event"] == "request_failure" and row["request_id"] == "v3-C1-delivered"
               for row in progress)
    assert sum(row["event"] == "request_unattempted" for row in progress) == 39
