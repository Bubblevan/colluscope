from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts import freeze_b5_invariance_schedule as freeze
from scripts import project_monitor_http_request_v2 as projector
from scripts import run_b5_invariance as runner
from scripts import score_b5_invariance_run as scorer


def _response(label: str = "absent", *, model: str = "deepseek-flash",
              fingerprint: str = "offline-test-only") -> tuple[int, bytes, dict[str, str]]:
    value = {
        "id": "offline-test-only",
        "model": model,
        "system_fingerprint": fingerprint,
        "choices": [{"index": 0, "finish_reason": "tool_calls",
                     "message": {"role": "assistant", "tool_calls": [{
                         "id": "call-test", "type": "function",
                         "function": {"name": "report_evidence", "arguments": json.dumps({
                             "label": label, "evidence_refs": []})},
                     }]}}],
        "usage": {"prompt_tokens": 30, "completion_tokens": 8, "total_tokens": 38},
    }
    return 200, json.dumps(value).encode(), {"content-type": "application/json"}


def test_frozen_schedule_has_120_unique_rows_and_metadata_stays_out_of_body():
    schedule = freeze.build()
    assert len(schedule["rows"]) == 120
    assert len({row["request_id"] for row in schedule["rows"]}) == 120
    assert sum(row["trajectory_id"] == "primary" for row in schedule["rows"]) == 100
    assert sum(row["trajectory_id"] == "label_flip_positive_control" for row in schedule["rows"]) == 20
    manifest = json.loads(freeze.MANIFEST.read_bytes())
    group_ids = {group["group_id"] for group in manifest["groups"]}
    prompt = freeze.PROMPT_PATH.read_text(encoding="utf-8")
    for group in manifest["groups"]:
        for trajectory in group["trajectories"]:
            for variant in trajectory["variants"]:
                if variant["variant_id"] not in freeze.VARIANTS and not (
                        trajectory["trajectory_id"] == "label_flip_positive_control"
                        and variant["variant_id"] == "public_canonical"):
                    continue
                body = projector.serialize_http_request(
                    projector.project_variant_http_request(prompt, variant))
                assert not any(group_id.encode() in body for group_id in group_ids)
                assert b"scoring_reference" not in body
                assert b"primary_label" not in body
                assert b'"split"' not in body


def test_runner_records_all_calls_and_never_persists_auth_header(tmp_path: Path):
    out = tmp_path / "run"
    calls: list[bytes] = []

    def fake(body: bytes, _key: str):
        calls.append(body)
        return _response()

    result = runner.run(out, test_mode=True, transport=fake)
    assert result["status"] == "COMPLETE"
    assert result["assigned"] == 120
    assert result["physical_attempts_total"] == 120
    assert len(calls) == 120
    attempts = runner.read_jsonl(out / "attempts.jsonl")
    assert sum(row.get("event") == "attempt_started" for row in attempts) == 120
    assert sum(row.get("event") == "attempt_terminal" for row in attempts) == 120
    assert b"Authorization" not in (out / "attempts.jsonl").read_bytes()
    assert b"mock-key-for-test" not in b"".join(path.read_bytes() for path in out.rglob("*") if path.is_file())


def test_transport_failure_is_retained_and_resume_does_not_retry_failed_id(tmp_path: Path):
    out = tmp_path / "run"
    first_ids: list[str] = []

    def fail_first(_body: bytes, _key: str):
        first_ids.append("first")
        raise TimeoutError("simulated offline transport failure")

    first = runner.run(out, test_mode=True, transport=fail_first)
    assert first["status"] == "STOPPED_WITH_UNSENT_ROWS"
    assert first["physical_attempts_total"] == 1
    first_id = next(row["request_id"] for row in runner.read_jsonl(out / "attempts.jsonl")
                    if row.get("event") == "attempt_started")
    second_calls: list[bytes] = []

    def success(body: bytes, _key: str):
        second_calls.append(body)
        return _response()

    second = runner.run(out, test_mode=True, transport=success)
    assert second["status"] == "COMPLETE"
    assert second["physical_attempts_total"] == 120
    assert len(second_calls) == 119
    assert sum(row.get("request_id") == first_id and row.get("event") == "attempt_started"
               for row in runner.read_jsonl(out / "attempts.jsonl")) == 1


def test_malformed_success_response_is_not_repaired_or_retried(tmp_path: Path):
    out = tmp_path / "run"

    def malformed(_body: bytes, _key: str):
        return 200, b'{"model":"deepseek-flash","system_fingerprint":"offline-test-only","choices":[{"finish_reason":"length","message":{}}]}', {}

    result = runner.run(out, test_mode=True, transport=malformed)
    assert result["physical_attempts_total"] == 120
    row = runner.read_jsonl(out / "results.jsonl")[0]
    assert row["http_status"] == 200
    assert row["parse_error_code"] == "FINISH_REASON_NOT_TOOL_CALLS"
    assert row["parsed"] is None
    assert len([row for row in runner.read_jsonl(out / "attempts.jsonl")
                if row.get("event") == "attempt_started"]) == 120


def test_preexisting_unclosed_attempt_is_terminalized_and_never_resent(tmp_path: Path):
    out = tmp_path / "run"
    schedule, raw = runner.load_schedule()
    out.mkdir()
    (out / "schedule.json").write_bytes(raw)
    first = schedule["rows"][0]
    body = runner.frozen_request(first)
    req = out / "requests" / f"{first['request_id']}.json"
    req.parent.mkdir()
    req.write_bytes(body)
    runner.append(out / "attempts.jsonl", {"event": "attempt_started",
                                             "request_id": first["request_id"],
                                             "schedule_sha256": runner.sha(raw),
                                             "body_sha256": runner.sha(body),
                                             "request_path": f"requests/{first['request_id']}.json",
                                             "reserved_peak_usd": (len(body) * runner.RATE_INPUT_PEAK
                                                                   + 512 * runner.RATE_OUTPUT_PEAK)})
    calls: list[bytes] = []

    def success(body: bytes, _key: str):
        calls.append(body)
        return _response()

    result = runner.run(out, test_mode=True, transport=success)
    assert result["physical_attempts_total"] == 120
    assert len(calls) == 119
    recovered = next(row for row in runner.read_jsonl(out / "results.jsonl")
                     if row["request_id"] == first["request_id"])
    assert recovered["status"] == "INTERRUPTED_UNKNOWN_OUTCOME"
    assert recovered["parsed"] is None


def test_hard_call_and_cost_caps_are_enforced(tmp_path: Path, monkeypatch):
    out = tmp_path / "run"
    monkeypatch.setattr(runner, "MAX_CALLS", 1)
    calls: list[bytes] = []

    def success(body: bytes, _key: str):
        calls.append(body)
        return _response()

    result = runner.run(out, test_mode=True, transport=success)
    assert result["physical_attempts_total"] == 1
    assert len(calls) == 1
    assert result["unsent"] == 119

    out2 = tmp_path / "cost-run"
    monkeypatch.setattr(runner, "MAX_CALLS", 120)
    monkeypatch.setattr(runner, "MAX_RESERVED_USD", 0.0000001)
    call_count_before = len(calls)
    with pytest.raises(RuntimeError, match="complete frozen schedule exceeds"):
        runner.run(out2, test_mode=True, transport=success)
    assert len(calls) == call_count_before


def test_http_non_200_aborts_without_retry_and_saves_body(tmp_path: Path):
    out = tmp_path / "run"

    def http_400(_body: bytes, _key: str):
        return 400, b'{"error":"fixture"}', {"content-type": "application/json"}

    result = runner.run(out, test_mode=True, transport=http_400)
    assert result["physical_attempts_total"] == 1
    assert result["unsent"] == 119
    row = runner.read_jsonl(out / "results.jsonl")[0]
    assert row["http_status"] == 400
    assert (out / row["response_path"]).read_bytes() == b'{"error":"fixture"}'


def test_returned_model_mismatch_and_fingerprint_drift_stop_dispatch(tmp_path: Path):
    wrong_model_out = tmp_path / "wrong-model"
    calls = []

    def wrong_model(body: bytes, _key: str):
        calls.append(body)
        return _response(model="deepseek-v4-pro")

    wrong = runner.run(wrong_model_out, test_mode=True, transport=wrong_model)
    assert wrong["physical_attempts_total"] == 1
    assert wrong["stop_reason"] == "MODEL_IDENTITY_MISMATCH"
    assert runner.read_jsonl(wrong_model_out / "results.jsonl")[0]["identity_mismatch"] is True

    drift_out = tmp_path / "fingerprint-drift"
    calls.clear()

    def drift(body: bytes, _key: str):
        calls.append(body)
        fingerprint = "fingerprint-a" if len(calls) == 1 else "fingerprint-b"
        return _response(fingerprint=fingerprint)

    drift_result = runner.run(drift_out, test_mode=True, transport=drift)
    assert drift_result["physical_attempts_total"] == 2
    assert drift_result["stop_reason"] == "PROVIDER_FINGERPRINT_DRIFT"
    assert runner.read_jsonl(drift_out / "results.jsonl")[1]["fingerprint_drift"] is True


def test_production_dispatch_is_pinned_to_single_authorized_run_root(tmp_path: Path):
    output = tmp_path / "other-run"
    with pytest.raises(PermissionError, match="sole authorized run directory"):
        runner.run(output, test_mode=False)
    assert not output.exists()


def test_independent_scorer_recomputes_references_and_keeps_mock_claim_limited(tmp_path: Path):
    out = tmp_path / "scored-run"
    out.mkdir()
    schedule, raw = runner.load_schedule()
    (out / "schedule.json").write_bytes(raw)
    attempts = []
    results = []
    manifest = json.loads(freeze.MANIFEST.read_bytes())
    public_event_by_group = {}
    for group in manifest["groups"]:
        primary = group["trajectories"][0]
        public = next(v for v in primary["variants"] if v["variant_id"] == "public_canonical")
        public_event_by_group[group["group_id"]] = public["monitor_input"]["events"][0]["event_id"]
    for row in schedule["rows"]:
        body = runner.frozen_request(row)
        path = out / "requests" / f"{row['request_id']}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(body)
        attempts.append({"event": "attempt_started", "request_id": row["request_id"],
                         "body_sha256": runner.sha(body),
                         "request_path": f"requests/{row['request_id']}.json"})
        results.append({"request_id": row["request_id"], "http_status": 200,
                        "parsed": {"prediction": {"label": row["scoring_reference"],
                                                   "evidence_refs": [public_event_by_group[row["group_id"]]]}},
                        "identity_mismatch": False, "fingerprint_drift": False})
    (out / "attempts.jsonl").write_text("".join(json.dumps(x) + "\n" for x in attempts), encoding="utf-8")
    (out / "results.jsonl").write_text("".join(json.dumps(x) + "\n" for x in results), encoding="utf-8")
    summary = scorer.score(out)
    assert summary["physical_attempts"] == 120
    assert summary["independent_reference_metadata_mismatches"] == 0
    assert summary["public_primary_exact_of_20"] == 20
    assert summary["public_positive_control_exact_of_20"] == 20
    assert summary["decision_gate"] == "SUPPORT_LOW_INSTABILITY"
    assert summary["collusion_gold_label_created"] is False
