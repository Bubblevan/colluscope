from __future__ import annotations

import json

import pytest

from colluscope.deepseek_m4_audit import AuditFailure
from scripts.audit_deepseek_first_research import _parse_monitor
from scripts import run_deepseek_first_research as orchestrator
from scripts.run_deepseek_first_pilot import _monitor_schedule
from scripts.run_deepseek_first_pilot import _freeze_pilot_plan
from colluscope.deepseek_monitor_v1 import _monitor_messages
from colluscope.deepseek_m4_v1 import canonical
from pathlib import Path


def _monitor_response(args, *, finish="tool_calls", function_name="report_evidence"):
    return json.dumps({"model": "deepseek-flash", "system_fingerprint": "fixture-fp",
        "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        "choices": [{"finish_reason": finish, "message": {"content": None,
            "tool_calls": [{"type": "function", "function": {"name": function_name,
                "arguments": json.dumps(args, separators=(",", ":"))}}]}}]}).encode()


def test_independent_monitor_parser_accepts_atomic_prediction_and_rejects_duplicate_keys():
    raw = _monitor_response({"label": "supported", "evidence_refs": ["M01"]})
    args, response = _parse_monitor(raw, "strict_function_calling", ["supported", "not_supported", "uncertain"])
    assert args == {"label": "supported", "evidence_refs": ["M01"]}
    assert response["system_fingerprint"] == "fixture-fp"

    duplicate_response = json.loads(raw)
    duplicate_response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = (
        '{"label":"supported","label":"uncertain","evidence_refs":["M01"]}')
    duplicate = json.dumps(duplicate_response).encode()
    with pytest.raises(AuditFailure, match="duplicate JSON key"):
        _parse_monitor(duplicate, "strict_function_calling", ["supported", "not_supported", "uncertain"])


@pytest.mark.parametrize("interface", ["strict_function_calling", "json_object_fallback"])
def test_monitor_pilot_uses_same_frozen_message_renderer_as_formal_plan(interface):
    pilot_rows = _monitor_schedule(interface)
    assert pilot_rows
    row = pilot_rows[0]
    assert row["messages"] == _monitor_messages(task=row["task"], evidence=row["evidence"], interface=interface)


def test_committed_pilot_plan_reproduces_byte_for_byte():
    plan = _freeze_pilot_plan()
    frozen_path = Path(__file__).resolve().parents[1] / "configs/m4-deepseek-pilot-plan-v1.json"
    assert frozen_path.read_bytes() == canonical(plan) + b"\n"
    assert len(plan["rows"]) == 30
    assert sum(row["interface"] == "strict_function_calling" for row in plan["rows"]) == 20
    assert sum(row["interface"] == "json_object_fallback" for row in plan["rows"]) == 10


@pytest.mark.parametrize("finish,name", [("length", "report_evidence"), ("tool_calls", "submit_ballot")])
def test_independent_monitor_parser_does_not_repair_bad_finish_or_wrong_tool(finish, name):
    raw = _monitor_response({"label": "supported", "evidence_refs": []}, finish=finish,
                            function_name=name)
    with pytest.raises(AuditFailure):
        _parse_monitor(raw, "strict_function_calling", ["supported", "not_supported", "uncertain"])


def test_orchestrator_stops_after_compatibility_no_go_without_later_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "RUN_ROOT", tmp_path)
    monkeypatch.setattr(orchestrator, "JOURNAL", tmp_path / "events.jsonl")
    monkeypatch.setattr(orchestrator, "SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(orchestrator.pilot, "run", lambda: {"status": "NO_GO", "actual_calls": 1})
    monkeypatch.setattr(orchestrator.agent, "run", lambda *_args: (_ for _ in ()).throw(AssertionError("Agent gate must not run")))
    monkeypatch.setattr(orchestrator.monitor, "run", lambda *_args: (_ for _ in ()).throw(AssertionError("Monitor must not run")))
    result = orchestrator.run()
    assert result["status"] == "STOP_PILOT_NO_GO"
    assert result["global_physical_requests"] == 0


def test_orchestrator_stops_after_agent_gate_no_go(tmp_path, monkeypatch):
    monkeypatch.setattr(orchestrator, "RUN_ROOT", tmp_path)
    monkeypatch.setattr(orchestrator, "JOURNAL", tmp_path / "events.jsonl")
    monkeypatch.setattr(orchestrator, "SUMMARY", tmp_path / "summary.json")
    monkeypatch.setattr(orchestrator.pilot, "run", lambda: {"status": "PASS"})
    calls = []
    monkeypatch.setattr(orchestrator.agent, "run", lambda phase: (calls.append(phase) or {"status": "NO_GO"}))
    monkeypatch.setattr(orchestrator.monitor, "run", lambda *_args: (_ for _ in ()).throw(AssertionError("Monitor must not run")))
    result = orchestrator.run()
    assert result["status"] == "STOP_AGENT_GATE_NO_GO"
    assert calls == ["gate"]
