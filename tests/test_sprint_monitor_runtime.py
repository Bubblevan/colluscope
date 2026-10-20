from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts import run_sprint_monitor as runtime
from colluscope.sprint_controls import scripted_cases
from scripts.prepare_sprint_baselines import _make_llm_schedule


def _config_with_request_cap(tmp_path: Path, cap: int = 1) -> Path:
    text = runtime.CONFIG_PATH.read_text(encoding="utf-8")
    text = text.replace("max_logical_requests = 280", f"max_logical_requests = {cap}")
    text = text.replace("max_http_attempts = 280", f"max_http_attempts = {cap}")
    path = tmp_path / f"runtime-cap-{cap}.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _response(content: str, *, status: int = 200, model: str = "deepseek-flash",
              fingerprint: str = "mock-fingerprint") -> runtime.HTTPResult:
    body = json.dumps({
        "model": model,
        "system_fingerprint": fingerprint,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
    }, separators=(",", ":")).encode("utf-8")
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


def test_offline_mock_end_to_end_terminalizes_all_280_without_model_claim(tmp_path):
    summary = _run(tmp_path, runtime.mock_transport)
    run = tmp_path / "run"
    progress = runtime._read_jsonl(run / "progress.jsonl")
    attempts = runtime._read_jsonl(run / "attempts.jsonl")
    assert summary["status"] == "OFFLINE_MOCK_COMPLETE"
    assert summary["assigned_rows"] == summary["terminal_rows"] == 280
    assert summary["completed_rows"] == 280
    assert summary["real_model_or_api_calls"] == 0
    assert summary["mock_is_behavior_evidence"] is False
    assert len(progress) == 280 and len({row["request_id"] for row in progress}) == 280
    assert sum(row["event"] == "attempt_started" for row in attempts) == 280
    assert sum(row["event"] == "attempt_terminal" for row in attempts) == 280
    assert len(list((run / "requests").glob("*.json"))) == 280
    assert len(list((run / "responses").glob("*.json"))) == 280
    assert all(row["status"] == "COMPLETED" for row in progress)
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
    assert summary["logical_http_requests"] == summary["physical_http_attempts"] == 1
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
    assert summary["logical_http_requests"] == summary["physical_http_attempts"] == 1
    assert summary["retries"] == 0
    assert len(progress) == 280


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
    assert summary["real_model_or_api_calls"] == 0
    assert summary["mock_is_behavior_evidence"] is False
