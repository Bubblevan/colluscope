from __future__ import annotations

import hashlib
import json

import pytest

from colluscope.monitor_aggregate_budget import AggregateBudget, AggregateBudgetError


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def test_reservation_and_terminal_are_durable_and_never_refund_failed_slot(tmp_path):
    budget = AggregateBudget(tmp_path / "budget.jsonl", "TEST-EXECUTION")
    reserved = budget.reserve(
        phase_id="scripted_controls", request_id="r-1", body_sha256=_sha("body"),
        reserve_usd=0.0003, phase_request_cap=1, phase_cost_cap_usd=0.001,
    )
    budget.terminal(phase_id="scripted_controls", request_id="r-1",
                    status="TRANSPORT_ERROR", actual_cost_usd=None, http_status=None)

    summary = budget.summary()
    assert reserved["event"] == "request_reserved"
    assert summary["reserved_requests"] == summary["terminal_requests"] == 1
    assert summary["reserved_peak_cost_usd"] == 0.0003
    assert summary["per_phase"]["scripted_controls"]["reported_actual_cost_usd"] == 0
    assert [json.loads(line)["event"] for line in (tmp_path / "budget.jsonl").read_text().splitlines()] == [
        "request_reserved", "request_terminal"]


def test_phase_request_cap_and_duplicate_id_fail_before_second_reservation(tmp_path):
    budget = AggregateBudget(tmp_path / "budget.jsonl", "TEST-EXECUTION")
    kwargs = dict(body_sha256=_sha("body"), reserve_usd=0.0001,
                  phase_request_cap=1, phase_cost_cap_usd=0.001)
    budget.reserve(phase_id="scripted_controls", request_id="same", **kwargs)
    with pytest.raises(AggregateBudgetError, match="already reserved"):
        budget.reserve(phase_id="scripted_controls", request_id="same", **kwargs)
    with pytest.raises(AggregateBudgetError, match="phase request cap"):
        budget.reserve(phase_id="scripted_controls", request_id="next", **kwargs)
    assert len(budget.rows()) == 1


def test_global_budget_cap_blocks_cross_phase_overrun(tmp_path):
    budget = AggregateBudget(tmp_path / "budget.jsonl", "TEST-EXECUTION")
    # A valid full-count ledger exactly fills 856 slots but stays below $3.
    for phase, count, cap in (
        ("scripted_controls", 280, 280),
        ("m4_trace_eval", 504, 504),
        ("matched_worlds", 72, 72),
    ):
        for index in range(count):
            budget.reserve(phase_id=phase, request_id=f"{phase}-{index}",
                           body_sha256=_sha(f"{phase}-{index}"), reserve_usd=0.0001,
                           phase_request_cap=cap,
                           phase_cost_cap_usd={"scripted_controls": 1.0,
                                               "m4_trace_eval": 1.5,
                                               "matched_worlds": 0.5}[phase])
    with pytest.raises(AggregateBudgetError, match="global request cap"):
        budget.reserve(phase_id="matched_worlds", request_id="over-cap", body_sha256=_sha("over"),
                       reserve_usd=0.0001, phase_request_cap=72, phase_cost_cap_usd=0.5)
    assert budget.summary()["reserved_requests"] == 856


def test_orphan_reservation_remains_consumed_and_cannot_be_replayed(tmp_path):
    budget = AggregateBudget(tmp_path / "budget.jsonl", "TEST-EXECUTION")
    kwargs = dict(phase_id="scripted_controls", request_id="crash-window",
                  body_sha256=_sha("body"), reserve_usd=0.0001,
                  phase_request_cap=1, phase_cost_cap_usd=0.001)
    budget.reserve(**kwargs)
    # Simulate a crash after durable reservation but before HTTP start/terminal.
    assert budget.summary()["reserved_requests"] == 1
    with pytest.raises(AggregateBudgetError, match="already reserved"):
        budget.reserve(**kwargs)


def test_terminal_rejects_cross_phase_and_duplicate_close(tmp_path):
    budget = AggregateBudget(tmp_path / "budget.jsonl", "TEST-EXECUTION")
    budget.reserve(phase_id="scripted_controls", request_id="r", body_sha256=_sha("body"),
                   reserve_usd=0.0001, phase_request_cap=1, phase_cost_cap_usd=0.001)
    with pytest.raises(AggregateBudgetError, match="matching reservation"):
        budget.terminal(phase_id="matched_worlds", request_id="r", status="COMPLETED",
                        actual_cost_usd=0.00001, http_status=200)
    budget.terminal(phase_id="scripted_controls", request_id="r", status="COMPLETED",
                    actual_cost_usd=0.00001, http_status=200)
    with pytest.raises(AggregateBudgetError, match="matching reservation"):
        budget.terminal(phase_id="scripted_controls", request_id="r", status="COMPLETED",
                        actual_cost_usd=0.00001, http_status=200)
