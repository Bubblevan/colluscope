"""Run the separately authorized 25-episode, local-only M1-P0 Pilot.

The runner always performs the bounded tokenizer/API preflight first. It has no
provider fallback and refuses every non-loopback endpoint. Episode and request
failures are retained; no failed episode is replaced or omitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import tomllib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from colluscope.m1_runtime import (  # noqa: E402
    RequestAdapter, RequestBudget, _assert_no_forbidden_fields, _canonical_hash,
    _condition_order, _verify_settlement, _verify_v2_message_continuity,
    load_runtime_config, run_episode,
)
from colluscope.openai_compat_llamacpp import (  # noqa: E402
    LlamaCppPreflightBudget, LocalLlamaCppBackend, llama_runtime_bundle_identity,
    llama_server_command, load_llamacpp_backend_config,
)
from scripts.run_m1_p0_local_preflight import (  # noqa: E402
    GpuSampler, _build_probes, _listener_snapshot, _process_image, _stop_own_process,
)

PREFLIGHT_APPROVAL_ID = "USER-APPROVED-8081-PREFLIGHT-2026-10-19"
PILOT_APPROVAL_ID = "USER-AUTHORIZED-M1-P0-25-EPISODE-PILOT-2026-10-19"
JSON_PREFIX_PREFLIGHT_APPROVAL_ID = "USER-REQUEST-JSON-PREFIX-PARSER-PREFLIGHT-2026-10-19"
JSON_PREFIX_PILOT_APPROVAL_ID = "USER-REQUEST-JSON-PREFIX-PARSER-PILOT-2026-10-19"
JSON_PREFIX_OUTPUT_CONTRACT = "json-v2-exact-empty-think-envelope"
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


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_port_free(port: int) -> None:
    # An exclusive bind is authoritative for whether this local endpoint can
    # be claimed. Avoid pre-launch process-table/CIM probes, which were denied
    # in this Windows runner despite succeeding in an independent shell.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind(("127.0.0.1", port))


def _validate_authorized_config(config_path: Path) -> Any:
    raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    approval_pair = (raw.get("preflight_approval_id"), raw.get("full_pilot_approval_id"))
    legacy_pair = (PREFLIGHT_APPROVAL_ID, PILOT_APPROVAL_ID)
    json_prefix_pair = (JSON_PREFIX_PREFLIGHT_APPROVAL_ID, JSON_PREFIX_PILOT_APPROVAL_ID)
    if (raw.get("model_calls_enabled") is not True or raw.get("preflight_enabled") is not True or
            approval_pair not in {legacy_pair, json_prefix_pair} or
            (approval_pair == json_prefix_pair and
             raw.get("action_output_contract_revision") != JSON_PREFIX_OUTPUT_CONTRACT) or
            (approval_pair == legacy_pair and raw.get("action_output_contract_revision") is not None)):
        raise PermissionError("run-scoped config lacks the exact preflight and 25-episode approvals")
    if (raw.get("max_api_spend_usd") != 0.0 or raw["server"].get("base_url") !=
            f"http://127.0.0.1:{PORT}/v1" or raw["launch"].get("port") != PORT):
        raise ValueError("pilot must remain $0 external spend on the authorized 127.0.0.1:8081 endpoint")
    config = load_llamacpp_backend_config(config_path)
    if (config.max_logical_requests != 95 or config.max_total_attempts != 190 or
            config.max_attempts_per_request != 2 or config.preflight_max_logical_requests != 6 or
            config.preflight_max_attempts != 12 or config.preflight_max_completion_attempts != 4):
        raise ValueError("request limits differ from the frozen 6/12/4 and 95/190 budgets")
    return config


def _consume_pilot_approval(out_dir: Path, ledger_dir: Path | None = None,
                            approval_id: str = PILOT_APPROVAL_ID) -> Path:
    """Make this 25-episode approval single-use across output directories."""
    ledger_dir = ledger_dir or ROOT / "runs" / "m1_p0_local" / "approval-ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    approval_key = hashlib.sha256(approval_id.encode("utf-8")).hexdigest()
    ledger_path = ledger_dir / f"{approval_key}.json"
    record = {"approval_id": approval_id,
              "consumed_at_utc": datetime.now(timezone.utc).isoformat(),
              "run_dir": str(out_dir.resolve()),
              "maximum_episode_count": 25,
              "maximum_logical_requests": 95,
              "maximum_http_attempts": 190}
    try:
        with ledger_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    except FileExistsError as exc:
        raise PermissionError("this full 25-episode pilot approval was already consumed") from exc
    _write_json(out_dir / "approval-consumption.json", record)
    return ledger_path


def _health_check(url: str, pid: int, image: str, out_dir: Path) -> dict[str, Any]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    health_url = url.rsplit("/v1", 1)[0] + "/health"
    with opener.open(health_url, timeout=5) as response:
        body = response.read(4097).decode("utf-8", errors="strict")
        status = response.status
    payload = json.loads(body)
    result = {"status": "PASS" if status == 200 and payload.get("status") == "ok" else "FAIL",
              "method": "GET", "url": health_url, "http_status": status,
              "response_body": body, "pid": pid, "pid_image": image,
              "process_owner_attestation": "recorded separately"}
    _write_json(out_dir / "server-health.json", result)
    if result["status"] != "PASS":
        raise RuntimeError("llama.cpp health endpoint did not report status=ok")
    return result


def _copy_frozen_inputs(out_dir: Path, runtime_config_path: Path) -> dict[str, str]:
    prompt_root = ROOT / "prompts" / "m1-p0-v2"
    frozen_prompts = out_dir / "frozen_protocol" / "prompts"
    frozen_prompts.mkdir(parents=True, exist_ok=True)
    prompt_hashes: dict[str, str] = {}
    for source in sorted(prompt_root.iterdir()):
        if source.is_file():
            target = frozen_prompts / source.name
            target.write_bytes(source.read_bytes())
            prompt_hashes[target.relative_to(out_dir).as_posix()] = _sha256_file(target)
    frozen_configs = out_dir / "frozen_protocol" / "configs"
    frozen_configs.mkdir(parents=True, exist_ok=True)
    for source in (runtime_config_path, ROOT / "configs" / "m1-pilot-draft.toml"):
        target = frozen_configs / source.name
        target.write_bytes(source.read_bytes())
    return prompt_hashes


def _runtime_source_files() -> list[Path]:
    # Include imported orchestration code as well as the entry point. Omitting
    # the preflight runner would leave a mutable part of the actual call path
    # outside the per-run source fingerprint.
    return [Path(__file__), ROOT / "scripts" / "run_m1_p0_local_preflight.py",
            ROOT / "src" / "colluscope" / "m1_runtime.py",
            ROOT / "src" / "colluscope" / "openai_compat_llamacpp.py",
            ROOT / "src" / "colluscope" / "gguf_tokenizer.py"]


def _validate_preflight_continuation(previous_dir: Path, config_path: Path,
                                     runtime_config_path: Path, backend_config: Any,
                                     probes: list[Any], prompt_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate a single continuation after setup checks and tokenizer parity failed.

    Successful `/props`, `/apply-template`, and `/tokenize` calls are reused as
    cumulative preflight evidence. The next run must repeat the exact frozen
    server command and may issue only the three remaining action probes, keeping
    the aggregate preflight within 6 logical / 12 HTTP / 4 completion attempts.
    """
    previous_dir = previous_dir.resolve()
    if not previous_dir.is_relative_to(ROOT.resolve()):
        raise ValueError("preflight continuation evidence must be inside this repository")
    manifest_path = previous_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in manifest.get("sha256", {}).items():
        path = (previous_dir / relative).resolve()
        if not path.is_relative_to(previous_dir) or not path.is_file() or _sha256_file(path) != expected:
            raise ValueError(f"prior preflight artifact hash mismatch: {relative}")
    environment = json.loads((previous_dir / "environment.json").read_text(encoding="utf-8"))
    previous_head = environment.get("git_head")
    if not isinstance(previous_head, str) or len(previous_head) != 40:
        raise ValueError("prior preflight does not identify a full Git commit SHA")
    if (environment.get("model_sha256") != EXPECTED_MODEL_SHA256 or
            environment.get("server_sha256") != EXPECTED_SERVER_SHA256 or
            environment.get("runtime_bundle_sha256") != EXPECTED_BUNDLE_SHA256 or
            environment.get("base_url") != backend_config.base_url):
        raise ValueError("prior preflight model/server/endpoint differs from the frozen local pilot")
    for relative, expected in manifest.get("runtime_source_sha256", {}).items():
        source = subprocess.run(["git", "show", f"{previous_head}:{relative}"], cwd=ROOT,
                                capture_output=True, timeout=15, check=True)
        if hashlib.sha256(source.stdout).hexdigest() != expected:
            raise ValueError(f"prior run source fingerprint does not match its Git commit: {relative}")

    terminal = json.loads((previous_dir / "terminal-status.json").read_text(encoding="utf-8"))
    result = json.loads((previous_dir / "preflight" / "result.json").read_text(encoding="utf-8"))
    if (terminal.get("status") != "NO_GO_PREFLIGHT" or terminal.get("episodes_attempted") != 0 or
            terminal.get("pilot_logical_requests") != 0 or terminal.get("pilot_http_attempts") != 0 or
            result.get("status") != "FAIL" or
            result.get("error") != "local GGUF tokenizer IDs differ from llama.cpp /tokenize"):
        raise ValueError("continuation is allowed only for the retained preflight tokenizer mismatch with zero episodes")
    state = result.get("budget_state", {})
    if (state.get("logical_requests") != 3 or state.get("http_attempts") != 3 or
            state.get("completion_attempts") != 0 or state.get("attempts_by_request") != {
                "preflight-props": 1, "preflight-template": 1, "preflight-tokenize": 1}):
        raise ValueError("prior preflight usage differs from the three permitted setup checks")
    approval = json.loads((previous_dir / "approval-record.json").read_text(encoding="utf-8"))
    consumed = json.loads((previous_dir / "approval-consumption.json").read_text(encoding="utf-8"))
    ledger = ROOT / "runs" / "m1_p0_local" / "approval-ledger" / (
        hashlib.sha256(PILOT_APPROVAL_ID.encode("utf-8")).hexdigest() + ".json")
    ledger_record = json.loads(ledger.read_text(encoding="utf-8"))
    if (approval.get("full_25_episode_pilot_approval_id") != PILOT_APPROVAL_ID or
            approval.get("preflight_approval_id") != PREFLIGHT_APPROVAL_ID or
            consumed.get("approval_id") != PILOT_APPROVAL_ID or
            Path(consumed.get("run_dir", "")).resolve() != previous_dir or
            ledger_record.get("run_dir") != str(previous_dir)):
        raise PermissionError("prior preflight is not the run that consumed this exact pilot approval")
    if ((previous_dir / "full-pilot-config.toml").read_bytes() != config_path.read_bytes() or
            (previous_dir / "runtime-config.toml").read_bytes() != runtime_config_path.read_bytes()):
        raise ValueError("continuation config/runtime differs from the failed run's frozen inputs")
    previous_launch = json.loads((previous_dir / "launch.json").read_text(encoding="utf-8"))
    if previous_launch.get("command") != llama_server_command(backend_config):
        raise ValueError("continuation server command differs from the previous exact launch")
    health = json.loads((previous_dir / "server-health.json").read_text(encoding="utf-8"))
    owner = json.loads((previous_dir / "listener-owner-attestation.json").read_text(encoding="utf-8"))
    if (health.get("status") != "PASS" or owner.get("status") != "verified_exact_pid" or
            owner.get("expected_pid") != previous_launch.get("pid")):
        raise ValueError("prior run did not verify the exact local listener and health endpoint")

    old_inputs = json.loads((previous_dir / "preflight" / "inputs.json").read_text(encoding="utf-8"))
    if old_inputs.get("prompts") != prompt_evidence:
        raise ValueError("continuation probes differ from the failed run's exact prompt evidence")
    rows = _read_jsonl(previous_dir / "preflight" / "requests.jsonl")
    setup_ids = ("preflight-props", "preflight-template", "preflight-tokenize")
    setup_records: list[dict[str, Any]] = []
    reused: dict[str, bytes] = {}
    root = backend_config.base_url.rsplit("/v1", 1)[0]
    endpoints = {"preflight-props": ("GET", root + "/props"),
                 "preflight-template": ("POST", root + "/apply-template"),
                 "preflight-tokenize": ("POST", root + "/tokenize")}
    for request_id in setup_ids:
        matching = [row for row in rows if row.get("request_id") == request_id and
                    isinstance(row.get("attempt"), int)]
        if len(matching) != 1:
            raise ValueError(f"prior setup request is missing or duplicated: {request_id}")
        record = matching[0]
        method, url = endpoints[request_id]
        raw = record.get("raw_response")
        if record.get("method") != method or record.get("url") != url or not isinstance(raw, str):
            raise ValueError(f"prior setup request identity is invalid: {request_id}")
        setup_records.append(record)
        reused[request_id] = raw.encode("utf-8")
    return {"previous_dir": previous_dir, "previous_manifest": manifest,
            "previous_manifest_sha256": _sha256_file(manifest_path),
            "previous_requests_sha256": _sha256_file(previous_dir / "preflight" / "requests.jsonl"),
            "setup_records": setup_records, "setup_responses": reused}


def _claim_preflight_continuation(out_dir: Path, previous_dir: Path) -> Path:
    ledger_dir = ROOT / "runs" / "m1_p0_local" / "approval-ledger"
    approval_key = hashlib.sha256(PILOT_APPROVAL_ID.encode("utf-8")).hexdigest()
    marker = ledger_dir / f"{approval_key}.continuation.json"
    record = {"approval_id": PILOT_APPROVAL_ID,
              "continued_from": str(previous_dir.resolve()),
              "continuation_run_dir": str(out_dir.resolve()),
              "cumulative_setup_logical_requests": 3,
              "remaining_completion_attempts": 4,
              "at_utc": datetime.now(timezone.utc).isoformat()}
    try:
        with marker.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    except FileExistsError as exc:
        raise PermissionError("the single tokenizer-fix preflight continuation was already consumed") from exc
    _write_json(out_dir / "preflight-continuation-consumption.json", record)
    return marker


def _verify_preflight_continuation(out_dir: Path,
                                  current_requests: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = json.loads((out_dir / "preflight-resume.json").read_text(encoding="utf-8"))
    copied_parent = (out_dir / metadata["previous_run_copy"]).resolve()
    if not copied_parent.is_relative_to(out_dir.resolve()):
        raise ValueError("copied prior preflight path escapes the current run")
    manifest_path = copied_parent / "manifest.json"
    if _sha256_file(manifest_path) != metadata.get("previous_manifest_sha256"):
        raise ValueError("copied prior preflight manifest digest mismatch")
    prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative, expected in prior_manifest.get("sha256", {}).items():
        path = (copied_parent / relative).resolve()
        if not path.is_relative_to(copied_parent) or not path.is_file() or _sha256_file(path) != expected:
            raise ValueError(f"copied prior preflight artifact hash mismatch: {relative}")
    prior_requests_path = copied_parent / "preflight" / "requests.jsonl"
    if _sha256_file(prior_requests_path) != metadata.get("previous_requests_sha256"):
        raise ValueError("copied prior preflight request-ledger digest mismatch")
    prior_rows = _read_jsonl(prior_requests_path)
    current_by_id = {row.get("request_id"): row for row in current_requests
                     if isinstance(row.get("attempt"), int)}
    for request_id in ("preflight-props", "preflight-template", "preflight-tokenize"):
        prior = next((row for row in prior_rows if row.get("request_id") == request_id and
                      isinstance(row.get("attempt"), int)), None)
        current = current_by_id.get(request_id)
        if prior is None or current is None or prior.get("raw_response_sha256") != current.get("raw_response_sha256"):
            raise ValueError(f"resumed preflight changed setup evidence: {request_id}")
    terminal = json.loads((copied_parent / "terminal-status.json").read_text(encoding="utf-8"))
    if terminal.get("episodes_attempted") != 0 or terminal.get("pilot_logical_requests") != 0:
        raise ValueError("copied prior run is not a zero-episode preflight failure")
    return {"previous_run_id": metadata["previous_run_id"],
            "previous_manifest_sha256": metadata["previous_manifest_sha256"],
            "previous_artifact_hashes": len(prior_manifest.get("sha256", {})),
            "setup_responses_reused_and_reverified": 3}


def _verify_live_run(out_dir: Path, config: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    for relative, expected in manifest.get("runtime_source_sha256", {}).items():
        source = (ROOT / relative).resolve()
        if not source.is_relative_to(ROOT.resolve()) or _sha256_file(source) != expected:
            raise ValueError(f"runtime source snapshot mismatch: {relative}")
    checked: dict[str, str] = {}
    for relative, expected in manifest["sha256"].items():
        path = (out_dir / relative).resolve()
        if not path.is_relative_to(out_dir.resolve()):
            raise ValueError(f"manifest path escapes run directory: {relative}")
        actual = _sha256_file(path)
        if actual != expected:
            raise ValueError(f"artifact hash mismatch: {relative}")
        checked[relative] = actual
    preflight_result = json.loads((out_dir / "preflight" / "result.json").read_text(encoding="utf-8"))
    preflight_rows = _read_jsonl(out_dir / "preflight" / "requests.jsonl")
    preflight_budget = preflight_result.get("budget_state", {})
    preflight_attempt_rows = [row for row in preflight_rows if isinstance(row.get("attempt"), int)]
    preflight_ids = {row["request_id"] for row in preflight_attempt_rows}
    completion_rows = [row for row in preflight_attempt_rows if row.get("completion_attempt") is True]
    if (preflight_result.get("status") != "PASS" or len(preflight_ids) != 6 or
            len(preflight_attempt_rows) > 12 or len(completion_rows) > 4 or
            preflight_budget.get("logical_requests") != 6 or
            preflight_budget.get("http_attempts") != len(preflight_attempt_rows) or
            preflight_budget.get("completion_attempts") != len(completion_rows) or
            not {"preflight-props", "preflight-template", "preflight-tokenize",
                 "preflight-completion-1", "preflight-completion-2", "preflight-completion-3"}.issubset(preflight_ids)):
        raise ValueError("successful cumulative 6/12/4 preflight evidence is incomplete or over budget")
    continuation_result = None
    if (out_dir / "preflight-resume.json").is_file():
        continuation_result = _verify_preflight_continuation(out_dir, preflight_rows)
    researcher = out_dir / "researcher"
    t_rows = _read_jsonl(researcher / "T.jsonl")
    b_rows = _read_jsonl(researcher / "B.jsonl")
    e_rows = _read_jsonl(out_dir / "monitor_inputs" / "evidence.jsonl")
    observations = _read_jsonl(researcher / "agent_observations.jsonl")
    requests = _read_jsonl(researcher / "requests.jsonl")
    if not (len(t_rows) == len(b_rows) == len(e_rows) == 25):
        raise ValueError("all 25 assigned episodes must remain in T/B/E, including failures")
    if len({row["episode_id"] for row in t_rows}) != 25:
        raise ValueError("episode IDs are not unique")
    condition_counts = {condition["id"]: 0 for condition in config.conditions}
    for row in t_rows:
        condition_counts[row["condition_id"]] += 1
    if any(count != 5 for count in condition_counts.values()):
        raise ValueError("condition-by-seed coverage differs from the frozen 5x5 design")
    expected_order = [{"seed_block_id": seed, "condition_id": condition["id"],
                       "order_index": index}
                      for seed in config.seed_blocks
                      for index, condition in enumerate(_condition_order(config.conditions, seed))]
    saved_order = json.loads((out_dir / "randomized_order.json").read_text(encoding="utf-8"))
    if saved_order != {"scheme": "sha256-offset-direction-v1", "order": expected_order}:
        raise ValueError("randomized condition order does not recompute from the frozen seeds")
    request_ids_by_episode: dict[str, set[str]] = {}
    for row in observations:
        request_ids_by_episode.setdefault(row["episode_id"], set()).add(row["request_id"])
    request_attempts_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in requests:
        if isinstance(row.get("attempt"), int):
            request_attempts_by_id.setdefault(row["request_id"], []).append(row)
    if set(request_ids_by_episode) - {row["episode_id"] for row in t_rows}:
        raise ValueError("agent observations contain an unknown episode")
    for t, b, e in zip(t_rows, b_rows, e_rows, strict=True):
        if t["episode_id"] != b["episode_id"]:
            raise ValueError("T/B episode alignment mismatch")
        if set(e) != {"task_spec", "events"}:
            raise ValueError("monitor E contains fields outside the permitted task/evidence schema")
        if b["status"] == "COMPLETED":
            _verify_settlement(t, b, e, config)
            expected_action_count = 5 if t["assigned"]["private_chat_available"] else 3
            refs = [item["request_id"] for item in b["ballots"]]
            refs += [item["request_id"] for item in b["peer_messages"]]
            if len(refs) != expected_action_count or len(set(refs)) != expected_action_count:
                raise ValueError("completed episode action request graph differs from its assigned condition")
            for request_id in refs:
                if request_id not in request_attempts_by_id:
                    raise ValueError(f"episode action has no request/response attempt record: {request_id}")
            if not set(refs).issubset(request_ids_by_episode.get(t["episode_id"], set())):
                raise ValueError("episode action is missing its agent-visible observation record")
        elif b.get("failure") is None:
            raise ValueError("failed episode has no retained failure record")
    completed = [(t, b) for t, b in zip(t_rows, b_rows, strict=True) if b["status"] == "COMPLETED"]
    if completed:
        _verify_v2_message_continuity([row[0] for row in completed], [row[1] for row in completed],
                                      [row for row in observations
                                       if row["episode_id"] in {item[0]["episode_id"] for item in completed}])
    for row in observations:
        if row["sha256"] != _canonical_hash(row["observation"]):
            raise ValueError("agent-visible observation hash mismatch")
    _assert_no_forbidden_fields(e_rows, {
        "condition_id", "oracle", "policy_id", "model_kind", "seed_block_id",
        "split_group_id", "split", "private_incentive_rule",
        "your_private_task_score_rule", "private_peer_channel",
        "private_target_bonus_recipients", "episode_id", "generation_seed"})
    logical_ids = {row["request_id"] for row in requests if isinstance(row.get("attempt"), int)}
    attempts_by_id: dict[str, list[int]] = {}
    for row in requests:
        if isinstance(row.get("attempt"), int):
            attempts_by_id.setdefault(row["request_id"], []).append(row["attempt"])
    if len(logical_ids) > 95 or sum(len(value) for value in attempts_by_id.values()) > 190:
        raise ValueError("pilot exceeded the 95 logical / 190 HTTP-attempt hard cap")
    if any(sorted(attempts) != list(range(1, len(attempts) + 1)) or len(attempts) > 2
           for attempts in attempts_by_id.values()):
        raise ValueError("request retries are not sequential or exceed the frozen maximum")
    failed = sum(row["status"] != "COMPLETED" for row in b_rows)
    return {"status": "PASS_ARTIFACTS" if failed == 0 else "PASS_ARTIFACTS_WITH_RETAINED_EPISODE_FAILURES",
            "episodes": 25, "completed_episodes": 25 - failed, "failed_episodes": failed,
            "condition_counts": condition_counts, "unique_logical_request_ids": len(logical_ids),
            "http_attempt_records": sum(map(len, attempts_by_id.values())),
            "max_attempts_per_request": 2, "monitor_hidden_metadata_scan": "PASS",
            "observation_hashes": "PASS", "completed_settlements_independently_recomputed": True,
            "preflight_logical_requests": preflight_budget["logical_requests"],
            "preflight_http_attempts": preflight_budget["http_attempts"],
            "preflight_completion_attempts": preflight_budget["completion_attempts"],
            "preflight_continuation": continuation_result,
            "checked_hashes": checked, "detection_performance_claimed": False,
            "collusion_inference_claimed": False}


def run(config_path: Path, runtime_config_path: Path, out_dir: Path,
        resume_preflight_from: Path | None = None) -> dict[str, Any]:
    config_path, runtime_config_path, out_dir = config_path.resolve(), runtime_config_path.resolve(), out_dir.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"refusing to overwrite existing pilot artifacts: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = out_dir / "logs"
    logs_dir.mkdir()
    preflight_dir = out_dir / "preflight"
    preflight_dir.mkdir()
    backend_config = _validate_authorized_config(config_path)
    run_authorization = tomllib.loads(config_path.read_text(encoding="utf-8"))
    preflight_approval_id = run_authorization["preflight_approval_id"]
    pilot_approval_id = run_authorization["full_pilot_approval_id"]
    output_contract_revision = run_authorization.get("action_output_contract_revision", "json-v1")
    model_path = Path(backend_config.artifact_path).resolve()
    server_path = Path(backend_config.server_binary_path).resolve()
    bundle = llama_runtime_bundle_identity(server_path)
    if (_sha256_file(model_path) != EXPECTED_MODEL_SHA256 or
            _sha256_file(server_path) != EXPECTED_SERVER_SHA256 or
            bundle["sha256"] != EXPECTED_BUNDLE_SHA256):
        raise RuntimeError("local GGUF/server/runtime bytes differ from the frozen identities")
    base_runtime = load_runtime_config(runtime_config_path)
    probes, prompt_evidence = _build_probes(backend_config, runtime_config_path)
    token_counter = GGUFChatTokenCounter(model_path,
                                          expected_artifact_sha256=backend_config.artifact_sha256)
    continuation = (_validate_preflight_continuation(
        resume_preflight_from, config_path, runtime_config_path, backend_config, probes, prompt_evidence)
        if resume_preflight_from is not None else None)
    _copy_frozen_inputs(out_dir, runtime_config_path)
    (out_dir / "full-pilot-config.toml").write_bytes(config_path.read_bytes())
    (out_dir / "runtime-config.toml").write_bytes(runtime_config_path.read_bytes())
    _write_json(out_dir / "approval-record.json", {
        "preflight_approval_id": preflight_approval_id,
        "full_25_episode_pilot_approval_id": pilot_approval_id,
        "authority": ("user's direct instruction to repair the JSON-prefix parser and retry; "
                      "bounded by the frozen 25-episode/95-request and 6/12/4 preflight ceilings"
                      if pilot_approval_id == JSON_PREFIX_PILOT_APPROVAL_ID else
                      "user's direct request to run the 25 Episode behavior Pilot"),
        "action_output_contract_revision": output_contract_revision,
        "endpoint": "http://127.0.0.1:8081/v1", "external_paid_api_spend_usd": 0.0,
        "m2_authorized": False})
    if continuation is None:
        _consume_pilot_approval(out_dir, approval_id=pilot_approval_id)
    else:
        _claim_preflight_continuation(out_dir, continuation["previous_dir"])
        copied_parent = preflight_dir / "resumed-source"
        shutil.copytree(continuation["previous_dir"], copied_parent)
        _write_json(out_dir / "preflight-resume.json", {
            "status": "CONTINUATION_OF_FAILED_PREFLIGHT",
            "previous_run_id": continuation["previous_dir"].name,
            "previous_run_copy": "preflight/resumed-source",
            "previous_manifest_sha256": continuation["previous_manifest_sha256"],
            "previous_requests_sha256": continuation["previous_requests_sha256"],
            "reused_setup_request_ids": [row["request_id"] for row in continuation["setup_records"]],
            "cumulative_limits": {"logical_requests": 6, "http_attempts": 12,
                                  "completion_attempts": 4},
            "new_requests_permitted": ["preflight-completion-1", "preflight-completion-2",
                                       "preflight-completion-3"],
            "reason": "local Qwen2 pre-tokenizer corrected; previously returned setup HTTP responses are revalidated offline",
        })
    _write_json(out_dir / "environment.json", {
        "python": sys.version, "platform": platform.platform(),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                    text=True, timeout=10, check=True).stdout.strip(),
        "branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True,
                                  text=True, timeout=10, check=True).stdout.strip(),
        "model_path": str(model_path), "model_sha256": EXPECTED_MODEL_SHA256,
        "server_path": str(server_path), "server_sha256": EXPECTED_SERVER_SHA256,
        "runtime_bundle_sha256": bundle["sha256"], "runtime_bundle_file_count": bundle["file_count"],
        "python_packages": {
            "pytest": __import__("pytest").__version__,
            "tokenizers": __import__("tokenizers").__version__,
            "jinja2": __import__("jinja2").__version__,
        },
        "base_url": backend_config.base_url, "sampling": backend_config.sampling,
        "preflight_budget": {"logical": 6, "http_attempts": 12, "completion_attempts": 4},
        "preflight_prior_run_id": continuation["previous_dir"].name if continuation else None,
        "preflight_budget_is_cumulative_across_runs": continuation is not None,
        "pilot_budget": {"logical": 95, "http_attempts": 190, "episodes": 25,
                         "completion_probes": 0}})
    _write_json(preflight_dir / "inputs.json", {
        "probe_order": [request.request_id for request, _ in probes],
        "expected_actions": [expected or "ballot" for _, expected in probes],
        "prompts": prompt_evidence,
        "schema_sha256": {path.name: _sha256_file(path) for path in sorted(
            (ROOT / "prompts" / "m1-p0-v2").glob("*.schema.json"))}})

    process: subprocess.Popen[bytes] | None = None
    stdout_stream = None
    stderr_stream = None
    sampler: GpuSampler | None = None
    status = "RUNNING"
    error: dict[str, str] | None = None
    preflight_result: dict[str, Any] | None = None
    rows: list[dict[str, Any]] = []
    budget: RequestBudget | None = None
    adapter: RequestAdapter | None = None
    owner_attestation: dict[str, Any] | None = None
    try:
        _assert_port_free(PORT)
        sampler = GpuSampler(out_dir / "gpu-samples.jsonl", interval_seconds=1.0)
        sampler.start()
        stdout_stream = (logs_dir / "llama-server.stdout.log").open("wb")
        stderr_stream = (logs_dir / "llama-server.stderr.log").open("wb")
        command = llama_server_command(backend_config)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout_stream,
                                   stderr=stderr_stream, cwd=str(server_path.parent),
                                   creationflags=flags, close_fds=True)
        sampler.set_phase("server_starting_model_load")
        image = _process_image(process.pid)
        if image.casefold() != str(server_path).casefold():
            raise PermissionError("launched llama-server PID image differs from the frozen binary")
        _write_json(out_dir / "launch.json", {"pid": process.pid, "image_path": image,
                    "command": command, "cwd": str(server_path.parent), "host": "127.0.0.1",
                    "port": PORT, "created_at_utc": datetime.now(timezone.utc).isoformat()})
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"llama-server exited during startup: {process.returncode}")
            time.sleep(min(0.25, max(0.0, deadline - time.monotonic())))
        owner_rows, owner_diagnostics = _listener_snapshot(PORT)
        expected_owner = [{"LocalAddress": "127.0.0.1", "LocalPort": PORT,
                           "OwningProcess": process.pid}]
        if owner_rows and owner_rows != expected_owner:
            raise PermissionError(f"port 8081 is owned by a different listener: {owner_rows}")
        owner_attestation = {"expected_pid": process.pid, "rows": owner_rows,
                             "diagnostics": owner_diagnostics,
                             "status": "verified_exact_pid" if owner_rows == expected_owner
                             else "table_unavailable_endpoint_identity_required"}
        _write_json(out_dir / "listener-owner-attestation.json", owner_attestation)
        if process.poll() is not None or _process_image(process.pid).casefold() != str(server_path).casefold():
            raise PermissionError("launched llama-server process identity changed")

        def process_guard() -> bool:
            if process is None or process.poll() is not None:
                return False
            try:
                return _process_image(process.pid).casefold() == str(server_path).casefold()
            except Exception:
                return False

        health = _health_check(backend_config.base_url, process.pid, image, out_dir)
        sampler.set_phase("server_health_validated")
        events: list[dict[str, Any]] = []

        def event_hook(event: dict[str, Any]) -> None:
            row = {**event, "monotonic_ns": time.monotonic_ns()}
            events.append(row)
            event_name = event.get("event")
            if event_name == "completion_attempt_started":
                sampler.set_phase(f"preflight_inference:{event.get('request_id')}:{event.get('attempt')}")
            elif event_name in {"completion_attempt_finished", "completion_attempt_failed"}:
                sampler.set_phase("server_loaded_between_preflight_calls")
            elif event_name == "server_properties_validated":
                sampler.set_phase("model_loaded_properties_validated")
            elif event_name == "tokenizer_parity_validated":
                sampler.set_phase("tokenizer_parity_validated")
            _append_jsonl(preflight_dir / "events.jsonl", row)

        backend = LocalLlamaCppBackend(backend_config, token_counter,
                                       listener_guard=process_guard,
                                       preflight_event_hook=event_hook)
        preflight_budget = LlamaCppPreflightBudget(enabled=True, max_logical_requests=6,
                                                   max_attempts=12, max_completion_attempts=4)
        reused_setup_responses = None
        if continuation is not None:
            preflight_budget.reuse_verified_setup(continuation["setup_records"])
            reused_setup_responses = continuation["setup_responses"]
        try:
            preflight_result = backend.preflight(
                preflight_budget, probes, reused_setup_responses=reused_setup_responses)
            status_pre = "PASS"
        except Exception as exc:
            status_pre = "FAIL"
            preflight_result = {"status": "FAIL", "error_type": type(exc).__name__,
                                "error": str(exc), "records": preflight_budget.records}
        preflight_result["budget_state"] = {
            "logical_requests": len(preflight_budget.logical_ids),
            "http_attempts": preflight_budget.attempts,
            "completion_attempts": preflight_budget.completion_attempts,
            "attempts_by_request": preflight_budget.attempts_by_request}
        _write_json(preflight_dir / "result.json", preflight_result)
        for item in preflight_budget.records:
            _append_jsonl(preflight_dir / "requests.jsonl", item)
        if status_pre != "PASS":
            status = "NO_GO_PREFLIGHT"
            error = {"type": "PreflightFailed",
                     "error": preflight_result.get("error", "frozen local compatibility preflight failed")}
        else:
            sampler.set_phase("pilot_episode_start")
            runtime = backend_config.bind_runtime(base_runtime)
            budget = RequestBudget(95, 190, 2)
            adapter = RequestAdapter(backend, runtime, budget)
            order: list[dict[str, Any]] = []
            written_request_count = 0
            index = 0
            for seed_block in runtime.seed_blocks:
                for order_index, condition in enumerate(_condition_order(runtime.conditions, seed_block)):
                    index += 1
                    episode_id = f"pilot-episode-{index:03d}"
                    sampler.set_phase(f"episode:{episode_id}:{condition['id']}")
                    result = run_episode(condition, seed_block, episode_id, runtime, adapter)
                    result["T"]["randomized_order_index"] = order_index
                    rows.append(result)
                    order.append({"seed_block_id": seed_block,
                                  "condition_id": condition["id"], "order_index": order_index})
                    _append_jsonl(out_dir / "researcher" / "T.jsonl", result["T"])
                    _append_jsonl(out_dir / "researcher" / "B.jsonl", result["B"])
                    _append_jsonl(out_dir / "monitor_inputs" / "evidence.jsonl", result["E"])
                    for observation in result["observations"]:
                        _append_jsonl(out_dir / "researcher" / "agent_observations.jsonl", observation)
                    for request_record in adapter.records[written_request_count:]:
                        _append_jsonl(out_dir / "researcher" / "requests.jsonl", request_record)
                    written_request_count = len(adapter.records)
                    _append_jsonl(out_dir / "episode-progress.jsonl", {
                        "episode_id": episode_id, "condition_id": condition["id"],
                        "seed_block_id": seed_block, "status": result["B"]["status"],
                        "failure": result["failure"], "logical_requests": budget.logical_requests,
                        "http_attempts": budget.attempts})
            _write_json(out_dir / "randomized_order.json", {
                "scheme": "sha256-offset-direction-v1", "order": order})
            status = ("COMPLETE" if len(rows) == 25 and all(
                row["B"]["status"] == "COMPLETED" for row in rows)
                else "COMPLETE_WITH_EPISODE_FAILURES")
    except Exception as exc:
        status = "NO_GO_RUNTIME_FAILURE"
        error = {"type": type(exc).__name__, "error": str(exc)}
        _write_json(out_dir / "failure.json", {"at_utc": datetime.now(timezone.utc).isoformat(),
                                               "failure": error,
                                               "episodes_started": len(rows)})
    finally:
        if process is not None:
            if sampler is not None:
                sampler.set_phase("server_shutdown")
            shutdown = _stop_own_process(process)
            _write_json(out_dir / "shutdown.json", shutdown)
        if stdout_stream is not None:
            stdout_stream.close()
        if stderr_stream is not None:
            stderr_stream.close()
        if sampler is not None:
            sampler.set_phase("after_server_shutdown")
            sampler.stop()

    _write_json(out_dir / "terminal-status.json", {
        "status": status, "error": error,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "episodes_attempted": len(rows),
        "episodes_completed": sum(row["B"]["status"] == "COMPLETED" for row in rows),
        "episodes_failed": sum(row["B"]["status"] != "COMPLETED" for row in rows),
        "model_calls_enabled": True, "external_model_calls": 0, "paid_api_calls": 0,
        "preflight_status": preflight_result.get("status") if preflight_result else "NOT_RUN",
        "preflight_logical_request_limit": 6, "preflight_http_attempt_limit": 12,
        "preflight_completion_attempt_limit": 4,
        "pilot_logical_request_limit": 95, "pilot_http_attempt_limit": 190,
        "pilot_logical_requests": budget.logical_requests if budget else 0,
        "pilot_http_attempts": budget.attempts if budget else 0,
        "listener_owner_attestation": owner_attestation})

    source_files = _runtime_source_files()
    source_hashes = {path.relative_to(ROOT).as_posix(): _sha256_file(path) for path in source_files}
    files = sorted(path for path in out_dir.rglob("*") if path.is_file() and path.name != "manifest.json")
    manifest = {"schema_version": "1.0", "run_id": out_dir.name,
                "purpose": "m1_p0_local_real_llm_behavior_pilot",
                "model": {"id": backend_config.model_id, "path": str(model_path),
                          "sha256": EXPECTED_MODEL_SHA256, "runtime": "local llama.cpp",
                          "external_model_calls": 0, "paid_api_calls": 0,
                          "sampling": backend_config.sampling},
                "authorization": {"preflight": preflight_approval_id,
                                  "pilot": pilot_approval_id},
                "action_output_contract_revision": output_contract_revision,
                "condition_ids": [condition["id"] for condition in base_runtime.conditions],
                "seed_blocks": list(base_runtime.seed_blocks),
                "prompt_version": base_runtime.raw["prompt_version"],
                "pilot_call_graph": {"episodes": 25, "ballot_requests": 75,
                                     "peer_message_requests": 20,
                                     "comprehension_probes": 0,
                                     "logical_request_cap": 95, "http_attempt_cap": 190,
                                     "max_attempts_per_request": 2},
                "preflight_call_graph": {"logical_request_cap": 6, "http_attempt_cap": 12,
                                         "completion_attempt_cap": 4},
                "preflight_continuation": json.loads(
                    (out_dir / "preflight-resume.json").read_text(encoding="utf-8"))
                    if (out_dir / "preflight-resume.json").is_file() else None,
                "listener_owner_attestation": owner_attestation,
                "runtime_source_sha256": source_hashes,
                "sha256": {path.relative_to(out_dir).as_posix(): _sha256_file(path)
                           for path in files}}
    _write_json(out_dir / "manifest.json", manifest)
    verification = None
    try:
        verification = _verify_live_run(out_dir, base_runtime, manifest)
        _write_json(out_dir / "verification.json", verification)
    except Exception as exc:
        verification = {"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}
        _write_json(out_dir / "verification.json", verification)
    return {"status": status, "out_dir": str(out_dir), "verification": verification,
            "episodes_attempted": len(rows),
            "episodes_completed": sum(row["B"]["status"] == "COMPLETED" for row in rows),
            "episodes_failed": sum(row["B"]["status"] != "COMPLETED" for row in rows),
            "preflight_status": preflight_result.get("status") if preflight_result else "NOT_RUN",
            "pilot_logical_requests": budget.logical_requests if budget else 0,
            "pilot_http_attempts": budget.attempts if budget else 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path,
                        help="run-scoped local config with exact preflight and pilot IDs")
    parser.add_argument("--runtime-config", type=Path, default=ROOT / "configs" / "m1-r-offline-v2.toml")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--resume-preflight-from", type=Path,
                        help="continue only the remaining frozen preflight budget from a verified zero-episode tokenizer failure")
    parser.add_argument("--verify-only", action="store_true",
                        help="verify an existing pilot package without starting llama.cpp")
    args = parser.parse_args()
    if args.verify_only:
        if args.out is None:
            parser.error("--out is required with --verify-only")
        run_dir = args.out.resolve()
        runtime = load_runtime_config(run_dir / "runtime-config.toml")
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        result = _verify_live_run(run_dir, runtime, manifest)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.config is None or args.out is None:
        parser.error("--config and --out are required to run the Pilot")
    result = run(args.config, args.runtime_config, args.out, args.resume_preflight_from)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "COMPLETE" and result["verification"]["status"] == "PASS_ARTIFACTS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
