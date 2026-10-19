from __future__ import annotations

import hashlib
import io
import json
import urllib.error
from dataclasses import replace
from pathlib import Path

import pytest

from colluscope.m1_runtime import (AgentRequest, RequestAdapter,
                                   RequestBudget, RequestFailure, load_runtime_config, run_episode)
from colluscope.openai_compat_llamacpp import (LlamaCppPreflightBudget, LocalLlamaCppBackend,
                                               PREFLIGHT_NO_MESSAGE_INSTRUCTION,
                                               PREFLIGHT_SEND_MESSAGE_INSTRUCTION,
                                               llama_runtime_bundle_identity,
                                               load_llamacpp_backend_config, llama_server_command)


ROOT = Path(__file__).resolve().parents[1]
BACKEND_CONFIG_PATH = ROOT / "configs" / "m1-p0-llama-local-draft.toml"
RUNTIME_CONFIG = load_runtime_config(ROOT / "configs" / "m1-r-offline-v2.toml")
ACTION_ROOT = ROOT / "prompts" / "m1-p0-v2"
BASE = load_llamacpp_backend_config(BACKEND_CONFIG_PATH)


class FakeCounter:
    def __init__(self, config, *, token_count=47, template="test-template"):
        self.artifact_sha256 = config.artifact_sha256
        self.tokenizer_id = config.tokenizer_id
        self.tokenizer_revision = config.tokenizer_revision
        self.tokenizer_sha256 = config.tokenizer_sha256
        self.chat_template_sha256 = config.chat_template_sha256
        self.tokenizers_library_version = config.tokenizers_library_version
        self.jinja2_library_version = config.jinja2_library_version
        self.token_count = token_count
        self.template = template

    def render_chat(self, messages, *, enable_thinking=False):
        assert enable_thinking is False
        return self.template + "\n" + json.dumps(messages, ensure_ascii=False, separators=(",", ":"))

    def encode_chat(self, messages, *, enable_thinking=False):
        self.render_chat(messages, enable_thinking=enable_thinking)
        return list(range(self.token_count))


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit=-1):
        return self.body if limit < 0 else self.body[:limit]


class FakeOpener:
    """A deterministic HTTP boundary. It never opens a socket."""
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        body = result if isinstance(result, bytes) else json.dumps(result).encode("utf-8")
        return FakeResponse(body)


def config_for(*, live=False, preflight=False, **changes):
    values = {"model_calls_enabled": live,
              "full_pilot_approval_id": "FAKE-TEST-ONLY" if live else "",
              "preflight_enabled": preflight,
              "preflight_approval_id": "FAKE-PREFLIGHT-TEST-ONLY" if preflight else ""}
    values.update(changes)
    return replace(BASE, **values)


def counter_for(config, *, token_count=47, template="test-template"):
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    if template_hash != config.chat_template_sha256:
        config = replace(config, chat_template_sha256=template_hash)
    return config, FakeCounter(config, token_count=token_count, template=template)


def request_for(config, *, request_id="req-1", action_kind="ballot", content=None, timeout=17):
    filename = "communication.schema.json" if action_kind == "message" else "ballot.schema.json"
    schema = (ACTION_ROOT / filename).read_text(encoding="utf-8")
    if content is None:
        content = "task observation"
    prompt = f"frozen system instructions\n\n{content}\n{schema}"
    return AgentRequest(request_id, action_kind, "A", config.model_id, config.sampling,
                        timeout, "e" * 64, prompt, 72)


def _oneof_disjoint_by_required_type_const(schema):
    branches = schema.get("oneOf")
    if not isinstance(branches, list) or len(branches) < 2:
        return False
    constants = []
    for branch in branches:
        properties = branch.get("properties", {})
        if (branch.get("type") != "object"
                or "type" not in branch.get("required", [])
                or not isinstance(properties.get("type"), dict)
                or "const" not in properties["type"]):
            return False
        constants.append(properties["type"]["const"])
    return len(constants) == len(set(constants))


def test_frozen_communication_oneof_branches_are_disjoint_and_overlap_counterexample_fails():
    schema = json.loads((ACTION_ROOT / "communication.schema.json").read_text(encoding="utf-8"))
    assert _oneof_disjoint_by_required_type_const(schema)
    assert {branch["properties"]["type"]["const"] for branch in schema["oneOf"]} == {
        "send_message", "no_message"
    }

    overlapping = json.loads(json.dumps(schema))
    overlapping["oneOf"][1]["properties"]["type"]["const"] = "send_message"
    assert not _oneof_disjoint_by_required_type_const(overlapping)


def preflight_request_for(config, *, request_id, action_kind, requested_action=None):
    observation = {}
    if requested_action == "send_message":
        observation["preflight_probe_instruction"] = PREFLIGHT_SEND_MESSAGE_INSTRUCTION
    elif requested_action == "no_message":
        observation["preflight_probe_instruction"] = PREFLIGHT_NO_MESSAGE_INSTRUCTION
    schema_name = "communication.schema.json" if action_kind == "message" else "ballot.schema.json"
    template_name = "message.txt" if action_kind == "message" else "ballot.txt"
    system = (ACTION_ROOT / "system.txt").read_text(encoding="utf-8").strip()
    template = (ACTION_ROOT / template_name).read_text(encoding="utf-8").rstrip()
    schema = (ACTION_ROOT / schema_name).read_text(encoding="utf-8")
    observation_json = json.dumps(observation, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    prompt = f"{system}\n\n" + template.replace("{{action_schema}}", schema).replace(
        "{{observation_json}}", observation_json)
    return AgentRequest(request_id, action_kind, "A", config.model_id, config.sampling,
                        17, hashlib.sha256(observation_json.encode("utf-8")).hexdigest(), prompt, 72)


def response(text, *, model=None, prompt_tokens=47, reasoning=None):
    message = {"role": "assistant", "content": text}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return {"id": "offline-fake", "model": model or BASE.model_id,
            "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": 12,
                      "total_tokens": prompt_tokens + 12},
            "timings": {"prompt_ms": 1}}


def http_error(code, body):
    return urllib.error.HTTPError("http://127.0.0.1:8080/v1/chat/completions", code,
                                  "fake response", {}, io.BytesIO(body.encode("utf-8")))


def fake_server_bundle(config, tmp_path):
    package = tmp_path / "llama-runtime"
    package.mkdir()
    launcher = package / "llama-server.exe"
    launcher.write_bytes(b"fake launcher")
    (package / "llama-server-impl.dll").write_bytes(b"fake runtime")
    identity = llama_runtime_bundle_identity(launcher)
    return replace(config, server_binary_path=str(launcher),
                   runtime_bundle_sha256=identity["sha256"]), identity


def fake_preflight_setup_responses(settings, counter, ballot):
    messages = [{"role": "system", "content": ballot.prompt.split("\n\n", 1)[0]},
                {"role": "user", "content": ballot.prompt.split("\n\n", 1)[1]}]
    rendered = counter.render_chat(messages, enable_thinking=False)
    token_ids = counter.encode_chat(messages, enable_thinking=False)
    props = {"default_generation_settings": {"n_ctx": 4096,
             "params": {"temperature": 0.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0,
                        "samplers": ["top_k", "top_p", "min_p", "temperature"]}},
             "chat_template": counter.template, "model_path": settings.artifact_path,
             "build_info": settings.server_build_info, "total_slots": 1}
    return [props, {"prompt": rendered}, {"tokens": token_ids}]


def test_default_config_is_denied_and_launch_command_is_only_a_candidate():
    settings = load_llamacpp_backend_config(BACKEND_CONFIG_PATH)
    command = llama_server_command(settings)
    assert settings.model_calls_enabled is False
    assert settings.preflight_enabled is False
    assert settings.full_pilot_approval_id == ""
    assert command[0] == settings.server_binary_path
    assert "--offline" in command and "--no-warmup" in command
    assert "--ctx-size" in command and command[command.index("--ctx-size") + 1] == "4096"
    assert settings.max_logical_requests == 95 and settings.max_total_attempts == 190

    settings, counter = counter_for(settings)
    opener = FakeOpener([])
    backend = LocalLlamaCppBackend(settings, counter, opener)
    with pytest.raises(PermissionError, match="disabled"):
        backend.complete(request_for(settings), timeout_seconds=17)
    assert opener.calls == []


def test_live_config_flags_require_separate_nonempty_approval_ids(tmp_path):
    config_text = BACKEND_CONFIG_PATH.read_text(encoding="utf-8")
    for enabled_line, message in (("preflight_enabled = false", "preflight ID"),
                                  ("model_calls_enabled = false", "pilot ID")):
        path = tmp_path / (message.replace(" ", "-") + ".toml")
        path.write_text(config_text.replace(enabled_line, enabled_line.replace("false", "true")),
                        encoding="utf-8")
        with pytest.raises(PermissionError, match=message):
            load_llamacpp_backend_config(path)


def test_direct_llamacpp_schema_envelope_exact_request_and_usage_are_recorded():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    raw = '{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'
    opener = FakeOpener([response(raw)])
    backend = LocalLlamaCppBackend(settings, counter, opener)
    adapter = RequestAdapter(backend, RUNTIME_CONFIG, RequestBudget(1, 2, 2))
    assert adapter.invoke(request_for(settings)) == raw

    sent, timeout = opener.calls[0]
    payload = json.loads(sent.data)
    expected_schema = json.loads((ACTION_ROOT / "ballot.schema.json").read_text(encoding="utf-8"))
    assert sent.full_url == "http://127.0.0.1:8080/v1/chat/completions"
    assert sent.get_method() == "POST" and sent.get_header("Authorization") is None
    assert timeout == 17
    assert payload["response_format"] == {"type": "json_schema", "schema": expected_schema}
    assert "json_schema" not in payload["response_format"]
    assert payload["cache_prompt"] is False
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["model"] == settings.model_id and payload["seed"] == 72
    assert payload["max_tokens"] == settings.ballot_max_output_tokens
    assert payload["samplers"] == list(settings.sampler_chain)
    assert adapter.records[0]["usage"]["prompt_tokens"] == 47
    assert adapter.records[0]["transport"]["payload_sha256"]
    assert adapter.records[0]["backend_response_sha256"]


def test_schema_rejection_is_retained_and_never_falls_back_or_retries():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    opener = FakeOpener([http_error(400, '{"error":"oneOf unsupported"}')])
    backend = LocalLlamaCppBackend(settings, counter, opener)
    adapter = RequestAdapter(backend, RUNTIME_CONFIG, RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="HTTP 400") as failure:
        adapter.invoke(request_for(settings))
    assert failure.value.raw_response == '{"error":"oneOf unsupported"}'
    assert len(opener.calls) == adapter.budget.attempts == 1
    assert adapter.records[0]["status"] == "failed"
    assert "oneOf unsupported" in adapter.records[0]["backend_response"]


def test_transient_http_error_is_bounded_and_both_raw_failures_are_retained():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    opener = FakeOpener([http_error(503, "busy-1"), http_error(503, "busy-2")])
    backend = LocalLlamaCppBackend(settings, counter, opener)
    adapter = RequestAdapter(backend, RUNTIME_CONFIG, RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="transport after 2 attempt"):
        adapter.invoke(request_for(settings))
    assert len(opener.calls) == adapter.budget.attempts == 2
    assert [row["status"] for row in adapter.records] == ["retryable_failure", "failed"]
    assert [row["backend_response"] for row in adapter.records] == ["busy-1", "busy-2"]


def test_timeout_is_retried_only_to_the_shared_two_attempt_limit():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    opener = FakeOpener([TimeoutError("simulated timeout 1"), TimeoutError("simulated timeout 2")])
    adapter = RequestAdapter(LocalLlamaCppBackend(settings, counter, opener), RUNTIME_CONFIG,
                             RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="timeout after 2 attempt"):
        adapter.invoke(request_for(settings))
    assert len(opener.calls) == adapter.budget.attempts == 2
    assert [row["status"] for row in adapter.records] == ["retryable_failure", "failed"]


@pytest.mark.parametrize("override, message", [
    ({"model": "unexpected-fallback"}, "different model alias"),
    ({"usage": None}, "missing usage metadata"),
    ({"prompt_tokens": 46}, "differs from server prompt_tokens"),
    ({"reasoning": "hidden chain of thought"}, "reasoning content"),
])
def test_backend_rejects_model_usage_and_reasoning_drift(override, message):
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    payload = response('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}',
                       prompt_tokens=override.get("prompt_tokens", 47),
                       model=override.get("model"), reasoning=override.get("reasoning"))
    if "usage" in override:
        payload["usage"] = override["usage"]
    opener = FakeOpener([payload])
    adapter = RequestAdapter(LocalLlamaCppBackend(settings, counter, opener), RUNTIME_CONFIG,
                             RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match=message):
        adapter.invoke(request_for(settings))
    assert len(opener.calls) == 1
    assert adapter.records[0]["status"] == "failed"
    assert adapter.records[0]["backend_response"]


def test_malformed_assistant_action_fails_explicitly_and_is_never_repaired():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    raw = '{"type":"ballot","assignment":{"A":"T1"}}'
    opener = FakeOpener([response(raw)])
    runtime = settings.bind_runtime(RUNTIME_CONFIG)
    adapter = RequestAdapter(LocalLlamaCppBackend(settings, counter, opener), runtime,
                             RequestBudget(3, 6, 2))
    episode = run_episode(runtime.conditions[0], "seed-0", "malformed-action", runtime, adapter)
    assert episode["B"]["status"] == "FAILED"
    assert episode["failure"]["failure_kind"] == "invalid_output"
    assert episode["failure"]["raw_response"] == raw
    assert episode["B"]["ballots"][-1]["sealed"] is False
    assert len(opener.calls) == adapter.budget.attempts == 1
    assert adapter.records[0]["status"] == "response_returned"


def test_fake_http_send_message_flows_through_runtime_and_is_delivered_only_to_peer():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    runtime = settings.bind_runtime(RUNTIME_CONFIG)
    condition = next(row for row in runtime.conditions
                     if row["id"] == "coalition_incentive_private_chat")
    sentinel = "FAKE-TRANSPORT-PEER-ONLY-SENTINEL"
    ballot = '{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'
    opener = FakeOpener([
        response(json.dumps({"type": "send_message", "text": sentinel})),
        response('{"type":"no_message"}'),
        response(ballot), response(ballot), response(ballot),
    ])
    adapter = RequestAdapter(LocalLlamaCppBackend(settings, counter, opener), runtime,
                             RequestBudget(5, 10, 2))

    episode = run_episode(condition, "seed-0", "fake-http-message-route", runtime, adapter,
                          auditor_can_see_private_messages=True)

    assert episode["B"]["status"] == "COMPLETED"
    sent = episode["B"]["peer_messages"][0]
    assert sent["sender"] == "A" and sent["recipient"] == "B"
    assert sent["sent"] is True and sent["delivered"] is True
    assert sent["text"] == sentinel
    observations = {row["agent_id"] + ":" + row["stage"]: row["observation"]
                    for row in episode["observations"]}
    assert observations["A:ballot"]["your_previous_message_action"] == {
        "type": "send_message", "text": sentinel}
    assert sentinel in json.dumps(observations["B:ballot"], ensure_ascii=False)
    assert sentinel not in json.dumps(observations["C:ballot"], ensure_ascii=False)
    assert all(event["actor"] != "C" for event in episode["E"]["events"]
               if event["type"] == "message")
    assert any(event["type"] == "message" and sentinel in json.dumps(event, ensure_ascii=False)
               for event in episode["E"]["events"])
    assert len(opener.calls) == adapter.budget.attempts == 5
    assert len(adapter.records) == 5


def test_context_limit_fails_before_dispatch_and_retains_attempt_record():
    settings = config_for(live=True)
    settings, counter = counter_for(settings, token_count=4000)
    opener = FakeOpener([])
    adapter = RequestAdapter(LocalLlamaCppBackend(settings, counter, opener), RUNTIME_CONFIG,
                             RequestBudget(1, 2, 2))
    with pytest.raises(RequestFailure, match="input-token budget"):
        adapter.invoke(request_for(settings))
    assert opener.calls == []
    assert adapter.records[0]["status"] == "failed"
    assert adapter.budget.attempts == 1


def test_remote_endpoint_and_mismatched_tokenizer_identity_are_rejected():
    with pytest.raises(ValueError, match="loopback"):
        LocalLlamaCppBackend(config_for(base_url="https://example.com/v1"), FakeCounter(BASE), FakeOpener([]))
    settings = config_for()
    settings, counter = counter_for(settings)
    counter.tokenizer_sha256 = "0" * 64
    with pytest.raises(ValueError, match="tokenizer_sha256"):
        LocalLlamaCppBackend(settings, counter, FakeOpener([]))


def test_transport_rejects_remote_redirect_targets_and_remote_url_before_dispatch():
    settings = config_for()
    settings, counter = counter_for(settings)
    opener = FakeOpener([])
    backend = LocalLlamaCppBackend(settings, counter, opener)
    with pytest.raises(PermissionError, match="frozen local loopback"):
        backend._open("http://example.com/v1/chat/completions", b"{}", 10, "POST")
    assert opener.calls == []

    default_backend = LocalLlamaCppBackend(settings, counter)
    redirect = next(handler for handler in default_backend.opener.handlers
                     if handler.__class__.__name__ == "_NoRedirect")
    request = __import__("urllib.request", fromlist=["Request"]).Request(
        "http://127.0.0.1:8080/v1/chat/completions")
    assert redirect.redirect_request(request, None, 302, "Found", {}, "https://example.com/") is None


def test_preflight_budget_has_independent_hard_caps():
    budget = LlamaCppPreflightBudget(enabled=True)
    for index in range(6):
        budget.reserve(f"read-{index}", 1)
    with pytest.raises(RuntimeError, match="logical-request hard limit"):
        budget.reserve("seventh", 1)
    with pytest.raises(ValueError, match="cannot exceed"):
        LlamaCppPreflightBudget(enabled=True, max_logical_requests=7)

    completions = LlamaCppPreflightBudget(enabled=True)
    for index in range(4):
        completions.reserve(f"completion-{index}", 1, completion=True)
    with pytest.raises(RuntimeError, match="completion hard limit"):
        completions.reserve("fifth-completion", 1, completion=True)


def test_server_runtime_bundle_identity_covers_launcher_and_dlls(tmp_path):
    package = tmp_path / "runtime"
    package.mkdir()
    launcher = package / "llama-server.exe"
    dll = package / "llama-server-impl.dll"
    launcher.write_bytes(b"launcher")
    dll.write_bytes(b"runtime-v1")
    before = llama_runtime_bundle_identity(launcher)
    assert before["file_count"] == 2
    assert {entry["name"] for entry in before["files"]} == {
        "llama-server.exe", "llama-server-impl.dll"}
    dll.write_bytes(b"runtime-v2")
    after = llama_runtime_bundle_identity(launcher)
    assert before["sha256"] != after["sha256"]


def test_fake_preflight_runs_exact_six_request_sequence_and_parses_all_actions(tmp_path):
    template = "frozen fake template"
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    settings = config_for(preflight=True, chat_template_sha256=template_hash)
    settings, bundle = fake_server_bundle(settings, tmp_path)
    counter = FakeCounter(settings, template=template)
    ballot = preflight_request_for(settings, request_id="probe-ballot", action_kind="ballot")
    send = preflight_request_for(settings, request_id="probe-send", action_kind="message",
                                 requested_action="send_message")
    no_message = preflight_request_for(settings, request_id="probe-no-message", action_kind="message",
                                       requested_action="no_message")
    ballot_messages = [{"role": "system", "content": ballot.prompt.split("\n\n", 1)[0]},
                       {"role": "user", "content": ballot.prompt.split("\n\n", 1)[1]}]
    rendered = counter.render_chat(ballot_messages, enable_thinking=False)
    token_ids = counter.encode_chat(ballot_messages, enable_thinking=False)
    props = {"default_generation_settings": {"n_ctx": 4096,
             "params": {"temperature": 0.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0,
                        "samplers": ["top_k", "top_p", "min_p", "temperature"]}},
             "chat_template": template, "model_path": settings.artifact_path,
             "build_info": settings.server_build_info, "total_slots": 1}
    responses = [
        props,
        {"prompt": rendered},
        {"tokens": token_ids},
        response('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'),
        response('{"type":"send_message","text":"Proposal"}'),
        response('{"type":"no_message"}'),
    ]
    opener = FakeOpener(responses)
    events = []
    backend = LocalLlamaCppBackend(settings, counter, opener, preflight_event_hook=events.append)
    budget = LlamaCppPreflightBudget(enabled=True)
    result = backend.preflight(budget, [(ballot, None), (send, "send_message"),
                                        (no_message, "no_message")])
    assert result["status"] == "PASS_INTERFACE"
    assert result["logical_requests"] == len(opener.calls) == 6
    assert result["http_attempts"] == 6
    assert result["model_completion_attempts"] == 3
    assert result["verified_runtime_bundle_sha256"] == bundle["sha256"]
    assert result["verified_actions"] == ["ballot", "send_message", "no_message"]
    assert [call[0].full_url.removeprefix("http://127.0.0.1:8080") for call in opener.calls] == [
        "/props", "/apply-template", "/tokenize", "/v1/chat/completions",
        "/v1/chat/completions", "/v1/chat/completions"]
    assert [event["event"] for event in events if event["event"] in {
        "server_properties_validated", "tokenizer_parity_validated",
        "completion_attempt_started", "completion_attempt_finished"}] == [
        "server_properties_validated", "tokenizer_parity_validated",
        "completion_attempt_started", "completion_attempt_finished",
        "completion_attempt_started", "completion_attempt_finished",
        "completion_attempt_started", "completion_attempt_finished"]
    assert result["protocol_id"] == "m1-p0-interface-v3"
    assert result["schema_transport_status"] == "PASS"
    assert result["status"] == "PASS_INTERFACE"
    assert [row["followed_instruction"] for row in result["action_choice_diagnostics"]] == [True, True, True]


def test_valid_no_message_for_send_probe_is_compliance_diagnostic_not_interface_failure(tmp_path):
    template = "frozen fake template"
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    settings = config_for(preflight=True, chat_template_sha256=template_hash)
    settings, _ = fake_server_bundle(settings, tmp_path)
    counter = FakeCounter(settings, template=template)
    ballot = preflight_request_for(settings, request_id="probe-ballot", action_kind="ballot")
    send = preflight_request_for(settings, request_id="probe-send", action_kind="message",
                                 requested_action="send_message")
    no_message = preflight_request_for(settings, request_id="probe-no-message", action_kind="message",
                                       requested_action="no_message")
    raw_no_message = '{"type":"no_message"}'
    opener = FakeOpener([
        *fake_preflight_setup_responses(
            settings, counter, ballot,
        ),
        response('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'),
        response(raw_no_message),
        response(raw_no_message),
    ])
    budget = LlamaCppPreflightBudget(enabled=True)

    result = LocalLlamaCppBackend(settings, counter, opener).preflight(
        budget, [(ballot, None), (send, "send_message"), (no_message, "no_message")])

    assert result["status"] == "PASS_INTERFACE"
    assert result["schema_transport_status"] == "PASS"
    assert result["verified_actions"] == ["ballot", "no_message", "no_message"]
    assert result["action_choice_diagnostics"] == [
        {"request_id": "probe-ballot", "action_kind": "ballot",
         "requested_action": "ballot", "actual_action": "ballot",
         "followed_instruction": True, "role": "descriptive_instruction_compliance_only"},
        {"request_id": "probe-send", "action_kind": "message",
         "requested_action": "send_message", "actual_action": "no_message",
         "followed_instruction": False, "role": "descriptive_instruction_compliance_only"},
        {"request_id": "probe-no-message", "action_kind": "message",
         "requested_action": "no_message", "actual_action": "no_message",
         "followed_instruction": True, "role": "descriptive_instruction_compliance_only"},
    ]
    assert result["positive_send_message_model_output"] == "UNVERIFIED"
    assert result["positive_send_message_offline_plumbing"] == "NOT_ASSESSED_BY_LIVE_PREFLIGHT"
    assert len(opener.calls) == budget.attempts == 6
    assert not any(row.get("status") == "failed" for row in budget.records)


def test_preflight_rejects_action_metadata_that_disagrees_with_frozen_prompt_before_http(tmp_path):
    template = "frozen fake template"
    settings = config_for(preflight=True,
                          chat_template_sha256=hashlib.sha256(template.encode()).hexdigest())
    settings, _ = fake_server_bundle(settings, tmp_path)
    counter = FakeCounter(settings, template=template)
    ballot = preflight_request_for(settings, request_id="probe-ballot", action_kind="ballot")
    # The request says no_message, while its independent metadata claims send_message.
    send_request = preflight_request_for(settings, request_id="probe-send", action_kind="message",
                                         requested_action="no_message")
    no_message = preflight_request_for(settings, request_id="probe-no-message", action_kind="message",
                                       requested_action="no_message")
    opener = FakeOpener([])
    budget = LlamaCppPreflightBudget(enabled=True)

    with pytest.raises(ValueError, match="metadata send_message does not match prompt instruction no_message"):
        LocalLlamaCppBackend(settings, counter, opener).preflight(
            budget, [(ballot, None), (send_request, "send_message"), (no_message, "no_message")])

    assert opener.calls == [] and budget.attempts == 0
    assert budget.records[0]["phase"] == "preflight_gate_before_http"


def test_malformed_message_action_still_fails_interface_gate_and_retains_response(tmp_path):
    template = "frozen fake template"
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    settings = config_for(preflight=True, chat_template_sha256=template_hash)
    settings, _ = fake_server_bundle(settings, tmp_path)
    counter = FakeCounter(settings, template=template)
    ballot = preflight_request_for(settings, request_id="probe-ballot", action_kind="ballot")
    send = preflight_request_for(settings, request_id="probe-send", action_kind="message",
                                 requested_action="send_message")
    no_message = preflight_request_for(settings, request_id="probe-no-message", action_kind="message",
                                       requested_action="no_message")
    malformed = '{"type":"no_message","extra":true}'
    opener = FakeOpener([
        *fake_preflight_setup_responses(settings, counter, ballot),
        response('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'),
        response(malformed),
    ])
    budget = LlamaCppPreflightBudget(enabled=True)

    with pytest.raises(RuntimeError, match="strict parser"):
        LocalLlamaCppBackend(settings, counter, opener).preflight(
            budget, [(ballot, None), (send, "send_message"), (no_message, "no_message")])

    assert len(opener.calls) == budget.attempts == 5
    assert budget.records[-1]["status"] == "failed"
    assert budget.records[-1]["raw_response"] == malformed


def test_fake_preflight_continuation_reuses_setup_and_dispatches_only_three_actions(tmp_path):
    template = "frozen fake template"
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    settings = config_for(preflight=True, chat_template_sha256=template_hash)
    settings, bundle = fake_server_bundle(settings, tmp_path)
    counter = FakeCounter(settings, template=template)
    ballot = preflight_request_for(settings, request_id="probe-ballot", action_kind="ballot")
    send = preflight_request_for(settings, request_id="probe-send", action_kind="message",
                                 requested_action="send_message")
    no_message = preflight_request_for(settings, request_id="probe-no-message", action_kind="message",
                                       requested_action="no_message")
    probes = [(ballot, None), (send, "send_message"), (no_message, "no_message")]
    messages = [{"role": "system", "content": ballot.prompt.split("\n\n", 1)[0]},
                {"role": "user", "content": ballot.prompt.split("\n\n", 1)[1]}]
    rendered = counter.render_chat(messages, enable_thinking=False)
    tokens = counter.encode_chat(messages, enable_thinking=False)
    props = {"default_generation_settings": {"n_ctx": 4096,
             "params": {"temperature": 0.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0,
                        "samplers": ["top_k", "top_p", "min_p", "temperature"]}},
             "chat_template": template, "model_path": settings.artifact_path,
             "build_info": settings.server_build_info, "total_slots": 1}
    setup_payloads = {
        "preflight-props": ("GET", "http://127.0.0.1:8080/props", None, props),
        "preflight-template": ("POST", "http://127.0.0.1:8080/apply-template",
                               {"messages": messages, "chat_template_kwargs": {"enable_thinking": False}},
                               {"prompt": rendered}),
        "preflight-tokenize": ("POST", "http://127.0.0.1:8080/tokenize",
                               {"content": rendered, "add_special": False,
                                "parse_special": True, "with_pieces": False},
                               {"tokens": tokens}),
    }
    setup_records = []
    reused_responses = {}
    for request_id, (method, url, payload, response_body) in setup_payloads.items():
        request_body = (json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                        if payload is not None else None)
        raw = json.dumps(response_body, ensure_ascii=False, separators=(",", ":"))
        setup_records.append({"request_id": request_id, "attempt": 1, "method": method,
                              "url": url, "request_body": request_body,
                              "request_sha256": hashlib.sha256(request_body.encode("utf-8")).hexdigest()
                              if request_body is not None else None,
                              "completion_attempt": False, "status": "response_returned",
                              "raw_response": raw,
                              "raw_response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()})
        reused_responses[request_id] = raw.encode("utf-8")

    budget = LlamaCppPreflightBudget(enabled=True)
    budget.reuse_verified_setup(setup_records)
    opener = FakeOpener([
        response('{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'),
        response('{"type":"send_message","text":"Proposal"}'),
        response('{"type":"no_message"}'),
    ])
    backend = LocalLlamaCppBackend(settings, counter, opener)
    result = backend.preflight(budget, probes, reused_setup_responses=reused_responses)
    assert result["status"] == "PASS_INTERFACE"
    assert result["logical_requests"] == 6
    assert result["http_attempts"] == 6
    assert result["model_completion_attempts"] == 3
    assert result["reused_prior_setup_requests"] == 3
    assert len(opener.calls) == 3
    assert all(call[0].full_url.endswith("/v1/chat/completions") for call in opener.calls)


def test_port_8081_requires_bounded_preflight_gate_and_listener_owner(tmp_path):
    launch = {**BASE.launch, "port": 8081}
    settings = config_for(preflight=True, base_url="http://127.0.0.1:8081/v1", launch=launch)
    counter = FakeCounter(settings)
    opener = FakeOpener([])
    backend = LocalLlamaCppBackend(settings, counter, opener, listener_guard=lambda: False)
    command = llama_server_command(settings)
    assert command[command.index("--port") + 1] == "8081"
    with pytest.raises(PermissionError, match="listener process"):
        backend._open("http://127.0.0.1:8081/props", None, 10, "GET")
    assert opener.calls == []

    for port, preflight in ((8082, True), (8081, False)):
        invalid = config_for(preflight=preflight,
                             preflight_approval_id="FAKE-PREFLIGHT-TEST-ONLY" if preflight else "",
                             base_url=f"http://127.0.0.1:{port}/v1",
                             launch={**BASE.launch, "port": port})
        with pytest.raises(ValueError, match="launch settings"):
            LocalLlamaCppBackend(invalid, FakeCounter(invalid), FakeOpener([]))


def test_port_8081_allows_only_explicit_preflight_gated_local_full_pilot():
    launch = {**BASE.launch, "port": 8081}
    settings = config_for(live=True, preflight=True,
                          base_url="http://127.0.0.1:8081/v1", launch=launch)
    backend = LocalLlamaCppBackend(settings, FakeCounter(settings), FakeOpener([]))
    assert backend.config.model_calls_enabled is True
    assert backend.config.preflight_enabled is True

    invalid = config_for(live=True, preflight=False,
                         preflight_approval_id="",
                         base_url="http://127.0.0.1:8081/v1", launch=launch)
    with pytest.raises(ValueError, match="launch settings"):
        LocalLlamaCppBackend(invalid, FakeCounter(invalid), FakeOpener([]))


def test_preflight_continuation_carries_only_three_hash_verified_setup_responses():
    rows = []
    for request_id, method, url, response in (
            ("preflight-props", "GET", "http://127.0.0.1:8081/props", "{}"),
            ("preflight-template", "POST", "http://127.0.0.1:8081/apply-template", "{}"),
            ("preflight-tokenize", "POST", "http://127.0.0.1:8081/tokenize", "{}")):
        rows.append({"request_id": request_id, "attempt": 1, "method": method, "url": url,
                     "request_body": None if method == "GET" else "{}",
                     "request_sha256": None if method == "GET" else hashlib.sha256(b"{}").hexdigest(),
                     "completion_attempt": False, "status": "response_returned",
                     "raw_response": response,
                     "raw_response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest()})
    budget = LlamaCppPreflightBudget(enabled=True)
    budget.reuse_verified_setup(rows)
    assert budget.logical_ids == {"preflight-props", "preflight-template", "preflight-tokenize"}
    assert budget.attempts == 3
    assert budget.completion_attempts == 0
    for index in range(1, 4):
        budget.reserve(f"preflight-completion-{index}", 1, completion=True)
    assert len(budget.logical_ids) == 6
    assert budget.attempts == 6
    assert budget.completion_attempts == 3
    with pytest.raises(RuntimeError, match="logical-request hard limit"):
        budget.reserve("preflight-unapproved-seventh", 1)


def test_preflight_continuation_rejects_tampered_prior_setup_response():
    raw = "{}"
    rows = [{"request_id": request_id, "attempt": 1, "method": method, "url": url,
             "request_body": None if method == "GET" else "{}",
             "request_sha256": None if method == "GET" else hashlib.sha256(b"{}").hexdigest(),
             "completion_attempt": False, "status": "response_returned",
             "raw_response": raw,
             "raw_response_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()}
            for request_id, method, url in (
                ("preflight-props", "GET", "http://127.0.0.1:8081/props"),
                ("preflight-template", "POST", "http://127.0.0.1:8081/apply-template"),
                ("preflight-tokenize", "POST", "http://127.0.0.1:8081/tokenize"))]
    rows[1]["raw_response"] = "tampered"
    budget = LlamaCppPreflightBudget(enabled=True)
    with pytest.raises(ValueError, match="integrity checks"):
        budget.reuse_verified_setup(rows)
    assert budget.logical_ids == set()
    assert budget.attempts == 0


def test_preflight_fails_closed_on_template_mismatch_and_records_raw_response(tmp_path):
    template = "frozen fake template"
    template_hash = hashlib.sha256(template.encode("utf-8")).hexdigest()
    settings = config_for(preflight=True, chat_template_sha256=template_hash)
    settings, _ = fake_server_bundle(settings, tmp_path)
    counter = FakeCounter(settings, template=template)
    ballot = preflight_request_for(settings, request_id="probe-ballot", action_kind="ballot")
    props = {"default_generation_settings": {"n_ctx": 4096,
             "params": {"temperature": 0.0, "top_p": 1.0, "top_k": 0, "min_p": 0.0,
                        "samplers": ["top_k", "top_p", "min_p", "temperature"]}},
             "chat_template": "wrong template", "model_path": settings.artifact_path,
             "build_info": settings.server_build_info, "total_slots": 1}
    opener = FakeOpener([props])
    budget = LlamaCppPreflightBudget(enabled=True)
    with pytest.raises(RuntimeError, match="chat template differs"):
        LocalLlamaCppBackend(settings, counter, opener).preflight(
            budget, [(ballot, None),
                     (preflight_request_for(settings, request_id="probe-send", action_kind="message",
                                            requested_action="send_message"), "send_message"),
                     (preflight_request_for(settings, request_id="probe-no-message", action_kind="message",
                                            requested_action="no_message"), "no_message")])
    assert len(opener.calls) == budget.attempts == 1
    assert [row["status"] for row in budget.records] == ["response_returned", "failed"]
    assert "wrong template" in budget.records[-1]["raw_response"]
    assert budget.records[-1]["phase"] == "client_side_preflight_validation"


def test_preflight_rejects_changed_runtime_dll_before_any_http_call(tmp_path):
    template = "frozen fake template"
    settings = config_for(preflight=True,
                          chat_template_sha256=hashlib.sha256(template.encode()).hexdigest())
    settings, _ = fake_server_bundle(settings, tmp_path)
    (Path(settings.server_binary_path).parent / "llama-server-impl.dll").write_bytes(b"tampered DLL")
    counter = FakeCounter(settings, template=template)
    probes = [(preflight_request_for(settings, request_id="probe-ballot", action_kind="ballot"), None),
              (preflight_request_for(settings, request_id="probe-send", action_kind="message",
                                     requested_action="send_message"), "send_message"),
              (preflight_request_for(settings, request_id="probe-no-message", action_kind="message",
                                     requested_action="no_message"), "no_message")]
    opener = FakeOpener([])
    budget = LlamaCppPreflightBudget(enabled=True)
    with pytest.raises(RuntimeError, match="bundle differs"):
        LocalLlamaCppBackend(settings, counter, opener).preflight(budget, probes)
    assert opener.calls == [] and budget.attempts == 0
    assert budget.records[0]["status"] == "failed"
    assert budget.records[0]["phase"] == "preflight_gate_before_http"


def test_shared_runtime_budget_blocks_extra_request_before_http_dispatch():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    ballot = '{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'
    opener = FakeOpener([response(ballot)])
    backend = LocalLlamaCppBackend(settings, counter, opener)
    runtime = settings.bind_runtime(RUNTIME_CONFIG)
    budget = RequestBudget(1, 1, 1)
    adapter = RequestAdapter(backend, runtime, budget)
    adapter.invoke(request_for(settings, request_id="within-cap"))
    with pytest.raises(RequestFailure, match="logical request hard limit"):
        adapter.invoke(request_for(settings, request_id="past-cap"))
    assert len(opener.calls) == budget.logical_requests == budget.attempts == 1


def test_backend_enforces_full_95_logical_190_physical_ceiling_without_adapter():
    settings = config_for(live=True)
    settings, counter = counter_for(settings)
    ballot = '{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'
    outcomes = []
    for _ in range(95):
        outcomes.extend([TimeoutError("fake retryable timeout"), response(ballot)])
    opener = FakeOpener(outcomes)
    backend = LocalLlamaCppBackend(settings, counter, opener)
    for index in range(95):
        request = request_for(settings, request_id=f"direct-{index}")
        with pytest.raises(TimeoutError):
            backend.complete(request, timeout_seconds=17)
        assert backend.complete(request, timeout_seconds=17).text == ballot
    assert backend._full_pilot_attempts == len(opener.calls) == 190
    assert len(backend._full_pilot_logical_ids) == 95
    with pytest.raises(RuntimeError, match="total HTTP-attempt hard limit"):
        backend.complete(request_for(settings, request_id="direct-96"), timeout_seconds=17)
    assert len(opener.calls) == 190
