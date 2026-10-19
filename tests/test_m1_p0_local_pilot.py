from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_m1_p0_local_pilot import (
    PILOT_APPROVAL_ID, PREFLIGHT_APPROVAL_ID, ROOT, _consume_pilot_approval,
    _runtime_source_files, _validate_authorized_config,
)


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
