from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import run_m2_v2_repair as repair
from scripts import run_m2_v2 as runner


def _write_decision(path: Path, status: str, all_ten: bool) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "preflight-decision.json").write_text(
        json.dumps({"status": status, "all_ten_valid": all_ten}), encoding="utf-8")


def test_each_repair_has_a_versioned_candidate_registry_and_prompts():
    registry, full_prompt, compact_prompt = repair.repair_paths(1)
    value = json.loads(registry.read_text(encoding="utf-8"))
    original = json.loads((repair.ROOT / "configs/m2-v2-candidates.json").read_text(encoding="utf-8"))
    assert value["repair_iteration"] == 1
    assert [(row["candidate_id"], row["contract"], row["response_format"]["type"])
            for row in value["candidates"]] == [
                (row["candidate_id"], row["contract"], row["response_format"]["type"])
                for row in original["candidates"]]
    assert full_prompt.is_file() and compact_prompt.is_file()
    assert full_prompt != runner.SYSTEM_FULL
    assert compact_prompt != runner.SYSTEM_COMPACT


def test_repair_loop_rejects_out_of_range_iterations():
    with pytest.raises(ValueError, match="between 1 and 3"):
        repair.repair_paths(4)


def test_repair_requires_failed_prior_gate(monkeypatch, tmp_path):
    original = tmp_path / "study"
    _write_decision(original, "PASS_INTERFACE", True)
    monkeypatch.setattr(repair, "run_root", lambda: tmp_path)
    with pytest.raises(PermissionError, match="previous gate failed"):
        repair._require_prior_no_go(1)


def test_repair_cumulative_budget_is_hard_capped(monkeypatch, tmp_path):
    _write_decision(tmp_path / "study", "NO_GO_INTERFACE", False)
    attempts = tmp_path / "study" / "preflight-attempts.jsonl"
    attempts.write_text("\n".join(
        json.dumps({"event": "attempt_started"}) for _ in range(91)) + "\n", encoding="utf-8")
    monkeypatch.setattr(repair, "run_root", lambda: tmp_path)
    with pytest.raises(RuntimeError, match="120-attempt cumulative hard cap"):
        repair._require_prior_no_go(1)


def test_current_formal_phase_requires_all_ten_pass(tmp_path):
    _write_decision(tmp_path, "NO_GO_INTERFACE", False)
    with pytest.raises(PermissionError, match="10/10 PASS_INTERFACE"):
        repair._require_current_pass(tmp_path)


def test_independent_score_cannot_run_before_f1_and_full_ledger_gates(tmp_path):
    _write_decision(tmp_path, "PASS_INTERFACE", True)
    with pytest.raises(PermissionError, match="F1 calibration gate"):
        repair._require_score_gates(tmp_path)
    (tmp_path / "calibration-freeze.json").write_text(
        json.dumps({"status": "CALIBRATION_GO"}), encoding="utf-8")
    with pytest.raises(PermissionError, match="1,000 evaluations"):
        repair._require_score_gates(tmp_path)


def test_attempt_counter_counts_only_actual_http_starts(monkeypatch, tmp_path):
    run = tmp_path / "study"
    run.mkdir()
    ledger = run / "preflight-attempts.jsonl"
    ledger.write_text("\n".join(json.dumps({"event": event}) for event in (
        "attempt_started", "response_returned", "attempt_started", "attempt_failed")) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(repair, "run_root", lambda: tmp_path)
    assert repair.attempt_counts()["original"] == 2

