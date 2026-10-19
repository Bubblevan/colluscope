from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts import run_m1_p0_local_preflight as preflight_runner
from scripts.run_m1_p0_local_preflight import (APPROVAL_ID, ROOT, _build_probes,
                                               _listener_rows, _validate_approved_config,
                                               _wait_for_server_startup)
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


@pytest.mark.skipif(os.name != "nt" or os.environ.get("COLLUSCOPE_LIVE_WINDOWS_LISTENER_TEST") != "1",
                    reason="opt-in host-dependent Windows owner-table integration check")
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


@pytest.mark.skipif(os.name != "nt", reason="Windows TCP owner table parser")
def test_listener_snapshot_parses_netstat_loopback_owner_row(monkeypatch):
    original_run = preflight_runner.subprocess.run

    def mocked_run(command, *args, **kwargs):
        if isinstance(command, (list, tuple)) and command and command[0].lower() == "netstat.exe":
            return subprocess.CompletedProcess(
                command, 0,
                "Active Connections\n  TCP    127.0.0.1:8081         0.0.0.0:0              LISTENING       43210\n",
                "")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(preflight_runner.subprocess, "run", mocked_run)
    rows, diagnostics = preflight_runner._listener_snapshot(8081)
    assert rows == [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                     "OwningProcess": 43210}]
    assert diagnostics.startswith("netstat:")


@pytest.mark.skipif(os.name != "nt", reason="Windows TCP owner table parser")
def test_listener_probe_uses_powershell_fallback_when_netstat_omits_listener(monkeypatch):
    owner_pid = 43210
    original_run = preflight_runner.subprocess.run

    def mocked_run(command, *args, **kwargs):
        if isinstance(command, (list, tuple)) and command and command[0].lower() == "netstat.exe":
            return subprocess.CompletedProcess(command, 0, "Active Connections\\n", "")
        if isinstance(command, (list, tuple)) and command and command[0].lower() == "powershell.exe":
            rows = [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                     "OwningProcess": owner_pid}]
            return subprocess.CompletedProcess(command, 0, json.dumps(rows), "")
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(preflight_runner.subprocess, "run", mocked_run)
    rows, diagnostics = preflight_runner._listener_snapshot(8081)
    assert rows == [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                     "OwningProcess": owner_pid}]
    assert "powershell:" in diagnostics


@pytest.mark.skipif(os.name != "nt", reason="Windows listener-query subprocess behavior")
def test_listener_probe_preserves_cim_failure_with_empty_stderr(monkeypatch):
    original_run = preflight_runner.subprocess.run

    def mocked_run(command, *args, **kwargs):
        if isinstance(command, (list, tuple)) and command and command[0].lower() == "netstat.exe":
            return subprocess.CompletedProcess(command, 0, "Active Connections\n", "")
        if isinstance(command, (list, tuple)) and command and command[0].lower() == "powershell.exe":
            return subprocess.CompletedProcess(command, 1, "", None)
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(preflight_runner.subprocess, "run", mocked_run)
    rows, diagnostics = preflight_runner._listener_snapshot(8081)
    assert rows == []
    assert "powershell fallback failed" in diagnostics


@pytest.mark.skipif(os.name != "nt", reason="Windows loopback readiness behavior")
def test_startup_settle_wait_uses_no_socket_or_process_table_probes(tmp_path, monkeypatch):
    child = subprocess.Popen([sys.executable, "-m", "http.server", "8081", "--bind", "127.0.0.1"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        monkeypatch.setattr(preflight_runner, "_listener_snapshot",
                            lambda _port: (_ for _ in ()).throw(AssertionError("table poll was called")))
        monkeypatch.setattr(preflight_runner.socket, "create_connection",
                            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                                AssertionError("socket probe ran before listener attestation")))
        polls = tmp_path / "readiness.jsonl"
        _wait_for_server_startup(child, polls, settle_seconds=0.05)
        row = json.loads(polls.read_text(encoding="utf-8").splitlines()[-1])
        assert row["status"] == "startup_settle_elapsed_process_alive"
        assert row["expected_pid"] == child.pid
    finally:
        child.terminate()
        child.wait(timeout=10)


def test_readiness_wait_fails_immediately_for_exited_server(tmp_path):
    class Exited:
        pid = 12345
        returncode = 7

        @staticmethod
        def poll():
            return 7

    with pytest.raises(RuntimeError, match="exited during startup"):
        _wait_for_server_startup(Exited(), tmp_path / "readiness.jsonl", settle_seconds=5)
