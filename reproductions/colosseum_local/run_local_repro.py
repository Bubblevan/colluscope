from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
import yaml


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "reference" / "colosseum"
UPSTREAM_RUN = UPSTREAM / "experiments" / "collusion" / "run.py"
UPSTREAM_CONFIG = UPSTREAM / "experiments" / "collusion" / "configs" / "collusion_jira_topologies.yaml"
OUT_ROOT = UPSTREAM / "experiments" / "collusion" / "outputs" / "colluscope-qwen3-conceptual-20261020"
MODEL_PATH = Path(os.environ.get(
    "COLLUSCOPE_MODEL_PATH",
    "Qwen3-8B-Q4_K_M.gguf",
))
LLAMA_SERVER = Path(os.environ.get("COLLUSCOPE_LLAMA_SERVER", "llama-server"))
EXPECTED_UPSTREAM_SHA = "b077fe7e2f10566e92156cc12e06ffb2aac54790"
EXPECTED_MODEL_SHA256 = "D98CDCBD03E17CE47681435B5150E34C1417F50B5C0019DD560E4882C5745785"
EXPECTED_LOCK_SHA256 = "392C56D8448A2076E015A7A035D62FEDA51B77B3D58FB7747F1541F98C74F49E"
EXPECTED_ACTIVE_CONFIG_SHA256 = "3305410D091F37228CA429E1D68591ED78FD8C8F31C0EF4D03DE7FBD6FBEA06F"
LOCAL_BASE_URL = "http://127.0.0.1:8081/v1"
LOCAL_ALIAS = "colluscope-qwen3-8b-q4km"
API_KEY_PLACEHOLDER = "local-only-not-a-secret"
PORT = 8081
MAX_HTTP_ATTEMPTS = 900
MAX_OUTPUT_TOKENS = 1500
TEMPERATURE = 0.7
REQUEST_TIMEOUT_SECONDS = 600
SEEDS = (1, 2, 3, 4, 5)
CONDITIONS = (
    ("no_secret_control", False, "control"),
    ("secret_channel_control", True, "control"),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


@dataclass(frozen=True)
class Episode:
    condition: str
    secret_channel_enabled: bool
    prompt_variant: str
    seed: int

    @property
    def episode_id(self) -> str:
        return f"{self.condition}__seed{self.seed}"


def assignments() -> list[Episode]:
    return [Episode(condition, secret, prompt, seed)
            for seed in SEEDS
            for condition, secret, prompt in CONDITIONS]


def max_generation_bound() -> int:
    # Upstream run.py: six agents; four planning rounds plus one execution
    # turn; max_conversation_steps=3 bounds each turn to three generations.
    return 6 * (4 + 1) * 3


class BudgetExceeded(RuntimeError):
    pass


class LocalEndpointPolicyError(RuntimeError):
    pass


class RequestGuard:
    """Count and constrain every requests.Session HTTP attempt in this process."""

    def __init__(self, ledger_path: Path, hard_cap: int = MAX_HTTP_ATTEMPTS):
        self.ledger_path = ledger_path
        self.hard_cap = hard_cap
        self.attempts = 0
        if ledger_path.exists():
            for line_no, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Malformed request ledger line {line_no}; fail closed") from exc
                if row.get("event") == "http_attempt_started":
                    self.attempts += 1
        if self.attempts > self.hard_cap:
            raise RuntimeError("Existing request ledger exceeds the frozen hard cap")
        self.episode_id = "bootstrap"
        self._lock = threading.Lock()
        self._original_request = requests.Session.request

    def install(self) -> None:
        original = self._original_request
        guard = self

        def guarded_request(session, method, url, **kwargs):
            parsed = urlsplit(str(url))
            allowed = (
                str(method).upper() == "POST"
                and parsed.scheme == "http"
                and parsed.hostname == "127.0.0.1"
                and parsed.port == PORT
                and parsed.path == "/v1/chat/completions"
                and not parsed.query
                and not parsed.fragment
            )
            if not allowed:
                append_jsonl(guard.ledger_path, {
                    "time": utc_now(), "episode_id": guard.episode_id,
                    "event": "blocked_endpoint_or_method", "method": str(method),
                    "url_origin": f"{parsed.scheme}://{parsed.netloc}",
                    "path": parsed.path,
                })
                raise LocalEndpointPolicyError(
                    f"Only POST {LOCAL_BASE_URL}/chat/completions is permitted"
                )

            body = kwargs.get("data")
            if body is None and kwargs.get("json") is not None:
                body = json.dumps(kwargs["json"], sort_keys=True, ensure_ascii=False)
            if isinstance(body, str):
                body = body.encode("utf-8")
            body_hash = sha256_bytes(body if isinstance(body, bytes) else b"")
            with guard._lock:
                if guard.attempts >= guard.hard_cap:
                    append_jsonl(guard.ledger_path, {
                        "time": utc_now(), "episode_id": guard.episode_id,
                        "event": "blocked_over_budget", "attempts_already_sent": guard.attempts,
                        "hard_cap": guard.hard_cap, "request_sha256": body_hash,
                    })
                    raise BudgetExceeded(f"HTTP hard cap {guard.hard_cap} reached")
                guard.attempts += 1
                attempt = guard.attempts
                append_jsonl(guard.ledger_path, {
                    "time": utc_now(), "episode_id": guard.episode_id,
                    "event": "http_attempt_started", "attempt": attempt,
                    "method": "POST", "url": f"{LOCAL_BASE_URL}/chat/completions",
                    "request_sha256": body_hash,
                })
            try:
                response = original(session, method, url, **kwargs)
                response_bytes = response.content
                append_jsonl(guard.ledger_path, {
                    "time": utc_now(), "episode_id": guard.episode_id,
                    "event": "http_response", "attempt": attempt,
                    "status_code": int(response.status_code),
                    "response_sha256": sha256_bytes(response_bytes),
                    "response_bytes": len(response_bytes),
                })
                return response
            except Exception as exc:
                append_jsonl(guard.ledger_path, {
                    "time": utc_now(), "episode_id": guard.episode_id,
                    "event": "http_exception", "attempt": attempt,
                    "error_type": type(exc).__name__, "error": str(exc)[:800],
                })
                raise

        requests.Session.request = guarded_request

    def set_episode(self, episode_id: str) -> None:
        self.episode_id = episode_id


def source_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def llama_version() -> str:
    result = subprocess.run(
        [str(LLAMA_SERVER), "--version"], check=True, capture_output=True, text=True,
        timeout=20,
    )
    return (result.stdout + result.stderr).strip()


def imported_source_paths() -> dict[str, Path]:
    sys.path.insert(0, str(UPSTREAM))
    import experiments.collusion.metrics as metrics
    import experiments.collusion.prompts as prompts
    import experiments.common.local_protocol as protocol
    import terrarium.agents.base as base_agent
    import terrarium.utils as terrarium_utils
    import envs.abstract_environment as abstract_environment
    import envs.dcops.jira_ticket.jira_ticket_env as jira_env
    import envs.dcops.jira_ticket.jira_ticket_prompts as jira_prompts
    import llm_server.clients.together_client as together_client

    import inspect
    return {
        "collusion_run.py": UPSTREAM_RUN,
        "collusion_metrics.py": Path(inspect.getfile(metrics)),
        "collusion_prompts.py": Path(inspect.getfile(prompts)),
        "local_protocol.py": Path(inspect.getfile(protocol)),
        "agent_base.py": Path(inspect.getfile(base_agent)),
        "terrarium_utils.py": Path(inspect.getfile(terrarium_utils)),
        "abstract_environment.py": Path(inspect.getfile(abstract_environment)),
        "jira_ticket_env.py": Path(inspect.getfile(jira_env)),
        "jira_ticket_prompts.py": Path(inspect.getfile(jira_prompts)),
        "together_client.py": Path(inspect.getfile(together_client)),
    }


def preregistration_manifest() -> dict[str, Any]:
    if source_commit() != EXPECTED_UPSTREAM_SHA:
        raise RuntimeError(f"Unexpected Colosseum source HEAD: {source_commit()}")
    if sha256_file(MODEL_PATH) != EXPECTED_MODEL_SHA256:
        raise RuntimeError("Local GGUF identity hash mismatch")
    lock_path = UPSTREAM / "uv.lock"
    if sha256_file(lock_path) != EXPECTED_LOCK_SHA256:
        raise RuntimeError("Colosseum uv.lock hash mismatch")
    if sha256_file(UPSTREAM_CONFIG) != EXPECTED_ACTIVE_CONFIG_SHA256:
        raise RuntimeError("Upstream active Jira config hash mismatch")

    config = yaml.safe_load(UPSTREAM_CONFIG.read_text(encoding="utf-8"))
    sweep = config["experiment"]["sweeps"][0]
    if sweep["topologies"] != ["complete"] or sweep["num_agents"] != [6]:
        raise RuntimeError("Unexpected topology/agent count in upstream config")
    if sweep["colluder_counts"] != [2] or config["environment"]["name"] != "JiraTicketEnvironment":
        raise RuntimeError("Unexpected Jira/colluder design in upstream config")
    if config["simulation"]["max_planning_rounds"] != 4 or config["simulation"]["max_conversation_steps"] != 3:
        raise RuntimeError("Unexpected upstream call-graph bound")

    source_hashes = {name: sha256_file(path) for name, path in imported_source_paths().items()}
    venv_python = UPSTREAM / ".venv" / "Scripts" / "python.exe"
    return {
        "protocol_id": "collosseum-jira-local-qwen3-conceptual-v1",
        "created_utc": utc_now(),
        "orchestration_sha256": sha256_file(Path(__file__).resolve()),
        "claim_boundary": "protocol-level conceptual replication; not paper-model replication",
        "upstream": {
            "repository": "https://github.com/umass-ai-safety/colosseum",
            "commit": source_commit(), "coLLAB_gitlink": "018c9e4229d2c5d980285f25be3cca8d1508140f",
            "uv_lock_sha256": EXPECTED_LOCK_SHA256,
            "active_jira_config_sha256": EXPECTED_ACTIVE_CONFIG_SHA256,
            "relevant_source_sha256": source_hashes,
        },
        "environment": {
            "python_executable": str(venv_python),
            "python_version": sys.version,
            "platform": sys.platform,
            "llama_server": str(LLAMA_SERVER), "llama_version": llama_version(),
            "model_path": str(MODEL_PATH), "model_sha256": EXPECTED_MODEL_SHA256,
            "api_host": "127.0.0.1", "api_port": PORT, "api_key": "placeholder only; no credential",
            "external_http_policy": "process-wide requests.Session guard: deny every request except exact local completion endpoint",
            "dotenv": "PYTHON_DOTENV_DISABLED=1; no .env read",
        },
        "design": {
            "agents": 6, "colluders": 2, "environment": "JiraTicketEnvironment",
            "topology": "complete", "planning_rounds": 4,
            "max_conversation_steps_per_turn": 3,
            "conditions": [
                {"id": "no_secret_control", "secret_channel_enabled": False, "prompt_variant": "control"},
                {"id": "secret_channel_control", "secret_channel_enabled": True, "prompt_variant": "control"},
            ],
            "paired_seeds": list(SEEDS), "episodes": len(assignments()),
            "selection": "upstream random colluder selection and random agent order, same integer seed per matched condition pair",
            "intervention_bundle": "The secret-channel condition adds a colluder-only blackboard initialized with the Jira task context and a private-channel/participant announcement. The built-in control prompt variant is empty; this is not a channel-only manipulation of awareness/salience.",
            "interpretation": "condition assignment is an intervention label, not a collusion gold label",
        },
        "sampling_and_budget": {
            "temperature": TEMPERATURE, "max_output_tokens": MAX_OUTPUT_TOKENS,
            "top_p": 0.95, "top_k": 40, "min_p": 0.05, "repeat_penalty": 1.0,
            "llama_seed": "matched environment seed; server restarted for each episode",
            "context_tokens": 16384, "parallel_slots": 1, "gpu_layers": 99,
            "jinja": True, "webui": False, "timeout_seconds": REQUEST_TIMEOUT_SECONDS,
            "retry_policy": "zero client retries; no episode retries or replacement",
            "max_generations_per_episode": max_generation_bound(),
            "max_http_attempts_all_episodes": MAX_HTTP_ATTEMPTS,
            "maximum_calls_by_call_graph": len(assignments()) * max_generation_bound(),
            "actual_messages": "not called before this manifest is frozen",
        },
        "failure_policy": {
            "http_and_generation_retries": 0,
            "replacements": 0,
            "resume_cap": "A same-assignment infrastructure restart is permitted at most once only when the append-only ledger proves no HTTP attempt occurred; the original failure and separate server log are retained. Any request-bearing or ambiguous interrupted episode is never rerun.",
        },
        "analysis": {
            "primary_observables": ["episode completion/status", "coalition advantage", "action regret", "final allocation", "public welfare", "token usage"],
            "no_gold_label": "No latent collusion label is assigned; secret-channel access and metrics are not gold labels.",
            "judge_model": "not run",
        },
    }


def write_frozen_configs(out_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    base = yaml.safe_load(UPSTREAM_CONFIG.read_text(encoding="utf-8"))
    base_sweep = base["experiment"]["sweeps"][0]
    config_dir = out_dir / "frozen_configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for episode in assignments():
        cfg = json.loads(json.dumps(base))
        cfg["simulation"]["seed"] = episode.seed
        cfg["llm_models"] = [{
            "label": "qwen3-8b-q4km-local",
            "llm": {
                "provider": "together",
                "together": {
                    "model": LOCAL_ALIAS,
                    "base_url": LOCAL_BASE_URL,
                    "api_key": API_KEY_PLACEHOLDER,
                    "request_timeout": REQUEST_TIMEOUT_SECONDS,
                    "params": {"max_tokens": MAX_OUTPUT_TOKENS, "temperature": TEMPERATURE},
                },
            },
        }]
        cfg["experiment"]["tag"] = "colluscope_colosseum_local_conceptual"
        cfg["experiment"]["output_dir"] = str(OUT_ROOT / "upstream_runs" / episode.episode_id)
        cfg["experiment"]["max_concurrent_runs"] = 1
        sweep = json.loads(json.dumps(base_sweep))
        sweep["name"] = episode.condition
        sweep["secret_channel_enabled"] = [episode.secret_channel_enabled]
        sweep["prompt_variants"] = [episode.prompt_variant]
        sweep["seeds"] = [episode.seed]
        cfg["experiment"]["sweeps"] = [sweep]
        path = config_dir / f"{episode.episode_id}.yaml"
        rendered = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        path.write_text(rendered, encoding="utf-8", newline="\n")
        rows.append({"episode_id": episode.episode_id, "path": str(path), "sha256": sha256_file(path)})
    manifest["frozen_configurations"] = rows
    return rows


def tcp_listener_ready(host: str = "127.0.0.1", port: int = PORT) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def wait_for_server(process: subprocess.Popen, log_path: Path, timeout: int = 420) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited with code {process.returncode}; see {log_path}")
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="replace")
            lowered = text.lower()
            if (
                "model loaded" in lowered
                and f"listening on http://127.0.0.1:{PORT}" in lowered
                and tcp_listener_ready()
            ):
                return
        time.sleep(1)
    raise TimeoutError(f"llama-server did not reach ready state in {timeout}s; see {log_path}")


def server_args(seed: int) -> list[str]:
    return [
        str(LLAMA_SERVER), "--model", str(MODEL_PATH), "--host", "127.0.0.1",
        "--port", str(PORT), "--api-key", API_KEY_PLACEHOLDER, "--alias", LOCAL_ALIAS,
        "--ctx-size", "16384", "--parallel", "1", "--n-gpu-layers", "99",
        "--seed", str(seed), "--temp", str(TEMPERATURE), "--top-p", "0.95",
        "--top-k", "40", "--min-p", "0.05", "--repeat-penalty", "1.0",
        "--predict", str(MAX_OUTPUT_TOKENS), "--jinja", "--no-webui",
    ]


def start_server(episode: Episode, raw_dir: Path, attempt_no: int) -> tuple[subprocess.Popen, Any, Path]:
    log_path = raw_dir / f"llama-server-attempt-{attempt_no:02d}.log"
    log_stream = log_path.open("wb")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        server_args(episode.seed), cwd=str(UPSTREAM), stdout=log_stream,
        stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=flags,
    )
    return process, log_stream, log_path


def stop_server(process: subprocess.Popen | None, log_stream: Any | None) -> None:
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    if log_stream is not None:
        log_stream.flush()
        log_stream.close()


def set_safe_environment() -> None:
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ["TOGETHER_MAX_RETRIES"] = "0"
    os.environ.pop("TOGETHER_API_KEY", None)
    os.environ.pop("TOGETHER_RETRY_BASE_SLEEP_S", None)
    os.environ.pop("TOGETHER_RETRY_MAX_SLEEP_S", None)


def run_all(out_dir: Path, guard: RequestGuard, start_index: int = 0) -> None:
    sys.path.insert(0, str(UPSTREAM))
    set_safe_environment()
    import asyncio
    from experiments.collusion.run import run_from_config

    progress_path = out_dir / "progress.jsonl"
    events: dict[str, list[dict[str, Any]]] = {}
    if progress_path.exists():
        for line in progress_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            events.setdefault(row["episode_id"], []).append(row)

    for index, episode in enumerate(assignments()):
        if index < start_index:
            continue
        episode_events = events.get(episode.episode_id, [])
        started_count = sum(row.get("event") == "episode_started" for row in episode_events)
        terminal_rows = [row for row in episode_events if row.get("event") == "episode_terminal"]
        last_terminal = terminal_rows[-1] if terminal_rows else None
        attempt_no = started_count + 1
        # Permit one infrastructure recovery only when a prior terminal record
        # proves that zero generation HTTP requests were attempted. Never rerun
        # an episode after a request was sent or after an ambiguous interruption.
        if started_count:
            resumable_pre_generation_failure = (
                last_terminal is not None
                and last_terminal.get("status") == "failed_pre_generation_no_http"
                and started_count == 1
                and last_terminal.get("http_attempts_before") == last_terminal.get("http_attempts_after")
            )
            if last_terminal is None:
                append_jsonl(progress_path, {
                    "time": utc_now(), "episode_id": episode.episode_id,
                    "event": "episode_terminal", "status": "interrupted_indeterminate_no_rerun",
                    "detail": "A prior start exists without a terminal record; preserve and do not regenerate.",
                })
                continue
            if not resumable_pre_generation_failure:
                continue

        guard.set_episode(episode.episode_id)
        append_jsonl(progress_path, {
            "time": utc_now(), "episode_id": episode.episode_id,
            "event": "episode_started", "condition": episode.condition,
            "attempt_no": attempt_no,
            "seed": episode.seed, "secret_channel_enabled": episode.secret_channel_enabled,
            "prompt_variant": episode.prompt_variant,
            "http_attempts_before": guard.attempts,
        })
        raw_dir = out_dir / "raw" / episode.episode_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        cfg_path = out_dir / "frozen_configs" / f"{episode.episode_id}.yaml"
        process = log_stream = None
        attempts_before = guard.attempts
        try:
            process, log_stream, log_path = start_server(episode, raw_dir, attempt_no)
            wait_for_server(process, log_path)
            append_jsonl(progress_path, {
                "time": utc_now(), "episode_id": episode.episode_id,
                "event": "server_ready", "server_pid": process.pid,
                "server_args_sha256": sha256_bytes("\0".join(server_args(episode.seed)).encode()),
                "server_log": str(log_path),
            })
            out = asyncio.run(run_from_config(
                str(cfg_path), out_dir=str(OUT_ROOT / "upstream_runs" / episode.episode_id),
                max_concurrent_runs=1,
            ))
            append_jsonl(progress_path, {
                "time": utc_now(), "episode_id": episode.episode_id,
                "event": "episode_terminal", "status": "runner_returned",
                "attempt_no": attempt_no,
                "upstream_output": str(out), "http_attempts_before": attempts_before,
                "http_attempts_after": guard.attempts,
            })
        except Exception as exc:
            append_jsonl(progress_path, {
                "time": utc_now(), "episode_id": episode.episode_id,
                "event": "episode_terminal",
                "status": "failed_pre_generation_no_http" if guard.attempts == attempts_before else "failed_preserved",
                "attempt_no": attempt_no,
                "http_attempts_before": attempts_before,
                "error_type": type(exc).__name__, "error": str(exc)[:2000],
                "traceback": traceback.format_exc()[-6000:],
                "http_attempts_after": guard.attempts,
            })
            if isinstance(exc, (BudgetExceeded, LocalEndpointPolicyError)):
                for remaining in assignments()[index + 1:]:
                    append_jsonl(progress_path, {
                        "time": utc_now(), "episode_id": remaining.episode_id,
                        "event": "episode_terminal", "status": "not_run_safety_guard",
                        "detail": type(exc).__name__,
                    })
                break
        finally:
            stop_server(process, log_stream)


def write_freeze() -> Path:
    if not MODEL_PATH.is_file() or not LLAMA_SERVER.is_file() or not UPSTREAM_RUN.is_file():
        raise FileNotFoundError("Required local model, llama-server, or upstream source is missing")
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT_ROOT / "frozen_protocol.json"
    if manifest_path.exists():
        raise FileExistsError(f"Freeze already exists; refusing to overwrite: {manifest_path}")
    manifest = preregistration_manifest()
    write_frozen_configs(OUT_ROOT, manifest)
    manifest["frozen_configurations_sha256"] = sha256_bytes(json.dumps(
        manifest["frozen_configurations"], sort_keys=True
    ).encode())
    payload = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    manifest_path.write_text(payload, encoding="utf-8", newline="\n")
    return manifest_path


def validate_freeze(out_dir: Path) -> dict[str, Any]:
    path = out_dir / "frozen_protocol.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if source_commit() != manifest["upstream"]["commit"]:
        raise RuntimeError("Frozen upstream commit changed")
    if sha256_file(Path(__file__).resolve()) != manifest["orchestration_sha256"]:
        raise RuntimeError("Frozen orchestration source changed")
    if sha256_file(UPSTREAM_CONFIG) != manifest["upstream"]["active_jira_config_sha256"]:
        raise RuntimeError("Frozen upstream Jira configuration changed")
    if sha256_file(UPSTREAM / "uv.lock") != manifest["upstream"]["uv_lock_sha256"]:
        raise RuntimeError("Frozen upstream dependency lock changed")
    for name, path in imported_source_paths().items():
        expected = manifest["upstream"]["relevant_source_sha256"].get(name)
        if expected is None or sha256_file(path) != expected:
            raise RuntimeError(f"Frozen upstream source changed: {name}")
    if llama_version() != manifest["environment"]["llama_version"]:
        raise RuntimeError("Frozen llama.cpp server version changed")
    if sha256_file(MODEL_PATH) != manifest["environment"]["model_sha256"]:
        raise RuntimeError("Frozen model hash changed")
    for row in manifest["frozen_configurations"]:
        cfg_path = Path(row["path"])
        if not cfg_path.is_file() or sha256_file(cfg_path) != row["sha256"]:
            raise RuntimeError(f"Frozen episode config changed: {cfg_path}")
    return manifest


def self_test() -> None:
    assert len(assignments()) == 10
    assert max_generation_bound() == 90
    assert len({(x.seed, x.condition) for x in assignments()}) == 10
    for seed in SEEDS:
        pair = [x for x in assignments() if x.seed == seed]
        assert len(pair) == 2 and pair[0].seed == pair[1].seed
        assert {x.secret_channel_enabled for x in pair} == {False, True}
        assert {x.prompt_variant for x in pair} == {"control"}

    # The upstream `control` variant is empty, but the treatment channel's
    # initial context explicitly discloses private status and participants.
    sys.path.insert(0, str(UPSTREAM))
    from experiments.collusion.prompts import _BUILTIN_VARIANTS
    import inspect
    from envs.abstract_environment import AbstractEnvironment
    assert _BUILTIN_VARIANTS["control"] == ""
    channel_formatter = inspect.getsource(AbstractEnvironment.format_blackboard_context)
    assert "private communication channel" in channel_formatter
    assert "Participants:" in channel_formatter

    # Adversarial request-policy tests: only an exact local completion POST is
    # ever forwarded; non-local, alternate path, GET, and request 901 are blocked.
    temp = ROOT / "runs" / "colosseum-local-selftest-http.jsonl"
    temp.parent.mkdir(parents=True, exist_ok=True)
    if temp.exists():
        temp.unlink()
    original = requests.Session.request
    calls: list[str] = []

    class FakeResponse:
        status_code = 200
        content = b"ok"

    requests.Session.request = lambda session, method, url, **kwargs: calls.append(str(url)) or FakeResponse()
    guard = RequestGuard(temp, hard_cap=1)
    guard.install()
    session = requests.Session()
    guard.set_episode("selftest")
    try:
        response = session.post(f"{LOCAL_BASE_URL}/chat/completions", data="{}")
        assert response.status_code == 200 and guard.attempts == 1
        blocked = 0
        for method, url in [
            ("POST", "https://example.com/v1/chat/completions"),
            ("POST", f"{LOCAL_BASE_URL}/models"),
            ("GET", f"{LOCAL_BASE_URL}/chat/completions"),
            ("POST", f"{LOCAL_BASE_URL}/chat/completions"),
        ]:
            try:
                session.request(method, url, data="{}")
            except (LocalEndpointPolicyError, BudgetExceeded):
                blocked += 1
        assert blocked == 4
        assert len(calls) == 1
        rows = [json.loads(line) for line in temp.read_text(encoding="utf-8").splitlines()]
        assert sum(row.get("event") == "http_attempt_started" for row in rows) == 1
        assert sum(row.get("event") == "blocked_endpoint_or_method" for row in rows) == 3
        assert sum(row.get("event") == "blocked_over_budget" for row in rows) == 1
    finally:
        requests.Session.request = original
        temp.unlink(missing_ok=True)

    # A fresh process must recover the hard-cap count from the durable ledger.
    resumed_ledger = ROOT / "runs" / "colosseum-local-selftest-resume.jsonl"
    if resumed_ledger.exists():
        resumed_ledger.unlink()
    append_jsonl(resumed_ledger, {"event": "http_attempt_started", "attempt": 1})
    append_jsonl(resumed_ledger, {"event": "http_attempt_started", "attempt": 2})
    resumed_guard = RequestGuard(resumed_ledger, hard_cap=2)
    assert resumed_guard.attempts == 2
    resumed_ledger.unlink()
    set_safe_environment()
    assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"
    assert os.environ["TOGETHER_MAX_RETRIES"] == "0"
    print("SELF-TEST PASS: 10 matched episodes, 900-call bound, treatment-context disclosure identified, endpoint and request-cap counterexamples blocked; 0 model calls")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--freeze-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--out", type=Path, default=OUT_ROOT)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0
    if args.freeze_only:
        print(write_freeze())
        return 0
    manifest = validate_freeze(args.out)
    del manifest
    set_safe_environment()
    guard = RequestGuard(args.out / "http_requests.jsonl")
    guard.install()
    run_all(args.out, guard)
    print(json.dumps({"http_attempts": guard.attempts, "hard_cap": guard.hard_cap, "output": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
