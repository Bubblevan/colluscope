import json

from scripts import run_monitor_recovery_diagnostic as diagnostic


def test_offline_monitor_diagnostic_builds_exact_payloads_without_gold_labels():
    requests = diagnostic._build_requests()
    assert len(requests) == 16
    assert len({row["schedule"]["request_id"] for row in requests}) == 16
    for row in requests:
        payload = json.loads(row["body"])
        assert payload["model"] == "deepseek-flash"
        assert payload["thinking"] == {"type": "disabled"}
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["max_tokens"] == 256
        assert set(payload) == {"model", "messages", "thinking", "temperature",
                                "max_tokens", "response_format", "stream"}
        wire = row["body"].decode("utf-8")
        assert row["schedule"]["case_ref"] not in wire
        assert "condition_id" not in wire
        assert "reference_answer" not in wire
        assert "construction_truth" not in wire
        assert "private_reward_target" not in wire
        assert row["schedule"]["assessable_reference"] is True


def test_monitor_recovery_request_schedule_has_required_positive_hard_negative_pairs():
    schedule = json.loads(diagnostic.SCHEDULE.read_bytes())
    rows = schedule["rows"]
    assert schedule["inference_authorized"] is False
    assert schedule["logical_request_limit"] == schedule["physical_http_limit"] == 16
    assert schedule["retry_limit"] == schedule["replacement_limit"] == 0
    for case_ref in ("SC-POS-01", "SC-NEG-02"):
        pair = [row for row in rows if row["case_ref"] == case_ref
                and row["task"] == "explicit_sequence" and row["permission"] == "privileged_audit"]
        assert {row["baseline_id"] for row in pair} == {"B4_raw_fusion", "B5_evidence_aware"}
        assert len(pair) == 2


def test_monitor_independent_auditor_never_counts_json_shaped_http_500_as_prediction():
    from scripts.audit_monitor_recovery_diagnostic import _http_success

    assert _http_success({"http_status": 200})
    assert not _http_success({"http_status": 500})
    assert not _http_success({"http_status": None})
    assert not _http_success({"http_status": "200"})


def test_monitor_diagnostic_manifest_binds_runner_auditor_prompts_and_source_controls():
    from scripts.audit_monitor_recovery_diagnostic import _verify_artifact_hashes

    hashes = diagnostic._artifact_hashes()
    assert "scripts/run_monitor_recovery_diagnostic.py" in hashes
    assert "scripts/audit_monitor_recovery_diagnostic.py" in hashes
    assert "data/sprint-baseline-v1/controls.jsonl" in hashes
    _verify_artifact_hashes(hashes)
    hashes["scripts/audit_monitor_recovery_diagnostic.py"] = "0" * 64
    try:
        _verify_artifact_hashes(hashes)
    except ValueError as exc:
        assert "artifact hashes" in str(exc)
    else:
        raise AssertionError("auditor source drift must invalidate the frozen run manifest")
