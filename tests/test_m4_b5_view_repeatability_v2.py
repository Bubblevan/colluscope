from __future__ import annotations

from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

import pytest

from scripts import run_m4_b5_view_repeatability_v2 as runner


CANARY_ROOT = runner.ROOT / "runs/sprint-monitor/m4-b5-view-repeatability-v2-offline-canaries"


def _run_dir(name: str) -> Path:
    out = CANARY_ROOT / name
    runner.prepare(out, test_mode=True)
    return out


def _tool_response(*, malformed: bool = False) -> bytes:
    arguments = "not-json" if malformed else json.dumps({"label": "absent", "evidence_refs": []})
    return json.dumps({
        "model": "deepseek-flash",
        "system_fingerprint": "offline-canary-fingerprint",
        "usage": {"prompt_tokens": 10, "completion_tokens": 4},
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {"tool_calls": [{
                "type": "function",
                "function": {"name": "report_evidence", "arguments": arguments},
            }]},
        }],
    }).encode("utf-8")


class _Server:
    def __init__(self, *, first_status: int = 200, first_malformed: bool = False):
        self.count = 0
        self.auth_seen = 0
        self.first_status = first_status
        self.first_malformed = first_malformed
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                _ = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                outer.count += 1
                if self.headers.get("Authorization") == "Bearer offline-test-key-never-saved":
                    outer.auth_seen += 1
                if outer.count == 1 and outer.first_status != 200:
                    status, body = outer.first_status, b"offline-server-error"
                else:
                    status = 200
                    body = _tool_response(malformed=outer.first_malformed and outer.count == 1)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("X-Request-Id", f"offline-{outer.count}")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/chat/completions"

    def close(self):
        self.httpd.shutdown()
        self.thread.join(timeout=5)
        self.httpd.server_close()

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()


def _transport(body: bytes, key: str, endpoint: str):
    return runner._local_test_transport(body, key, endpoint)


def test_prepare_freezes_144_hash_only_repeated_requests():
    out = _run_dir("prepare-only")
    summary = runner.prepare(out, test_mode=True)
    assert summary["status"] == "PREPARED_OFFLINE_NO_CALLS"
    assert summary["assigned"] == 144
    assert summary["public_only"] == 72
    assert summary["privileged_original"] == 72
    assert summary["model_calls"] == 0
    rows = json.loads((out / "request_manifest.json").read_bytes())["request_rows"]
    assert len(rows) == 144
    profiles = {}
    for row in rows:
        profiles.setdefault((row["unit_sha256"], row["view"]), set()).add(row["body_sha256"])
    assert len(profiles) == 48
    assert all(len(digests) == 1 for digests in profiles.values())
    for row in rows:
        body = (out / "requests" / f"{row['request_id']}.bin").read_bytes()
        assert not body.startswith(b"Authorization")
        assert b"offline-test-key-never-saved" not in body


def test_loopback_fake_server_keeps_invalid_output_and_resume_never_resends():
    out = _run_dir("malformed-first-response")
    with _Server(first_malformed=True) as server:
        summary = runner.dispatch(out, test_mode=True, endpoint=server.url, transport=_transport)
        assert summary["status"] in {"COMPLETE", "ALREADY_COMPLETE"}
        assert summary["assigned"] == summary["attempts_total"] == 144
        assert summary["new_attempts"] in {0, 144}
        assert summary["unattempted"] == 0
        assert server.count == server.auth_seen == summary["new_attempts"]

        results = runner.read_jsonl(out / "results.jsonl")
        counts = Counter(row["status"] for row in results)
        assert counts["HTTP_200_INVALID_OUTPUT"] == 1
        assert counts["HTTP_200_VALID"] == 143
        assert sum(row["parse_error_code"] is not None for row in results) == 1
        assert all(row.get("auth_header_saved") is False for row in results)
        assert all("authorization" not in {key.lower() for key in row.get("safe_response_headers", {})}
                   for row in results)
        for filename in ("request_ledger.jsonl", "results.jsonl", "campaign_events.jsonl"):
            artifact = out / filename
            if artifact.exists():
                assert b"offline-test-key-never-saved" not in artifact.read_bytes()

        repeated = runner.dispatch(out, test_mode=True, endpoint=server.url, transport=_transport)
        assert repeated["status"] == "ALREADY_COMPLETE"
        assert repeated["new_attempts"] == 0
        assert server.count == 0


def test_http_error_is_terminal_and_never_retried():
    out = _run_dir("http-400-first-response")
    with _Server(first_status=400) as server:
        try:
            summary = runner.dispatch(out, test_mode=True, endpoint=server.url, transport=_transport)
            assert summary["status"] == "STOPPED_WITH_UNATTEMPTED_ROWS"
            assert summary["attempts_total"] == summary["new_attempts"] == 1
            assert summary["unattempted"] == 143
            assert summary["stop_reason"] == "TRANSPORT_OR_HTTP_FAILURE"
        except runner.RunnerError as exc:
            assert str(exc) == "PRIOR_STOP_REQUIRES_MANUAL_REVIEW"
        starts = [row for row in runner.read_jsonl(out / "request_ledger.jsonl")
                  if row.get("event") == "attempt_started"]
        assert len(starts) == 1 and starts[0]["retry"] is False
        assert server.count in {0, 1}
        with pytest.raises(runner.RunnerError, match="PRIOR_STOP_REQUIRES_MANUAL_REVIEW"):
            runner.dispatch(out, test_mode=True, endpoint=server.url, transport=_transport)
        assert server.count in {0, 1}


def test_interrupted_started_slot_is_terminalized_and_not_resubmitted():
    out = _run_dir("interrupted-before-response-v3")
    manifest = json.loads((out / "request_manifest.json").read_bytes())
    first = manifest["request_rows"][0]
    existing_starts = [row for row in runner.read_jsonl(out / "request_ledger.jsonl")
                       if row.get("event") == "attempt_started"]
    if not existing_starts:
        runner.append_jsonl(out / "request_ledger.jsonl", {
            "event": "attempt_started", "request_id": first["request_id"],
            "body_sha256": first["body_sha256"], "at_utc": runner.iso_now(),
            "retry": False,
        })
    with _Server() as server:
        summary = runner.dispatch(out, test_mode=True, endpoint=server.url, transport=_transport)
        assert summary["status"] in {"COMPLETE", "ALREADY_COMPLETE"}
        assert summary["attempts_total"] == 144
        assert summary["new_attempts"] in {0, 143}
        assert summary["unattempted"] == 0
        assert server.count == summary["new_attempts"]
        results = {row["request_id"]: row for row in runner.read_jsonl(out / "results.jsonl")}
        assert results[first["request_id"]]["status"] == "INTERRUPTED_UNKNOWN_OUTCOME"
        starts = [row for row in runner.read_jsonl(out / "request_ledger.jsonl")
                  if row.get("event") == "attempt_started"]
        assert len(starts) == len({row["request_id"] for row in starts}) == 144
        recovery = [row for row in runner.read_jsonl(out / "campaign_events.jsonl")
                    if row.get("event") == "interrupted_attempts_terminalized_no_resend"]
        assert len(recovery) == 1


def test_offline_transport_rejects_non_loopback_target_before_sending():
    out = _run_dir("wrong-endpoint")
    with pytest.raises(runner.RunnerError, match="OFFLINE_TEST_ENDPOINT_MUST_BE_LOOPBACK_HTTP"):
        runner.dispatch(out, test_mode=True, endpoint="https://example.invalid/api",
                        transport=lambda *_args: pytest.fail("transport must not be called"))


def test_production_dispatch_fails_closed_before_credentials_when_unregistered():
    with pytest.raises(runner.RunnerError, match="NEW_EXPERIMENT_NOT_REGISTERED"):
        runner.dispatch(runner.RUN_ROOT)
