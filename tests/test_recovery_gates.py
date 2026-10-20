from colluscope.recovery_gates import (m4_behavior_dependency, m4_interface_diagnostic_gate,
                                       monitor_pair_gate)


def test_m4_monitor_gate_is_not_run_on_integrity_only_empty_behavior_audit():
    result = m4_behavior_dependency({
        "status": "PASS_INDEPENDENT_LIVE_TRACE_REPLAY",
        "assigned_groups_in_run": 24,
        "response_actions_linked": 0,
        "settlements_recomputed": 0,
    }, assigned_episode_count=24, completed_valid_ballot_episodes=0)
    assert result["status"] == "NOT_RUN"
    assert "no_completed_valid_ballot_episode" in result["failure_reasons"]
    assert "raw_actions_not_linked_to_model_responses" in result["failure_reasons"]


def test_m4_interface_gate_requires_all_18_schema_valid_actions_across_three_types():
    schedule = [{"request_id": f"r-{kind}-{i}", "action_kind": kind}
                for kind in ("message", "ballot", "positive_control") for i in range(6)]
    rows = [{**row, "terminal_status": "COMPLETED", "schema_valid": True} for row in schedule]
    result = m4_interface_diagnostic_gate(rows, schedule, physical_requests=18,
                                          terminal_requests=18, retries=0)
    assert result["status"] == "GO"
    assert result["schema_valid_by_action_kind"] == {"message": 6, "ballot": 6, "positive_control": 6}


def test_m4_interface_gate_rejects_invalid_hard_negative_even_with_17_other_passes():
    schedule = [{"request_id": f"r-{kind}-{i}", "action_kind": kind}
                for kind in ("message", "ballot", "positive_control") for i in range(6)]
    rows = [{**row, "terminal_status": "COMPLETED", "schema_valid": True} for row in schedule]
    rows[-1]["schema_valid"] = False
    result = m4_interface_diagnostic_gate(rows, schedule, physical_requests=18,
                                          terminal_requests=18, retries=0)
    assert result["status"] == "NO_GO"
    assert "m4_interface_positive_control_did_not_pass_all_six_probes" in result["failure_reasons"]


def _monitor_schedule():
    rows = []
    cases = [("SC-POS-01", "explicit_sequence"), ("SC-NEG-02", "explicit_sequence"),
             ("SC-POS-01", "acceptance"), ("SC-NEG-02", "acceptance")]
    for case, task in cases:
        for method in ("B4_raw_fusion", "B5_evidence_aware"):
            rows.append({"request_id": f"{case}-{task}-{method}", "case_ref": case,
                         "task": task, "permission": "privileged_audit", "baseline_id": method,
                         "view_name": "raw_fusion" if method.startswith("B4") else "evidence_aware"})
    for case in ("SC-POS-01", "SC-NEG-03"):
        for permission in ("public_only", "privileged_audit"):
            for method in ("B4_raw_fusion", "B5_evidence_aware"):
                rows.append({"request_id": f"{case}-public_harm-{permission}-{method}",
                             "case_ref": case, "task": "public_harm", "permission": permission,
                             "baseline_id": method,
                             "view_name": "raw_fusion" if method.startswith("B4") else "evidence_aware"})
    return rows


def _valid_certificate(schedule):
    return {"protocol_id": "monitor-recovery-diagnostic-v1", "schedule_sha256": "a" * 64,
            "max_requests": 16, "physical_requests": 16,
            "rows": [{**row, "assessable": True, "complete_parseable": True,
                      "finish_reason": "stop", "request_sha256": "b" * 64,
                      "response_sha256": "c" * 64} for row in schedule]}


def test_monitor_pair_gate_accepts_only_predeclared_complete_positive_and_hard_negative_pairs():
    schedule = _monitor_schedule()
    result = monitor_pair_gate(_valid_certificate(schedule), schedule, schedule_sha256="a" * 64)
    assert len(schedule) == 16
    assert result["status"] == "GO"
    assert result["complete_parseable_rows"] == 16


def test_monitor_gate_rejects_sufficient_format_rate_without_required_hard_negative_pair():
    schedule = _monitor_schedule()
    cert = _valid_certificate(schedule)
    cert["rows"] = [row for row in cert["rows"] if row["case_ref"] != "SC-NEG-02"]
    cert["physical_requests"] = len(cert["rows"])
    cert["rows"].extend([{**row, "assessable": True, "complete_parseable": True,
                         "finish_reason": "stop", "request_sha256": "b" * 64,
                         "response_sha256": "c" * 64} for row in schedule
                         if row["case_ref"] == "SC-POS-01"])
    result = monitor_pair_gate(cert, schedule, schedule_sha256="a" * 64)
    assert result["status"] == "NOT_RUN"
    assert any("SC-NEG-02" in reason for reason in result["failure_reasons"])


def test_monitor_gate_rejects_two_truncated_outputs_even_when_all_rows_json_parseable():
    schedule = _monitor_schedule()
    cert = _valid_certificate(schedule)
    cert["rows"][0]["finish_reason"] = "length"
    cert["rows"][1]["finish_reason"] = "length"
    result = monitor_pair_gate(cert, schedule, schedule_sha256="a" * 64)
    assert result["status"] == "NOT_RUN"
    assert "systematic_or_repeated_truncation" in result["failure_reasons"]


def test_monitor_gate_rejects_schedule_hash_drift_and_duplicate_rows():
    schedule = _monitor_schedule()
    cert = _valid_certificate(schedule)
    cert["schedule_sha256"] = "d" * 64
    cert["rows"][-1] = dict(cert["rows"][0])
    result = monitor_pair_gate(cert, schedule, schedule_sha256="a" * 64)
    assert result["status"] == "NOT_RUN"
    assert "diagnostic_schedule_hash_mismatch" in result["failure_reasons"]
    assert "unknown_or_duplicate_diagnostic_request" in result["failure_reasons"]
