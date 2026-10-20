from __future__ import annotations

import json
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading

import pytest

from colluscope import deepseek_m4_v1 as runtime
from scripts import run_m4_b5_context_sensitivity as campaign
from scripts.run_m4_b5_context_sensitivity import (
    CampaignError,
    HIDDEN_RESEARCH_KEYS,
    MAX_ATTEMPTS,
    NEUTRAL_MESSAGE,
    _http_once,
    _load_schedule,
    _a1_pair_profile_audit,
    _build_public_request_manifest,
    _m4_request,
    _m4_sources,
    _parse_response,
    _production_request,
    _validate_public_request_manifest,
    compile_requests,
    dispatch,
    prepare,
)
from scripts.validate_synthetic_invariance_groups_v2 import _load_manifest


def _valid_response(*, model: str = "deepseek-flash", fingerprint: str = "offline-fp") -> bytes:
    return json.dumps({
        "model": model,
        "system_fingerprint": fingerprint,
        "usage": {"prompt_tokens": 128, "completion_tokens": 24},
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "content": None,
                "tool_calls": [{
                    "type": "function",
                    "function": {
                        "name": "report_evidence",
                        "arguments": json.dumps({"label": "present", "evidence_refs": []}),
                    },
                }],
            },
        }],
    }).encode()


def _assert_no_hidden_keys(value):
    if isinstance(value, dict):
        assert not any(str(key).casefold() in HIDDEN_RESEARCH_KEYS for key in value)
        for child in value.values():
            _assert_no_hidden_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_hidden_keys(child)


def test_frozen_schedule_compiles_all_assigned_requests_without_oracle_fields():
    schedule, schedule_raw = _load_schedule()
    rows, meta = compile_requests(schedule)
    assert len(rows) == MAX_ATTEMPTS == 232
    assert sum(row["block"] == "A1" for row in rows) == 72
    assert sum(row["block"] == "A2" for row in rows) == 160
    assert max(row["input_token_upper_bound"] for row in rows) <= 12_500
    assert {arm: sum(row["arm_id"] == arm for row in rows) for arm in {
        "A1-PUBLIC", "A1-PRIVILEGED-ORIGINAL", "A1-PRIVILEGED-NEUTRAL",
        "A2-V2-DIRECT", "A2-PRODUCTION-B5", "A2-PRODUCTION-ARITHMETIC",
        "A2-REVERSED-LABEL-ORDER",
    }} == {
        "A1-PUBLIC": 24, "A1-PRIVILEGED-ORIGINAL": 24,
        "A1-PRIVILEGED-NEUTRAL": 24, "A2-V2-DIRECT": 40,
        "A2-PRODUCTION-B5": 40, "A2-PRODUCTION-ARITHMETIC": 40,
        "A2-REVERSED-LABEL-ORDER": 40,
    }
    for row in rows:
        _assert_no_hidden_keys(json.loads(row["_body"]))
    profiles = _a1_pair_profile_audit(rows)
    assert profiles["public_vs_neutral"]["assigned_pairs"] == 24
    assert profiles["public_vs_neutral"]["unique_exact_input_profiles"] == 23
    assert profiles["public_vs_neutral"]["duplicate_cluster_sizes"] == [2]
    assert profiles["public_vs_original"]["unique_exact_input_profiles"] == 24
    assert profiles["neutral_vs_original"]["unique_exact_input_profiles"] == 24

    manifest = _build_public_request_manifest(rows, meta, schedule_raw)
    assert manifest["schema_version"] == 3
    assert manifest["private_source_file_hashes"] == {
        "runs/deepseek-first-m4/agent/episodes.jsonl": meta["m4_source_episodes_sha256"],
        "runs/deepseek-first-m4/agent/run_manifest.json": meta["m4_source_manifest_sha256"],
    }
    _validate_public_request_manifest(manifest, rows, meta, schedule_raw)
    tampered = copy.deepcopy(manifest)
    tampered["private_source_file_hashes"]["runs/deepseek-first-m4/agent/episodes.jsonl"] = "0" * 64
    with pytest.raises(CampaignError, match="PUBLIC_REQUEST_MANIFEST_DOES_NOT_MATCH_RECOMPILED_SOURCES"):
        _validate_public_request_manifest(tampered, rows, meta, schedule_raw)


def test_oversize_request_error_reports_the_frozen_runtime_cap(monkeypatch):
    monkeypatch.setattr(campaign, "MAX_INPUT_TOKENS", 1)
    schedule, _ = _load_schedule()
    with pytest.raises(CampaignError, match="FROZEN_REQUEST_EXCEEDS_1_INPUT_TOKEN_BOUND"):
        compile_requests(schedule)


def test_a1_public_neutral_and_privileged_views_keep_message_boundary():
    sources, _ = _m4_sources()
    source = sources[0]
    private_texts = [event["content"]["text"] for event in source["B"]["events"]
                     if event.get("type") == "message"]
    assert len(private_texts) == 2
    public_body, public_request = _m4_request(source, "public_only")
    privileged_body, privileged_request = _m4_request(source, "privileged_audit")
    neutral_body, neutral_request = _m4_request(source, "privileged_audit", neutral=True)

    assert not any(event.get("type") == "message"
                   for event in public_request["evidence"].get("events", []))
    assert all(text.encode("utf-8") not in public_body for text in private_texts)
    assert all(text.encode("utf-8") in privileged_body for text in private_texts)
    assert neutral_body.count(NEUTRAL_MESSAGE.encode("utf-8")) == 2
    assert all(text.encode("utf-8") not in neutral_body for text in private_texts)
    assert len(privileged_request["evidence"]["events"]) == len(neutral_request["evidence"]["events"])


def test_a2_arithmetic_aid_is_unranked_and_structured_oracle_keys_fail_closed():
    manifest, _ = _load_manifest()
    sample = next(variant["monitor_input"] for group in manifest["groups"]
                  for trajectory in group["trajectories"]
                  for variant in trajectory["variants"]
                  if variant["variant_id"] == "public_canonical")
    _body, compiled = _production_request(sample, add_arithmetic_table=True)
    user_text = compiled["payload"]["messages"][1]["content"]
    table = user_text.split("Public calculation aid:", 1)[1]
    assert sum(": total quality " in line for line in table.splitlines()) == 6
    assert not any(word in table.casefold() for word in (
        "optimum", "optimal", "regret", "realized welfare", "reference label", "ground truth"))
    payload_with_leak = dict(compiled["payload"])
    payload_with_leak["scoring_reference"] = "present"
    with pytest.raises(CampaignError, match="A2_REQUEST_CONTAINS_ORACLE_OR_ROUTING_METADATA"):
        from scripts.run_m4_b5_context_sensitivity import _assert_no_hidden_research_keys
        _assert_no_hidden_research_keys(
            payload_with_leak, error_code="A2_REQUEST_CONTAINS_ORACLE_OR_ROUTING_METADATA")


def test_strict_response_parser_accepts_valid_tool_and_rejects_non_tool_or_bad_arguments():
    parsed = _parse_response(_valid_response())
    assert parsed["finish_reason"] == "tool_calls"
    assert parsed["prediction"] == {"label": "present", "evidence_refs": []}

    wrong_finish = json.loads(_valid_response())
    wrong_finish["choices"][0]["finish_reason"] = "stop"
    with pytest.raises(Exception):
        _parse_response(json.dumps(wrong_finish).encode())

    malformed = json.loads(_valid_response())
    malformed["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = "{"
    with pytest.raises(Exception):
        _parse_response(json.dumps(malformed).encode())


def test_http_transport_uses_loopback_canary_only_when_explicit_and_never_follows_redirects():
    seen = {"count": 0, "authorized": False}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            seen["count"] += 1
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            seen["authorized"] = self.headers.get("Authorization") == "Bearer fake-key"
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://example.invalid/should-not-follow")
                self.end_headers()
                return
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Request-Id", "offline-canary")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with pytest.raises(CampaignError, match="PRODUCTION_ENDPOINT_IS_NOT_OFFICIAL_DEEPSEEK"):
            _http_once(b"{}", "fake-key", endpoint=base + "/chat/completions")
        status, raw, headers, _elapsed = _http_once(
            b"{}", "fake-key", endpoint=base + "/chat/completions", allow_loopback_test=True)
        assert status == 200 and raw == b'{"ok":true}'
        assert seen["authorized"] is True
        assert "authorization" not in headers
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_http_transport_rejects_loopback_redirect_without_following_offsite_target():
    seen = {"count": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            seen["count"] += 1
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(302)
            self.send_header("Location", "http://example.invalid/no")
            self.end_headers()

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_port}/redirect"
    try:
        status, _body, _headers, _elapsed = _http_once(
            b"{}", "fake-key", endpoint=endpoint, allow_loopback_test=True)
        assert status == 302
        assert seen["count"] == 1
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_interrupted_request_is_terminalized_without_resending(tmp_path: Path):
    out = tmp_path / "campaign"
    prepare(out, test_mode=True)
    calls = []

    def interrupt(_body, _key):
        calls.append(1)
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        dispatch(out, transport=interrupt, test_mode=True)
    ledger = out / "request_ledger.jsonl"
    first_start = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    assert first_start["event"] == "attempt_started"
    assert first_start["auth_header_saved"] is False

    def should_not_call(_body, _key):
        calls.append(2)
        return 200, _valid_response(), {}

    with pytest.raises(CampaignError, match="PRIOR_FAILURE_OR_INTERRUPTION_TERMINAL_NO_RESUME"):
        dispatch(out, transport=should_not_call, test_mode=True)
    assert calls == [1]
    results = [json.loads(line) for line in (out / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(results) == 1
    assert results[0]["status"] == "INTERRUPTED_UNKNOWN_OUTCOME"


def test_http_failure_is_preserved_and_resume_never_retries_or_replaces(tmp_path: Path):
    out = tmp_path / "campaign"
    prepare(out, test_mode=True)
    calls = []

    def fail_second(_body, _key):
        calls.append(len(calls) + 1)
        if len(calls) == 1:
            return 200, _valid_response(), {}
        return 500, b"synthetic-server-failure", {}

    result = dispatch(out, transport=fail_second, test_mode=True)
    assert result["attempts_total"] == 2
    assert result["unattempted"] == MAX_ATTEMPTS - 2
    assert calls == [1, 2]
    responses = [json.loads(line) for line in (out / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [row["status"] for row in responses] == ["HTTP_200_VALID", "HTTP_500"]
    assert (out / responses[1]["response_path"]).read_bytes() == b"synthetic-server-failure"
    with pytest.raises(CampaignError, match="PRIOR_FAILURE_OR_INTERRUPTION_TERMINAL_NO_RESUME"):
        dispatch(out, transport=lambda *_: calls.append(3), test_mode=True)
    assert calls == [1, 2]


def test_tampered_prepared_request_is_rejected_before_transport(tmp_path: Path):
    out = tmp_path / "campaign"
    manifest = prepare(out, test_mode=True)
    schedule, _ = _load_schedule()
    rows, _ = compile_requests(schedule)
    request = rows[0]
    path = out / "requests" / f"{request['request_id']}.bin"
    path.write_bytes(path.read_bytes() + b" ")
    calls = []
    with pytest.raises(CampaignError, match="PREPARED_REQUEST_MISSING_OR_TAMPERED"):
        dispatch(out, transport=lambda *_: calls.append(1), test_mode=True)
    assert calls == []
    assert manifest["assigned"] == MAX_ATTEMPTS


def test_model_fingerprint_drift_stops_without_retry(tmp_path: Path):
    out = tmp_path / "campaign"
    prepare(out, test_mode=True)
    calls = []

    def drift(_body, _key):
        calls.append(1)
        return 200, _valid_response(model="different-model"), {}

    result = dispatch(out, transport=drift, test_mode=True)
    assert result["attempts_total"] == 1
    assert result["stop_reason"] == "IDENTITY_MISMATCH"
    with pytest.raises(CampaignError, match="PRIOR_FAILURE_OR_INTERRUPTION_TERMINAL_NO_RESUME"):
        dispatch(out, transport=drift, test_mode=True)
    assert calls == [1]


def test_full_mock_dispatch_enforces_232_attempt_cap_and_completes_once(tmp_path: Path):
    out = tmp_path / "campaign"
    prepare(out, test_mode=True)
    calls = []

    def success(_body, _key):
        calls.append(1)
        return 200, _valid_response(), {"content-type": "application/json"}

    result = dispatch(out, transport=success, test_mode=True)
    assert result["status"] == "COMPLETE"
    assert result["attempts_total"] == MAX_ATTEMPTS == 232
    assert len(calls) == 232
    second = dispatch(out, transport=success, test_mode=True)
    assert second["status"] == "ALREADY_COMPLETE"
    assert len(calls) == 232
    events = [json.loads(line) for line in (out / "campaign_events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["event"] == "campaign_complete"
    assert not (out / "stop.json").exists()
