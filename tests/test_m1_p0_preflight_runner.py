from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.run_m1_p0_local_preflight import (APPROVAL_ID, ROOT, _build_probes,
                                               _listener_rows, _validate_approved_config)
from colluscope.openai_compat_llamacpp import load_llamacpp_backend_config


def test_8081_preflight_config_changes_only_approved_scope():
    config_path = ROOT / "runs" / "m1_p0_local" / "gguf-preflight-iteration-03" / "configs" / "m1-p0-8081-preflight.toml"
    original_path = ROOT / "configs" / "m1-p0-llama-local-draft.toml"
    approved = _validate_approved_config(config_path, original_path)
    assert approved["model_calls_enabled"] is False
    assert approved["preflight_enabled"] is True
    assert approved["preflight_approval_id"] == APPROVAL_ID
    assert approved["launch"]["port"] == 8081
    assert approved["server"]["base_url"] == "http://127.0.0.1:8081/v1"


@pytest.mark.parametrize("old,new", [
    ("port = 8081", "port = 8082"),
    ("model_calls_enabled = false", "model_calls_enabled = true"),
    ("temperature = 0.0", "temperature = 0.1"),
    ("min_p = 0.0", "min_p = 0.1"),
])
def test_preflight_runner_rejects_unapproved_config_mutations(tmp_path: Path, old: str, new: str):
    source = ROOT / "runs" / "m1_p0_local" / "gguf-preflight-iteration-03" / "configs" / "m1-p0-8081-preflight.toml"
    text = source.read_text(encoding="utf-8")
    assert old in text
    mutated = tmp_path / "mutated.toml"
    mutated.write_text(text.replace(old, new, 1), encoding="utf-8")
    with pytest.raises((ValueError, PermissionError)):
        _validate_approved_config(mutated, ROOT / "configs" / "m1-p0-llama-local-draft.toml")


def test_engineering_probe_prompts_have_no_treatment_or_episode_metadata():
    config = load_llamacpp_backend_config(ROOT / "configs" / "m1-p0-llama-local-draft.toml")
    probes, evidence = _build_probes(config, ROOT / "configs" / "m1-r-offline-v2.toml")
    assert [expected or "ballot" for _, expected in probes] == ["ballot", "send_message", "no_message"]
    assert len({request.agent_id for request, _ in probes}) == 2
    for request, _ in probes:
        observation = next(row["observation"] for row in evidence
                           if row["request_id"] == request.request_id)
        assert "condition_id" not in observation
        assert "seed_block_id" not in observation
        assert "oracle" not in json.dumps(observation).lower()
        assert request.request_id.startswith("m1-p0-preflight-")
        assert request.generation_seed is not None


@pytest.mark.skipif(os.name != "nt", reason="Windows TCP owner table API")
def test_listener_owner_probe_sees_loopback_listener_and_owner_pid():
    child = subprocess.Popen([sys.executable, "-m", "http.server", "8081", "--bind", "127.0.0.1"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        rows = []
        for _ in range(30):
            rows = _listener_rows(8081)
            if rows:
                break
            time.sleep(0.1)
        assert rows == [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                         "OwningProcess": child.pid}]
    finally:
        child.terminate()
        child.wait(timeout=10)
