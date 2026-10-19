"""Run the separately approved, bounded local llama.cpp compatibility preflight.

This is an engineering compatibility check, not a research episode. It starts
only the frozen local server and stops only the process it created.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import tomllib
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from colluscope.m1_runtime import (AgentRequest, _canonical_hash, _generation_seed,
                                   _observation, _render, _task_spec, load_runtime_config)  # noqa: E402
from colluscope.openai_compat_llamacpp import (PREFLIGHT_NO_MESSAGE_INSTRUCTION,
                                               PREFLIGHT_SEND_MESSAGE_INSTRUCTION,
                                               LlamaCppPreflightBudget, LocalLlamaCppBackend,
                                               llama_runtime_bundle_identity, llama_server_command,
                                               load_llamacpp_backend_config)  # noqa: E402
from scripts.local_llama_security import create_api_key_file, remove_api_key_file  # noqa: E402


APPROVAL_ID = "USER-APPROVED-M1-P0-IF-V3-LOCAL-8081-6L12H4-20261019-RUN02"
CONSUMED_APPROVAL_IDS = frozenset({"USER-APPROVED-8081-PREFLIGHT-2026-10-19"})
EXPECTED_MODEL_SHA256 = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
EXPECTED_SERVER_SHA256 = "3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb"
EXPECTED_BUNDLE_SHA256 = "9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759"
PORT = 8081


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _write_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _listener_snapshot(port: int) -> tuple[list[dict[str, Any]], str]:
    if os.name != "nt":
        raise RuntimeError("listener-owner attestation currently requires Windows")
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("listener query requires a valid TCP port")
    result = subprocess.run(["netstat.exe", "-ano", "-p", "tcp"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            timeout=10, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"netstat listener query failed: {result.stderr.strip()}")
    rows: list[dict[str, Any]] = []
    matched_lines = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP" or fields[-2].upper() != "LISTENING":
            continue
        local_endpoint = fields[1]
        if local_endpoint.startswith("[") and "]:" in local_endpoint:
            address, local_port_text = local_endpoint[1:].rsplit("]:", 1)
        else:
            address, separator, local_port_text = local_endpoint.rpartition(":")
            if not separator:
                continue
        try:
            local_port, owner_pid = int(local_port_text), int(fields[-1])
        except ValueError:
            continue
        if local_port == port:
            normalized_address = address.strip("[]")
            rows.append({"LocalAddress": normalized_address, "LocalPort": local_port,
                         "OwningProcess": owner_pid})
            matched_lines.append(line.strip())
    if rows:
        return rows, "netstat: " + "\n".join(matched_lines)

    # netstat.exe has intermittently omitted a live llama-server listener in
    # this Windows session even though the kernel TCP table and a direct HTTP
    # client could see it. Use the PowerShell TCP table as an independent,
    # bounded fallback; the caller still checks the exact PID and image.
    command = (
        "$rows = @(Get-NetTCPConnection -LocalPort " + str(port) +
        " -State Listen -ErrorAction Stop | "
        "Select-Object LocalAddress,LocalPort,OwningProcess); "
        "ConvertTo-Json -InputObject $rows -Compress"
    )
    fallback = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=10, check=False)
    diagnostics = "netstat: no matching listener"
    if fallback.returncode != 0:
        return [], diagnostics + "; powershell fallback failed: " + (fallback.stderr or "").strip()
    try:
        raw_rows = json.loads(fallback.stdout.strip() or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"PowerShell listener query returned malformed JSON: {exc}") from exc
    if isinstance(raw_rows, dict):
        raw_rows = [raw_rows]
    if not isinstance(raw_rows, list):
        raise RuntimeError("PowerShell listener query did not return a row list")
    for item in raw_rows:
        if not isinstance(item, dict):
            raise RuntimeError("PowerShell listener query returned a malformed row")
        try:
            row = {"LocalAddress": str(item["LocalAddress"]),
                   "LocalPort": int(item["LocalPort"]),
                   "OwningProcess": int(item["OwningProcess"])}
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"PowerShell listener query row is incomplete: {item!r}") from exc
        if row["LocalPort"] == port:
            rows.append(row)
    return rows, diagnostics + "; powershell: " + fallback.stdout.strip()


def _listener_rows(port: int) -> list[dict[str, Any]]:
    return _listener_snapshot(port)[0]


def _wait_for_server_startup(process: subprocess.Popen[bytes], readiness_path: Path,
                             settle_seconds: float = 15) -> None:
    """Let llama-server finish local model initialization before any socket probe.

    Runner parity experiments found that listener-table attestation followed by
    HTTP works, while a client TCP probe before that attestation can receive
    WinError 10013. The frozen model loads in about 4–6 seconds here; 15 seconds
    gives startup margin without spawning repeated OS queries or connections.
    """
    if settle_seconds < 0:
        raise ValueError("server startup settle time cannot be negative")
    deadline = time.monotonic() + settle_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited during startup with code {process.returncode}")
        time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
    if process.poll() is not None:
        raise RuntimeError(f"llama-server exited during startup with code {process.returncode}")
    _write_jsonl(readiness_path, {"at_utc": datetime.now(timezone.utc).isoformat(),
                                  "monotonic_ns": time.monotonic_ns(),
                                  "expected_pid": process.pid,
                                  "settle_seconds": settle_seconds,
                                  "status": "startup_settle_elapsed_process_alive"})


def _process_image(pid: int) -> str:
    if os.name != "nt":
        raise RuntimeError("process-image attestation currently requires Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    open_process.restype = ctypes.c_void_p
    query = kernel32.QueryFullProcessImageNameW
    query.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p,
                      ctypes.POINTER(ctypes.c_ulong)]
    query.restype = ctypes.c_int
    close = kernel32.CloseHandle
    close.argtypes = [ctypes.c_void_p]
    close.restype = ctypes.c_int
    handle = open_process(0x1000, 0, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = ctypes.c_ulong(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not query(handle, 0, buffer, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return str(Path(buffer.value).resolve())
    finally:
        close(handle)


def _assert_port_free(port: int) -> None:
    rows = _listener_rows(port)
    if rows:
        raise RuntimeError(f"approved preflight port {port} is already occupied: {rows}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind(("127.0.0.1", port))


class GpuSampler:
    def __init__(self, output_path: Path, interval_seconds: float = 0.25):
        self.output_path = output_path
        self.interval_seconds = interval_seconds
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._phase = "prelaunch"
        self._thread: threading.Thread | None = None
        self.rows: list[dict[str, Any]] = []

    def set_phase(self, phase: str) -> None:
        with self._lock:
            self._phase = phase

    def sample(self, *, reason: str = "periodic") -> dict[str, Any]:
        with self._lock:
            phase = self._phase
        row: dict[str, Any] = {
            "at_utc": datetime.now(timezone.utc).isoformat(),
            "monotonic_ns": time.monotonic_ns(), "phase": phase, "reason": reason,
        }
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=False)
            row["returncode"] = result.returncode
            row["stdout"] = result.stdout.strip()
            row["stderr"] = result.stderr.strip()
            row["gpus"] = []
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    columns = [value.strip() for value in line.split(",")]
                    if len(columns) == 4:
                        row["gpus"].append({"name": columns[0], "memory_total_mib": columns[1],
                                            "memory_free_mib": columns[2],
                                            "utilization_percent": columns[3]})
        except Exception as exc:
            row.update({"returncode": None, "error_type": type(exc).__name__, "error": str(exc)})
        self.rows.append(row)
        _write_jsonl(self.output_path, row)
        return row

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.sample()

    def start(self) -> None:
        self.sample(reason="before_model_load")
        self._thread = threading.Thread(target=self._run, name="m1-p0-gpu-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        self.sample(reason="sampler_stopped")


def _validate_approved_config(config_path: Path, original_path: Path) -> dict[str, Any]:
    approved_raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    original = tomllib.loads(original_path.read_text(encoding="utf-8"))
    expected = json.loads(json.dumps(original))
    expected["preflight_enabled"] = True
    expected["preflight_approval_id"] = APPROVAL_ID
    expected["server"]["base_url"] = f"http://127.0.0.1:{PORT}/v1"
    expected["launch"]["port"] = PORT
    expected["authorization"]["live_preflight"] = APPROVAL_ID
    if approved_raw != expected:
        raise ValueError("8081 config differs from the approved preflight-only delta")
    if approved_raw["model_calls_enabled"] is not False or approved_raw["preflight_enabled"] is not True:
        raise PermissionError("preflight-only model-call gates are invalid")
    if approved_raw["preflight_approval_id"] != APPROVAL_ID:
        raise PermissionError("config approval ID differs from the user's 8081 authorization")
    if (approved_raw["server"]["base_url"] != f"http://127.0.0.1:{PORT}/v1" or
            approved_raw["launch"]["port"] != PORT):
        raise ValueError("approved endpoint is not the 127.0.0.1:8081 loopback endpoint")
    return approved_raw


def _reserve_preflight_approval(approval_id: str, out_dir: Path,
                                ledger_dir: Path | None = None) -> Path:
    if approval_id in CONSUMED_APPROVAL_IDS:
        raise PermissionError("historical 8081 preflight approval was consumed")
    if approval_id != APPROVAL_ID:
        raise PermissionError("--approval-id must equal the current V3 run-scoped authorization")
    ledger_dir = ledger_dir or ROOT / "runs" / "m1_p0_local" / "approval-ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_dir / (hashlib.sha256(approval_id.encode("utf-8")).hexdigest() + ".json")
    record = {"approval_id": approval_id, "status": "RESERVED",
              "scope": "one local M1-P0 Interface V3 preflight; no Pilot or M2",
              "output_directory": str(out_dir.resolve()),
              "reserved_at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        with ledger_path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise PermissionError("this run-scoped preflight approval is already reserved or consumed") from exc
    return ledger_path


def _build_probes(backend_config: Any, runtime_config_path: Path) -> tuple[list[tuple[AgentRequest, str | None]], list[dict[str, Any]]]:
    runtime = load_runtime_config(runtime_config_path)
    by_id = {condition["id"]: condition for condition in runtime.conditions}
    ballot_condition = by_id["normal_cooperation"]
    chat_condition = by_id["private_chat_no_side_bonus"]
    specifications = [
        ("ballot", "A", ballot_condition, None, None),
        ("message", "A", chat_condition, "send_message", PREFLIGHT_SEND_MESSAGE_INSTRUCTION),
        ("message", "B", chat_condition, "no_message", PREFLIGHT_NO_MESSAGE_INSTRUCTION),
    ]
    probes: list[tuple[AgentRequest, str | None]] = []
    prompt_evidence: list[dict[str, Any]] = []
    for index, (action_kind, agent, condition, requested_action, instruction) in enumerate(specifications, start=1):
        task_spec = _task_spec(condition["public_target_bonus_units"], runtime)
        observation = _observation(agent, task_spec, condition, runtime)
        if instruction is not None:
            observation["preflight_probe_instruction"] = instruction
        canonical_observation = json.dumps(observation, ensure_ascii=False, sort_keys=True,
                                           separators=(",", ":"))
        prompt = _render(action_kind, observation, runtime)
        request = AgentRequest(
            request_id=f"m1-p0-preflight-{index}-{action_kind}-{agent}",
            action_kind=action_kind, agent_id=agent, model_id=backend_config.model_id,
            sampling=backend_config.sampling, timeout_seconds=backend_config.timeout_seconds,
            observation_sha256=_canonical_hash(observation), prompt=prompt,
            generation_seed=_generation_seed("seed-0", agent, action_kind))
        probes.append((request, requested_action))
        prompt_evidence.append({
            "request_id": request.request_id, "action_kind": action_kind, "agent_id": agent,
            "requested_action": "ballot" if requested_action is None else requested_action,
            "engineering_probe_not_research_episode": True,
            "observation": observation, "observation_canonical_json": canonical_observation,
            "observation_sha256": request.observation_sha256,
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "generation_seed": request.generation_seed, "sampling": backend_config.sampling,
        })
    return probes, prompt_evidence


def _stop_own_process(process: subprocess.Popen[bytes]) -> dict[str, Any]:
    if process.poll() is not None:
        return {"pid": process.pid, "already_exited": True, "returncode": process.returncode}
    try:
        process.terminate()
    except OSError as exc:
        if process.poll() is not None:
            return {"pid": process.pid, "already_exited": True, "returncode": process.returncode,
                    "terminate_race": str(exc)}
        raise
    try:
        process.wait(timeout=25)
        return {"pid": process.pid, "terminated": True, "returncode": process.returncode}
    except subprocess.TimeoutExpired:
        # Popen.kill targets the process handle returned by CreateProcess, so
        # cleanup cannot accidentally target an unrelated listener/PID reuse.
        process.kill()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        return {"pid": process.pid, "forced_own_process_termination": True,
                "returncode": process.poll()}


def _manifest(out_dir: Path) -> dict[str, Any]:
    hashes = {}
    for path in sorted((item for item in out_dir.rglob("*") if item.is_file() and item.name != "manifest.json"),
                       key=lambda item: item.relative_to(out_dir).as_posix()):
        hashes[path.relative_to(out_dir).as_posix()] = {
            "size_bytes": path.stat().st_size, "sha256": _sha256_file(path)}
    manifest = {"purpose": "bounded_local_gguf_preflight_8081", "approval_id": APPROVAL_ID,
                "files": hashes, "external_model_calls": 0, "paid_api_calls": 0,
                "research_episodes": 0}
    _write_json(out_dir / "manifest.json", manifest)
    return manifest


def execute(config_path: Path, runtime_config_path: Path, original_config_path: Path,
            out_dir: Path, supplied_approval: str) -> int:
    if supplied_approval in CONSUMED_APPROVAL_IDS:
        raise PermissionError("historical 8081 preflight approval was consumed")
    if supplied_approval != APPROVAL_ID:
        raise PermissionError("--approval-id must equal the current V3 run-scoped authorization")
    _validate_approved_config(config_path, original_config_path)
    out_dir = out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty preflight evidence directory: {out_dir}")
    approval_ledger_path = _reserve_preflight_approval(supplied_approval, out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = out_dir / "logs"
    logs_dir.mkdir()
    shutil_copy = __import__("shutil").copy2
    shutil_copy(config_path, out_dir / "approved-config.toml")
    approval = {"approval_id": APPROVAL_ID,
                "user_authorization": "current explicit user approval for one local M1-P0 Interface V3 preflight",
                "scope": "frozen local Qwen3/llama.cpp on 127.0.0.1:8081; max 6 logical / 12 HTTP / 4 completion attempts; no Pilot or M2",
                "recorded_at_utc": datetime.now(timezone.utc).isoformat()}
    _write_json(out_dir / "approval-record.json", approval)
    result: dict[str, Any] = {
        "status": "NOT_RUN", "approval_id": APPROVAL_ID, "config_path": str(config_path.resolve()),
        "runtime_config_path": str(runtime_config_path.resolve()), "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "logical_request_ceiling": 6, "http_attempt_ceiling": 12,
        "completion_attempt_ceiling": 4, "research_episodes": 0,
        "full_pilot_authorized": False, "m2_authorized": False,
    }
    sampler: GpuSampler | None = None
    process: subprocess.Popen[bytes] | None = None
    api_key: str | None = None
    api_key_file: Path | None = None
    api_key_metadata: dict[str, Any] | None = None
    stdout_stream = stderr_stream = None
    try:
        backend_config = load_llamacpp_backend_config(config_path)
        runtime_bundle = llama_runtime_bundle_identity(backend_config.server_binary_path)
        model_path = Path(backend_config.artifact_path).resolve()
        server_path = Path(backend_config.server_binary_path).resolve()
        if not model_path.is_file() or _sha256_file(model_path) != EXPECTED_MODEL_SHA256:
            raise RuntimeError("GGUF is absent or differs from the previously frozen model bytes")
        if not server_path.is_file() or _sha256_file(server_path) != EXPECTED_SERVER_SHA256:
            raise RuntimeError("llama-server executable is absent or differs from inspected bytes")
        if runtime_bundle["sha256"] != EXPECTED_BUNDLE_SHA256:
            raise RuntimeError("complete llama.cpp runtime bundle differs from the inspected bytes")
        if backend_config.model_calls_enabled or not backend_config.preflight_enabled:
            raise PermissionError("only preflight is enabled; full model-call gate must remain false")
        if backend_config.launch["port"] != PORT:
            raise ValueError("the user-approved 8081 preflight port is not frozen in this config")
        _assert_port_free(PORT)
        api_key, api_key_file, api_key_metadata = create_api_key_file(out_dir)

        environment = {"python": sys.version, "platform": platform.platform(),
                       "architecture": platform.machine(), "processor": platform.processor(),
                       "cwd": str(Path.cwd()), "git_head": _git_head(),
                       "config_sha256": _sha256_file(config_path),
                       "model_path": str(model_path), "model_sha256": EXPECTED_MODEL_SHA256,
                       "model_size_bytes": model_path.stat().st_size,
                       "server_path": str(server_path), "server_sha256": EXPECTED_SERVER_SHA256,
                       "runtime_bundle": runtime_bundle,
                       "config_sampling": backend_config.sampling,
                       "launch_command": llama_server_command(backend_config, api_key_file),
                       "api_key_sha256": api_key_metadata["sha256"],
                        "network_boundary": {"inference_endpoint": backend_config.base_url,
                                             "loopback_only": True, "llama_cpp_offline": True,
                                             "third_party_api_calls": False,
                                             "proxy_discovery_disabled_for_client": True},
                       "port_prelaunch_listeners": []}
        try:
            nvidia = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu",
                                     "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                    timeout=5, check=False)
            environment["gpu_before_load_command_exit"] = nvidia.returncode
            environment["gpu_before_load"] = nvidia.stdout.strip()
            environment["gpu_before_load_stderr"] = nvidia.stderr.strip()
        except Exception as exc:
            environment["gpu_before_load_error"] = {"type": type(exc).__name__, "error": str(exc)}
        _write_json(out_dir / "environment.json", environment)

        runtime_config = load_runtime_config(runtime_config_path)
        probes, prompt_evidence = _build_probes(backend_config, runtime_config_path)
        token_counter = GGUFChatTokenCounter(model_path,
                                              expected_artifact_sha256=backend_config.artifact_sha256)
        action_root = ROOT / "prompts" / "m1-p0-v2"
        input_evidence = {"protocol_id": "m1-p0-interface-v3",
                          "probe_order": [item[0].request_id for item in probes],
                          "requested_actions": [item[1] or "ballot" for item in probes],
                          "prompts": prompt_evidence,
                          "schema_sha256": {path.name: _sha256_file(path)
                                            for path in sorted(action_root.glob("*.schema.json"))},
                          "runtime_prompt_version": runtime_config.raw["prompt_version"],
                          "condition_source": "frozen M1-R config; engineering probes only",
                          "seed_scheme": "existing frozen seed-0/agent/stage derivation; no episode created"}
        _write_json(out_dir / "preflight-inputs.json", input_evidence)

        _assert_port_free(PORT)
        sampler = GpuSampler(out_dir / "gpu-samples.jsonl")
        sampler.start()
        stdout_stream = (logs_dir / "llama-server.stdout.log").open("wb")
        stderr_stream = (logs_dir / "llama-server.stderr.log").open("wb")
        command = llama_server_command(backend_config, api_key_file)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout_stream,
                                  stderr=stderr_stream, cwd=str(server_path.parent),
                                  creationflags=flags, close_fds=True)
        sampler.set_phase("server_starting_model_load")
        launched_image = _process_image(process.pid)
        if launched_image.casefold() != str(server_path).casefold():
            raise RuntimeError(f"launched PID image mismatch: {launched_image}")
        _write_json(out_dir / "launch.json", {"pid": process.pid, "image_path": launched_image,
                    "command": command, "cwd": str(server_path.parent),
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "port": PORT, "host": "127.0.0.1"})

        readiness_path = out_dir / "readiness-polls.jsonl"
        _wait_for_server_startup(process, readiness_path, settle_seconds=15)
        owner_rows, owner_diagnostics = _listener_snapshot(PORT)
        _write_jsonl(out_dir / "listener-owner-attestations.jsonl", {
            "at_utc": datetime.now(timezone.utc).isoformat(), "expected_pid": process.pid,
            "listener_rows": owner_rows, "query_diagnostics": owner_diagnostics})
        if owner_rows != [{"LocalAddress": "127.0.0.1", "LocalPort": PORT,
                           "OwningProcess": process.pid}]:
            raise PermissionError(f"port ownership/address is not the launched loopback server: {owner_rows}")
        if _process_image(process.pid).casefold() != str(server_path).casefold():
            raise PermissionError("server PID image changed after startup")

        _write_json(out_dir / "server-readiness.json", {
            "status": "PROCESS_AND_LOOPBACK_OWNER_VERIFIED",
            "http_probe_sent": False,
            "readiness_http_check": "the first budgeted GET /props request in the frozen six-request sequence",
            "pid": process.pid,
            "pid_image": launched_image,
            "listener_rows": owner_rows,
            "endpoint": f"http://127.0.0.1:{PORT}"})
        sampler.set_phase("server_listening_waiting_for_preflight")

        def listener_guard() -> bool:
            if process is None or process.poll() is not None:
                return False
            try:
                rows, matching_netstat_lines = _listener_snapshot(PORT)
                image = _process_image(process.pid)
                passed = (rows == [{"LocalAddress": "127.0.0.1", "LocalPort": PORT,
                                    "OwningProcess": process.pid}] and
                          image.casefold() == str(server_path).casefold())
                _write_jsonl(out_dir / "listener-guard-checks.jsonl", {
                    "at_utc": datetime.now(timezone.utc).isoformat(),
                    "expected_pid": process.pid, "listener_rows": rows,
                    "netstat_matching_lines": matching_netstat_lines,
                    "image_path": image, "passed": passed})
                return passed
            except Exception as exc:
                _write_jsonl(out_dir / "listener-guard-checks.jsonl", {
                    "at_utc": datetime.now(timezone.utc).isoformat(),
                    "expected_pid": process.pid, "passed": False,
                    "error_type": type(exc).__name__, "error": str(exc)})
                return False

        events: list[dict[str, Any]] = []
        def event_hook(event: dict[str, Any]) -> None:
            row = {**event, "monotonic_ns": time.monotonic_ns()}
            events.append(row)
            event_name = event.get("event", "unknown")
            if event_name == "completion_attempt_started":
                sampler.set_phase(f"inference:{event.get('request_id')}:{event.get('attempt')}")
            elif event_name in {"completion_attempt_finished", "completion_attempt_failed"}:
                sampler.set_phase("server_loaded_between_completions")
            elif event_name == "server_properties_validated":
                sampler.set_phase("model_loaded_properties_validated")
            elif event_name == "tokenizer_parity_validated":
                sampler.set_phase("tokenizer_parity_validated")
            _write_jsonl(out_dir / "preflight-events.jsonl", row)

        backend = LocalLlamaCppBackend(backend_config, token_counter, api_key=api_key,
                                       listener_guard=listener_guard,
                                       preflight_event_hook=event_hook)
        budget = LlamaCppPreflightBudget(enabled=True, max_logical_requests=6,
                                         max_attempts=12, max_completion_attempts=4)
        result = backend.preflight(budget, probes)
        result["budget_state"] = {"logical_requests": len(budget.logical_ids),
                                  "http_attempts": budget.attempts,
                                  "completion_attempts": budget.completion_attempts,
                                  "attempts_by_request": budget.attempts_by_request}
        result["records"] = budget.records
        result["listener_owner_after_preflight"] = _listener_rows(PORT)
        if not listener_guard():
            raise PermissionError("launched server no longer exclusively owns the approved port")
        _write_json(out_dir / "preflight-result.json", result)
        result_status = result["status"]
        if result_status != "PASS_INTERFACE":
            raise RuntimeError(f"unexpected preflight status for protocol v3: {result_status}")
        result_error = None
    except Exception as exc:
        result_status = "FAIL"
        result_error = {"type": type(exc).__name__, "error": str(exc)}
        _write_json(out_dir / "failure.json", {"status": result_status, "failure": result_error,
                    "at_utc": datetime.now(timezone.utc).isoformat(),
                    "process_pid": process.pid if process else None})
        if "budget" in locals():
            _write_json(out_dir / "preflight-result.json", {
                "status": "FAIL", "failure": result_error, "records": budget.records,
                "budget_state": {"logical_requests": len(budget.logical_ids),
                                 "http_attempts": budget.attempts,
                                 "completion_attempts": budget.completion_attempts,
                                 "attempts_by_request": budget.attempts_by_request}})
    finally:
        if process is not None:
            sampler.set_phase("server_shutdown") if sampler else None
            stop_result = _stop_own_process(process)
            _write_json(out_dir / "shutdown.json", stop_result)
        if api_key_file is not None:
            _write_json(out_dir / "api-key-cleanup.json", remove_api_key_file(api_key_file))
        if stdout_stream is not None:
            stdout_stream.close()
        if stderr_stream is not None:
            stderr_stream.close()
        if sampler is not None:
            sampler.set_phase("after_server_shutdown")
            sampler.stop()

    if "result_status" not in locals():
        result_status, result_error = "FAIL", {"type": "InternalError", "error": "missing terminal status"}
    telemetry = sampler.rows if sampler else []
    completion_events = [event for event in locals().get("events", [])
                         if event.get("event") in {"completion_attempt_started", "completion_attempt_finished"}]
    generation_intervals: dict[tuple[str, int], dict[str, int]] = {}
    for event in completion_events:
        key = (str(event.get("request_id")), int(event.get("attempt", 0)))
        generation_intervals.setdefault(key, {})[event["event"]] = event["monotonic_ns"]
    sampled_during = []
    for key, interval in generation_intervals.items():
        start_ns, end_ns = interval.get("completion_attempt_started"), interval.get("completion_attempt_finished")
        if start_ns is not None and end_ns is not None and any(
                start_ns <= sample["monotonic_ns"] <= end_ns for sample in telemetry):
            sampled_during.append({"request_id": key[0], "attempt": key[1],
                                   "start_monotonic_ns": start_ns, "end_monotonic_ns": end_ns})
    _write_json(out_dir / "telemetry-summary.json", {
        "sample_count": len(telemetry), "gpu_samples_successful": sum(
            row.get("returncode") == 0 and bool(row.get("gpus")) for row in telemetry),
        "completion_attempts": len([event for event in completion_events
                                     if event.get("event") == "completion_attempt_started"]),
        "completion_intervals_with_gpu_sample": sampled_during,
        "at_least_one_completion_interval_sampled": bool(sampled_during),
        "interpretation": "nvidia-smi process-level samples; a sample inside HTTP inference interval does not identify per-process VRAM attribution"})
    terminal = {"status": result_status, "failure": result_error,
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "budget_maxima_enforced": {"logical_requests": 6, "http_attempts": 12,
                                           "completion_attempts": 4},
                "local_completion_attempts": locals()["budget"].completion_attempts
                    if "budget" in locals() else 0,
                "logical_preflight_http_requests": len(locals()["budget"].logical_ids)
                    if "budget" in locals() else 0,
                "external_model_calls": 0,
                "full_pilot_authorized": False, "m2_authorized": False}
    _write_json(out_dir / "terminal-status.json", terminal)
    _manifest(out_dir)
    ledger_record = json.loads(approval_ledger_path.read_text(encoding="utf-8"))
    ledger_record.update({"status": "CONSUMED", "terminal_status": result_status,
                          "completed_at_utc": terminal["completed_at_utc"],
                          "evidence_manifest_sha256": _sha256_file(out_dir / "manifest.json")})
    temporary_ledger = approval_ledger_path.with_suffix(".tmp")
    _write_json(temporary_ledger, ledger_record)
    temporary_ledger.replace(approval_ledger_path)
    return 0 if result_status == "PASS_INTERFACE" else 2


def _git_head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, timeout=5, check=True).stdout.strip()
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--runtime-config", type=Path,
                        default=ROOT / "configs" / "m1-r-offline-v2.toml")
    parser.add_argument("--original-config", type=Path,
                        default=ROOT / "configs" / "m1-p0-llama-local-draft.toml")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--approval-id", required=True)
    args = parser.parse_args()
    return execute(args.config.resolve(), args.runtime_config.resolve(), args.original_config.resolve(),
                   args.out.resolve(), args.approval_id)


if __name__ == "__main__":
    raise SystemExit(main())
