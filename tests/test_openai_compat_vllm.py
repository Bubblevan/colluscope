from __future__ import annotations

import json
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from colluscope.m1_runtime import (AgentRequest, RequestAdapter, RequestBudget, RequestFailure,
                                   load_runtime_config, run_episode)
from colluscope.openai_compat_vllm import (EngineeringPreflightBudget, LocalVLLMBackend,
                                           VLLMBackendConfig, load_vllm_backend_config)


ROOT = Path(__file__).resolve().parents[1]
OFFLINE_CONFIG = load_runtime_config(ROOT / "configs" / "m1-r-offline-v2.toml")


class FakeCounter:
    tokenizer_id = "test/tokenizer"
    tokenizer_revision = "b" * 40
    tokenizer_sha256 = "c" * 64
    chat_template_sha256 = "d" * 64

    def __init__(self, tokens: int = 47):
        self.tokens = tokens
        self.messages = []

    def count_chat_tokens(self, messages):
        self.messages.append(messages)
        return self.tokens


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=-1):
        return self.payload if limit < 0 else self.payload[:limit]


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        payload = result if isinstance(result, bytes) else json.dumps(result).encode("utf-8")
        return FakeResponse(payload)


def valid_config(**changes):
    config = VLLMBackendConfig(
        model_calls_enabled=True, max_api_spend_usd=0.0,
        base_url="http://127.0.0.1:8000/v1", model_id="test/model",
        model_revision="a" * 40, server_version="0.10.0-test",
        tokenizer_id=FakeCounter.tokenizer_id, tokenizer_revision=FakeCounter.tokenizer_revision,
        tokenizer_sha256=FakeCounter.tokenizer_sha256,
        chat_template_sha256=FakeCounter.chat_template_sha256, context_length=4096,
        input_budget_tokens=3072,
        thinking_mode="disabled", thinking_mode_parameter="chat_template_kwargs.enable_thinking",
        temperature=0.7, top_p=0.8, top_k=20, message_max_output_tokens=512,
        ballot_max_output_tokens=256, timeout_seconds=19,
        max_attempts_per_request=2, max_logical_requests=95, max_total_attempts=190)
    return replace(config, **changes)


def request_for(config, request_id="req-test", prompt=None, action_kind="ballot", generation_seed=72):
    schema_file = "communication.schema.json" if action_kind == "message" else "ballot.schema.json"
    schema = (ROOT / "prompts" / "m1-p0-v2" / schema_file).read_text(encoding="utf-8")
    if prompt is None:
        prompt = "system instructions\n\nuser observation\n" + schema
    return AgentRequest(request_id, action_kind, "A", config.model_id, config.sampling,
                        17, "e" * 64, prompt, generation_seed)


def completion(text, finish_reason="stop"):
    return {"id": "cmpl-test", "model": "test/model", "choices": [
        {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 47, "completion_tokens": 19, "total_tokens": 66}}


def test_adapter_records_exact_local_request_actual_usage_and_role_mapping():
    settings = valid_config()
    opener = FakeOpener([completion('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}')])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 2, 2))
    raw = adapter.invoke(request_for(settings))
    assert raw.startswith('{"type":"ballot"')
    sent, timeout = opener.calls[0]
    payload = json.loads(sent.data)
    assert timeout == 17  # transport-level deadline, not an advisory field
    assert sent.full_url == "http://127.0.0.1:8000/v1/chat/completions"
    assert sent.get_method() == "POST"
    assert sent.get_header("Authorization") is None
    schema_text = (ROOT / "prompts" / "m1-p0-v2" / "ballot.schema.json").read_text(encoding="utf-8")
    expected_schema = json.loads(schema_text)
    assert payload == {
        "model": "test/model",
        "messages": [{"role": "system", "content": "system instructions"},
                     {"role": "user", "content": "user observation\n" + schema_text}],
        "temperature": 0.7, "top_p": 0.8, "top_k": 20, "seed": 72,
        "max_tokens": 256, "stream": False,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "m1_p0_ballot_action", "schema": expected_schema}},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    record = adapter.records[0]
    assert record["usage"] == {"prompt_tokens": 47, "completion_tokens": 19, "total_tokens": 66}
    assert record["backend_response_metadata"]["finish_reason"] == "stop"
    assert record["transport"]["role_mapping"] == ["system", "user"]
    assert record["transport"]["model_revision"] == "a" * 40
    assert record["transport"]["thinking_mode"] == "disabled"
    assert record["transport"]["generation_seed"] == 72
    assert record["transport"]["action_schema_sha256"]
    assert json.loads(record["transport"]["payload_json"]) == payload
    assert record["backend_response_sha256"]


def test_local_backend_binds_explicit_model_settings_into_v2_episode_runtime():
    settings = valid_config()
    runtime = settings.bind_runtime(OFFLINE_CONFIG)
    assert runtime.model_id == settings.model_id
    assert runtime.sampling == settings.sampling
    assert runtime.timeout_seconds == settings.timeout_seconds
    response = completion('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}')
    opener = FakeOpener([response, response, response])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    budget = RequestBudget(settings.max_logical_requests, settings.max_total_attempts,
                           settings.max_attempts_per_request)
    adapter = RequestAdapter(backend, runtime, budget)
    episode = run_episode(runtime.conditions[0], "seed-0", "fake-backend-episode", runtime, adapter)
    assert episode["B"]["status"] == "COMPLETED"
    assert len(opener.calls) == budget.logical_requests == 3
    assert all(json.loads(call[0].data)["model"] == settings.model_id for call in opener.calls)
    assert all(json.loads(call[0].data)["temperature"] == settings.temperature for call in opener.calls)


def test_no_selected_model_or_enabled_config_can_be_loaded_from_template():
    with pytest.raises(PermissionError, match="real model calls are disabled"):
        load_vllm_backend_config(ROOT / "configs" / "m1-p0-vllm-local.template.toml")


def test_local_qwen_inventory_draft_is_explicit_and_default_denied():
    path = ROOT / "configs" / "m1-p0-local-draft.toml"
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    assert raw["model_calls_enabled"] is False
    assert raw["preflight_enabled"] is False
    assert raw["checkpoint"]["path"] == (
        r"E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf")
    assert raw["checkpoint"]["format"] == "GGUF Q4_K_M"
    assert raw["tokenizer"]["sha256"] == "NOT_MEASURED"
    assert raw["budgets"]["full_pilot_logical_requests"] == 95
    assert raw["budgets"]["full_pilot_max_attempts"] == 190
    with pytest.raises(PermissionError, match="real model calls are disabled"):
        load_vllm_backend_config(path)


def test_explicit_real_backend_config_parser_round_trips_all_frozen_fields(tmp_path):
    settings = valid_config()
    path = tmp_path / "explicit-approved-fields.toml"
    path.write_text(f'''model_calls_enabled = true
max_api_spend_usd = 0.0

[backend]
kind = "openai-compatible-vllm"
base_url = "{settings.base_url}"
model_id = "{settings.model_id}"
model_revision = "{settings.model_revision}"
server_version = "{settings.server_version}"
tokenizer_id = "{settings.tokenizer_id}"
tokenizer_revision = "{settings.tokenizer_revision}"
tokenizer_sha256 = "{settings.tokenizer_sha256}"
chat_template_sha256 = "{settings.chat_template_sha256}"
context_length = {settings.context_length}

[thinking]
mode = "{settings.thinking_mode}"
request_parameter = "{settings.thinking_mode_parameter}"

[sampling]
temperature = {settings.temperature}
top_p = {settings.top_p}
top_k = {settings.top_k}
input_budget_tokens = {settings.input_budget_tokens}

[stage_limits]
message_max_output_tokens = {settings.message_max_output_tokens}
ballot_max_output_tokens = {settings.ballot_max_output_tokens}

[limits]
timeout_seconds = {settings.timeout_seconds}
max_attempts_per_request = {settings.max_attempts_per_request}
max_logical_requests = {settings.max_logical_requests}
max_total_attempts = {settings.max_total_attempts}
comprehension_probe_calls = 0
''', encoding="utf-8")
    assert load_vllm_backend_config(path) == settings


def test_remote_endpoint_and_tokenizer_mismatch_fail_before_any_request():
    with pytest.raises(ValueError, match="remote endpoints are forbidden"):
        LocalVLLMBackend(valid_config(base_url="https://example.com/v1"), FakeCounter(), FakeOpener([]))
    with pytest.raises(ValueError, match="token counter identity/hash"):
        LocalVLLMBackend(valid_config(), replace_counter_revision(FakeCounter()), FakeOpener([]))


def replace_counter_revision(counter):
    counter.tokenizer_revision = "f" * 40
    return counter


def test_context_overflow_is_retained_as_failed_attempt_without_http_dispatch():
    settings = valid_config(input_budget_tokens=40)
    opener = FakeOpener([])
    backend = LocalVLLMBackend(settings, FakeCounter(tokens=50), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="input-token budget"):
        adapter.invoke(request_for(settings))
    assert opener.calls == []
    assert adapter.budget.attempts == 1  # conservative reservation before backend validation
    assert adapter.records[0]["status"] == "failed"
    assert "exceeds the frozen input-token budget" in adapter.records[0]["error"]


def test_transport_timeout_uses_bounded_shared_retry_budget():
    settings = valid_config()
    opener = FakeOpener([TimeoutError("simulated socket timeout"), TimeoutError("simulated socket timeout")])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="timeout after 2 attempt"):
        adapter.invoke(request_for(settings))
    assert len(opener.calls) == 2
    assert [row["status"] for row in adapter.records] == ["retryable_failure", "failed"]
    assert adapter.budget.attempts == 2


def test_truncated_finish_reason_is_retained_and_never_retried():
    settings = valid_config()
    content = '{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'
    opener = FakeOpener([completion(content, finish_reason="length")])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="truncated") as error:
        adapter.invoke(request_for(settings))
    assert error.value.raw_response == content
    assert len(opener.calls) == 1
    assert adapter.records[0]["status"] == "truncated_output"
    assert adapter.records[0]["raw_response"] == content
    assert adapter.budget.attempts == 1


def test_malformed_backend_response_body_is_retained_without_retry():
    settings = valid_config()
    opener = FakeOpener([b"{not-json"])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="malformed Chat Completions") as error:
        adapter.invoke(request_for(settings))
    assert error.value.raw_response == "{not-json"
    assert len(opener.calls) == 1
    assert adapter.records[0]["backend_response"] == "{not-json"
    assert adapter.records[0]["backend_response_sha256"]
    assert adapter.records[0]["retryable"] is False


def test_backend_rejects_returned_model_fallback_and_retains_response():
    settings = valid_config()
    response = completion('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}')
    response["model"] = "different/model"
    opener = FakeOpener([response])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="model fallback is forbidden") as error:
        adapter.invoke(request_for(settings))
    assert "different/model" in error.value.raw_response
    assert len(opener.calls) == 1
    assert adapter.records[0]["retryable"] is False
    assert adapter.records[0]["backend_response"] == error.value.raw_response


def test_retryable_server_error_body_is_preserved_and_attempt_stays_bounded():
    import io
    import urllib.error
    settings = valid_config()
    failure = urllib.error.HTTPError("http://127.0.0.1:8000/v1/chat/completions", 503,
                                     "busy", {}, io.BytesIO(b"server busy"))
    valid = completion('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}')
    opener = FakeOpener([failure, valid])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 2, 2))
    adapter.invoke(request_for(settings))
    assert len(opener.calls) == 2
    assert adapter.records[0]["status"] == "retryable_failure"
    assert adapter.records[0]["backend_response"] == "server busy"
    assert adapter.records[1]["status"] == "response_returned"
    assert adapter.budget.attempts == 2


def test_preflight_is_explicit_get_only_and_does_not_attest_model_revision():
    settings = valid_config()
    opener = FakeOpener([{"version": settings.server_version}, {"data": [{"id": settings.model_id}]}])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    budget = EngineeringPreflightBudget(enabled=True)
    result = backend.preflight(budget)
    assert [call[0].get_method() for call in opener.calls] == ["GET", "GET"]
    assert [call[0].full_url for call in opener.calls] == [
        "http://127.0.0.1:8000/version", "http://127.0.0.1:8000/v1/models"]
    assert result["model_revision_verification"].startswith("configured immutable revision is not attested")
    assert result["model_completion_calls"] == result["external_api_calls"] == 0
    assert result["preflight_logical_requests"] == result["preflight_attempts"] == 2


def test_preflight_budget_is_default_denied_and_hard_capped():
    settings = valid_config()
    opener = FakeOpener([{"version": settings.server_version}, {"data": [{"id": settings.model_id}]}])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    with pytest.raises(PermissionError, match="preflight budget is disabled"):
        backend.preflight(EngineeringPreflightBudget())
    assert opener.calls == []
    with pytest.raises(ValueError, match="cannot exceed 6 logical / 12 attempts"):
        EngineeringPreflightBudget(enabled=True, max_logical_requests=7)
    budget = EngineeringPreflightBudget(enabled=True, max_logical_requests=1, max_attempts=2)
    budget.reserve("one")
    budget.reserve("one", attempt=2)
    with pytest.raises(RuntimeError, match="logical-request ceiling"):
        budget.reserve("two")
    assert (budget.attempts, len(budget.logical_ids)) == (2, 1)


def test_message_and_ballot_requests_use_distinct_token_caps_and_their_exact_schemas():
    settings = valid_config()
    message_opener = FakeOpener([completion('{"type":"no_message"}')])
    message_backend = LocalVLLMBackend(settings, FakeCounter(), message_opener)
    message_backend.complete(request_for(settings, action_kind="message"), 17)
    message_payload = json.loads(message_opener.calls[0][0].data)
    assert message_payload["max_tokens"] == 512
    message_schema = json.loads((ROOT / "prompts" / "m1-p0-v2" / "communication.schema.json").read_text(encoding="utf-8"))
    assert message_schema["oneOf"]
    assert message_payload["response_format"]["json_schema"]["schema"] == message_schema

    ballot_opener = FakeOpener([completion('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}')])
    ballot_backend = LocalVLLMBackend(settings, FakeCounter(), ballot_opener)
    ballot_backend.complete(request_for(settings, action_kind="ballot"), 17)
    ballot_payload = json.loads(ballot_opener.calls[0][0].data)
    assert ballot_payload["max_tokens"] == 256
    assert ballot_payload["response_format"]["json_schema"]["schema"]["type"] == "object"


def test_api_schema_cannot_be_added_if_it_differs_from_the_prompt_schema():
    settings = valid_config()
    opener = FakeOpener([])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    request = request_for(settings, prompt="system instructions\n\nuser observation without schema")
    with pytest.raises(ValueError, match="does not contain the exact API action schema"):
        backend.complete(request, 17)
    assert opener.calls == []


def test_request_budget_rejects_extra_model_call_before_transport():
    settings = valid_config()
    opener = FakeOpener([completion('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}')])
    backend = LocalVLLMBackend(settings, FakeCounter(), opener)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, RequestBudget(1, 1, 2))
    adapter.invoke(request_for(settings, "req-one"))
    with pytest.raises(RequestFailure, match="logical request hard limit"):
        adapter.invoke(request_for(settings, "req-two"))
    assert len(opener.calls) == 1
    assert adapter.budget.logical_requests == 1
    assert adapter.budget.attempts == 1
