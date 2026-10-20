from __future__ import annotations

from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

import pytest

from scripts import run_sprint_monitor as runtime
from scripts import audit_sprint_monitor_live as live_auditor
from colluscope.sprint_controls import scripted_cases
from scripts.prepare_sprint_baselines import _make_llm_schedule
from colluscope.monitor_aggregate_budget import AggregateBudget


def _config_with_request_cap(tmp_path: Path, cap: int = 1) -> Path:
    text = runtime.CONFIG_PATH.read_text(encoding="utf-8")
    text = text.replace("max_logical_requests = 280", f"max_logical_requests = {cap}")
    text = text.replace("max_http_attempts = 280", f"max_http_attempts = {cap}")
    path = tmp_path / f"runtime-cap-{cap}.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _live_config_with_request_cap(tmp_path: Path, cap: int = 1) -> Path:
    text = runtime.CONFIG_PATH.read_text(encoding="utf-8")
    text = text.replace("max_logical_requests = 280", f"max_logical_requests = {cap}")
    text = text.replace("max_http_attempts = 280", f"max_http_attempts = {cap}")
    text = text.replace("live_dispatch_enabled = false", "live_dispatch_enabled = true")
    text = text.replace('authorization_id = ""', 'authorization_id = "TEST-APPROVED"')
    path = tmp_path / f"live-test-cap-{cap}.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _response(content: str, *, status: int = 200, model: str = "deepseek-flash",
              fingerprint: str | None = "mock-fingerprint",
              usage: dict | None = None) -> runtime.HTTPResult:
    payload = {
        "model": model,
        "system_fingerprint": fingerprint,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
    }
    if usage is not None:
        payload["usage"] = usage
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return runtime.HTTPResult(status, body, {"content-type": "application/json"})


def _run(tmp_path: Path, transport, *, config_path=None):
    return runtime.run_schedule(
        tmp_path / "run",
        mode="mock",
        config_path=config_path or runtime.CONFIG_PATH,
        transport=transport,
        secure_storage=False,
    )


def test_frozen_schedule_and_peak_cost_reservation_fit_hard_caps():
    config = runtime._load_config()
    schedule = runtime.build_schedule(config)
    assert len(schedule) == 280
    assert len({row.request_id for row in schedule}) == 280
    assert all(row.input_upper_bound <= 8192 for row in schedule)
    assert sum(row.reserve_usd for row in schedule) < 1.0
    assert config["max_http_attempts"] == config["max_logical_requests"] == 280
    assert config["max_attempts_per_logical_request"] == 1


def test_live_dispatch_is_refused_before_creating_run_or_calling_transport(tmp_path):
    called = []
    out = tmp_path / "must-not-exist"
    with pytest.raises(runtime.LiveDispatchDisabled, match="frozen off"):
        runtime.run_schedule(out, mode="live", transport=lambda *args: called.append(args))
    assert not out.exists()
    assert called == []


def test_live_api_entrypoint_rejects_transport_and_acl_bypasses_outside_test_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path)
    out = tmp_path / "must-not-exist"
    with pytest.raises(runtime.LiveDispatchDisabled, match="injected transports and ACL bypass"):
        runtime.run_schedule(out, mode="live", config_path=config_path,
                             approval_id="TEST-APPROVED",
                             transport=lambda *_args: pytest.fail("production seam must refuse"),
                             secure_storage=False)
    assert not out.exists()


def test_monitor_http_transport_does_not_forward_authentication_through_redirect():
    redirect_target_hits = []
    observed_auth = []

    class SinkHandler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            redirect_target_hits.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

    sink = ThreadingHTTPServer(("127.0.0.1", 0), SinkHandler)
    sink_thread = threading.Thread(target=sink.serve_forever, daemon=True)
    sink_thread.start()

    class RedirectHandler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            return

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            observed_auth.append(self.headers.get("Authorization"))
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{sink.server_port}/credential-sink")
            self.send_header("Content-Length", "0")
            self.end_headers()

    redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    redirect_thread = threading.Thread(target=redirect.serve_forever, daemon=True)
    redirect_thread.start()
    try:
        response = runtime.urllib_transport(
            f"http://127.0.0.1:{redirect.server_port}/chat/completions",
            b"{}", "test-secret-never-persist", 2)
        assert response.status == 302
        assert observed_auth == ["Bearer test-secret-never-persist"]
        assert redirect_target_hits == []
    finally:
        redirect.shutdown(); redirect.server_close(); redirect_thread.join(timeout=2)
        sink.shutdown(); sink.server_close(); sink_thread.join(timeout=2)


def test_live_fake_transport_accounts_for_usage_and_keeps_raw_gated_and_auth_separate(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path)
    calls = []
    content = '{"label":"not_visible","evidence_refs":[]}'

    def fake_provider(endpoint, body, api_key, timeout):
        calls.append((endpoint, body, api_key, timeout))
        return _response(content, model="DeepSeek-V4.1-Flash-1017",
                         fingerprint="fake-fingerprint",
                         usage={"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 125})

    out = tmp_path / "run"
    summary = runtime.run_schedule(
        out, mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=fake_provider, secure_storage=False, test_mode=True,
    )
    assert len(calls) == 1
    endpoint, body, api_key, timeout = calls[0]
    assert endpoint == "https://api.deepseek.com/chat/completions"
    assert body and api_key == "test-secret-never-persist" and timeout == 90
    assert summary["returned_model_identity"] == ["DeepSeek-V4.1-Flash-1017", "fake-fingerprint"]
    assert summary["provider_reported_usage_rows"] == 1
    assert summary["provider_reported_peak_cost_usd"] == 0.00006
    assert summary["missing_usage_reserved_upper_usd"] == 0
    assert summary["conservative_total_peak_cost_usd"] == 0.00006
    progress = runtime._read_jsonl(out / "progress.jsonl")
    assert progress[0]["usage"] == {"input_tokens": 100, "output_tokens": 25}
    assert progress[0]["cost_upper_peak_usd"] == 0.00006
    raw = runtime._read_jsonl(out / "raw_predictions.jsonl")
    gated = runtime._read_jsonl(out / "gated_predictions.jsonl")
    assert len(raw) == len(gated) == 1
    assert raw[0]["raw_prediction"]["label"] == gated[0]["raw_label"]
    assert b"reference_answer" not in body and b"construction_truth" not in body
    serialized = b"".join(path.read_bytes() for path in out.rglob("*") if path.is_file())
    assert b"test-secret-never-persist" not in serialized
    assert b"Bearer " not in serialized
    assert all(row["auth_header_saved"] is False for row in runtime._read_jsonl(out / "attempts.jsonl"))
    audit = live_auditor.audit(out, config_path=config_path, allow_fake_test_run=True)
    assert audit["status"] == "PASS_FAKE_TRANSPORT_REPLAY_ONLY"
    assert audit["completed_predictions_independently_rescored"] == 1


def test_live_dispatch_reserves_shared_budget_before_transport(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path, cap=1)
    request = runtime.build_schedule()[0]
    budget = AggregateBudget(tmp_path / "aggregate.jsonl", "TEST-EXECUTION")
    calls = []

    def provider(endpoint, body, api_key, timeout):
        rows = budget.rows()
        assert len(rows) == 1 and rows[0]["event"] == "request_reserved"
        assert rows[0]["request_id"] == request.request_id
        calls.append((endpoint, body, api_key, timeout))
        return _response('{"label":"not_visible","evidence_refs":[]}',
                         usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120})

    out = tmp_path / "run"
    summary = runtime.run_schedule(
        out, mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=provider, secure_storage=False, test_mode=True,
        requests_override=[request], budget_ledger=budget, phase_id="scripted_controls",
    )
    assert len(calls) == 1
    assert [row["event"] for row in budget.rows()] == ["request_reserved", "request_terminal"]
    assert summary["aggregate_budget"]["reserved_requests"] == 1
    assert summary["aggregate_budget"]["terminal_requests"] == 1
    assert summary["physical_http_attempts"] == 0


def test_orphan_global_reservation_is_terminalized_without_transport_replay(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path, cap=1)
    request = runtime.build_schedule()[0]
    budget = AggregateBudget(tmp_path / "aggregate.jsonl", "TEST-EXECUTION")
    budget.reserve(phase_id="scripted_controls", request_id=request.request_id,
                   body_sha256=request.body_sha256, reserve_usd=request.reserve_usd,
                   phase_request_cap=1, phase_cost_cap_usd=1.0)
    calls = []

    summary = runtime.run_schedule(
        tmp_path / "run", mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=lambda *args: calls.append(args), secure_storage=False, test_mode=True,
        requests_override=[request], budget_ledger=budget, phase_id="scripted_controls",
    )
    progress = runtime._read_jsonl(tmp_path / "run" / "progress.jsonl")
    assert calls == []
    assert progress[0]["status"] == "GLOBAL_RESERVED_NO_LOCAL_ATTEMPT_NO_REPLAY"
    assert summary["aggregate_budget"]["reserved_requests"] == 1
    assert summary["aggregate_budget"]["terminal_requests"] == 0


def test_live_monitor_independent_auditor_rejects_tampered_gated_prediction(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path)
    out = tmp_path / "run"
    runtime.run_schedule(
        out, mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=lambda *_args: _response(
            '{"label":"not_visible","evidence_refs":[]}',
            usage={"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 125}),
        secure_storage=False, test_mode=True,
    )
    gated_path = out / "gated_predictions.jsonl"
    record = runtime._read_jsonl(gated_path)[0]
    record["gated_label"] = "supported"
    gated_path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n",
                          encoding="utf-8")
    with pytest.raises(live_auditor.AuditFailure, match="independent rescoring"):
        live_auditor.audit(out, config_path=config_path, allow_fake_test_run=True)


def test_live_fake_transport_identity_drift_stops_and_terminalizes_remaining_schedule(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path, cap=2)
    calls = []

    def drifting_provider(endpoint, body, api_key, timeout):
        calls.append(body)
        model = "DeepSeek-V4.1-Flash-1017" if len(calls) == 1 else "deepseek-flash"
        return _response('{"label":"not_visible","evidence_refs":[]}', model=model,
                         fingerprint="fp-stable")

    summary = runtime.run_schedule(
        tmp_path / "run", mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=drifting_provider, secure_storage=False, test_mode=True,
    )
    rows = runtime._read_jsonl(tmp_path / "run" / "progress.jsonl")
    assert len(calls) == 2
    assert [row["status"] for row in rows[:2]] == ["COMPLETED", "MODEL_IDENTITY_DRIFT"]
    assert all(row["status"] == "NOT_SENT_AFTER_STOP" for row in rows[2:])
    assert summary["provider_error_stop_reason"] == "returned model or system fingerprint changed within the run"
    assert summary["real_model_or_api_calls"] == 0
    assert summary["fake_transport_attempt_slots"] == 2
    assert summary["physical_http_attempts"] == 0


def test_live_fake_transport_missing_fingerprint_stops_without_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path)
    calls = []

    def missing_fingerprint(endpoint, body, api_key, timeout):
        calls.append(body)
        return _response('{"label":"not_visible","evidence_refs":[]}', fingerprint=None)

    summary = runtime.run_schedule(
        tmp_path / "run", mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=missing_fingerprint, secure_storage=False, test_mode=True,
    )
    rows = runtime._read_jsonl(tmp_path / "run" / "progress.jsonl")
    assert len(calls) == 1
    assert rows[0]["status"] == "MODEL_FINGERPRINT_MISSING"
    assert summary["provider_error_stop_reason"] == "provider system_fingerprint missing"


@pytest.mark.parametrize(("usage", "expected_status"), [
    ({"prompt_tokens": -1, "completion_tokens": 1, "total_tokens": 0},
     "INVALID_USAGE_ACCOUNTING"),
    ({"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 126},
     "INVALID_USAGE_ACCOUNTING"),
    ({"prompt_tokens": 8193, "completion_tokens": 1, "total_tokens": 8194},
     "TOKEN_BUDGET_EXCEEDED"),
    ({"prompt_tokens": 8000, "completion_tokens": 100, "total_tokens": 8100},
     "REQUEST_COST_RESERVE_EXCEEDED"),
])
def test_live_usage_anomalies_stop_without_retry_and_keep_reserved_cost(tmp_path, monkeypatch, usage, expected_status):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path, cap=2)
    calls = []

    def bad_usage(endpoint, body, api_key, timeout):
        calls.append(body)
        return _response('{"label":"not_visible","evidence_refs":[]}', usage=usage)

    summary = runtime.run_schedule(
        tmp_path / "run", mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=bad_usage, secure_storage=False, test_mode=True,
    )
    rows = runtime._read_jsonl(tmp_path / "run" / "progress.jsonl")
    assert len(calls) == 1
    assert rows[0]["status"] == expected_status
    assert all(row["status"] == "NOT_SENT_AFTER_STOP" for row in rows[1:])
    assert summary["provider_error_stop_reason"] is not None
    assert summary["conservative_total_peak_cost_usd"] <= summary["hard_cost_ceiling_usd"]


def test_live_fake_transport_failure_resumes_without_reissuing_terminal_request(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-never-persist")
    config_path = _live_config_with_request_cap(tmp_path)
    first_calls = []

    def interrupted(*_args):
        first_calls.append(1)
        raise runtime.TransportFailure("TimeoutError", "fake timeout")

    out = tmp_path / "run"
    first = runtime.run_schedule(
        out, mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=interrupted, secure_storage=False, test_mode=True,
    )
    replay_calls = []
    second = runtime.run_schedule(
        out, mode="live", config_path=config_path, approval_id="TEST-APPROVED",
        transport=lambda *args: replay_calls.append(args), secure_storage=False, test_mode=True,
    )
    assert first_calls == [1]
    assert replay_calls == []
    assert first["real_model_or_api_calls"] == second["real_model_or_api_calls"] == 0
    assert first["fake_transport_attempt_slots"] == second["fake_transport_attempt_slots"] == 1
    row = runtime._read_jsonl(out / "progress.jsonl")[0]
    assert row["status"] == "TRANSPORT_ERROR"
    assert "test-secret-never-persist" not in (out / "attempts.jsonl").read_text(encoding="utf-8")


def test_offline_mock_end_to_end_terminalizes_all_280_without_model_claim(tmp_path):
    summary = _run(tmp_path, runtime.mock_transport)
    run = tmp_path / "run"
    progress = runtime._read_jsonl(run / "progress.jsonl")
    attempts = runtime._read_jsonl(run / "attempts.jsonl")
    assert summary["status"] == "OFFLINE_MOCK_COMPLETE"
    assert summary["assigned_rows"] == summary["terminal_rows"] == 280
    assert summary["completed_rows"] == 280
    assert summary["real_model_or_api_calls"] == 0
    assert summary["physical_http_attempts"] == 0
    assert summary["fake_transport_attempt_slots"] == 280
    assert summary["mock_is_behavior_evidence"] is False
    assert len(progress) == 280 and len({row["request_id"] for row in progress}) == 280
    assert sum(row["event"] == "attempt_started" for row in attempts) == 280
    assert sum(row["event"] == "attempt_terminal" for row in attempts) == 280
    assert len(list((run / "requests").glob("*.json"))) == 280
    assert len(list((run / "responses").glob("*.json"))) == 280
    assert all(row["status"] == "COMPLETED" for row in progress)
    assert summary["provider_reported_usage_rows"] == 0
    assert summary["provider_reported_peak_cost_usd"] == 0
    assert summary["missing_usage_reserved_upper_usd"] == summary["reserved_peak_cost_usd"]
    assert summary["conservative_total_peak_cost_usd"] == summary["reserved_peak_cost_usd"]
    assert all(row["auth_header_saved"] is False for row in attempts)
    serialized_logs = (run / "attempts.jsonl").read_text(encoding="utf-8")
    assert "Authorization" not in serialized_logs and "Bearer " not in serialized_logs
    assert len(runtime._read_jsonl(run / "raw_predictions.jsonl")) == 280
    assert len(runtime._read_jsonl(run / "gated_predictions.jsonl")) == 280
    assert len(runtime._read_jsonl(run / "analysis" / "audit_layers.jsonl")) == 280


def test_logical_and_physical_caps_stop_dispatch_and_terminalize_unsent_rows(tmp_path):
    called = []

    def transport(endpoint, body, api_key, timeout):
        called.append((endpoint, body, api_key, timeout))
        return _response('{"label":"not_visible","evidence_refs":[]}')

    summary = _run(tmp_path, transport, config_path=_config_with_request_cap(tmp_path, 1))
    progress = runtime._read_jsonl(tmp_path / "run" / "progress.jsonl")
    assert len(called) == 1
    assert summary["logical_http_requests"] == summary["fake_transport_attempt_slots"] == 1
    assert summary["physical_http_attempts"] == 0
    assert summary["retries"] == 0
    assert summary["terminal_rows"] == 280
    assert sum(row["status"] == "BUDGET_EXHAUSTED" for row in progress) == 279


def test_started_but_unclosed_request_is_terminalized_and_never_retried(tmp_path):
    out = tmp_path / "run"
    out.mkdir()
    request = runtime.build_schedule()[0]
    request_path = out / "requests" / f"{request.request_id}.json"
    request_path.parent.mkdir(parents=True)
    request_path.write_bytes(runtime._json_bytes(request.http_payload))
    runtime._append_jsonl(out / "attempts.jsonl", {
        "event": "attempt_started", "request_id": request.request_id,
        "body_sha256": request.body_sha256,
        "request_path": f"requests/{request.request_id}.json",
        "attempt_index": 1, "reserve_usd": request.reserve_usd,
        "auth_header_saved": False,
    })
    called = []
    summary = runtime.run_schedule(
        out, mode="mock", config_path=_config_with_request_cap(tmp_path, 1),
        transport=lambda *args: called.append(args), secure_storage=False,
    )
    progress = runtime._read_jsonl(out / "progress.jsonl")
    first = next(row for row in progress if row["request_id"] == request.request_id)
    assert first["status"] == "INTERRUPTED_UNKNOWN_NO_RETRY"
    assert called == []
    assert summary["logical_http_requests"] == 1
    assert summary["physical_http_attempts"] == 0
    assert summary["fake_transport_attempt_slots"] == 1
    assert summary["retries"] == 0
    assert len(progress) == 280


def test_terminal_http_attempt_without_progress_row_is_recovered_without_resend(tmp_path):
    out = tmp_path / "run"
    config_path = _config_with_request_cap(tmp_path, 1)
    first_calls = []

    def successful(*args):
        first_calls.append(args)
        return _response('{"label":"not_visible","evidence_refs":[]}')

    _run(tmp_path, successful, config_path=config_path)
    assert len(first_calls) == 1
    progress_path = out / "progress.jsonl"
    rows = runtime._read_jsonl(progress_path)
    first_id = rows[0]["request_id"]
    kept = [row for row in rows if row["request_id"] != first_id]
    progress_path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                                  for row in kept), encoding="utf-8")

    replay_calls = []
    summary = runtime.run_schedule(
        out, mode="mock", config_path=config_path,
        transport=lambda *args: replay_calls.append(args), secure_storage=False,
    )
    recovered = next(row for row in runtime._read_jsonl(progress_path)
                     if row["request_id"] == first_id)
    assert recovered["status"] == "COMPLETED"
    assert recovered["recovered_after_terminal_attempt"] is True
    assert replay_calls == []
    assert summary["logical_http_requests"] == 1


def test_tampered_monitor_response_is_rejected_before_resume(tmp_path):
    config_path = _config_with_request_cap(tmp_path, 1)
    _run(tmp_path, lambda *_args: _response('{"label":"not_visible","evidence_refs":[]}'),
         config_path=config_path)
    out = tmp_path / "run"
    first = runtime._read_jsonl(out / "attempts.jsonl")
    request_id = next(row["request_id"] for row in first if row["event"] == "attempt_terminal")
    response_path = out / "responses" / f"{request_id}.json"
    response_path.write_bytes(response_path.read_bytes() + b"tamper")
    with pytest.raises(runtime.RuntimeIntegrityError, match="response bytes are missing or tampered"):
        runtime.run_schedule(out, mode="mock", config_path=config_path,
                             transport=lambda *_args: pytest.fail("tampered run must not dispatch"),
                             secure_storage=False)


def test_invalid_json_is_preserved_as_terminal_output_without_repair_or_retry(tmp_path):
    called = []

    def transport(*_args):
        called.append(1)
        return runtime.HTTPResult(200, b"not-json", {"content-type": "application/json"})

    summary = _run(tmp_path, transport, config_path=_config_with_request_cap(tmp_path, 1))
    progress = runtime._read_jsonl(tmp_path / "run" / "progress.jsonl")
    assert called == [1]
    assert progress[0]["status"] == "INVALID_RESPONSE_JSON"
    assert (tmp_path / "run" / "responses" / f"{progress[0]['request_id']}.json").read_bytes() == b"not-json"
    assert summary["logical_http_requests"] == 1
    assert summary["retries"] == 0


def test_invalid_citation_is_scored_separately_and_sequence_claim_is_gated(tmp_path):
    called = []
    content = '{"label":"supported","evidence_refs":["M99"]}'

    def transport(*_args):
        called.append(1)
        return _response(content)

    summary = _run(tmp_path, transport, config_path=_config_with_request_cap(tmp_path, 1))
    out = tmp_path / "run"
    raw = runtime._read_jsonl(out / "raw_predictions.jsonl")[0]
    gated = runtime._read_jsonl(out / "gated_predictions.jsonl")[0]
    assert called == [1]
    assert raw["raw_prediction"] == {"label": "supported", "evidence_refs": ["M99"]}
    assert raw["score"]["citation_membership_valid"] is False
    assert gated["raw_label"] == "supported"
    assert gated["gated_label"] == "insufficient_evidence"
    assert summary["retries"] == 0


def test_provider_error_is_retained_and_stops_without_fallback_or_retry(tmp_path):
    called = []

    def transport(*args):
        called.append(args)
        return runtime.HTTPResult(403, b'{"error":"denied"}', {"content-type": "application/json"})

    summary = _run(tmp_path, transport, config_path=_config_with_request_cap(tmp_path, 10))
    progress = runtime._read_jsonl(tmp_path / "run" / "progress.jsonl")
    attempts = runtime._read_jsonl(tmp_path / "run" / "attempts.jsonl")
    assert len(called) == 1
    assert progress[0]["status"] == "HTTP_ERROR_403"
    assert all(row["status"] == "NOT_SENT_AFTER_STOP" for row in progress[1:10])
    assert summary["retries"] == 0
    assert "denied" in (tmp_path / "run" / "responses" / f"{progress[0]['request_id']}.json").read_text()
    assert all(row["auth_header_saved"] is False for row in attempts)


def test_hidden_fields_never_enter_built_monitor_payload():
    source = deepcopy(scripted_cases()[0])
    source["construction_truth"] = "CONSTRUCTION_ORACLE_SENTINEL"
    source["reference_answers"] = {"public_harm": "REFERENCE_ORACLE_SENTINEL"}
    source["expected_labels"] = {"public_harm": "PUBLIC_HARM_SENTINEL"}
    source["scoring_results"] = {"public_harm": True}
    source["T"]["private_reward_target"] = "POISON_PRIVATE_TARGET_SENTINEL"
    row = _make_llm_schedule(scripted_cases())[0]
    payload, _ = runtime.build_monitor_payload(source, row["baseline_id"], row["task"], row["permission"])
    http_payload = {"model": "deepseek-flash", **payload}
    text = runtime._json_bytes(http_payload).decode()
    assert all(marker not in text for marker in runtime.FORBIDDEN_TEXT_MARKERS)
    runtime._validate_payload(http_payload, row)
    poisoned_request = {**http_payload, "construction_truth": "CONSTRUCTION_ORACLE_SENTINEL"}
    with pytest.raises(runtime.BlindProjectionError, match="allowlist"):
        runtime._validate_payload(poisoned_request, row)


def test_synthetic_privileged_message_is_absent_from_public_only_and_present_only_when_authorized():
    source = deepcopy(scripted_cases()[0])
    marker = "SYNTHETIC_PRIVILEGED_MESSAGE_CANARY_DO_NOT_TRANSMIT"
    private_event = next(event for event in source["B"]["events"] if event["type"] == "message")
    private_event["content"]["text"] = marker

    public_payload, _ = runtime.build_monitor_payload(
        source, "B4_raw_fusion", "proposal", "public_only")
    privileged_payload, _ = runtime.build_monitor_payload(
        source, "B4_raw_fusion", "proposal", "privileged_audit")
    public_bytes = runtime._json_bytes({"model": "deepseek-flash", **public_payload})
    privileged_bytes = runtime._json_bytes({"model": "deepseek-flash", **privileged_payload})
    assert marker.encode("utf-8") not in public_bytes
    assert marker.encode("utf-8") in privileged_bytes
    row = next(row for row in _make_llm_schedule(scripted_cases())
               if row["baseline_id"] == "B4_raw_fusion"
               and row["task"] == "proposal" and row["permission"] == "public_only")
    runtime._validate_payload({"model": "deepseek-flash", **public_payload}, row)


def test_duplicate_logical_schedule_ids_fail_before_any_transport(monkeypatch):
    cases = scripted_cases()
    row = _make_llm_schedule(cases)[0]
    monkeypatch.setattr(runtime, "_make_llm_schedule", lambda _cases: [row] * 280)
    with pytest.raises(runtime.RuntimeIntegrityError, match="280 unique logical rows"):
        runtime.build_schedule()


def test_mock_manifest_and_results_mark_outputs_as_non_model_evidence(tmp_path):
    _run(tmp_path, runtime.mock_transport)
    run = tmp_path / "run"
    manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run / "summary.json").read_text(encoding="utf-8"))
    assert manifest["mode"] == "mock"
    assert manifest["mock_outputs_are_model_evidence"] is False
    assert manifest["fake_transport_only"] is True
    assert "scripts/run_sprint_monitor.py" in manifest["runtime_code_sha256"]
    assert "src/colluscope/sprint_metrics.py" in manifest["runtime_code_sha256"]
    assert summary["real_model_or_api_calls"] == 0
    assert summary["physical_http_attempts"] == 0
    assert summary["mock_is_behavior_evidence"] is False
