from __future__ import annotations

import hashlib
import json
import os
import queue
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from colluscope.m1_runtime import RequestAdapter, RequestBudget, RequestFailure
from colluscope.openai_compat_vllm import LocalVLLMBackend
from test_openai_compat_vllm import FakeCounter, OFFLINE_CONFIG, completion, request_for, valid_config


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = os.environ.get("COLLUSCOPE_OFFLINE_HTTP_EVIDENCE")
_EVIDENCE_LOCK = threading.Lock()


def _record(scenario: str, record: dict):
    if not EVIDENCE_PATH:
        return
    path = Path(EVIDENCE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {"scenario": scenario, "external_model_calls": 0, "paid_api_calls": 0, **record}
    with _EVIDENCE_LOCK, path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = None
        mode = self.server.modes.get_nowait() if not self.server.modes.empty() else "success"
        received = {
            "path": self.path,
            "method": "POST",
            "authorization_header_present": self.headers.get("Authorization") is not None,
            "body_utf8": body.decode("utf-8", errors="replace"),
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "payload": payload,
            "mode": mode,
        }
        self.server.audit.append(received)
        self.audit_record = received
        if mode == "oneof_unsupported":
            schema = (((payload or {}).get("response_format") or {}).get("json_schema") or {}).get("schema")
            if schema and "oneOf" in schema:
                self._respond(400, {"error": {"message": "offline canary: schema keyword oneOf unsupported"}})
                return
        if mode == "server_error":
            self._respond(503, {"error": {"message": "offline canary: transient server busy"}})
            return
        if mode == "timeout":
            time.sleep(1.2)
        if mode == "malformed_content":
            text = "{malformed action"
        elif (payload or {}).get("response_format", {}).get("json_schema", {}).get("name") == "m1_p0_communication_action":
            text = '{"type":"no_message"}'
        else:
            text = '{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'
        result = completion(text)
        result["id"] = "offline-http-canary"
        self._respond(200, result)

    def _respond(self, status: int, value):
        body = value if isinstance(value, bytes) else json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.audit_record["response_status"] = status
        self.audit_record["response_body"] = body.decode("utf-8", errors="replace")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            self.audit_record["client_closed_before_response"] = True

    def log_message(self, *_args):
        return


class OfflineHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, modes=()):
        super().__init__(("127.0.0.1", 0), _Handler)
        self.modes = queue.Queue()
        for mode in modes:
            self.modes.put(mode)
        self.audit = []
        self.thread = threading.Thread(target=self.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.shutdown()
        self.server_close()
        self.thread.join(timeout=2)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server_port}/v1"


def _adapter(server, *, timeout=3, attempts=2, max_attempts=2, max_requests=2):
    settings = valid_config(base_url=server.base_url, timeout_seconds=timeout)
    backend = LocalVLLMBackend(settings, FakeCounter(), opener=None)
    budget = RequestBudget(max_requests, max_attempts, attempts)
    return settings, backend, RequestAdapter(backend, OFFLINE_CONFIG, budget), budget


def _request(settings, kind="ballot", request_id="req-http", timeout=3):
    request = request_for(settings, request_id=request_id, action_kind=kind)
    return type(request)(request.request_id, request.action_kind, request.agent_id, request.model_id,
                         request.sampling, timeout, request.observation_sha256, request.prompt,
                         request.generation_seed)


def test_real_adapter_http_success_transmits_ballot_and_oneof_schemas_and_exact_hashes():
    with OfflineHTTPServer() as server:
        settings, backend, adapter, budget = _adapter(server)
        for index, kind in enumerate(("message", "ballot")):
            action = _request(settings, kind=kind, request_id=f"req-{kind}-{index}")
            response = adapter.invoke(action)
            assert response.startswith("{")
        assert len(server.audit) == 2
        assert server.audit[0]["payload"]["response_format"]["json_schema"]["schema"]["oneOf"]
        assert server.audit[1]["payload"]["response_format"]["json_schema"]["schema"]["type"] == "object"
        for record, adapter_row in zip(server.audit, adapter.records, strict=True):
            metadata = adapter_row["transport"]
            schema_name = record["payload"]["response_format"]["json_schema"]["name"]
            schema_file = ("communication.schema.json" if schema_name == "m1_p0_communication_action"
                           else "ballot.schema.json")
            schema_bytes = (ROOT / "prompts" / "m1-p0-v2" / schema_file).read_bytes()
            assert record["payload"]["response_format"]["json_schema"]["schema"] == json.loads(schema_bytes)
            assert metadata["action_schema_sha256"] == hashlib.sha256(schema_bytes).hexdigest()
            assert metadata["generation_seed"] == record["payload"]["seed"]
            assert hashlib.sha256(record["body_utf8"].encode()).hexdigest() == record["body_sha256"]
            assert metadata["payload_sha256"] == record["body_sha256"]
            assert record["authorization_header_present"] is False
        assert budget.logical_requests == budget.attempts == 2
        _record("successful_ballot_and_oneof_schema", {"requests": server.audit,
                "logical_requests": budget.logical_requests, "attempts": budget.attempts})


def test_unsupported_oneof_is_explicitly_rejected_and_raw_error_is_retained():
    with OfflineHTTPServer(("oneof_unsupported",)) as server:
        settings, _, adapter, budget = _adapter(server)
        action = _request(settings, kind="message")
        with pytest.raises(RequestFailure, match="HTTP 400") as error:
            adapter.invoke(action)
        assert "oneOf unsupported" in error.value.raw_response
        assert len(server.audit) == 1
        assert adapter.records[0]["status"] == "failed"
        assert adapter.records[0]["retryable"] is False
        assert budget.attempts == 1
        _record("unsupported_oneof", {"requests": server.audit, "failure": adapter.records[0]})


def test_malformed_action_from_successful_http_response_is_not_repaired():
    from colluscope.m1_runtime import _parse_action

    with OfflineHTTPServer(("malformed_content",)) as server:
        settings, _, adapter, _ = _adapter(server)
        raw = adapter.invoke(_request(settings))
        with pytest.raises(ValueError, match="malformed JSON"):
            _parse_action(raw, "ballot")
        assert raw == "{malformed action"
        assert len(server.audit) == 1
        assert adapter.records[0]["status"] == "response_returned"
        _record("malformed_action_no_repair", {"requests": server.audit,
                "adapter_record": adapter.records[0], "parser_rejected": True})


def test_timeout_is_physically_retried_twice_and_both_attempts_are_recorded():
    with OfflineHTTPServer(("timeout", "timeout")) as server:
        settings, _, adapter, budget = _adapter(server, timeout=1)
        with pytest.raises(RequestFailure, match="timeout after 2 attempt"):
            adapter.invoke(_request(settings, timeout=1))
        assert len(adapter.records) == 2
        assert [row["status"] for row in adapter.records] == ["retryable_failure", "failed"]
        assert budget.attempts == 2
        _record("timeout_two_attempts", {"requests": server.audit, "adapter_records": adapter.records,
                "logical_requests": budget.logical_requests, "attempts": budget.attempts})


def test_connection_refusal_is_bounded_and_recorded():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        unused_port = probe.getsockname()[1]
    settings = valid_config(base_url=f"http://127.0.0.1:{unused_port}/v1", timeout_seconds=1)
    backend = LocalVLLMBackend(settings, FakeCounter())
    budget = RequestBudget(1, 2, 2)
    adapter = RequestAdapter(backend, OFFLINE_CONFIG, budget)
    with pytest.raises(RequestFailure, match="after 2 attempt"):
        adapter.invoke(_request(settings, timeout=1))
    assert len(adapter.records) == 2
    assert adapter.records[-1]["status"] == "failed"
    assert budget.attempts == 2
    _record("connection_refusal", {"adapter_records": adapter.records, "logical_requests": budget.logical_requests,
            "attempts": budget.attempts})


def test_duplicate_request_id_cannot_reach_server_twice():
    with OfflineHTTPServer() as server:
        settings, _, adapter, budget = _adapter(server, max_requests=1, max_attempts=2)
        action = _request(settings)
        adapter.invoke(action)
        with pytest.raises(RequestFailure, match="cannot be reused"):
            adapter.invoke(action)
        assert len(server.audit) == 1
        assert adapter.records[-1]["status"] == "not_started_duplicate_request_id"
        _record("duplicate_request_id", {"requests": server.audit, "adapter_records": adapter.records,
                "logical_requests": budget.logical_requests, "attempts": budget.attempts})


def test_retry_cannot_bypass_global_attempt_budget():
    with OfflineHTTPServer(("server_error",)) as server:
        settings, _, adapter, budget = _adapter(server, max_requests=1, max_attempts=1)
        with pytest.raises(RequestFailure, match="attempt hard limit"):
            adapter.invoke(_request(settings))
        assert len(server.audit) == 1
        assert [row["status"] for row in adapter.records] == ["retryable_failure", "not_started_budget_exhausted"]
        assert budget.attempts == 1
        _record("global_retry_budget", {"requests": server.audit, "adapter_records": adapter.records,
                "logical_requests": budget.logical_requests, "attempts": budget.attempts})
