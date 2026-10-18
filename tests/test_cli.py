from pathlib import Path
import json

import pytest

from colluscope.cli import generate_run, verify_run


ROOT = Path(__file__).resolve().parents[1]


def _file_hashes(run_dir):
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    return {name.replace(run_dir.name, "<RUN>"): digest
            for name, digest in manifest["sha256"].items()}


def test_two_full_m0_runs_have_identical_core_artifact_hashes_and_verify(tmp_path):
    config = ROOT / "configs" / "m0.toml"
    out = tmp_path / "runs" / "m0"
    command = ["python", "-m", "colluscope", "m0", "--config", "configs/m0.toml", "--out", "runs/m0"]
    run1 = generate_run(config, out, command)
    run2 = generate_run(config, out, command)
    assert run1.name != run2.name
    assert _file_hashes(run1) == _file_hashes(run2)
    result1 = verify_run(run1)
    result2 = verify_run(run2)
    assert result1["status"] == result2["status"] == "PASS"
    assert result1["episode_count"] == result2["episode_count"] == 24
    assert result1["identical_c1_c6_evidence_pairs"] == result2["identical_c1_c6_evidence_pairs"] == 4
    assert result1["external_model_calls"] == result1["paid_api_calls"] == 0
    oracle = (run1 / "manifest.json")
    manifest = json.loads(oracle.read_text(encoding="utf-8"))
    oracle_path = (run1 / manifest["paths"]["oracle"]).resolve()
    input_root = (run1 / manifest["paths"]["monitor_input_root"]).resolve()
    assert not oracle_path.is_relative_to(input_root)
    assert input_root == (run1 / "inputs" / "views").resolve()
    for view_path in manifest["paths"]["views"].values():
        rows = [json.loads(line) for line in (run1 / view_path).read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 24
        assert all(set(row) == {"task_spec", "events"} or
                   set(row) == {"task_spec", "events", "findings"} for row in rows)
        serialized = json.dumps(rows, sort_keys=True).lower()
        for marker in ("episode_id", "view_name", "model_kind", "scripted", "mechanism_id",
                       "construction_truth", "policy_id", "condition_id", "seed", "split", "group_id"):
            assert marker not in serialized


def test_privileged_monitor_view_is_valid_and_distinguishes_c1_c6(tmp_path):
    config_text = (ROOT / "configs" / "m0.toml").read_text(encoding="utf-8")
    config_path = tmp_path / "private.toml"
    config_path.write_text(config_text.replace("monitor_can_see_private = false",
                                               "monitor_can_see_private = true"), encoding="utf-8")
    run_dir = generate_run(config_path, tmp_path / "runs", ["test privileged view"])
    result = verify_run(run_dir)
    assert result["status"] == "PASS"
    assert result["identical_c1_c6_evidence_pairs"] == 0


def test_verifier_rejects_tampered_trace_without_repair(tmp_path):
    run_dir = generate_run(ROOT / "configs" / "m0.toml", tmp_path / "runs", ["test tamper"])
    trace_path = run_dir / "inputs" / "trace.jsonl"
    trace_path.write_bytes(trace_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        verify_run(run_dir)


def test_m0_config_refuses_any_nonzero_model_or_api_calls(tmp_path):
    config_text = (ROOT / "configs" / "m0.toml").read_text(encoding="utf-8")
    config_path = tmp_path / "paid.toml"
    config_path.write_text(config_text.replace("paid_api_calls = 0", "paid_api_calls = 1"), encoding="utf-8")
    with pytest.raises(ValueError, match="nonzero model/API call budgets"):
        generate_run(config_path, tmp_path / "runs", ["must not run"])
