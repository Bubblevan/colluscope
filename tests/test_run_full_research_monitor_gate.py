import json
from pathlib import Path

from scripts import run_full_research_monitor as runner


def test_m4_monitor_phase_returns_not_run_before_credentials_when_behavior_data_missing(tmp_path, monkeypatch):
    source = tmp_path / "m4"
    source.mkdir()
    episodes = [{"terminal_status": "FAILED", "researcher_B": {"messages": [], "ballots": [], "settlement": None}}
                for _ in range(24)]
    (source / "episodes.jsonl").write_text("".join(json.dumps(row) + "\n" for row in episodes), encoding="utf-8")
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({"status": "PASS_INDEPENDENT_LIVE_TRACE_REPLAY",
                                 "assigned_groups_in_run": 24, "response_actions_linked": 0,
                                 "settlements_recomputed": 0}), encoding="utf-8")
    monkeypatch.setattr(runner, "M4_SOURCE_RUN", source)
    monkeypatch.setattr(runner, "M4_AUDIT", audit)
    monkeypatch.setattr(runner.monitor, "_load_config", lambda _path: {})
    monkeypatch.setattr(runner, "_install_secret_in_memory",
                        lambda: (_ for _ in ()).throw(AssertionError("credential loader must not run")))
    monkeypatch.setattr(runner.monitor, "run_schedule",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("transport must not run")))
    result = runner.execute("m4_trace_eval", tmp_path, tmp_path / "out")
    assert result["status"] == "NOT_RUN"
    assert result["real_model_or_api_calls"] == 0
    assert "no_completed_valid_ballot_episode" in result["dependency_gate"]["failure_reasons"]


def test_matched_monitor_phase_returns_not_run_without_paired_diagnostic_certificate(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.monitor, "_load_config", lambda _path: {})
    monkeypatch.setattr(runner, "RECOVERY_MONITOR_CERTIFICATE", tmp_path / "missing.json")
    monkeypatch.setattr(runner, "_install_secret_in_memory",
                        lambda: (_ for _ in ()).throw(AssertionError("credential loader must not run")))
    monkeypatch.setattr(runner.monitor, "run_schedule",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("transport must not run")))
    result = runner.execute("matched_worlds", tmp_path, tmp_path / "out")
    assert result["status"] == "NOT_RUN"
    assert result["real_model_or_api_calls"] == 0
    assert result["dependency_gate"]["failure_reasons"] == [
        "paired_assessable_B4_B5_diagnostic_certificate_missing"]
