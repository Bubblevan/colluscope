from __future__ import annotations

import json
from pathlib import Path

import pytest

from colluscope.deepseek_m4_v1 import (
    DeepSeekClient, DeepSeekRequestError, agent_tool, canonical, monitor_tool,
    parse_completion, request_cost_bound, request_payload, validate_agent_arguments,
    validate_monitor_arguments,
)
from scripts.run_deepseek_first_pilot import _strict_rejection


def _response(args: dict, *, model: str = "deepseek-flash", fingerprint: str = "fp1",
              finish: str = "tool_calls", tool_name: str = "submit_message",
              calls: list | None = None, content=None) -> bytes:
    tool_calls = calls if calls is not None else [{
        "id": "call-1", "type": "function",
        "function": {"name": tool_name, "arguments": json.dumps(args, separators=(",", ":"))},
    }]
    return json.dumps({
        "id": "resp-1", "model": model, "system_fingerprint": fingerprint,
        "choices": [{"finish_reason": finish, "message": {
            "role": "assistant", "content": content, "tool_calls": tool_calls}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 15},
    }).encode()


def _client(tmp_path: Path, transport):
    return DeepSeekClient(run_dir=tmp_path / "run",
        budget_ledger=tmp_path / "global.jsonl", api_key="test-secret",
        interface="strict_function_calling", transport=transport)


def test_strict_message_forces_one_tool_and_accepts_no_message():
    name, schema = agent_tool("message")
    body = request_payload(interface="strict_function_calling",
        messages=[{"role": "user", "content": "choose"}], tool_name=name, schema=schema)
    assert body["thinking"] == {"type": "disabled"}
    assert body["tool_choice"] == {"type": "function", "function": {"name": "submit_message"}}
    assert body["tools"][0]["function"]["strict"] is True
    args, finish = parse_completion(json.loads(_response(
        {"action": "no_message", "text": ""})), interface="strict_function_calling",
        tool_name=name, schema=schema)
    assert args == {"action": "no_message", "text": ""}
    assert validate_agent_arguments("message", args) == {"type": "no_message"}
    assert finish == "tool_calls"


@pytest.mark.parametrize("response,expected", [
    (_response({"action": "send_message", "text": "hello"}, finish="stop"), "NO_FORCED_TOOL_CALL"),
    (_response({"action": "no_message", "text": ""}, calls=[]), "TOOL_CALL_COUNT"),
    (_response({"action": "no_message", "text": ""}, content="action"), "FREE_TEXT_ACTION"),
    (_response({"action": "no_message", "text": ""}, tool_name="wrong"), "TOOL_NAME_MISMATCH"),
])
def test_strict_parser_rejects_non_contract_responses(response, expected):
    name, schema = agent_tool("message")
    with pytest.raises(DeepSeekRequestError) as caught:
        parse_completion(json.loads(response), interface="strict_function_calling",
                         tool_name=name, schema=schema)
    assert caught.value.status == expected


def test_duplicate_keys_and_invalid_ballot_are_not_repaired():
    name, schema = agent_tool("message")
    response = json.loads(_response({"action": "no_message", "text": ""}))
    response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = (
        '{"action":"no_message","action":"send_message","text":""}')
    with pytest.raises(DeepSeekRequestError) as caught:
        parse_completion(response, interface="strict_function_calling", tool_name=name, schema=schema)
    assert caught.value.status == "DUPLICATE_JSON_KEY"
    with pytest.raises(DeepSeekRequestError) as caught:
        validate_agent_arguments("ballot", {"assignment": {"A": "T1", "B": "T1", "C": "T3"}})
    assert caught.value.status == "INVALID_TOOL_ARGUMENTS"


def test_monitor_schema_is_atomic_and_references_are_not_silently_filtered():
    name, schema = monitor_tool(["supported", "not_supported", "uncertain"])
    args = {"label": "supported", "evidence_refs": ["M01"]}
    assert validate_monitor_arguments("explicit_sequence", ["supported", "not_supported", "uncertain"], args) == args
    with pytest.raises(DeepSeekRequestError):
        validate_monitor_arguments("explicit_sequence", ["supported", "not_supported", "uncertain"],
                                   {"label": "present", "evidence_refs": []})


def test_json_fallback_requires_stop_and_valid_json_object():
    schema = {"type": "object", "required": ["choice"], "additionalProperties": False,
              "properties": {"choice": {"type": "string", "enum": ["T1", "T2"]}}}
    response = {"choices": [{"finish_reason": "stop", "message": {
        "content": '{"choice":"T2"}', "tool_calls": []}}]}
    args, _ = parse_completion(response, interface="json_object_fallback",
                               tool_name="submit_choice", schema=schema)
    assert args == {"choice": "T2"}
    response["choices"][0]["finish_reason"] = "length"
    with pytest.raises(DeepSeekRequestError) as caught:
        parse_completion(response, interface="json_object_fallback",
                         tool_name="submit_choice", schema=schema)
    assert caught.value.status == "NONTERMINAL_JSON_OUTPUT"


def test_global_client_records_raw_bytes_and_never_persists_auth(tmp_path):
    raw = _response({"action": "no_message", "text": ""})
    calls = []
    client = _client(tmp_path, lambda endpoint, body, key, timeout:
                     (calls.append((endpoint, body, key)) or (200, raw, 0.01)))
    name, schema = agent_tool("message")
    action, receipt = client.call(request_id="test-action", role="agent",
        messages=[{"role": "user", "content": "probe"}], tool_name=name, schema=schema,
        semantic=lambda value: validate_agent_arguments("message", value))
    assert action == {"type": "no_message"}
    assert receipt["prompt_tokens"] == 100
    assert len(calls) == 1
    assert calls[0][0] == "https://api.deepseek.com/beta/chat/completions"
    for path in (tmp_path / "run").rglob("*"):
        if path.is_file():
            assert b"test-secret" not in path.read_bytes()
            assert b"Authorization" not in path.read_bytes()
    assert len((tmp_path / "global.jsonl").read_text().splitlines()) == 2


def test_http_failure_is_terminal_and_never_retried(tmp_path):
    calls = []
    client = _client(tmp_path, lambda *args: (calls.append(1) or (500, b'{"error":"x"}', 0.01)))
    name, schema = agent_tool("message")
    with pytest.raises(DeepSeekRequestError) as caught:
        client.call(request_id="http-500", role="agent", messages=[{"role": "user", "content": "x"}],
            tool_name=name, schema=schema, semantic=lambda value: value)
    assert caught.value.status == "HTTP_500"
    assert len(calls) == 1
    attempts = (tmp_path / "run" / "attempts.jsonl").read_text().splitlines()
    assert len(attempts) == 2 and '"retry":false' in attempts[0]
    assert (tmp_path / "run" / "responses" / "http-500.bin").read_bytes() == b'{"error":"x"}'


def test_ambiguous_timeout_is_not_resent_on_resume(tmp_path):
    calls = []
    def timeout(*args):
        calls.append(1)
        raise TimeoutError("connection timed out after dispatch")
    client = _client(tmp_path, timeout)
    name, schema = agent_tool("message")
    call = lambda: client.call(request_id="uncertain", role="agent",
        messages=[{"role": "user", "content": "x"}], tool_name=name, schema=schema,
        semantic=lambda value: value)
    with pytest.raises(DeepSeekRequestError) as caught:
        call()
    assert caught.value.status == "INTERRUPTED_UNKNOWN"
    with pytest.raises(DeepSeekRequestError) as caught:
        call()
    assert caught.value.status == "UNKNOWN_OR_FAILED_PRIOR_ATTEMPT"
    assert len(calls) == 1


def test_provider_identity_drift_stops_without_retry(tmp_path):
    calls = []
    def transport(_endpoint, _body, _key, _timeout):
        calls.append(1)
        return 200, _response({"action": "no_message", "text": ""},
                              fingerprint="fp1" if len(calls) == 1 else "fp2"), 0.01
    client = _client(tmp_path, transport)
    name, schema = agent_tool("message")
    for request_id in ("identity-1", "identity-2"):
        if request_id == "identity-1":
            client.call(request_id=request_id, role="agent", messages=[{"role": "user", "content": "x"}],
                tool_name=name, schema=schema, semantic=lambda value: validate_agent_arguments("message", value))
        else:
            with pytest.raises(DeepSeekRequestError) as caught:
                client.call(request_id=request_id, role="agent", messages=[{"role": "user", "content": "x"}],
                    tool_name=name, schema=schema, semantic=lambda value: validate_agent_arguments("message", value))
            assert caught.value.status == "PROVIDER_IDENTITY_DRIFT"
    assert len(calls) == 2


def test_conservative_reservation_fits_900_request_cap_at_per_request_bound():
    _, reserve = request_cost_bound(b"x" * 7372, 512)
    assert reserve * 900 <= 5


def test_per_run_request_cap_stops_before_second_transport_attempt(tmp_path):
    calls = []
    client = _client(tmp_path, lambda *args: (calls.append(1) or
        (200, _response({"action": "no_message", "text": ""}), 0.01)))
    name, schema = agent_tool("message")
    client.call(request_id="capped-1", role="agent", messages=[{"role": "user", "content": "x"}],
        tool_name=name, schema=schema, semantic=lambda value: validate_agent_arguments("message", value),
        run_request_limit=1)
    with pytest.raises(DeepSeekRequestError) as caught:
        client.call(request_id="capped-2", role="agent", messages=[{"role": "user", "content": "y"}],
            tool_name=name, schema=schema, semantic=lambda value: validate_agent_arguments("message", value),
            run_request_limit=1)
    assert caught.value.status == "RUN_REQUEST_CAP"
    assert caught.value.fatal is True
    assert len(calls) == 1


@pytest.mark.parametrize("error,expected", [
    ({"message": "Strict function calling is not supported for this endpoint"}, True),
    ({"message": "invalid schema: additionalProperties must be false"}, False),
    ({"message": "unsupported model"}, False),
    ({"message": "tool_choice is not supported"}, True),
])
def test_json_fallback_requires_explicit_strict_capability_rejection(tmp_path, error, expected):
    run_dir = tmp_path / "pilot-run"
    (run_dir / "responses").mkdir(parents=True)
    (run_dir / "responses" / "request-1.bin").write_text(json.dumps({"error": error}), encoding="utf-8")
    client = type("Client", (), {"run_dir": run_dir})()
    exc = DeepSeekRequestError("HTTP_400", "provider rejected request")
    assert _strict_rejection(client, "request-1", exc) is expected
