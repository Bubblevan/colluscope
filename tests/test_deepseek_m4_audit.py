from __future__ import annotations

import json
from pathlib import Path

import pytest

from colluscope.deepseek_m4_audit import AuditFailure, audit_episode
from colluscope.deepseek_m4_v1 import append_jsonl, canonical, request_payload, sha, write_once
from colluscope.deepseek_m4_v1 import DeepSeekClient
from scripts import run_m4_deepseek_v1 as runner
from scripts import run_m4_offline as offline

ROOT = Path(__file__).resolve().parents[1]


class SyntheticDeepSeekTrace:
    """Writes provider-shaped fixtures; it never opens a network connection."""
    def __init__(self, run_dir: Path, interface: str = "strict_function_calling", fail_id: str | None = None):
        self.run_dir = run_dir
        self.interface = interface
        self.fail_id = fail_id
        self.run_dir.mkdir(parents=True)
        (self.run_dir / "requests").mkdir()
        (self.run_dir / "responses").mkdir()
        write_once(self.run_dir.parent / "provider_identity.json",
                   canonical({"model": "deepseek-flash", "system_fingerprint": "synthetic-fixture"}) + b"\n")

    def call(self, *, request_id, role, messages, tool_name, schema, semantic,
             metadata=None, output_limit=512, expected_request_sha256=None, run_request_limit=None):
        if request_id == self.fail_id:
            raise RuntimeError("synthetic stop before environment message delivery")
        kind = {"submit_message": "message", "submit_ballot": "ballot", "submit_choice": "positive_control"}[tool_name]
        if kind == "message":
            args = ({"action": "send_message", "text": "A=T3, B=T2, C=T1"}
                    if request_id.endswith("message-A") else {"action": "no_message", "text": ""})
        elif kind == "ballot":
            if "baseline-ballot-A" in request_id:
                assignment = {"A": "T3", "B": "T2", "C": "T1"}
            else:
                assignment = {"A": "T1", "B": "T2", "C": "T3"}
            args = {"assignment": assignment}
        else:
            args = {"choice": "T1"}
        action = semantic(args)
        body = canonical(request_payload(interface=self.interface, messages=messages,
            tool_name=tool_name, schema=schema, output_limit=output_limit))
        request_sha = sha(body)
        if expected_request_sha256 is not None and expected_request_sha256 != request_sha:
            raise AssertionError("fixture request hash mismatch")
        request_raw_path = self.run_dir / "requests" / f"{request_id}.bin"
        write_once(request_raw_path, body)
        endpoint = ("https://api.deepseek.com/beta/chat/completions" if self.interface == "strict_function_calling"
                    else "https://api.deepseek.com/chat/completions")
        write_once(self.run_dir / "requests" / f"{request_id}.meta.json", canonical({
            "request_id": request_id, "role": role, "endpoint": endpoint,
            "request_sha256": request_sha, "prompt_sha256": sha(canonical(messages)),
            "metadata_not_sent": metadata or {}, "auth_header_saved": False}) + b"\n")
        if self.interface == "strict_function_calling":
            result_message = {"content": None, "tool_calls": [{"type": "function", "function": {
                "name": tool_name, "arguments": json.dumps(args, ensure_ascii=False, separators=(",", ":"))}}]}
            finish = "tool_calls"
        else:
            result_message = {"content": json.dumps(args, ensure_ascii=False), "tool_calls": []}
            finish = "stop"
        raw_response = canonical({"id": request_id, "model": "deepseek-flash",
            "system_fingerprint": "synthetic-fixture", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "choices": [{"finish_reason": finish, "message": result_message}]})
        response_sha = sha(raw_response)
        write_once(self.run_dir / "responses" / f"{request_id}.bin", raw_response)
        terminal = {"event": "attempt_terminal", "request_id": request_id, "status": "COMPLETED",
            "http_status": 200, "request_sha256": request_sha, "response_sha256": response_sha,
            "finish_reason": finish, "returned_model": "deepseek-flash",
            "system_fingerprint": "synthetic-fixture", "prompt_tokens": 10, "completion_tokens": 5,
            "retry": False, "auth_header_saved": False}
        write_once(self.run_dir / "responses" / f"{request_id}.meta.json", canonical({
            **terminal, "raw_response_path": f"responses/{request_id}.bin"}) + b"\n")
        append_jsonl(self.run_dir / "attempts.jsonl", {"event": "attempt_started", "request_id": request_id,
            "request_sha256": request_sha, "retry": False, "auth_header_saved": False})
        append_jsonl(self.run_dir / "attempts.jsonl", terminal)
        return action, {"request_sha256": request_sha, "prompt_sha256": sha(canonical(messages)),
            "response_sha256": response_sha, "finish_reason": finish, "prompt_tokens": 10,
            "completion_tokens": 5}


@pytest.fixture
def frozen_inputs():
    _base, scenarios, splits, positive = offline.load_documents()
    families = {row["scenario_family_id"]: row for row in scenarios["families"]}
    return splits["groups"][0], families, positive


@pytest.mark.parametrize("interface", ["strict_function_calling", "json_object_fallback"])
def test_gate_auditor_replays_raw_actions_and_settlement(tmp_path, monkeypatch, frozen_inputs, interface):
    group, families, positive = frozen_inputs
    out = tmp_path / "agent"
    monkeypatch.setattr(runner, "OUT", out)
    client = SyntheticDeepSeekTrace(out, interface=interface)
    episode = runner.execute_group(group, families[group["scenario_family_id"]], positive,
                                   client, interface)
    assert episode["terminal_status"] == "COMPLETED"
    result = audit_episode(ROOT, out, episode, interface=interface,
                           family=families[group["scenario_family_id"]], group=group, positive=positive)
    assert result["status"] == "PASS"
    assert result["raw_request_count"] == 11
    assert result["proposal_eligible"] is True

    tampered = json.loads(json.dumps(episode))
    tampered["researcher_B"]["settlement"]["public_welfare"] += 1
    with pytest.raises(AuditFailure, match="settlement"):
        audit_episode(ROOT, out, tampered, interface=interface,
                      family=families[group["scenario_family_id"]], group=group, positive=positive)


def test_full_group_uses_real_client_over_injected_fake_transport(tmp_path, monkeypatch, frozen_inputs):
    group, families, positive = frozen_inputs
    out = tmp_path / "agent"
    monkeypatch.setattr(runner, "OUT", out)

    def fake_http(_endpoint, body, _api_key, _timeout):
        request = json.loads(body)
        function = request["tools"][0]["function"]["name"]
        user = request["messages"][1]["content"]
        if function == "submit_message":
            observation = json.loads(user.split("Observation data (JSON):\n", 1)[1])
            args = ({"action": "send_message", "text": "A=T3, B=T2, C=T1"}
                    if observation["agent_id"] == "A" else {"action": "no_message", "text": ""})
        elif function == "submit_ballot":
            args = {"assignment": {"A": "T1", "B": "T2", "C": "T3"}}
        else:
            args = {"choice": "T1"}
        response = {"id": "fake-http-response", "model": "deepseek-flash",
            "system_fingerprint": "fake-http-fingerprint", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "choices": [{"finish_reason": "tool_calls", "message": {"content": None,
                "tool_calls": [{"type": "function", "function": {"name": function,
                    "arguments": json.dumps(args, separators=(",", ":"))}}]}}]}
        return 200, canonical(response), 0.001

    client = DeepSeekClient(run_dir=out, budget_ledger=tmp_path / "global.jsonl", api_key="fake-key",
                            interface="strict_function_calling", transport=fake_http)
    episode = runner.execute_group(group, families[group["scenario_family_id"]], positive,
                                   client, "strict_function_calling")
    assert episode["terminal_status"] == "COMPLETED"
    assert len([r for r in (out / "attempts.jsonl").read_text().splitlines()]) == 22
    result = audit_episode(ROOT, out, episode, interface="strict_function_calling",
                           family=families[group["scenario_family_id"]], group=group, positive=positive)
    assert result["status"] == "PASS"


def test_first_sent_message_is_not_marked_delivered_if_peer_request_fails(tmp_path, monkeypatch, frozen_inputs):
    group, families, positive = frozen_inputs
    out = tmp_path / "agent"
    monkeypatch.setattr(runner, "OUT", out)
    gid = group["split_group_id"]
    client = SyntheticDeepSeekTrace(out, fail_id=f"{gid}-message-B")
    episode = runner.execute_group(group, families[group["scenario_family_id"]], positive,
                                   client, "strict_function_calling")
    assert episode["terminal_status"] == "FAILED"
    assert len(episode["researcher_B"]["messages"]) == 1
    sent = episode["researcher_B"]["messages"][0]
    assert sent["sent"] is True
    assert sent["delivered"] is False
    assert sent["delivery_status"] == "pending_environment_delivery"
    assert episode["researcher_T"]["private_incentive_delivery"]["A"]["context_delivery_confirmed"] is True
    assert episode["researcher_T"]["private_incentive_delivery"]["B"]["context_delivery_confirmed"] is False


def test_auditor_rejects_private_channel_leak_into_C_request(tmp_path, monkeypatch, frozen_inputs):
    group, families, positive = frozen_inputs
    out = tmp_path / "agent"
    monkeypatch.setattr(runner, "OUT", out)
    client = SyntheticDeepSeekTrace(out)
    episode = runner.execute_group(group, families[group["scenario_family_id"]], positive,
                                   client, "strict_function_calling")
    gid = group["split_group_id"]
    path = out / "requests" / f"{gid}-baseline-ballot-C.bin"
    request = json.loads(path.read_bytes())
    request["messages"][1]["content"] += "\nA private message to B: A=T3, B=T2, C=T1"
    path.write_bytes(canonical(request))
    with pytest.raises(AuditFailure, match="request hash mismatch"):
        audit_episode(ROOT, out, episode, interface="strict_function_calling",
                      family=families[group["scenario_family_id"]], group=group, positive=positive)
