"""Fail-closed, resumable local runner for the M1 package-replication v3 draft.

The default path is offline validation only. Live execution requires a matching
registered preregistration and current immutable authorization batch; this
module never selects a remote provider.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ID = "m1-reward-chat-24group-replication-v1"
RESEARCH_SCOPE = "m1-package-replication-v3"
SCHEDULE_PATH = ROOT / "research/drafts/m1-package-24-matrix-scenarios-20261021.json"
CONFIG_PATH = ROOT / "configs/m1-package-replication-v3.toml"
RUNTIME_CONFIG_PATH = ROOT / "configs/m1-r-offline-v2.toml"
FROZEN_SCHEDULE_SHA256 = "79358acd02dcade31291e879d1d173e5e92e9bf5f57305c65a3d59f954ca502a"
GENERATION_MAX = 456
IDENTITY_HTTP_MAX = 24
PHYSICAL_HTTP_MAX = 480
FROZEN_INPUT_PATHS = (
    "configs/m1-package-replication-v3.toml",
    "configs/m1-r-offline-v2.toml",
    "research/drafts/m1-package-24-matrix-scenarios-20261021.json",
    "scripts/freeze_m1_package_24_matrix_design.py",
    "scripts/audit_m1_package_24_matrix_design.py",
    "scripts/audit_m1_replication_prompt_profiles.py",
    "scripts/run_m1_package_replication_v3.py",
    "scripts/local_llama_security.py",
    "scripts/run_m1_p0_local_preflight.py",
    "scripts/researchctl.py",
    "tests/test_m1_package_replication_v3_runtime.py",
    "tests/test_openai_compat_llamacpp.py",
    "docs/M1_PACKAGE_REPLICATION_V3_PROTOCOL.md",
    "docs/M1_PACKAGE_REPLICATION_V3_RUNTIME_TRD.md",
    "src/colluscope/m1_package_replication_v3_runtime.py",
    "src/colluscope/openai_compat_llamacpp.py",
    "src/colluscope/m1_runtime.py",
    "src/colluscope/gguf_tokenizer.py",
    "prompts/m1-p0-v2/system.txt",
    "prompts/m1-p0-v2/message.txt",
    "prompts/m1-p0-v2/ballot.txt",
    "prompts/m1-p0-v2/communication.schema.json",
    "prompts/m1-p0-v2/ballot.schema.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class HashChainJournal:
    """Append-only JSONL with per-row hashes; each append is flushed to disk."""

    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.is_symlink() or self.path.resolve() != self.path.absolute():
            raise PermissionError("append-only journal path cannot traverse a symlink or junction")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.rows = self._read_and_verify()
        self.sequence = len(self.rows)
        self.previous_hash = self.rows[-1]["record_sha256"] if self.rows else "0" * 64

    def _read_and_verify(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        output = []
        previous = "0" * 64
        for expected_sequence, line in enumerate(self.path.read_bytes().splitlines(), start=1):
            try:
                row = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError(f"journal is corrupt at line {expected_sequence}") from exc
            claimed = row.pop("record_sha256", None)
            if (row.get("sequence") != expected_sequence or row.get("previous_sha256") != previous
                    or claimed != sha256_bytes(canonical_json(row).rstrip(b"\n"))):
                raise ValueError(f"journal hash chain is corrupt at line {expected_sequence}")
            row["record_sha256"] = claimed
            output.append(row)
            previous = claimed
        return output

    def append(self, payload: dict[str, Any]) -> dict[str, Any]:
        row = {"sequence": self.sequence + 1, "previous_sha256": self.previous_hash,
               "at_utc": utc_now(), "payload": payload}
        row["record_sha256"] = sha256_bytes(canonical_json(row).rstrip(b"\n"))
        line = canonical_json(row)
        with self.path.open("ab") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())
        self.sequence += 1
        self.previous_hash = row["record_sha256"]
        self.rows.append(row)
        return row


def load_frozen_schedule(path: Path = SCHEDULE_PATH) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if sha256_bytes(raw) != FROZEN_SCHEDULE_SHA256:
        raise ValueError("M1 v3 matrix schedule differs from its pre-generation frozen SHA-256")
    schedule = json.loads(raw)
    if schedule.get("status") != "DRAFT_FROZEN_BEFORE_ANY_NEW_MODEL_RESPONSE":
        raise ValueError("M1 v3 schedule is not the frozen pre-response candidate")
    scenarios = schedule.get("scenarios")
    groups = schedule.get("groups")
    if not isinstance(scenarios, list) or len(scenarios) != 24 or not isinstance(groups, list) or len(groups) != 24:
        raise ValueError("M1 v3 schedule must contain 24 distinct matched groups and matrices")
    by_id = {row["scenario_family_id"]: row for row in scenarios}
    if len(by_id) != 24:
        raise ValueError("M1 v3 scenario IDs are not unique")
    assignment_count = 0
    seen_episode_ids = set()
    expected_conditions = {
        "normal_cooperation", "common_incentive_parallel_behavior",
        "coalition_incentive_private_chat", "coalition_incentive_no_private_chat",
        "private_chat_no_side_bonus",
    }
    for group in groups:
        if group.get("scenario_family_id") not in by_id:
            raise ValueError("M1 v3 group references an unknown payoff matrix")
        conditions = group.get("condition_order")
        if not isinstance(conditions, list) or set(conditions) != expected_conditions or len(conditions) != 5:
            raise ValueError("M1 v3 group does not assign all five frozen conditions exactly once")
        for condition_id in conditions:
            episode_id = f"{group['group_id']}__{condition_id}"
            if episode_id in seen_episode_ids:
                raise ValueError("M1 v3 schedule contains duplicate assigned episodes")
            seen_episode_ids.add(episode_id)
            assignment_count += 1
    if assignment_count != 120 or len(seen_episode_ids) != 120:
        raise ValueError("M1 v3 assigned denominator differs from 120 episodes")
    if schedule.get("design", {}).get("total_local_generations") != GENERATION_MAX:
        raise ValueError("M1 v3 generation ceiling differs from 456")
    return schedule


def assigned_episodes(schedule: dict[str, Any]) -> list[dict[str, Any]]:
    scenarios = {row["scenario_family_id"]: row for row in schedule["scenarios"]}
    rows = []
    for group in schedule["groups"]:
        scenario = scenarios[group["scenario_family_id"]]
        for condition_id in group["condition_order"]:
            rows.append({"episode_id": f"{group['group_id']}__{condition_id}",
                         "group_id": group["group_id"], "scenario_family_id": scenario["scenario_family_id"],
                         "scenario_sha256": group["scenario_sha256"], "seed_block_id": group["seed_block_id"],
                         "condition_id": condition_id, "condition_order": list(group["condition_order"]),
                         "target_regret_stratum": group["target_regret_stratum"], "scenario": scenario})
    return rows


def verify_live_authorization(approval_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    """Require the exact registered experiment and current immutable approval.

    This check only reads registry files. It does not launch llama.cpp or send
    a request. The current M4 grant is intentionally insufficient for M1.
    """
    if not approval_id or Path(approval_id).name != approval_id:
        raise PermissionError("live M1 v3 requires an explicit approval ID")
    experiment = ROOT / "research/experiments" / EXPERIMENT_ID
    prereg_path = experiment / "preregistration.json"
    registration_path = experiment / "registration.json"
    if not prereg_path.is_file() or not registration_path.is_file():
        raise PermissionError("M1 v3 must be formally registered before any live execution")
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    if prereg.get("experiment_id") != EXPERIMENT_ID or registration.get("experiment_id") != EXPERIMENT_ID:
        raise PermissionError("registered experiment identity does not match M1 v3")
    if prereg.get("evidence_class") != "real_llm_behavior":
        raise PermissionError("registered M1 v3 evidence class is not real local agent behavior")
    if registration.get("preregistration_sha256") != sha256_file(prereg_path):
        raise PermissionError("M1 v3 preregistration bytes differ from its registration manifest")
    frozen_rows = prereg.get("protocol", {}).get("frozen_inputs", [])
    frozen_hashes = {row.get("path"): row.get("sha256") for row in frozen_rows if isinstance(row, dict)}
    if len(frozen_hashes) != len(FROZEN_INPUT_PATHS) or set(frozen_hashes) != set(FROZEN_INPUT_PATHS):
        raise PermissionError("registered M1 v3 preregistration lacks the complete runtime freeze manifest")
    changed = [relative for relative in FROZEN_INPUT_PATHS
               if frozen_hashes.get(relative) != sha256_file(ROOT / relative)]
    if changed:
        raise PermissionError("registered M1 v3 frozen inputs changed: " + ", ".join(changed))
    approval = prereg.get("authorization", {})
    if approval.get("approval_id") != approval_id:
        raise PermissionError("M1 v3 preregistration does not bind the requested approval ID")
    batch_path = ROOT / "research/authorizations" / f"{approval_id}.json"
    budget_path = ROOT / "research/budget.json"
    state_path = ROOT / "research/state.json"
    if not batch_path.is_file() or not budget_path.is_file() or not state_path.is_file():
        raise PermissionError("current authorization snapshot or immutable approval batch is missing")
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    budget = json.loads(budget_path.read_text(encoding="utf-8"))["authorization"]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if (batch.get("approval_id") != approval_id or budget.get("status") != "active"
            or budget.get("approval_id") != approval_id
            or EXPERIMENT_ID not in batch.get("authorized_experiment_ids", [])):
        raise PermissionError("requested M1 approval is not the current, matching active authorization")
    if registration.get("authorization_batch_sha256") != sha256_file(batch_path):
        raise PermissionError("immutable authorization batch differs from preregistration")
    if batch.get("max_model_calls") != GENERATION_MAX or batch.get("max_external_cost_usd") != 0.0:
        raise PermissionError("M1 v3 approval must be exactly 456 local generations and zero external cost")
    if prereg.get("budget", {}).get("max_model_calls") != GENERATION_MAX:
        raise PermissionError("registered M1 v3 budget differs from 456 local generations")
    if state.get("active_experiment_id") != EXPERIMENT_ID:
        raise PermissionError("research registry does not mark M1 v3 as the active experiment")
    expiry = datetime.fromisoformat(batch["expires_at_utc"].replace("Z", "+00:00"))
    approved = datetime.fromisoformat(batch["approved_at_utc"].replace("Z", "+00:00"))
    current = now or datetime.now(timezone.utc)
    if current < approved or current > expiry:
        raise PermissionError("M1 v3 authorization is not currently effective")
    audit = subprocess.run([sys.executable, str(ROOT / "scripts/researchctl.py"), "audit"],
                           cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
    if audit.returncode != 0:
        raise PermissionError("researchctl audit failed; live M1 v3 dispatch is blocked")
    return {"experiment_id": EXPERIMENT_ID, "approval_id": approval_id,
            "authorization_sha256": sha256_file(batch_path),
            "preregistration_sha256": sha256_file(prereg_path),
            "expires_at_utc": batch["expires_at_utc"], "registry_audit": "PASS"}


def _write_once_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or path.resolve() != path.absolute():
        raise PermissionError("immutable evidence path cannot traverse a symlink or junction")
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    with path.open("xb") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    return sha256_bytes(body)


def _reconstruct_run_state(request_journal: HashChainJournal,
                           group_journal: HashChainJournal) -> tuple[dict[str, int], set[str], int, int]:
    attempts: dict[str, int] = {}
    for envelope in request_journal.rows:
        record = envelope["payload"]
        if record.get("event") == "logical_request_attempt_reserved":
            request_id = record["request_id"]
            if request_id in attempts:
                raise ValueError("duplicate logical request reservation found in append-only ledger")
            attempts[request_id] = 1
    terminal = set()
    started = set()
    for envelope in group_journal.rows:
        row = envelope["payload"]
        if row.get("event") == "episode_started":
            if row["episode_id"] in started:
                raise ValueError("duplicate episode start in append-only group ledger; replay is forbidden")
            started.add(row["episode_id"])
        elif row.get("event") in {"episode_terminal", "episode_interrupted_on_resume"}:
            if row["episode_id"] not in started or row["episode_id"] in terminal:
                raise ValueError("orphan or duplicate episode terminal in append-only group ledger")
            terminal.add(row["episode_id"])
    unresolved = started - terminal
    if unresolved:
        for episode_id in sorted(unresolved):
            group_journal.append({"event": "episode_interrupted_on_resume", "episode_id": episode_id,
                                  "status": "FAILED_INTERRUPTED_NO_REPLAY", "replayed": False})
            terminal.add(episode_id)
    identity_count = 0
    terminal_requests = {envelope["payload"].get("request_id") for envelope in request_journal.rows
                         if envelope["payload"].get("event") == "logical_request_terminal"}
    if not terminal_requests.issubset(attempts):
        raise ValueError("logical request terminal lacks a durable pre-call reservation")
    physical_count = 0
    generation_count = 0
    seen_physical = set()
    for envelope in request_journal.rows:
        row = envelope["payload"]
        if row.get("event") == "physical_http_attempt_reserved":
            physical_count += 1
            physical_key = (row.get("request_id"), row.get("attempt"))
            if physical_key in seen_physical:
                raise ValueError("duplicate physical HTTP attempt key found; zero-retry freeze was violated")
            seen_physical.add(physical_key)
            if row.get("kind") == "identity":
                identity_count += 1
            elif row.get("kind") == "generation":
                generation_count += 1
                if row.get("request_id") not in attempts:
                    raise ValueError("physical generation request lacks a prior durable logical reservation")
            else:
                raise ValueError("unknown physical HTTP request kind in append-only ledger")
    if (len(attempts) > GENERATION_MAX or generation_count > GENERATION_MAX
            or identity_count > IDENTITY_HTTP_MAX or physical_count > PHYSICAL_HTTP_MAX):
        raise ValueError("resume ledger already exceeds the frozen M1 v3 request ceiling")
    return attempts, terminal, physical_count, identity_count


def validate_offline_candidate() -> dict[str, Any]:
    """Validate frozen source identities and computed assignment/request counts."""
    schedule = load_frozen_schedule()
    from .m1_runtime import load_runtime_config
    from .openai_compat_llamacpp import load_llamacpp_backend_config

    backend = load_llamacpp_backend_config(CONFIG_PATH)
    runtime = load_runtime_config(RUNTIME_CONFIG_PATH)
    if runtime.raw.get("prompt_version") != "m1-p0-frozen-v2":
        raise ValueError("M1 v3 runner requires the frozen M1-P0 V2 prompt/action contract")
    if runtime.monitor_can_see_private_messages is not False:
        raise PermissionError("public-only monitor evidence permission changed")
    if (runtime.private_bonus_units != 20 or backend.research_scope != RESEARCH_SCOPE
            or backend.max_logical_requests != GENERATION_MAX or backend.max_total_attempts != GENERATION_MAX
            or backend.max_attempts_per_request != 1):
        raise ValueError("runtime reward, scope, or request budget differs from the v3 freeze")
    episodes = assigned_episodes(schedule)
    expected_ballots = len(episodes) * 3
    expected_messages = sum(2 for row in episodes if row["condition_id"] in {
        "coalition_incentive_private_chat", "private_chat_no_side_bonus"})
    if (expected_ballots, expected_messages, expected_ballots + expected_messages) != (360, 96, 456):
        raise ValueError("M1 v3 actual request graph no longer totals 360 ballots + 96 messages")
    gate_commands = (
        [sys.executable, str(ROOT / "scripts/freeze_m1_package_24_matrix_design.py"), "--check"],
        [sys.executable, str(ROOT / "scripts/audit_m1_package_24_matrix_design.py"), "--check"],
        [sys.executable, str(ROOT / "scripts/audit_m1_replication_prompt_profiles.py"), "--check"],
        [sys.executable, str(ROOT / "scripts/researchctl.py"), "audit"],
    )
    gate_results = []
    for command in gate_commands:
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                   timeout=120, check=False)
        gate_results.append({"command": [Path(command[0]).name, *command[1:]],
                             "returncode": completed.returncode,
                             "stdout": completed.stdout.strip(),
                             "stderr": completed.stderr.strip()})
        if completed.returncode != 0:
            raise RuntimeError("offline source gate failed: " + " ".join(command[1:]))
    return {"status": "PASS_OFFLINE_CANDIDATE", "experiment_id": EXPERIMENT_ID,
            "schedule_sha256": sha256_file(SCHEDULE_PATH), "config_sha256": sha256_file(CONFIG_PATH),
            "runtime_config_sha256": sha256_file(RUNTIME_CONFIG_PATH),
            "assigned_episodes": len(episodes), "ballot_generations": expected_ballots,
            "message_generations": expected_messages, "generation_ceiling": GENERATION_MAX,
            "identity_http_max": IDENTITY_HTTP_MAX, "physical_http_max": PHYSICAL_HTTP_MAX,
            "external_calls": 0, "external_cost_usd": 0.0,
            "model_calls_disabled_by_default": backend.model_calls_enabled is False,
            "monitor_can_see_private_messages": False, "offline_source_gates": gate_results}


def _validate_model_and_server_identity(config: Any) -> dict[str, Any]:
    from .openai_compat_llamacpp import llama_runtime_bundle_identity

    model = Path(config.artifact_path).resolve()
    server = Path(config.server_binary_path).resolve()
    if not model.is_file() or sha256_file(model) != config.artifact_sha256:
        raise RuntimeError("local Qwen3 GGUF bytes do not match the frozen model identity")
    if not server.is_file() or sha256_file(server) != config.server_binary_sha256:
        raise RuntimeError("local llama.cpp launcher bytes do not match the frozen server identity")
    bundle = llama_runtime_bundle_identity(server)
    if bundle["sha256"] != config.runtime_bundle_sha256:
        raise RuntimeError("local llama.cpp runtime bundle differs from the frozen candidate")
    return {"model_sha256": config.artifact_sha256, "server_sha256": config.server_binary_sha256,
            "runtime_bundle_sha256": bundle["sha256"], "runtime_file_count": bundle["file_count"]}


def _check_live_guard(authorization: dict[str, Any], frozen_hashes: dict[str, str]) -> None:
    expiry = datetime.fromisoformat(authorization["expires_at_utc"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expiry:
        raise PermissionError("M1 v3 approval expired before the next local HTTP attempt")
    batch_path = ROOT / "research/authorizations" / f"{authorization['approval_id']}.json"
    budget_path = ROOT / "research/budget.json"
    if sha256_file(batch_path) != authorization["authorization_sha256"]:
        raise PermissionError("immutable M1 v3 approval changed during the run")
    budget = json.loads(budget_path.read_text(encoding="utf-8"))["authorization"]
    if budget.get("status") != "active" or budget.get("approval_id") != authorization["approval_id"]:
        raise PermissionError("M1 v3 approval is no longer the active registry snapshot")
    changed = [relative for relative, expected in frozen_hashes.items()
               if sha256_file(ROOT / relative) != expected]
    if changed:
        raise PermissionError("frozen M1 v3 runtime inputs changed during execution: " + ", ".join(changed))


def _run_identity_checks(backend: Any, counter: Any, config: Any,
                         request_journal: HashChainJournal, startup_id: str) -> dict[str, Any]:
    """Three authenticated, non-generation checks; all are charged to HTTP cap."""
    root = config.base_url.rsplit("/v1", 1)[0]

    def identity_call(name: str, method: str, path: str, body: bytes | None) -> bytes:
        request_id = f"identity-{startup_id}-{name}"
        request_journal.append({"event": "identity_http_request_prepared", "request_id": request_id,
                                "method": method, "url": root + path,
                                "request_body": body.decode("utf-8") if body is not None else None,
                                "request_body_sha256": sha256_bytes(body) if body is not None else None,
                                "authorization_header_value_saved": False})
        try:
            raw = backend._open(root + path, body, config.timeout_seconds, method,
                                request_id=request_id, attempt_number=1)
        except Exception as exc:
            raw = getattr(exc, "raw_response", None)
            request_journal.append({"event": "identity_http_failure", "request_id": request_id,
                                    "error_type": type(exc).__name__, "error": str(exc),
                                    "http_status": backend._last_http_status,
                                    "raw_response": raw,
                                    "raw_response_sha256": sha256_bytes(raw.encode("utf-8"))
                                    if isinstance(raw, str) else None})
            raise
        request_journal.append({"event": "identity_http_response_raw", "request_id": request_id,
                                "http_status": backend._last_http_status,
                                "response_body_base64": base64.b64encode(raw).decode("ascii"),
                                "response_body_sha256": sha256_bytes(raw),
                                "response_body_length_bytes": len(raw)})
        return raw

    props_raw = identity_call("props", "GET", "/props", None)
    props = json.loads(props_raw)
    try:
        params = props["default_generation_settings"]["params"]
        model_path = Path(props["model_path"]).resolve()
        build_info = str(props["build_info"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError("llama.cpp /props omitted frozen identity metadata") from exc
    if (model_path != Path(config.artifact_path).resolve() or config.server_commit not in build_info
            or props.get("default_generation_settings", {}).get("n_ctx") != config.context_length
            or props.get("total_slots") != 1):
        raise RuntimeError("live llama.cpp /props differs from the frozen model/server/context identity")
    for key, expected in (("temperature", config.temperature), ("top_p", config.top_p),
                          ("top_k", config.top_k), ("min_p", config.min_p)):
        if params.get(key) != expected:
            raise RuntimeError(f"live llama.cpp /props {key} differs from frozen sampling")
    if params.get("samplers") != list(config.sampler_chain):
        raise RuntimeError("live llama.cpp sampler chain differs from frozen sampling")
    template = props.get("chat_template")
    if not isinstance(template, str) or sha256_bytes(template.encode("utf-8")) != config.chat_template_sha256:
        raise RuntimeError("live llama.cpp chat template differs from the embedded GGUF template")

    from .m1_runtime import _observation, _task_spec, load_runtime_config
    runtime_base = load_runtime_config(RUNTIME_CONFIG_PATH)
    condition = next(row for row in runtime_base.conditions if row["id"] == "normal_cooperation")
    task = _task_spec(0, runtime_base)
    task["chair"] = "A"
    observation = _observation("A", task, condition, runtime_base)
    from .m1_runtime import _render
    prompt = _render("ballot", observation, runtime_base)
    messages = backend._messages(prompt)
    local_render = counter.render_chat(messages, enable_thinking=False)
    apply_payload = json.dumps({"messages": messages, "chat_template_kwargs": {"enable_thinking": False}},
                               ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    apply_raw = identity_call("template", "POST", "/apply-template", apply_payload)
    if json.loads(apply_raw).get("prompt") != local_render:
        raise RuntimeError("live llama.cpp apply-template output differs from local GGUF renderer")
    local_ids = counter.encode_chat(messages, enable_thinking=False)
    tokenize_payload = json.dumps({"content": local_render,
                                   "add_special": config.tokenizer_metadata.get("add_bos_token", False),
                                   "parse_special": True, "with_pieces": False},
                                  ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    tokenize_raw = identity_call("tokenize", "POST", "/tokenize", tokenize_payload)
    token_ids = json.loads(tokenize_raw).get("tokens")
    if token_ids != local_ids:
        raise RuntimeError("live llama.cpp tokenizer IDs differ from frozen GGUF tokenizer")
    return {"status": "PASS_LIVE_IDENTITY", "checks": ["props", "apply-template", "tokenize"],
            "identity_http_requests": 3, "sampling": config.sampling, "context_length": config.context_length}


def _write_private_jsonl(path: Path, row: dict[str, Any]) -> None:
    if path.is_symlink() or path.resolve() != path.absolute():
        raise PermissionError("private evidence path cannot traverse a symlink or junction")
    body = canonical_json(row)
    with path.open("ab") as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())


def _validate_output_path(output_dir: Path) -> Path:
    output_dir = Path(os.path.abspath(output_dir))
    restricted_root = Path(os.path.abspath(ROOT / "runs/m1_100/m1-package-replication-v3"))
    if not output_dir.is_relative_to(restricted_root) or output_dir == restricted_root:
        raise PermissionError("live M1 v3 artifacts must remain below ignored runs/m1_100/m1-package-replication-v3/")
    if output_dir.is_symlink() or output_dir.resolve() != output_dir or restricted_root.resolve() != restricted_root:
        raise PermissionError("M1 v3 run path and its parents must not traverse symlinks or junctions")
    return output_dir


def run_live(*, approval_id: str, output_dir: Path) -> dict[str, Any]:
    """Execute only a registered and freshly authorized M1 v3 schedule.

    The local server is started with the frozen offline command. Existing
    listeners are never contacted or terminated.
    """
    if os.name != "nt":
        raise RuntimeError("live v3 execution is limited to the frozen Windows local environment")
    authorization = verify_live_authorization(approval_id)
    candidate = validate_offline_candidate()
    schedule = load_frozen_schedule()
    episodes = assigned_episodes(schedule)
    output_dir = _validate_output_path(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    resuming = output_dir.exists()
    if output_dir.is_symlink():
        raise PermissionError("M1 v3 run directory cannot be a symlink")
    if resuming and (output_dir / "run-summary.json").exists():
        raise FileExistsError("terminal M1 v3 run cannot be resumed or rewritten")
    if not resuming:
        output_dir.mkdir(parents=False, exist_ok=False)
    from scripts.local_llama_security import (create_api_key_file, remove_api_key_file,
                                             restrict_private_directory_acl, verify_private_directory_acl)
    if not resuming:
        restrict_private_directory_acl(output_dir)
        (output_dir / "episodes").mkdir()
        (output_dir / "logs").mkdir()
        (output_dir / "private").mkdir()
        restrict_private_directory_acl(output_dir)
    else:
        required = (output_dir / "episodes", output_dir / "logs", output_dir / "private",
                    output_dir / "environment.json")
        if any(not item.exists() for item in required):
            raise ValueError("resume run directory is missing frozen evidence files")
        if any(item.is_symlink() or item.resolve() != item.absolute() for item in required):
            raise PermissionError("resume evidence paths cannot traverse a symlink or junction")

    from .gguf_tokenizer import GGUFChatTokenCounter
    from .m1_runtime import RequestAdapter, RequestBudget, load_runtime_config, run_episode
    from .openai_compat_llamacpp import (LocalLlamaCppBackend, llama_server_command,
                                         load_llamacpp_backend_config)
    from scripts.run_m1_p0_local_preflight import (_listener_snapshot, _process_image,
                                                   _stop_own_process)

    request_journal = HashChainJournal(output_dir / "request-ledger.jsonl")
    group_journal = HashChainJournal(output_dir / "group-ledger.jsonl")
    known_assignment = next((row["payload"] for row in group_journal.rows
                             if row["payload"].get("event") == "assignment_plan_frozen"), None)
    assignment_hash = sha256_bytes(canonical_json([{key: value for key, value in row.items()
                                                    if key != "scenario"} for row in episodes]))
    expected_assigned = {row["episode_id"] for row in episodes}
    if known_assignment and known_assignment.get("assignment_plan_sha256") != assignment_hash:
        raise ValueError("resume assignment plan differs from the original frozen plan")
    if known_assignment:
        assignment_rows = known_assignment.get("rows", [])
        existing_assigned = {row.get("episode_id") for row in assignment_rows}
        if len(assignment_rows) != 120 or existing_assigned != expected_assigned:
            raise ValueError("resume ledger assigned denominator differs from frozen 120 episodes")
        if any(row["payload"].get("event") in {"episode_started", "episode_terminal",
                                                "episode_interrupted_on_resume"}
               and row["payload"].get("episode_id") not in expected_assigned
               for row in group_journal.rows):
            raise ValueError("resume group ledger references an Episode outside the frozen assignment plan")
    elif request_journal.rows or group_journal.rows:
        raise ValueError("nonempty run ledgers lack their initial frozen assignment plan")
    attempts, terminal_episodes, prior_http, prior_identity = _reconstruct_run_state(request_journal,
                                                                                     group_journal)
    if not known_assignment:
        group_journal.append({"event": "assignment_plan_frozen", "experiment_id": EXPERIMENT_ID,
                              "schedule_sha256": candidate["schedule_sha256"],
                              "assignment_plan_sha256": assignment_hash, "assigned_episodes": len(episodes),
                              "rows": [{key: value for key, value in row.items() if key != "scenario"}
                                       for row in episodes]})
    else:
        if not terminal_episodes.issubset(expected_assigned):
            raise ValueError("resume ledger contains terminal Episode IDs outside the frozen assignment plan")
        for request_id in attempts:
            episode_id = next((value for value in expected_assigned
                               if request_id.startswith(value + "-req-")), None)
            if episode_id is None:
                raise ValueError("resume ledger contains a logical request outside the frozen assignment plan")
            suffix = request_id.removeprefix(episode_id + "-req-")
            if not suffix.isdigit() or not 1 <= int(suffix) <= 7:
                raise ValueError("resume request ID does not match the frozen per-Episode call graph")
    if any(row["payload"].get("event") == "run_halt_after_infrastructure_failure"
           for row in group_journal.rows):
        raise PermissionError("prior M1 v3 infrastructure stop requires an explicit audit before any resume")

    config = load_llamacpp_backend_config(CONFIG_PATH)
    config = replace(config, model_calls_enabled=True, full_pilot_approval_id=approval_id)
    identity = _validate_model_and_server_identity(config)
    runtime_base = config.bind_runtime(load_runtime_config(RUNTIME_CONFIG_PATH))
    counter = GGUFChatTokenCounter(Path(config.artifact_path), expected_artifact_sha256=config.artifact_sha256)
    frozen_hashes = {relative: sha256_file(ROOT / relative) for relative in FROZEN_INPUT_PATHS}
    environment = {
        "protocol_id": RESEARCH_SCOPE, "experiment_id": EXPERIMENT_ID, "approval": authorization,
        "candidate": candidate, "identity": identity, "python": sys.version,
        "platform": platform.platform(), "created_at_utc": utc_now(),
        "network": {"endpoint": config.base_url, "offline_server": True,
                    "third_party_fallback": False, "secret_material_saved": False},
        "request_budget": {"assigned_episodes": 120, "generation_max": GENERATION_MAX,
                           "identity_http_max": IDENTITY_HTTP_MAX, "physical_http_max": PHYSICAL_HTTP_MAX,
                           "attempts_per_request": 1, "retries": 0, "replacements": 0},
        "tokenizer": config.tokenizer_metadata,
        "tokenizer_runtime": {"tokenizers_library_version": counter.tokenizers_library_version,
                              "jinja2_library_version": counter.jinja2_library_version,
                              "tokenizer_sha256": counter.tokenizer_sha256,
                              "chat_template_sha256": counter.chat_template_sha256},
        "source_hashes": frozen_hashes,
    }
    environment_path = output_dir / "environment.json"
    if resuming:
        prior_environment = json.loads(environment_path.read_text(encoding="utf-8"))
        if (prior_environment.get("protocol_id") != RESEARCH_SCOPE
                or prior_environment.get("experiment_id") != EXPERIMENT_ID
                or prior_environment.get("approval", {}).get("approval_id") != approval_id
                or prior_environment.get("candidate", {}).get("schedule_sha256") != candidate["schedule_sha256"]
                or prior_environment.get("identity") != identity
                or prior_environment.get("source_hashes") != frozen_hashes):
            raise ValueError("resume environment differs from the original frozen M1 v3 run")
        verify_private_directory_acl(output_dir)
    else:
        _write_once_json(environment_path, environment)
    key_path = output_dir / "private/llama-api-key.txt"
    key: str | None = None
    key_info: dict[str, Any] | None = None
    server_out = None
    server_err = None
    process = None
    physical_http = prior_http
    identity_http = prior_identity
    startup_id = uuid.uuid4().hex[:12]
    try:
        owners, _diagnostic = _listener_snapshot(config.launch["port"])
        if owners:
            raise PermissionError("port 8081 already has a listener; the runner will not contact or stop it")
        if key_path.exists():
            verify_private_directory_acl(output_dir)
            key_path.unlink()
        key, key_path, key_info = create_api_key_file(output_dir)
        server_out = (output_dir / "logs/llama-server.stdout.log").open("ab")
        server_err = (output_dir / "logs/llama-server.stderr.log").open("ab")
        command = llama_server_command(config, key_path)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=server_out, stderr=server_err,
                                   cwd=str(Path(config.server_binary_path).resolve().parent),
                                   creationflags=flags, close_fds=True)
        image = _process_image(process.pid)
        if Path(image).resolve() != Path(config.server_binary_path).resolve():
            raise PermissionError("launched llama.cpp process image differs from frozen server identity")
        deadline = time.monotonic() + 240
        owners = []
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"llama.cpp exited during model load with code {process.returncode}")
            owners, _diagnostic = _listener_snapshot(config.launch["port"])
            if owners:
                break
            time.sleep(0.5)
        expected_owner = [{"LocalAddress": "127.0.0.1", "LocalPort": 8081, "OwningProcess": process.pid}]
        if owners != expected_owner:
            raise PermissionError("llama.cpp listener owner does not match the process started by this runner")
        group_journal.append({"event": "server_started", "pid": process.pid, "image_path": image,
                              "port": 8081, "api_key_sha256": key_info["sha256"],
                              "secret_material_saved": False, "command_sha256": sha256_bytes(
                                  canonical_json([str(part) for part in command]))})

        def listener_guard() -> bool:
            if process is None or process.poll() is not None:
                return False
            try:
                rows = _listener_snapshot(8081)[0]
                image_path = _process_image(process.pid)
                return (rows == expected_owner
                        and Path(image_path).resolve() == Path(config.server_binary_path).resolve())
            except Exception:
                return False

        def http_hook(row: dict[str, Any]) -> None:
            nonlocal physical_http, identity_http
            _check_live_guard(authorization, frozen_hashes)
            if row.get("url", "").split("/", 3)[:3] != ["http:", "", "127.0.0.1:8081"]:
                raise PermissionError("physical HTTP attempt escaped the frozen loopback endpoint")
            kind = "identity" if str(row.get("request_id", "")).startswith("identity-") else "generation"
            if physical_http >= PHYSICAL_HTTP_MAX:
                raise RuntimeError("hard 480 physical HTTP attempt ceiling reached")
            if kind == "identity" and identity_http >= IDENTITY_HTTP_MAX:
                raise RuntimeError("hard 24 identity HTTP request ceiling reached")
            physical_http += 1
            if kind == "identity":
                identity_http += 1
            request_journal.append({"event": "physical_http_attempt_reserved", "kind": kind,
                                    "request_id": row["request_id"], "attempt": row.get("attempt"),
                                    "method": row["method"], "url": row["url"],
                                    "request_body_sha256": row.get("request_body_sha256"),
                                    "authentication": row.get("transport_authentication"),
                                    "api_key_sha256": row.get("api_key_sha256"),
                                    "authorization_header_value_saved": False,
                                    "http_attempt_index": physical_http})

        backend = LocalLlamaCppBackend(config, counter, api_key=key,
                                       listener_guard=listener_guard, http_attempt_hook=http_hook)
        identity_result = _run_identity_checks(backend, counter, config, request_journal, startup_id)
        if physical_http > PHYSICAL_HTTP_MAX or identity_http > IDENTITY_HTTP_MAX:
            raise RuntimeError("identity checks exceeded one of their frozen caps")
        budget = RequestBudget(GENERATION_MAX, GENERATION_MAX, 1)
        for request_id in attempts:
            budget.logical_ids.add(request_id)
            budget.attempts_by_request[request_id] = 1
            budget.attempts += 1
        backend.restore_full_run_budget(attempts)

        def on_attempt_start(row: dict[str, Any]) -> None:
            request_journal.append({"event": "logical_request_attempt_reserved",
                                    "request_id": row["request_id"], "attempt": row["attempt"],
                                    "action_kind": row["action_kind"], "agent_id": row["agent_id"],
                                    "request": row["request"], "attempts_per_request": 1})

        def on_request_record(row: dict[str, Any]) -> None:
            request_journal.append({"event": "logical_request_terminal", **row})

        adapter = RequestAdapter(backend, runtime_base, budget,
                                 on_attempt_start=on_attempt_start, on_record=on_request_record)
        pending = [row for row in episodes if row["episode_id"] not in terminal_episodes]
        generation_reserved = len(attempts)
        for row in pending:
            episode_id = row["episode_id"]
            if generation_reserved >= GENERATION_MAX:
                raise RuntimeError("hard 456 generation ceiling reached before remaining assigned rows")
            condition = next(item for item in runtime_base.conditions if item["id"] == row["condition_id"])
            episode_runtime = replace(runtime_base, scenario_family_id=row["scenario_family_id"])
            request_start = len(adapter.records)
            group_journal.append({"event": "episode_started", "episode_id": episode_id,
                                  "group_id": row["group_id"], "condition_id": row["condition_id"],
                                  "scenario_family_id": row["scenario_family_id"],
                                  "seed_block_id": row["seed_block_id"], "replayed": False})
            observations: list[dict[str, Any]] = []

            def on_observation(observation: dict[str, Any]) -> None:
                _write_private_jsonl(output_dir / "observations.jsonl", observation)

            result = run_episode(condition, row["seed_block_id"], episode_id, episode_runtime, adapter,
                                 scenario=row["scenario"], split_partition="prospective_v3",
                                 request_id_prefix=episode_id,
                                 on_observation=on_observation)
            request_rows = adapter.records[request_start:]
            trace = {"T": result["T"], "B": result["B"], "E": result["E"],
                     "observations": result["observations"], "requests": request_rows,
                     "assigned": {key: row[key] for key in row if key != "scenario"},
                     "scenario": row["scenario"]}
            trace_path = output_dir / "episodes" / f"{episode_id}.json"
            trace_sha = _write_once_json(trace_path, trace)
            outcome = "COMPLETED" if result["B"]["status"] == "COMPLETED" else "FAILED"
            group_journal.append({"event": "episode_terminal", "episode_id": episode_id,
                                  "episode_status": outcome, "trace_path": trace_path.relative_to(output_dir).as_posix(),
                                  "trace_sha256": trace_sha,
                                  "request_count": len(request_rows),
                                  "failure": result["failure"], "replayed": False})
            terminal_episodes.add(episode_id)
            generation_reserved += sum(record.get("attempt") == 1 for record in request_rows)
            failure_kind = result["failure"].get("failure_kind") if result["failure"] else None
            if result["failure"] and failure_kind != "invalid_output":
                group_journal.append({"event": "run_halt_after_infrastructure_failure",
                                      "episode_id": episode_id, "failure_kind": failure_kind,
                                      "status": "STOPPED_NO_AUTOMATIC_RESUME"})
                raise RuntimeError("M1 v3 halted after infrastructure/runtime failure; inspect the preserved episode before resuming")
        status = "ALL_ASSIGNED_TERMINAL" if len(terminal_episodes) == 120 else "INCOMPLETE"
        terminal_request_records = [row["payload"] for row in request_journal.rows
                                    if row["payload"].get("event") == "logical_request_terminal"]
        usage_rows = [row.get("usage") for row in terminal_request_records if isinstance(row.get("usage"), dict)]
        response_metadata = [row.get("backend_response_metadata", {}) for row in terminal_request_records]
        result_summary = {"status": status, "assigned_episodes": 120,
                          "terminal_episodes": len(terminal_episodes),
                          "completed_episodes": sum(1 for item in group_journal.rows
                              if item["payload"].get("event") == "episode_terminal"
                              and item["payload"].get("episode_status") == "COMPLETED"),
                          "failed_or_interrupted_episodes": sum(1 for item in group_journal.rows
                              if item["payload"].get("event") in {"episode_terminal", "episode_interrupted_on_resume"}
                              and item["payload"].get("episode_status") != "COMPLETED"),
                          "generation_reservations": generation_reserved,
                          "usage_record_count": len(usage_rows),
                          "prompt_tokens_reported": sum(row.get("prompt_tokens", 0) for row in usage_rows),
                          "completion_tokens_reported": sum(row.get("completion_tokens", 0) for row in usage_rows),
                          "reported_latency_seconds": sum(
                              row.get("latency_seconds", 0.0) for row in response_metadata
                              if isinstance(row, dict) and isinstance(row.get("latency_seconds", 0.0), (int, float))),
                          "physical_http_attempts": physical_http, "identity_http_attempts": identity_http,
                          "identity_validation": identity_result,
                          "schedule_sha256": candidate["schedule_sha256"],
                          "final_request_chain_sha256": request_journal.previous_hash,
                          "final_group_chain_sha256": group_journal.previous_hash,
                          "acl": verify_private_directory_acl(output_dir)}
        _write_once_json(output_dir / "run-summary.json", result_summary)
        return result_summary
    except BaseException as exc:
        status = "FAILED" if not isinstance(exc, KeyboardInterrupt) else "INTERRUPTED"
        error = {"type": type(exc).__name__, "message": str(exc), "at_utc": utc_now()}
        group_journal.append({"event": "run_terminal", "status": status, "error": error,
                              "physical_http_attempts": physical_http, "identity_http_attempts": identity_http})
        raise
    finally:
        if process is not None:
            _stop_own_process(process)
        if server_out is not None:
            server_out.close()
        if server_err is not None:
            server_err.close()
        cleanup = (remove_api_key_file(key_path) if key_path.exists() else
                   {"status": "NOT_CREATED", "exists_after_cleanup": False})
        group_journal.append({"event": "api_key_cleanup", "status": cleanup["status"],
                              "secret_material_saved": False})


def _main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="M1 package replication v3 local-only runner")
    parser.add_argument("--check-only", action="store_true", help="validate frozen inputs without starting a server")
    parser.add_argument("--live", action="store_true", help="requires formal registration and fresh exact approval")
    parser.add_argument("--approval-id", default="")
    parser.add_argument("--out", type=Path, default=ROOT / "runs/m1_100/m1-package-replication-v3/run")
    args = parser.parse_args(argv)
    if args.live:
        try:
            result = run_live(approval_id=args.approval_id, output_dir=args.out)
        except Exception as exc:
            print(json.dumps({"status": "BLOCKED", "error_type": type(exc).__name__, "error": str(exc)},
                             ensure_ascii=False))
            return 2
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "ALL_ASSIGNED_TERMINAL" else 1
    if not args.check_only:
        parser.error("no execution default: use --check-only, or --live with exact registration and approval")
    print(json.dumps(validate_offline_candidate(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
