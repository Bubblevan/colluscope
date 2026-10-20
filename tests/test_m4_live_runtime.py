from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time

import pytest

from colluscope import m4_live_runtime as live


class FakeLlamaState:
    def __init__(self, mode: str = "success", *, send_proposal: bool = True):
        self.mode = mode
        self.send_proposal = send_proposal
        self.requests: list[dict] = []
        self.auth_headers: list[str | None] = []
        self.lock = threading.Lock()


def _server(state: FakeLlamaState):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            return

        def _send(self, status: int, data: bytes):
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            with state.lock:
                state.auth_headers.append(self.headers.get("Authorization"))
            alias = "wrong-model" if state.mode == "wrong_server_model" else "colluscope-qwen3-8b-q4km"
            body = json.dumps({"data": [{"id": alias}]}).encode()
            self._send(200, body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            with state.lock:
                state.requests.append(payload)
                state.auth_headers.append(self.headers.get("Authorization"))
                index = len(state.requests)
            if state.mode == "redirect" and index == 1:
                self.send_response(302)
                self.send_header("Location", "https://external.invalid/should-not-be-followed")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if state.mode == "timeout" and index == 1:
                time.sleep(0.25)
            if state.mode in {"http400", "http500"} and index == 1:
                status = 400 if state.mode == "http400" else 500
                self._send(status, json.dumps({"error": state.mode}).encode())
                return
            schema = payload["response_format"]["schema"]
            if state.mode == "malformed" and index == 1:
                content = "not-json"
            elif state.mode == "truncated" and index == 1:
                content = '{"type":'
            elif state.mode == "missing_action" and index == 1:
                content = "{}"
            else:
                if "oneOf" in schema:
                    action = ({"type": "send_message", "text": "A=T3, B=T2, C=T1"}
                              if state.send_proposal else {"type": "no_message"})
                elif "choice" in schema.get("properties", {}):
                    action = {"choice": "T1"}
                else:
                    if state.mode == "tie" and index in {3, 4, 5}:
                        assignments = [
                            {"A": "T1", "B": "T2", "C": "T3"},
                            {"A": "T2", "B": "T3", "C": "T1"},
                            {"A": "T3", "B": "T1", "C": "T2"},
                        ]
                        ballot = assignments[index - 3]
                    else:
                        ballot = {"A": "T3", "B": "T2", "C": "T1"}
                    action = {"type": "ballot", "assignment": ballot}
                content = json.dumps(action, separators=(",", ":"))
            response = {
                "model": ("wrong-model" if state.mode == "wrong_model" and index == 1
                          else "colluscope-qwen3-8b-q4km"),
                "choices": [{"index": 0,
                             "finish_reason": "length" if state.mode == "truncated" and index == 1 else "stop",
                             "message": {"role": "assistant", "content": content}}],
                "usage": {"prompt_tokens": 17, "completion_tokens": 8, "total_tokens": 25},
            }
            self._send(200, json.dumps(response, separators=(",", ":")).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}/v1"


def _run(tmp_path: Path, state: FakeLlamaState, *, transport=None, group_index: int = 0):
    server, thread, endpoint = _server(state)
    try:
        _config, _base, _scenarios, splits, _positive = live.load_live_config()
        summary = live.run_live(
            tmp_path / "run", approval_id="TEST-ONLY-NOT-AUTHORIZATION", execute_live=True,
            secure_storage=False, test_mode=True, test_endpoint=endpoint,
            transport=transport or live.local_http,
            assigned_groups=[splits["groups"][group_index]],
        )
        return summary, endpoint, server, thread
    except BaseException:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
        raise


def test_live_entrypoint_fails_closed_without_explicit_flag_or_approval(tmp_path):
    with pytest.raises(live.M4AuthorizationRequired):
        live.run_live(tmp_path / "run", approval_id=None, execute_live=False)
    assert not (tmp_path / "run").exists()


def test_fake_http_server_executes_complete_proposal_group_and_independent_replay(tmp_path):
    state = FakeLlamaState()
    summary, _endpoint, server, thread = _run(tmp_path, state)
    try:
        out = tmp_path / "run"
        assert summary["completed_groups"] == 1
        assert summary["logical_generation_requests"] == summary["physical_generation_attempts"] == 11
        assert summary["attempts_with_terminal_event"] == 11
        assert len(state.requests) == 11
        assert all(value == "Bearer test-only-key" for value in state.auth_headers)
        episode = live.read_jsonl(out / "episodes.jsonl")[0]
        assert episode["real_model_evidence"] is False
        assert episode["response_source"] == "fake_openai_compatible_server"
        assert episode["proposal_eligible"] is True
        assert episode["researcher_T"]["private_incentive_delivery"]["A"]["status"] == "HTTP_200_RESPONSE"
        assert episode["researcher_T"]["private_incentive_delivery"]["B"]["status"] == "HTTP_200_RESPONSE"
        assert len(episode["researcher_B"]["token_comparisons"]) == 1
        cmp = episode["researcher_B"]["token_comparisons"][0]
        assert cmp["treatment_minus_control_tokens"] == (
            cmp["token_counts_by_arm"]["masked_history_proposal"] -
            cmp["token_counts_by_arm"]["masked_history_neutral"])
        assert cmp["control"] == "masked_history_neutral"
        assert cmp["matched_own_history_context"] == "masked_in_both_arms"
        assert episode["researcher_E"]["projection"] == "public_only"
        assert "messages" not in episode["researcher_E"]
        assert live.verify_live_run(out, live.load_live_config()[2], live.load_live_config()[3])["settlements_recomputed"] == 1
        all_bytes = b"".join(path.read_bytes() for path in out.rglob("*") if path.is_file())
        assert b"test-only-key" not in all_bytes
        assert b"Bearer " not in all_bytes
        for request_path in (out / "requests").glob("*.json"):
            payload = json.loads(request_path.read_text(encoding="utf-8"))
            model_input = payload["messages"]
            user_text = model_input[1]["content"]
            if '"agent_id":"C"' in user_text:
                assert "your_private_task_score_rule" not in user_text
                assert "private_peer_channel" not in user_text
            if '"agent_id":"A"' in user_text or '"agent_id":"B"' in user_text:
                assert "your_private_task_score_rule" in user_text
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_no_proposal_is_valid_and_does_not_get_replaced_by_focal_calls(tmp_path):
    state = FakeLlamaState(send_proposal=False)
    summary, _endpoint, server, thread = _run(tmp_path, state)
    try:
        episode = live.read_jsonl(tmp_path / "run" / "episodes.jsonl")[0]
        assert episode["terminal_status"] == "COMPLETED"
        assert episode["proposal_eligible"] is False
        assert summary["logical_generation_requests"] == 7
        assert len(episode["researcher_B"]["ballots"]) == 3
        assert all(not row["sent"] and not row["delivered"] for row in episode["researcher_B"]["messages"])
        neutral = next(row for row in episode["researcher_B"]["positive_control"] if row["arm"] == "neutral")
        assert neutral["stimulus_text"] == "Signal code: NONE."
        assert neutral["delivery_status"] == "delivered" and neutral["no_delivery"] is False
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_plurality_allocation_chair_tiebreak_and_welfare_recompute_from_raw_ballots(tmp_path):
    state = FakeLlamaState("tie")
    summary, _endpoint, server, thread = _run(tmp_path, state)
    try:
        episode = live.read_jsonl(tmp_path / "run" / "episodes.jsonl")[0]
        settlement = episode["researcher_B"]["settlement"]
        assert len({tuple(row["ballot"][a] for a in ("A", "B", "C"))
                    for row in episode["researcher_B"]["ballots"] if row["stage"] == "baseline"}) == 3
        assert settlement["chair"] == "A"
        assert settlement["selected_assignment"] == {"A": "T1", "B": "T2", "C": "T3"}
        audit = live.verify_live_run(tmp_path / "run", live.load_live_config()[2], live.load_live_config()[3])
        assert audit["settlements_recomputed"] == 1
        assert summary["completed_groups"] == 1
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


@pytest.mark.parametrize("tamper_field", ["ballot", "welfare", "realized_score"])
def test_independent_auditor_rejects_episode_summary_that_disagrees_with_raw_actions(tmp_path, tamper_field):
    state = FakeLlamaState()
    _summary, _endpoint, server, thread = _run(tmp_path, state)
    try:
        out = tmp_path / "run"
        episode_path = out / "episodes.jsonl"
        episode = live.read_jsonl(episode_path)[0]
        if tamper_field == "ballot":
            episode["researcher_B"]["ballots"][0]["ballot"] = {"A": "T1", "B": "T2", "C": "T3"}
            expected = "recorded ballot differs"
        elif tamper_field == "welfare":
            episode["researcher_B"]["settlement"]["public_welfare"] += 1
            expected = "settlement/welfare replay mismatch"
        else:
            episode["researcher_B"]["settlement"]["realized_task_scores"]["A"] += 1
            expected = "settlement/welfare replay mismatch"
        episode_path.write_text(json.dumps(episode, separators=(",", ":")) + "\n", encoding="utf-8")
        _config, _base, scenarios, splits, _positive = live.load_live_config()
        with pytest.raises(live.M4LiveError, match=expected):
            live.verify_live_run(out, scenarios, splits)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_independent_auditor_rejects_completed_raw_action_omitted_from_episode(tmp_path):
    state = FakeLlamaState()
    _summary, _endpoint, server, thread = _run(tmp_path, state)
    try:
        out = tmp_path / "run"
        episode_path = out / "episodes.jsonl"
        episode = live.read_jsonl(episode_path)[0]
        episode["researcher_B"]["messages"].pop()
        episode_path.write_text(json.dumps(episode, separators=(",", ":")) + "\n", encoding="utf-8")
        _config, _base, scenarios, splits, _positive = live.load_live_config()
        with pytest.raises(live.M4LiveError, match="not one-to-one"):
            live.verify_live_run(out, scenarios, splits)
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


@pytest.mark.parametrize(("mode", "expected"), [
    ("malformed", "INVALID_JSON"),
    ("truncated", "TRUNCATED_OUTPUT"),
    ("missing_action", "MISSING_ACTION"),
    ("http400", "HTTP_ERROR_400"),
    ("http500", "HTTP_ERROR_500"),
    ("redirect", "HTTP_ERROR_302"),
    ("wrong_model", "MODEL_IDENTITY_MISMATCH"),
])
def test_bad_response_is_preserved_terminal_and_never_retried(tmp_path, mode, expected):
    state = FakeLlamaState(mode)
    summary, _endpoint, server, thread = _run(tmp_path, state)
    try:
        out = tmp_path / "run"
        assert summary["failed_groups"] == 1
        assert summary["logical_generation_requests"] == summary["physical_generation_attempts"] == 1
        attempt_rows = live.read_jsonl(out / "attempts.jsonl")
        assert len([row for row in attempt_rows if row["event"] == "attempt_started"]) == 1
        terminal = next(row for row in attempt_rows if row["event"] == "attempt_terminal")
        assert terminal["status"] == expected
        assert terminal["retry"] is False
        assert (out / "responses" / f"{terminal['request_id']}.body").exists()
        assert len(state.requests) == 1
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_transport_timeout_is_terminal_with_no_retry(tmp_path):
    state = FakeLlamaState("timeout")

    def short_timeout_transport(endpoint, **kwargs):
        return live.local_http(endpoint, timeout=0.05, **{k: v for k, v in kwargs.items() if k != "timeout"})

    summary, _endpoint, server, thread = _run(tmp_path, state, transport=short_timeout_transport)
    try:
        assert summary["failed_groups"] == 1
        attempt = next(row for row in live.read_jsonl(tmp_path / "run" / "attempts.jsonl")
                       if row["event"] == "attempt_terminal")
        assert attempt["status"] == "TRANSPORT_TIMEOUT"
        assert attempt["retry"] is False
        assert len(state.requests) == 1
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_interrupted_request_is_terminalized_and_resume_never_resends(tmp_path):
    state = FakeLlamaState()
    server, thread, endpoint = _server(state)
    _config, _base, _scenarios, splits, _positive = live.load_live_config()
    group = splits["groups"][0]

    def interrupt_after_wire_response(url, **kwargs):
        live.local_http(url, **kwargs)
        raise KeyboardInterrupt("test interruption after HTTP send")

    out = tmp_path / "run"
    try:
        first = live.run_live(out, approval_id="TEST-INTERRUPT", execute_live=True,
                              secure_storage=False, test_mode=True, test_endpoint=endpoint,
                              transport=interrupt_after_wire_response, assigned_groups=[group])
        assert first["physical_generation_attempts"] == 1
        starts_before = len(state.requests)
        second = live.run_live(out, approval_id="TEST-INTERRUPT", execute_live=True,
                               secure_storage=False, test_mode=True, test_endpoint=endpoint,
                               assigned_groups=[group])
        assert second["physical_generation_attempts"] == 1
        assert len(state.requests) == starts_before == 1
        episode = live.read_jsonl(out / "episodes.jsonl")[0]
        assert episode["failure_records"][0]["status"] == "INTERRUPTED_UNKNOWN"
        assert len([row for row in live.read_jsonl(out / "attempts.jsonl")
                    if row["event"] == "attempt_started"]) == 1
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_successful_run_resume_skips_every_terminal_request(tmp_path):
    state = FakeLlamaState()
    summary, endpoint, server, thread = _run(tmp_path, state)
    try:
        _config, _base, _scenarios, splits, _positive = live.load_live_config()
        first_count = len(state.requests)
        replay = live.run_live(tmp_path / "run", approval_id="TEST-ONLY-NOT-AUTHORIZATION",
                               execute_live=True, secure_storage=False, test_mode=True,
                               test_endpoint=endpoint, assigned_groups=[splits["groups"][0]])
        assert replay["physical_generation_attempts"] == summary["physical_generation_attempts"] == 11
        assert len(state.requests) == first_count
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_resume_recovers_durable_completed_episode_without_replaying_or_relabeling(tmp_path, monkeypatch):
    state = FakeLlamaState()
    server, thread, endpoint = _server(state)
    _config, _base, _scenarios, splits, _positive = live.load_live_config()
    group = splits["groups"][0]
    out = tmp_path / "run"
    original_append = live.append_jsonl

    def interrupt_before_group_terminal(path, row):
        if Path(path).name == "groups.jsonl" and row.get("event") == "group_terminal":
            raise OSError("simulated crash after durable episode append")
        return original_append(path, row)

    try:
        monkeypatch.setattr(live, "append_jsonl", interrupt_before_group_terminal)
        with pytest.raises(OSError, match="simulated crash"):
            live.run_live(out, approval_id="TEST-CRASH-WINDOW", execute_live=True,
                          secure_storage=False, test_mode=True, test_endpoint=endpoint,
                          assigned_groups=[group])
        assert len(state.requests) == 11
        prior_episode = live.read_jsonl(out / "episodes.jsonl")[0]
        assert prior_episode["terminal_status"] == "COMPLETED"

        monkeypatch.setattr(live, "append_jsonl", original_append)
        resumed = live.run_live(out, approval_id="TEST-CRASH-WINDOW", execute_live=True,
                                secure_storage=False, test_mode=True, test_endpoint=endpoint,
                                assigned_groups=[group])
        episodes = live.read_jsonl(out / "episodes.jsonl")
        terminal = [row for row in live.read_jsonl(out / "groups.jsonl")
                    if row.get("event") == "group_terminal"]
        assert len(episodes) == 1
        assert episodes[0]["terminal_status"] == "COMPLETED"
        assert len(terminal) == 1 and terminal[0]["status"] == "COMPLETED"
        assert terminal[0]["reason"] == "RECOVERED_DURABLE_EPISODE_NO_REPLAY"
        assert resumed["physical_generation_attempts"] == 11
        assert len(state.requests) == 11
        assert live.verify_live_run(out, live.load_live_config()[2], live.load_live_config()[3])["status"] == "PASS_INDEPENDENT_LIVE_TRACE_REPLAY"
    finally:
        monkeypatch.setattr(live, "append_jsonl", original_append)
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_resume_refuses_missing_attempt_terminal_inside_completed_group(tmp_path):
    state = FakeLlamaState()
    _summary, endpoint, server, thread = _run(tmp_path, state)
    try:
        out = tmp_path / "run"
        attempts_path = out / "attempts.jsonl"
        rows = live.read_jsonl(attempts_path)
        terminal_request_id = next(row["request_id"] for row in rows
                                   if row.get("event") == "attempt_terminal")
        retained = [row for row in rows if not (row.get("event") == "attempt_terminal"
                                                 and row.get("request_id") == terminal_request_id)]
        attempts_path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                                         for row in retained), encoding="utf-8")
        _config, _base, _scenarios, splits, _positive = live.load_live_config()
        with pytest.raises(live.M4LiveError, match="completed group contains an attempt"):
            live.run_live(out, approval_id="TEST-ONLY-NOT-AUTHORIZATION", execute_live=True,
                          secure_storage=False, test_mode=True, test_endpoint=endpoint,
                          assigned_groups=[splits["groups"][0]])
        assert len(state.requests) == 11
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_generation_hard_cap_refuses_before_writing_or_sending_next_request(tmp_path):
    out = tmp_path / "run"
    out.mkdir()
    for i in range(live.MAX_GENERATION_ATTEMPTS):
        live.append_jsonl(out / "attempts.jsonl", {"event": "attempt_started", "request_id": str(i)})
    _config, *_rest = live.load_live_config()
    counter = live._CharacterTokenCounter()
    client = live.GenerationClient(out=out, config=_config, api_key="unused", token_counter=counter,
                                   endpoint="http://127.0.0.1:8081/v1", transport=lambda *_a, **_k: pytest.fail("cap must stop"))
    with pytest.raises(live.M4RequestFailure, match="hard M4"):
        client.generate("cap-request", "g", "message", "A", "prompt", {"agent_id": "A"}, arm="message")
    assert not (out / "requests" / "cap-request.json").exists()


def test_wrong_checkpoint_hash_and_external_endpoint_are_rejected(tmp_path):
    config, *_ = live.load_live_config()
    fake_model = tmp_path / "fake.gguf"
    fake_model.write_bytes(b"wrong model")
    bad = json.loads(json.dumps(config))
    bad["model"]["path"] = str(fake_model)
    with pytest.raises(live.M4LiveError, match="checkpoint is missing or hash-mismatched"):
        live.verify_frozen_assets(bad)
    for endpoint in ("https://example.com/v1", "http://127.0.0.1:8082/v1",
                     "http://localhost:8081/v1", "http://127.0.0.1:8081/v1evil"):
        with pytest.raises(live.M4LiveError, match="outside the frozen"):
            live.validate_local_endpoint(endpoint)


def test_frozen_asset_verifier_maps_gguf_tokenizer_hash_to_config_sha256(monkeypatch, tmp_path):
    import colluscope.gguf_tokenizer as gguf_tokenizer
    import colluscope.openai_compat_llamacpp as runtime_identity

    config, *_ = live.load_live_config()
    model = tmp_path / "model.gguf"
    binary = tmp_path / "llama-server.exe"
    model.write_bytes(b"test-only-gguf")
    binary.write_bytes(b"test-only-runtime")
    test_config = json.loads(json.dumps(config))
    test_config["model"]["path"] = str(model)
    test_config["runtime"]["binary_path"] = str(binary)

    class FakeCounter:
        artifact_sha256 = test_config["model"]["sha256"]
        tokenizer_sha256 = test_config["tokenizer"]["sha256"]
        chat_template_sha256 = test_config["tokenizer"]["chat_template_sha256"]
        tokenizers_library_version = test_config["tokenizer"]["tokenizers_version"]
        jinja2_library_version = test_config["tokenizer"]["jinja2_version"]

        def __init__(self, path, *, expected_artifact_sha256):
            assert Path(path) == model
            assert expected_artifact_sha256 == self.artifact_sha256

    expected_hashes = {
        str(model.resolve()): test_config["model"]["sha256"],
        str(binary.resolve()): test_config["runtime"]["binary_sha256"],
    }
    monkeypatch.setattr(live, "sha_file", lambda path: expected_hashes[str(Path(path).resolve())])
    monkeypatch.setattr(gguf_tokenizer, "GGUFChatTokenCounter", FakeCounter)
    monkeypatch.setattr(runtime_identity, "llama_runtime_bundle_identity",
                        lambda _path: {"sha256": test_config["runtime"]["bundle_sha256"], "file_count": 1})

    result = live.verify_frozen_assets(test_config)
    assert result["verified"] is True
    assert result["tokenizer_sha256"] == test_config["tokenizer"]["sha256"]
    assert result["chat_template_sha256"] == test_config["tokenizer"]["chat_template_sha256"]

    test_config["tokenizer"]["sha256"] = "0" * 64
    with pytest.raises(live.M4LiveError, match="tokenizer/template runtime identity mismatch: tokenizer_sha256"):
        live.verify_frozen_assets(test_config)


def test_fake_server_models_route_verifies_and_rejects_wrong_server_identity():
    for mode, expected in (("success", True), ("wrong_server_model", False)):
        state = FakeLlamaState(mode)
        server, thread, endpoint = _server(state)
        try:
            response = live.local_http(endpoint + "/models", method="GET", api_key="test-secret",
                                       timeout=2, test_loopback_port=True)
            if expected:
                assert live.verify_model_alias_response(response.status, response.body,
                                                        "colluscope-qwen3-8b-q4km") == ["colluscope-qwen3-8b-q4km"]
            else:
                with pytest.raises(live.M4LiveError, match="differs from frozen model alias"):
                    live.verify_model_alias_response(response.status, response.body,
                                                     "colluscope-qwen3-8b-q4km")
            assert state.auth_headers == ["Bearer test-secret"]
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)


@pytest.mark.parametrize("kind", ["request", "request_metadata", "response", "response_metadata"])
def test_tampered_raw_bytes_block_resume_before_any_network_call(tmp_path, kind):
    state = FakeLlamaState()
    _summary, endpoint, server, thread = _run(tmp_path, state)
    try:
        out = tmp_path / "run"
        row = next(r for r in live.read_jsonl(out / "attempts.jsonl") if r["event"] == "attempt_terminal")
        if kind == "request":
            path = out / "requests" / f"{row['request_id']}.json"
        elif kind == "request_metadata":
            path = out / "requests" / f"{row['request_id']}.meta.json"
        elif kind == "response":
            path = out / "responses" / f"{row['request_id']}.body"
        else:
            path = out / "responses" / f"{row['request_id']}.meta.json"
        path.write_bytes(path.read_bytes() + b"tamper")
        _config, _base, _scenarios, splits, _positive = live.load_live_config()
        with pytest.raises(live.M4LiveError, match="tampered"):
            live.run_live(out, approval_id="TEST-ONLY-NOT-AUTHORIZATION", execute_live=True,
                          secure_storage=False, test_mode=True, test_endpoint=endpoint,
                          assigned_groups=[splits["groups"][0]])
        assert len(state.requests) == 11
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)


def test_http_response_usage_finish_reason_and_auth_are_audited_without_saving_secret(tmp_path):
    state = FakeLlamaState()
    summary, _endpoint, server, thread = _run(tmp_path, state)
    try:
        out = tmp_path / "run"
        first = next((out / "responses").glob("*.meta.json"))
        receipt = json.loads(first.read_text(encoding="utf-8"))
        assert receipt["finish_reason"] == "stop"
        assert receipt["usage"] == {"prompt_tokens": 17, "completion_tokens": 8, "total_tokens": 25}
        assert receipt["elapsed_seconds"] >= 0
        attempt_text = (out / "attempts.jsonl").read_text(encoding="utf-8")
        assert "auth_header_saved\":false" in attempt_text
        assert "test-only-key" not in attempt_text and "Bearer" not in attempt_text
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
