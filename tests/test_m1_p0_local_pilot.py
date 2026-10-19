from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from scripts.run_m1_p0_local_pilot import (
    JSON_PREFIX_OUTPUT_CONTRACT, JSON_PREFIX_PILOT_APPROVAL_ID,
    JSON_PREFIX_PREFLIGHT_APPROVAL_ID, PILOT_APPROVAL_ID, PREFLIGHT_APPROVAL_ID,
    ROOT, _consume_pilot_approval,
    _build_probes, _runtime_source_files, _validate_authorized_config,
    _validate_preflight_continuation, _verify_preflight_continuation,
)
from scripts.verify_m1_p0_preflight_blocker import verify as verify_preflight_blocker


def _pilot_config(tmp_path: Path) -> Path:
    source = (ROOT / "configs" / "m1-p0-llama-local-draft.toml").read_text(encoding="utf-8")
    replacements = [
        ('model_calls_enabled = false', 'model_calls_enabled = true'),
        ('preflight_enabled = false', 'preflight_enabled = true'),
        ('preflight_approval_id = ""', f'preflight_approval_id = "{PREFLIGHT_APPROVAL_ID}"'),
        ('full_pilot_approval_id = ""', f'full_pilot_approval_id = "{PILOT_APPROVAL_ID}"'),
        ('base_url = "http://127.0.0.1:8080/v1"',
         'base_url = "http://127.0.0.1:8081/v1"'),
        ('port = 8080', 'port = 8081'),
        ('live_preflight = "NOT_AUTHORIZED"', f'live_preflight = "{PREFLIGHT_APPROVAL_ID}"'),
        ('full_25_episode_pilot = "NOT_AUTHORIZED"',
         f'full_25_episode_pilot = "{PILOT_APPROVAL_ID}"'),
    ]
    for old, new in replacements:
        assert old in source
        source = source.replace(old, new, 1)
    path = tmp_path / "full-pilot.toml"
    path.write_text(source, encoding="utf-8")
    return path


def test_run_scoped_config_accepts_exact_local_25_episode_authorization(tmp_path):
    config = _validate_authorized_config(_pilot_config(tmp_path))
    assert config.model_calls_enabled is True
    assert config.preflight_enabled is True
    assert config.base_url == "http://127.0.0.1:8081/v1"
    assert config.max_logical_requests == 95
    assert config.max_total_attempts == 190


def test_run_scoped_config_rejects_wrong_pilot_approval(tmp_path):
    path = _pilot_config(tmp_path)
    path.write_text(path.read_text(encoding="utf-8").replace(
        PILOT_APPROVAL_ID, "UNAUTHORIZED-TEST-ID"), encoding="utf-8")
    with pytest.raises(PermissionError, match="exact preflight and 25-episode approvals"):
        _validate_authorized_config(path)


def test_json_prefix_revision_requires_its_own_exact_approval_pair_and_contract(tmp_path):
    path = _pilot_config(tmp_path)
    revised = path.read_text(encoding="utf-8")
    revised = revised.replace(PREFLIGHT_APPROVAL_ID, JSON_PREFIX_PREFLIGHT_APPROVAL_ID)
    revised = revised.replace(PILOT_APPROVAL_ID, JSON_PREFIX_PILOT_APPROVAL_ID)
    revised = revised.replace(
        "[checkpoint]", f'action_output_contract_revision = "{JSON_PREFIX_OUTPUT_CONTRACT}"\n\n[checkpoint]', 1)
    path.write_text(revised, encoding="utf-8")
    assert _validate_authorized_config(path).model_calls_enabled is True

    path.write_text(revised.replace(JSON_PREFIX_OUTPUT_CONTRACT, "wrong-contract"), encoding="utf-8")
    with pytest.raises(PermissionError, match="exact preflight and 25-episode approvals"):
        _validate_authorized_config(path)


def test_parser_revision_approval_ledger_is_separate_and_single_use(tmp_path):
    ledger = tmp_path / "ledger"
    output = tmp_path / "run"
    output.mkdir()
    consumed = _consume_pilot_approval(output, ledger, JSON_PREFIX_PILOT_APPROVAL_ID)
    assert consumed.is_file()
    record = json.loads(consumed.read_text(encoding="utf-8"))
    assert record["approval_id"] == JSON_PREFIX_PILOT_APPROVAL_ID
    with pytest.raises(PermissionError, match="already consumed"):
        _consume_pilot_approval(tmp_path / "second-run", ledger, JSON_PREFIX_PILOT_APPROVAL_ID)


def test_full_25_episode_approval_is_single_use(tmp_path):
    ledger = tmp_path / "ledger"
    output = tmp_path / "run"
    output.mkdir()
    consumed = _consume_pilot_approval(output, ledger)
    assert consumed.is_file()
    assert (output / "approval-consumption.json").is_file()
    with pytest.raises(PermissionError, match="already consumed"):
        _consume_pilot_approval(tmp_path / "second-run", ledger)


def test_runtime_fingerprint_covers_imported_preflight_orchestration():
    paths = {path.resolve() for path in _runtime_source_files()}
    assert (ROOT / "scripts" / "run_m1_p0_local_preflight.py").resolve() in paths


def test_retained_zero_episode_tokenizer_failure_is_valid_continuation_source():
    previous = ROOT / "runs/m1_p0_local/25ep-pilot-20261019/run"
    model = Path(r"E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf")
    if not previous.is_dir() or not model.is_file():
        pytest.skip("requires the retained local tokenizer-preflight failure and frozen GGUF")
    config_path = ROOT / "runs/m1_p0_local/25ep-pilot-20261019/configs/full-pilot.toml"
    runtime_path = ROOT / "configs/m1-r-offline-v2.toml"
    config = _validate_authorized_config(config_path)
    probes, evidence = _build_probes(config, runtime_path)
    continuation = _validate_preflight_continuation(
        previous, config_path, runtime_path, config, probes, evidence)
    assert set(continuation["setup_responses"]) == {
        "preflight-props", "preflight-template", "preflight-tokenize"}
    assert len(continuation["setup_records"]) == 3
    assert continuation["previous_manifest_sha256"]


def test_continuation_verifier_checks_the_copied_parent_and_reused_responses(tmp_path):
    previous = ROOT / "runs/m1_p0_local/25ep-pilot-20261019/run"
    if not previous.is_dir():
        pytest.skip("requires the retained failed-preflight evidence package")
    out_dir = tmp_path / "resumed-run"
    preflight = out_dir / "preflight"
    preflight.mkdir(parents=True)
    copied = preflight / "resumed-source"
    shutil.copytree(previous, copied)
    manifest_path = previous / "manifest.json"
    requests_path = previous / "preflight" / "requests.jsonl"
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    (out_dir / "preflight-resume.json").write_text(json.dumps({
        "previous_run_id": previous.name,
        "previous_run_copy": "preflight/resumed-source",
        "previous_manifest_sha256": digest(manifest_path),
        "previous_requests_sha256": digest(requests_path),
    }), encoding="utf-8")
    rows = [json.loads(line) for line in requests_path.read_text(encoding="utf-8").splitlines()]
    verified = _verify_preflight_continuation(out_dir, rows)
    assert verified["setup_responses_reused_and_reverified"] == 3
    (copied / "preflight" / "requests.jsonl").write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact hash mismatch"):
        _verify_preflight_continuation(out_dir, rows)


def test_preflight_blocker_verifier_reports_integrity_pass_and_research_no_go():
    run_dir = ROOT / "runs/m1_p0_local/25ep-pilot-20261019/run-resume-01"
    if not run_dir.is_dir():
        pytest.skip("requires the retained zero-episode live preflight blocker")
    result = verify_preflight_blocker(run_dir)
    assert result["status"] == "PASS_PACKAGE_INTEGRITY__NO_GO_PREFLIGHT"
    assert result["episodes"] == result["pilot_logical_requests"] == 0
    assert result["strict_parser_failure_preserved"] is True
