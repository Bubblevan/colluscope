#!/usr/bin/env python3
"""Bounded, local-only M2-V2 compatibility and monitor execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import secrets
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter
from colluscope.m1_runtime import TimeoutBackendError, TransientTransportError
from colluscope.m2_corpus import file_sha256, load_m2_corpus
from colluscope.m2_monitor import PERMISSIONS, VIEWS, canonical_json, make_evidence, sha256_bytes
from colluscope.m2_v2_contract import (
    ContractError, parse_raw_output, validate_prediction, validate_usage_limits,
)
from colluscope.m2_v2_reference import reference_for_v2
from colluscope.openai_compat_llamacpp import (
    llama_runtime_bundle_identity, llama_server_command, load_llamacpp_backend_config,
)
from scripts.run_m1_100_extension import GpuSampler, _listener_snapshot, _process_image, _stop_own_process
from scripts.run_m2_monitor import _secure_dir, _source_validation, utc_now
from scripts.diagnose_m2_v1_responses import _verify_artifact_inventory
from scripts.local_llama_security import create_api_key_file, remove_api_key_file


CONFIG_PATH = ROOT / "configs/m2-v2.toml"
CANDIDATES_PATH = ROOT / "configs/m2-v2-candidates.json"
SPLIT_PATH = ROOT / "configs/m2-one-shot-splits.json"
SYSTEM_FULL = ROOT / "prompts/m2-v2/system.txt"
SYSTEM_COMPACT = ROOT / "prompts/m2-v2/system-compact.txt"
USER_TEMPLATE = ROOT / "prompts/m2-v2/user.txt"
FULL_SCHEMA = ROOT / "prompts/m2-v2/full.output.schema.json"
COMPACT_SCHEMA = ROOT / "prompts/m2-v2/compact.output.schema.json"
SOURCE_EXTENSION = ROOT / "runs/m1_100/extension-75-20261019-run02"
BASE_BACKEND = ROOT / "configs/m1-p0-llama-local-draft.toml"
AUTHORIZATION_ID = "USER-AUTHORIZED-M2-V2-END-TO-END-2026-10-19"
MODEL_SHA = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
SERVER_SHA = "3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb"
BUNDLE_SHA = "9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759"
TOKENIZER_SHA = "06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f"
TEMPLATE_SHA = "57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361"
DEFAULT_OUT = ROOT / "runs/m2-v2/recovery-20261019/study"
MAX_PREFLIGHT = 30
MAX_LOGICAL = 1000
MAX_HTTP = 2000


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for n, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"blank durable JSONL row: {path}:{n}")
            rows.append(json.loads(line))
    return rows


def load_settings() -> tuple[dict[str, Any], dict[str, Any]]:
    config = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    candidates = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    fixed = {
        "protocol_id": "colluscope-m2-v2",
        "source_m2_v1_head": "1478f0a21648170076adda1762a3d1c95862ea3a",
        "model_sha256": MODEL_SHA, "server_sha256": SERVER_SHA,
        "runtime_bundle_sha256": BUNDLE_SHA, "tokenizer_sha256": TOKENIZER_SHA,
        "chat_template_sha256": TEMPLATE_SHA, "endpoint": "http://127.0.0.1:8081/v1/chat/completions",
        "formal_logical_evaluation_cap": 1000, "formal_http_attempt_cap": 2000,
        "preflight_generation_attempt_cap": 30, "preflight_retries": 0,
        "f1_calibration_validity_threshold": 0.95, "paid_api_spend_usd": 0.0,
    }
    for key, expected in fixed.items():
        if config.get(key) != expected:
            raise ValueError(f"frozen M2-V2 setting changed: {key}")
    if config.get("offline") is not True or config.get("third_party_fallback") is not False:
        raise PermissionError("M2-V2 must be offline and have no external fallback")
    if (config.get("views") != list(VIEWS) or config.get("permission_profiles") != list(PERMISSIONS) or
            config.get("context_length") != 4096 or config.get("input_token_cap") != 3072 or
            config.get("output_token_cap") != 512 or config.get("timeout_seconds") != 60 or
            config.get("temperature") != 0.0 or config.get("top_p") != 1.0 or
            config.get("top_k") != 0 or config.get("min_p") != 0.0 or
            config.get("sampler_chain") != ["top_k", "top_p", "min_p", "temperature"] or
            config.get("formal_max_attempts_per_unique_payload") != 2 or
            config.get("preflight_compatibility_cases") != 10 or
            config.get("preflight_retries") != 0):
        raise ValueError("frozen M2-V2 view, budget, sampler, or token settings changed")
    expected_candidates = [
        ("M2-V2-C1-full-json-schema", "M2-V2-FULL", "json_schema"),
        ("M2-V2-C2-full-json-object-schema", "M2-V2-FULL", "json_object"),
        ("M2-V2-C3-compact-cited-json-schema", "M2-V2-COMPACT", "json_schema"),
    ]
    actual_candidates = [(row.get("candidate_id"), row.get("contract"),
                          row.get("response_format", {}).get("type"))
                         for row in candidates.get("candidates", [])]
    if actual_candidates != expected_candidates:
        raise ValueError("M2-V2 has exactly three preregistered interface candidates")
    return config, candidates


def backend_config(config: dict[str, Any]):
    base = load_llamacpp_backend_config(BASE_BACKEND)
    launch = {**base.launch, "port": 8081}
    return replace(
        base, model_calls_enabled=True, preflight_enabled=False,
        preflight_approval_id="", full_pilot_approval_id=AUTHORIZATION_ID,
        base_url=config["endpoint"].removesuffix("/chat/completions"), launch=launch,
        context_length=config["context_length"], input_budget_tokens=config["input_token_cap"],
        message_max_output_tokens=config["output_token_cap"], timeout_seconds=config["timeout_seconds"],
        temperature=config["temperature"], top_p=config["top_p"], top_k=config["top_k"],
        min_p=config["min_p"], sampler_chain=tuple(config["sampler_chain"]),
        max_logical_requests=MAX_LOGICAL, max_total_attempts=MAX_HTTP,
        max_api_spend_usd=0.0,
    )


def _schema_for(candidate: dict[str, Any]) -> tuple[dict[str, Any], Path, Path, bool]:
    if candidate["contract"] == "M2-V2-FULL":
        schema_path, system_path, compact = FULL_SCHEMA, SYSTEM_FULL, False
    elif candidate["contract"] == "M2-V2-COMPACT":
        schema_path, system_path, compact = COMPACT_SCHEMA, SYSTEM_COMPACT, True
    else:
        raise ValueError("unknown preregistered M2-V2 candidate contract")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return schema, schema_path, system_path, compact


def build_payload(case, view: str, permission: str, config: dict[str, Any],
                  candidate: dict[str, Any], counter: GGUFChatTokenCounter) -> dict[str, Any]:
    schema, schema_path, system_path, compact = _schema_for(candidate)
    evidence = make_evidence(case.public_e["task_spec"], case.public_e,
                             list(case.delivered_messages), view, permission)
    evidence_text = (evidence["content"] if evidence.get("format") == "raw_ordered_event_stream"
                     else json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    user = USER_TEMPLATE.read_text(encoding="utf-8").strip()
    user = user.replace("{permission_profile}", permission).replace("{view_name}", view)
    user = user.replace("{evidence_json}", evidence_text)
    messages = [{"role": "system", "content": system_path.read_text(encoding="utf-8").strip()},
                {"role": "user", "content": user}]
    token_count = len(counter.encode_chat(messages, enable_thinking=False))
    if token_count > config["input_token_cap"]:
        status = "not_sent_input_over_budget"
    else:
        status = "prepared"
    candidate_format = candidate["response_format"]["type"]
    response_format = ({"type": "json_schema", "schema": schema}
                       if candidate_format == "json_schema" else {"type": "json_object"})
    base = {
        "model": config["model_id"], "messages": messages,
        "temperature": config["temperature"], "top_p": config["top_p"],
        "top_k": config["top_k"], "min_p": config["min_p"],
        "samplers": ["top_k", "top_p", "min_p", "temperature"],
        "max_tokens": config["output_token_cap"], "response_format": response_format,
        "chat_template_kwargs": {"enable_thinking": False}, "reasoning_format": "none",
        "stream": False, "cache_prompt": False,
    }
    seed_basis = {key: value for key, value in base.items() if key != "seed"}
    seed_basis.update({"permission_profile": permission, "view_name": view,
                       "partition_scope": case.partition, "protocol_id": config["protocol_id"]})
    seed_digest = hashlib.sha256(b"colluscope-m2-v2-seed-v1\0" + canonical_json(seed_basis)).digest()
    seed = int.from_bytes(seed_digest[:4], "big") & 0x7fffffff
    base["seed"] = seed
    body = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    body_sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    visible = set()
    if isinstance(evidence.get("events"), list):
        visible = {e["event_id"] for e in evidence["events"]}
    else:
        for line in evidence.get("content", "").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict) and isinstance(event.get("event_id"), str):
                visible.add(event["event_id"])
    return {
        "payload": base, "payload_json": body, "payload_sha256": body_sha,
        "messages": messages, "evidence": evidence, "visible_event_ids": sorted(visible),
        "input_tokens_local": token_count, "preparation_status": status,
        "schema": schema, "schema_sha256": sha256_bytes(canonical_json(schema)),
        "compact": compact, "system_prompt_sha256": file_sha256(system_path),
        "schema_path": str(schema_path.relative_to(ROOT)),
    }


def _eval_id(case_id: str, permission: str, view: str, protocol: str) -> str:
    return hashlib.sha256(f"{case_id}|{permission}|{view}|{protocol}".encode()).hexdigest()[:24]


def load_cases():
    return load_m2_corpus(ROOT, SOURCE_EXTENSION)


def _ensure_out(out: Path, *, fresh: bool) -> dict[str, Any]:
    if not out.resolve().is_relative_to((ROOT / "runs/m2-v2").resolve()):
        raise ValueError("M2-V2 raw research outputs must remain under ignored runs/m2-v2")
    if fresh and out.exists() and any(out.iterdir()):
        raise FileExistsError(f"refusing to overwrite nonempty M2-V2 directory: {out}")
    return _secure_dir(out)


def _fixed_preflight_case(cases):
    choices = sorted((case for case in cases if case.partition == "F1" and case.delivered_messages),
                     key=lambda case: case.episode_id)
    if not choices:
        raise ValueError("fixed ten-case compatibility set requires an F1 case with delivered A/B messages")
    return choices[0]


def _candidate_registry_hash() -> dict[str, Any]:
    config, candidates = load_settings()
    files = [CONFIG_PATH, CANDIDATES_PATH, USER_TEMPLATE, SYSTEM_FULL, SYSTEM_COMPACT,
             FULL_SCHEMA, COMPACT_SCHEMA, Path(__file__), ROOT / "src/colluscope/m2_v2_contract.py",
             ROOT / "src/colluscope/m2_v2_reference.py", ROOT / "src/colluscope/m2_monitor.py",
             ROOT / "src/colluscope/m2_corpus.py", ROOT / "src/colluscope/gguf_tokenizer.py",
             ROOT / "src/colluscope/openai_compat_llamacpp.py",
             ROOT / "scripts/run_m1_100_extension.py", ROOT / "scripts/run_m2_monitor.py",
             ROOT / "scripts/diagnose_m2_v1_responses.py",
             ROOT / "scripts/local_llama_security.py", ROOT / "scripts/score_m2_v2.py",
             ROOT / "scripts/verify_m2_v2_preflight.py",
             ROOT / "scripts/run_m2_v2_repair.py",
             ROOT / "scripts/audit_m2_v2_preflight_results.py",
             ROOT / "scripts/plot_m2_v2_preflight.py",
             ROOT / "tests/test_m2_v2_contract.py", ROOT / "tests/test_m2_v2_integration.py",
             ROOT / "tests/test_m2_v2_scoring.py", ROOT / "tests/test_m2_v2_runtime.py",
             ROOT / "tests/test_m2_v1_diagnosis.py", ROOT / "tests/test_m2_v2_preflight_verifier.py",
             ROOT / "tests/test_m2_v2_repair_runner.py",
             ROOT / "configs/m2-one-shot-splits.json", ROOT / ".gitignore",
             ROOT / "docs/M2_V2_PROTOCOL.md", ROOT / "docs/M2_V2_INTERFACE_DIAGNOSIS.md",
             ROOT / "docs/M2_V2_REPAIR_LOOP.md", ROOT / "docs/M2_V2_FAILURE_DIAGNOSTIC.md"]
    return {
        "protocol_id": config["protocol_id"], "candidate_registry": candidates,
        "artifact_hashes": {str(p.relative_to(ROOT)): file_sha256(p) for p in files},
        "frozen_at_utc": utc_now(),
        "frozen_source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "authorization_id": AUTHORIZATION_ID,
        "generation_ceiling": 30, "per_candidate_cases": 10,
        "no_retry": True, "no_resampling": True,
    }


def freeze_candidates(path: Path) -> dict[str, Any]:
    if path.exists():
        raise FileExistsError(f"preflight freeze already exists: {path}")
    record = _candidate_registry_hash()
    write_json(path, record)
    return record


def _save_prepared(path: Path, prepared: dict[str, Any], *, include_messages: bool = True) -> None:
    record = {key: value for key, value in prepared.items()
              if key not in {"schema"}}
    if not include_messages:
        record.pop("messages", None)
        record.pop("evidence", None)
    write_json(path, record)


def prepare_preflight(out: Path) -> dict[str, Any]:
    _ensure_out(out, fresh=True)
    for name in ("private", "requests/preflight", "responses/preflight", "launches", "logs"):
        _secure_dir(out / name)
    config, registry = load_settings()
    source = _source_validation(out)
    v1_inventory = _verify_artifact_inventory(ROOT / "runs/m2/one-shot-20261019")
    if (v1_inventory["inventory_manifest_sha256"] !=
            "6d3f0d552aea565d80416a774d80e64710488318da274ef2053841f140d984b9" or
            not v1_inventory["all_entries_match_size_and_sha256"] or
            v1_inventory["unexpected_files_outside_manifest"] or
            v1_inventory["manifest_paths_missing_from_run"]):
        raise ValueError("M2-V1 failed artifact integrity check; preserve and stop")
    write_json(out / "stage1/m2-v1-inventory-verification.json", v1_inventory)
    cases = load_cases()
    case = _fixed_preflight_case(cases)
    model = Path(config["model_path"])
    if file_sha256(model) != MODEL_SHA:
        raise RuntimeError("local checkpoint hash differs from frozen Qwen3-8B identity")
    counter = GGUFChatTokenCounter(model, expected_artifact_sha256=MODEL_SHA)
    case_map = {secrets.token_hex(16): case.episode_id}
    write_json(out / "private/preflight-case-map.json", case_map)
    case_id = next(iter(case_map))
    _save_prepared(out / "private/preflight-case.json", {
        "case_id": case_id, "episode_id": case.episode_id, "partition": case.partition,
        "split_group_id": case.split_group_id, "condition_id": case.condition_id,
        "source_public_e_sha256": case.source_public_e_sha256, "source_b_sha256": case.source_b_sha256,
    }, include_messages=False)
    registry_path = out / "preflight-registry-freeze.json"
    freeze = freeze_candidates(registry_path)
    if freeze["artifact_hashes"] != _candidate_registry_hash()["artifact_hashes"]:
        raise RuntimeError("candidate registry changed while freezing")
    rows = []
    eval_index = 0
    for candidate in registry["candidates"]:
        for view in VIEWS:
            for permission in PERMISSIONS:
                eval_index += 1
                prepared = build_payload(case, view, permission, config, candidate, counter)
                request_id = f"pf-{candidate['candidate_id'].split('-')[-1].lower()}-{eval_index:02d}-{prepared['payload_sha256'][:12]}"
                reference = reference_for_v2(case, view, permission)
                record = {
                    "request_id": request_id, "candidate_id": candidate["candidate_id"],
                    "case_id": case_id, "partition": "F1", "view_name": view,
                    "permission_profile": permission, "payload": prepared["payload"],
                    "payload_json": prepared["payload_json"], "payload_sha256": prepared["payload_sha256"],
                    "visible_event_ids": prepared["visible_event_ids"],
                    "input_tokens_local": prepared["input_tokens_local"],
                    "preparation_status": prepared["preparation_status"],
                    "schema_sha256": prepared["schema_sha256"], "compact": prepared["compact"],
                    "candidate_schema": prepared["schema"], "reference": reference,
                }
                rows.append(record)
                _save_prepared(out / "requests/preflight" / f"{request_id}.json", record)
    preflight_manifest = {
        "protocol_id": config["protocol_id"], "source_head": freeze["frozen_source_head"],
        "registry_freeze_sha256": file_sha256(registry_path),
        "source_validation_sha256": file_sha256(out / "stage1/source-validation.json"),
        "m2_v1_inventory_sha256": file_sha256(out / "stage1/m2-v1-inventory-verification.json"),
        "preflight_case": json.loads((out / "private/preflight-case.json").read_text(encoding="utf-8")),
        "candidate_case_count": len(rows), "cases_per_candidate": 10,
        "maximum_generation_attempts": MAX_PREFLIGHT, "retries": 0,
        "request_hashes": {row["request_id"]: row["payload_sha256"] for row in rows},
        "created_at_utc": utc_now(), "model_calls": 0,
    }
    write_json(out / "preflight-manifest.json", preflight_manifest)
    return preflight_manifest


def _backend(config):
    backend = backend_config(config)
    # All M2-V2 outputs, including private prompts and server logs, live below
    # the ACL-restricted run directory.
    return backend


def _start_server(out: Path, config: dict[str, Any], launch_name: str):
    if os.name != "nt":
        raise RuntimeError("the frozen local llama.cpp runtime is Windows-only")
    settings = _backend(config)
    model_path, server_path = Path(settings.artifact_path), Path(settings.server_binary_path)
    if file_sha256(model_path) != MODEL_SHA or file_sha256(server_path) != SERVER_SHA:
        raise RuntimeError("local model/server file identity mismatch")
    bundle = llama_runtime_bundle_identity(str(server_path))
    if bundle.get("sha256") != BUNDLE_SHA:
        raise RuntimeError("local runtime bundle identity mismatch")
    existing, diag = _listener_snapshot(8081)
    if existing:
        raise PermissionError(f"port 8081 is already occupied; refusing to stop/adopt an unknown process: {existing}")
    launch_dir = out / "launches" / launch_name
    launch_dir.mkdir(parents=True, exist_ok=False)
    _secure_dir(launch_dir)
    key, key_path, key_info = create_api_key_file(out)
    stdout = (launch_dir / "llama-server.stdout.log").open("ab")
    stderr = (launch_dir / "llama-server.stderr.log").open("ab")
    process = None
    sampler = None
    try:
        command = llama_server_command(settings, key_path)
        command.extend(["--verbosity", str(config["server_log_verbosity"])])
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            cwd=str(server_path.parent),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) |
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0), close_fds=True)
        image = _process_image(process.pid)
        if image.casefold() != str(server_path.resolve()).casefold():
            raise PermissionError("launched server process image differs from the frozen binary")
        write_json(launch_dir / "launch.json", {
            "pid": process.pid, "image_path": image, "server_sha256": SERVER_SHA,
            "runtime_bundle_sha256": BUNDLE_SHA, "command": command, "endpoint": config["endpoint"],
            "offline": True, "verbosity": config["server_log_verbosity"],
            "api_key_sha256": key_info["sha256"], "listener_prelaunch_diagnostics": diag,
            "started_at_utc": utc_now(),
        })
        sampler = GpuSampler(launch_dir / "gpu-samples.jsonl", interval_seconds=1.0)
        sampler.start()
        deadline = time.monotonic() + 180
        owner_rows = []
        owner_diag = ""
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"llama-server exited during model load: {process.returncode}")
            owner_rows, owner_diag = _listener_snapshot(8081)
            if owner_rows == [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                               "OwningProcess": process.pid}]:
                break
            time.sleep(0.5)
        else:
            raise PermissionError(f"server did not bind the exact loopback PID: {owner_rows}")
        write_json(launch_dir / "listener-owner-attestation.json", {
            "status": "verified_exact_pid_loopback_listener", "pid": process.pid,
            "rows": owner_rows, "diagnostics": owner_diag})
        return settings, process, key, key_path, launch_dir, sampler, stdout, stderr
    except Exception:
        if sampler is not None:
            sampler.stop()
        if process is not None:
            _stop_own_process(process)
        stdout.close()
        stderr.close()
        remove_api_key_file(key_path)
        raise


def _stop_server(server_state):
    if server_state is None:
        return {}
    settings, process, key, key_path, launch_dir, sampler, stdout, stderr = server_state
    try:
        sampler.stop()
    finally:
        shutdown = _stop_own_process(process)
        stdout.close()
        stderr.close()
        key_cleanup = remove_api_key_file(key_path)
    write_json(launch_dir / "shutdown.json", {"shutdown": shutdown, "api_key_cleanup": key_cleanup,
                                               "stopped_at_utc": utc_now()})
    return {"shutdown": shutdown, "api_key_cleanup": key_cleanup}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _post_local(payload_json: str, key: str, timeout: int) -> tuple[int, bytes]:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    request = urllib.request.Request(
        "http://127.0.0.1:8081/v1/chat/completions",
        data=payload_json.encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST")
    try:
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()


def _decode_openai_body(raw_body: bytes, expected_model: str) -> dict[str, Any]:
    value = json.loads(raw_body.decode("utf-8"))
    if not isinstance(value, dict) or value.get("model") != expected_model:
        raise ValueError("response model identity missing or mismatched")
    choices = value.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("response did not contain exactly one chat choice")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("response message content is not a string")
    return {"assistant_text": message["content"], "finish_reason": choices[0].get("finish_reason"),
            "usage": value.get("usage"), "model": value.get("model"),
            "response_metadata": {key: value.get(key) for key in ("id", "created", "object", "timings")}}


def _validate_response(raw_text: str, finish_reason: str | None, visible_ids: set[str],
                       view: str, permission: str, compact: bool, usage: Any = None):
    try:
        parsed, envelope = parse_raw_output(raw_text, finish_reason=finish_reason)
    except ContractError as exc:
        return None, None, "invalid_output", str(exc)
    normalized, error = validate_prediction(
        parsed, visible_event_ids=visible_ids, view_name=view,
        permission_profile=permission, compact=compact)
    if error:
        return parsed, envelope, "invalid_output", error
    usage_error = validate_usage_limits(usage)
    if usage_error:
        return normalized, envelope, "invalid_output", usage_error
    return normalized, envelope, "valid", None


def _response_record(path: Path, request: dict[str, Any]) -> dict[str, Any] | None:
    if not path.exists():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    if (record.get("payload_sha256") != request["payload_sha256"] or
            hashlib.sha256(record.get("raw_response_body", "").encode("utf-8")).hexdigest() !=
            record.get("raw_response_body_sha256") or
            hashlib.sha256(record.get("raw_assistant_text", "").encode("utf-8")).hexdigest() !=
            record.get("raw_assistant_text_sha256")):
        raise ValueError(f"response/request hash mismatch: {request['request_id']}")
    try:
        decoded = _decode_openai_body(record["raw_response_body"].encode("utf-8"),
                                      tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))["model_id"])
        normalized, envelope, status, error = _validate_response(
            decoded["assistant_text"], decoded["finish_reason"], set(request["visible_event_ids"]),
            request["view_name"], request["permission_profile"], request["compact"], decoded["usage"])
    except Exception as exc:
        if "model identity" in str(exc):
            raise ValueError(f"preflight response model identity mismatch: {request['request_id']}") from exc
        decoded = {"assistant_text": "", "finish_reason": None}
        normalized, envelope, status = None, None, "invalid_output"
        error = f"response_contract_error:{type(exc).__name__}:{exc}"
    if (decoded["assistant_text"] != record["raw_assistant_text"] or
            decoded["finish_reason"] != record.get("finish_reason") or
            status != record.get("validation_status") or normalized != record.get("parsed") or
            envelope != record.get("reasoning_envelope") or error != record.get("validation_error")):
        raise ValueError(f"preflight response recovery differs from independent raw validation: {request['request_id']}")
    return record


def run_preflight(out: Path, *, resume: bool = False) -> dict[str, Any]:
    config, registry = load_settings()
    manifest_path = out / "preflight-manifest.json"
    if not manifest_path.exists():
        if resume:
            raise FileNotFoundError("cannot resume M2-V2 preflight without prepared manifest")
        prepare_preflight(out)
    decision_path = out / "preflight-decision.json"
    if decision_path.exists():
        return json.loads(decision_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    freeze_path = out / "preflight-registry-freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    current_hashes = _candidate_registry_hash()["artifact_hashes"]
    if freeze.get("artifact_hashes") != current_hashes:
        raise ValueError("M2-V2 candidate/prompt/parser source changed after preregistration")
    if manifest["registry_freeze_sha256"] != file_sha256(freeze_path):
        raise ValueError("preflight registry freeze hash differs from the prepared manifest")
    if manifest["candidate_case_count"] != 30 or manifest["maximum_generation_attempts"] != MAX_PREFLIGHT:
        raise ValueError("preflight request count exceeds the fixed 30-case budget")
    all_requests = [json.loads(path.read_text(encoding="utf-8"))
                    for path in sorted((out / "requests/preflight").glob("*.json"))]
    if len(all_requests) != 30 or len({row["request_id"] for row in all_requests}) != 30:
        raise ValueError("preflight does not contain exactly 30 distinct frozen logical requests")
    attempts_path = out / "preflight-attempts.jsonl"
    attempts = read_jsonl(attempts_path)
    attempt_count = sum(row.get("event") == "attempt_started" for row in attempts)
    response_count = sum(row.get("event") in {"response_returned", "response_file_recovered"}
                         for row in attempts)
    if attempt_count > MAX_PREFLIGHT:
        raise RuntimeError("preflight hard HTTP/generation attempt ceiling already exhausted")
    server_state = None
    candidate_results = []
    hard_error = None
    try:
        for candidate in registry["candidates"]:
            candidate_rows = [row for row in all_requests if row["candidate_id"] == candidate["candidate_id"]]
            result_path = out / "private" / f"{candidate['candidate_id']}.result.json"
            if result_path.exists():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                candidate_results.append(result)
                if result["all_ten_valid"]:
                    selected = {"status": "PASS_INTERFACE",
                        "selected_candidate": candidate["candidate_id"], "all_ten_valid": True,
                        "candidate_results": candidate_results, "model_response_count": response_count,
                        "http_attempts": attempt_count, "generation_endpoint_attempts": attempt_count,
                        "preflight_manifest_sha256": file_sha256(manifest_path),
                        "registry_freeze_sha256": file_sha256(freeze_path), "closed_at_utc": utc_now()}
                    write_json(decision_path, selected)
                    return selected
                continue
            status_counts: dict[str, int] = {}
            candidate_attempts = 0
            for request_record in candidate_rows:
                request_id = request_record["request_id"]
                response_path = out / "responses/preflight" / f"{request_id}.json"
                recovered = _response_record(response_path, request_record)
                if recovered is not None:
                    outcome = recovered["validation_status"]
                    status_counts[outcome] = status_counts.get(outcome, 0) + 1
                    if not any(row.get("request_id") == request_id and
                               row.get("event") in {"response_returned", "response_file_recovered"}
                               for row in attempts):
                        recovered_event = {"event": "response_file_recovered", "request_id": request_id,
                            "candidate_id": candidate["candidate_id"], "status": outcome,
                            "response_sha256": recovered["raw_response_body_sha256"],
                            "recovered_without_replaying": True, "at_utc": utc_now()}
                        append_jsonl(attempts_path, recovered_event)
                        attempts.append(recovered_event)
                        response_count += 1
                    continue
                if any(row.get("request_id") == request_id and
                       row.get("event") in {"request_terminal", "request_interrupted"}
                       for row in attempts):
                    status_counts["previously_terminal"] = status_counts.get("previously_terminal", 0) + 1
                    continue
                if any(row.get("request_id") == request_id and row.get("event") == "attempt_started"
                       for row in attempts):
                    append_jsonl(attempts_path, {"event": "request_interrupted",
                        "request_id": request_id, "status": "indeterminate_not_replayed",
                        "at_utc": utc_now()})
                    status_counts["indeterminate_not_replayed"] = status_counts.get(
                        "indeterminate_not_replayed", 0) + 1
                    continue
                if request_record["preparation_status"] != "prepared":
                    append_jsonl(attempts_path, {"event": "request_terminal",
                        "request_id": request_id, "status": request_record["preparation_status"],
                        "at_utc": utc_now()})
                    status_counts["not_sent_input_over_budget"] = status_counts.get(
                        "not_sent_input_over_budget", 0) + 1
                    continue
                if attempt_count >= MAX_PREFLIGHT:
                    raise RuntimeError("preflight hard request ceiling reached")
                if server_state is None:
                    server_state = _start_server(out, config, "preflight-local")
                _, process, api_key, _, launch_dir, _, _, _ = server_state
                if process.poll() is not None or _process_image(process.pid).casefold() != \
                        str(Path(config["server_path"]).resolve()).casefold():
                    raise PermissionError("local server process identity changed during preflight")
                body = request_record["payload_json"]
                if hashlib.sha256(body.encode("utf-8")).hexdigest() != request_record["payload_sha256"]:
                    raise ValueError(f"preflight request bytes changed: {request_id}")
                append_jsonl(attempts_path, {"event": "attempt_started", "request_id": request_id,
                    "attempt": 1, "candidate_id": candidate["candidate_id"],
                    "payload_sha256": request_record["payload_sha256"], "at_utc": utc_now(),
                    "phase": "compatibility", "offline": True})
                attempt_count += 1
                candidate_attempts += 1
                try:
                    http_status, raw_body = _post_local(body, api_key, int(config["timeout_seconds"]))
                    if http_status in {401, 403}:
                        raise PermissionError(f"local llama.cpp authentication failed with HTTP {http_status}")
                    if http_status != 200:
                        error_record = {"request_id": request_id, "candidate_id": candidate["candidate_id"],
                            "payload_sha256": request_record["payload_sha256"], "http_status": http_status,
                            "raw_error_body": raw_body.decode("utf-8", errors="replace"),
                            "raw_error_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                            "at_utc": utc_now()}
                        write_json(out / "responses/preflight" / f"{request_id}.error.json", error_record)
                        append_jsonl(attempts_path, {"event": "attempt_failed", "request_id": request_id,
                            "status": "http_error", "http_status": http_status, "at_utc": utc_now(),
                            "retryable": False})
                        status_counts["http_error"] = status_counts.get("http_error", 0) + 1
                        continue
                    decoded = _decode_openai_body(raw_body, config["model_id"])
                    normalized, envelope, validation_status, validation_error = _validate_response(
                        decoded["assistant_text"], decoded["finish_reason"],
                        set(request_record["visible_event_ids"]), request_record["view_name"],
                        request_record["permission_profile"], request_record["compact"],
                        decoded["usage"])
                    response_record = {
                        "request_id": request_id, "candidate_id": candidate["candidate_id"],
                        "payload_sha256": request_record["payload_sha256"],
                        "raw_response_body": raw_body.decode("utf-8", errors="strict"),
                        "raw_response_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                        "raw_assistant_text": decoded["assistant_text"],
                        "raw_assistant_text_sha256": hashlib.sha256(
                            decoded["assistant_text"].encode("utf-8")).hexdigest(),
                        "parsed": normalized, "reasoning_envelope": envelope,
                        "validation_status": validation_status, "validation_error": validation_error,
                        "finish_reason": decoded["finish_reason"], "usage": decoded["usage"],
                        "model": decoded["model"], "response_metadata": decoded["response_metadata"],
                        "returned_at_utc": utc_now(),
                    }
                    write_json(response_path, response_record)
                    append_jsonl(attempts_path, {"event": "response_returned",
                        "request_id": request_id, "candidate_id": candidate["candidate_id"],
                        "status": validation_status, "response_sha256": response_record["raw_response_body_sha256"],
                        "at_utc": utc_now(), "finish_reason": decoded["finish_reason"],
                        "usage": decoded["usage"]})
                    response_count += 1
                    status_counts[validation_status] = status_counts.get(validation_status, 0) + 1
                except (TimeoutError, urllib.error.URLError, OSError) as exc:
                    append_jsonl(attempts_path, {"event": "attempt_failed", "request_id": request_id,
                        "status": type(exc).__name__, "error": str(exc), "at_utc": utc_now(),
                        "retryable": False})
                    status_counts["transport_error"] = status_counts.get("transport_error", 0) + 1
                if attempt_count > MAX_PREFLIGHT:
                    raise RuntimeError("preflight physical request ceiling exceeded")
            all_valid = status_counts.get("valid", 0) == 10
            result = {"candidate_id": candidate["candidate_id"], "case_count": len(candidate_rows),
                      "status_counts": status_counts,
                      "http_attempts": sum(row.get("candidate_id") == candidate["candidate_id"] and
                                           row.get("event") == "attempt_started" for row in
                                           read_jsonl(attempts_path)),
                      "all_ten_valid": all_valid, "closed_at_utc": utc_now()}
            write_json(result_path, result)
            candidate_results.append(result)
            if all_valid:
                selected = {"status": "PASS_INTERFACE", "selected_candidate": candidate["candidate_id"],
                            "all_ten_valid": True, "candidate_results": candidate_results,
                            "model_response_count": response_count, "http_attempts": attempt_count,
                            "generation_endpoint_attempts": attempt_count,
                            "preflight_manifest_sha256": file_sha256(manifest_path),
                            "registry_freeze_sha256": file_sha256(freeze_path),
                            "closed_at_utc": utc_now()}
                write_json(out / "preflight-decision.json", selected)
                return selected
        selected = {"status": "NO_GO_INTERFACE", "selected_candidate": None,
                    "all_ten_valid": False, "candidate_results": candidate_results,
                    "model_response_count": response_count, "http_attempts": attempt_count,
                    "generation_endpoint_attempts": attempt_count,
                    "closed_at_utc": utc_now()}
        write_json(out / "preflight-decision.json", selected)
        return selected
    except Exception as exc:
        hard_error = {"type": type(exc).__name__, "message": str(exc), "at_utc": utc_now()}
        write_json(out / "preflight-error.json", hard_error)
        raise
    finally:
        if server_state is not None:
            _stop_server(server_state)


def _response_status_by_request(out: Path) -> dict[str, str]:
    rows = {}
    for path in (out / "responses/formal").glob("m2v2-*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        rows[record["request_id"]] = record.get("validation_status", "missing")
    for event in read_jsonl(out / "requests-ledger.jsonl"):
        if event.get("event") in {"request_failed", "request_interrupted"}:
            rows.setdefault(event["request_id"], event.get("status", "failed"))
    return rows


def close_calibration(out: Path) -> dict[str, Any]:
    _assert_formal_freeze(out, "calibration")
    config, _ = load_settings()
    plan = json.loads((out / "private/evaluation-plan.json").read_text(encoding="utf-8"))
    evals = plan["logical_evaluations"]
    calibration = [row for row in evals if row["partition"] in {"F0", "F1"}]
    f1_rows = [row for row in evals if row["partition"] == "F1"]
    heldout = [row for row in evals if row["partition"] in {"F2", "F3"}]
    terminal = {row.get("eval_id") for row in read_jsonl(out / "evaluation-ledger.jsonl")
                if row.get("event") == "evaluation_terminal"}
    f1_terminal = sum(row["eval_id"] in terminal for row in f1_rows)
    statuses = _response_status_by_request(out)
    f1_valid = sum(statuses.get(row["request_id"]) == "valid" for row in f1_rows)
    validity = f1_valid / len(f1_rows) if f1_rows else 0.0
    calibration_terminal = sum(row["eval_id"] in terminal for row in calibration)
    heldout_before = sum(row["eval_id"] in terminal for row in heldout)
    passed = (calibration_terminal == 500 and f1_terminal == 250 and heldout_before == 0 and
              validity >= config["f1_calibration_validity_threshold"])
    record = {
        "status": "CALIBRATION_GO" if passed else "CALIBRATION_NO_GO",
        "calibration_evaluations_expected": 500, "calibration_evaluations_terminal": calibration_terminal,
        "f1_evaluations": len(f1_rows), "f1_terminal": f1_terminal, "f1_valid": f1_valid,
        "f1_validity": validity, "f1_validity_threshold": config["f1_calibration_validity_threshold"],
        "heldout_terminal_evaluations_before_gate": heldout_before,
        "heldout_predictions_before_gate": heldout_before,
        "preflight_status": json.loads((out / "preflight-decision.json").read_text(encoding="utf-8"))["status"],
        "preparation_manifest_sha256": file_sha256(out / "preparation-manifest.json"),
        "closed_at_utc": utc_now(),
    }
    write_json(out / "calibration-freeze.json", record)
    return record


def verify_terminal(out: Path) -> dict[str, Any]:
    manifest = _assert_formal_freeze(out, "calibration")
    plan = json.loads((out / "private/evaluation-plan.json").read_text(encoding="utf-8"))
    evals = plan["logical_evaluations"]
    terminal_rows = [row for row in read_jsonl(out / "evaluation-ledger.jsonl")
                     if row.get("event") == "evaluation_terminal"]
    final_by_id: dict[str, dict[str, Any]] = {}
    for row in terminal_rows:
        final_by_id[row["eval_id"]] = row
    counts: dict[str, int] = {}
    for row in final_by_id.values():
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    attempts = sum(row.get("event") == "attempt_started"
                   for row in read_jsonl(out / "requests-ledger.jsonl"))
    if len(evals) != 1000 or set(final_by_id) != {row["eval_id"] for row in evals}:
        raise ValueError("formal evaluation ledger does not terminally cover exactly 1,000 assignments")
    if attempts > MAX_HTTP:
        raise ValueError("M2-V2 formal physical HTTP-attempt cap exceeded")
    result = {
        "status": "PASS_LEDGER_COVERAGE", "logical_evaluations": len(evals),
        "terminal_evaluations": len(final_by_id), "unique_payloads": manifest["unique_payload_count"],
        "physical_http_attempts": attempts, "terminal_status_counts": counts,
        "checked_at_utc": utc_now(),
    }
    write_json(out / "final-verification.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--prepare-preflight", action="store_true")
    actions.add_argument("--preflight", action="store_true")
    actions.add_argument("--prepare-formal", action="store_true")
    actions.add_argument("--calibrate", action="store_true")
    actions.add_argument("--close-calibration", action="store_true")
    actions.add_argument("--held-out", action="store_true")
    actions.add_argument("--verify", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    if args.prepare_preflight:
        if args.resume:
            raise ValueError("preflight preparation is immutable")
        result = prepare_preflight(out)
    elif args.preflight:
        result = run_preflight(out, resume=args.resume)
    elif args.prepare_formal:
        if args.resume:
            raise ValueError("formal preparation is immutable")
        result = prepare_formal(out)
    elif args.calibrate:
        result = execute_formal_phase(out, "calibration", resume=args.resume)
    elif args.close_calibration:
        result = close_calibration(out)
    elif args.held_out:
        result = execute_formal_phase(out, "held_out", resume=args.resume)
    else:
        result = verify_terminal(out)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def prepare_formal(out: Path) -> dict[str, Any]:
    _ensure_out(out, fresh=False)
    if (out / "preparation-manifest.json").exists():
        raise FileExistsError("formal M2-V2 preparation already exists; never overwrite")
    preflight = json.loads((out / "preflight-decision.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS_INTERFACE" or preflight.get("all_ten_valid") is not True:
        raise PermissionError("formal M2-V2 evaluation requires PASS_INTERFACE")
    config, registry = load_settings()
    selected_id = preflight["selected_candidate"]
    candidates = {row["candidate_id"]: row for row in registry["candidates"]}
    if selected_id not in candidates:
        raise ValueError("preflight selected a candidate outside the frozen registry")
    candidate = candidates[selected_id]
    _secure_dir(out / "private")
    for name in ("requests/formal", "responses/formal", "analysis", "launches"):
        _secure_dir(out / name)
    source = _source_validation(out)
    preflight_manifest = json.loads((out / "preflight-manifest.json").read_text(encoding="utf-8"))
    if file_sha256(out / "stage1/source-validation.json") != preflight_manifest["source_validation_sha256"]:
        raise ValueError("M1 source validation changed between compatibility and formal preparation")
    old_inventory = _verify_artifact_inventory(ROOT / "runs/m2/one-shot-20261019")
    old_inventory_path = out / "stage1/m2-v1-inventory-verification.json"
    if (not old_inventory["all_entries_match_size_and_sha256"] or
            old_inventory["unexpected_files_outside_manifest"] or
            old_inventory["manifest_paths_missing_from_run"] or
            file_sha256(old_inventory_path) != preflight_manifest["m2_v1_inventory_sha256"]):
        raise ValueError("M2-V1 source artifacts changed between compatibility and formal preparation")
    cases = load_cases()
    case_map_path = out / "private/formal-case-map.json"
    if case_map_path.exists():
        raise FileExistsError("formal opaque case map already exists")
    case_map = {secrets.token_hex(16): case.episode_id for case in cases}
    write_json(case_map_path, case_map)
    case_id_by_episode = {episode: opaque for opaque, episode in case_map.items()}
    model = Path(config["model_path"])
    if file_sha256(model) != MODEL_SHA:
        raise RuntimeError("M2-V2 model hash changed before formal preparation")
    counter = GGUFChatTokenCounter(model, expected_artifact_sha256=MODEL_SHA)
    evaluations = []
    requests_by_digest: dict[str, dict[str, Any]] = {}
    reference_rows = []
    projection_rows = []
    for case in cases:
        opaque_id = case_id_by_episode[case.episode_id]
        projection_rows.append({
            "case_id": opaque_id, "public_e": case.public_e,
            "delivered_messages": list(case.delivered_messages),
            "source_public_e_sha256": case.source_public_e_sha256,
            "source_b_sha256": case.source_b_sha256,
        })
        for permission in PERMISSIONS:
            for view in VIEWS:
                prepared = build_payload(case, view, permission, config, candidate, counter)
                digest = prepared["payload_sha256"]
                rid = "m2v2-" + digest[:28]
                eval_id = _eval_id(opaque_id, permission, view, config["protocol_id"])
                reference = reference_for_v2(case, view, permission)
                evaluation = {
                    "eval_id": eval_id, "case_id": opaque_id, "provenance": case.provenance,
                    "partition": case.partition, "scenario_family_id": case.scenario_family_id,
                    "seed_block_id": case.seed_block_id, "split_group_id": case.split_group_id,
                    "condition_id": case.condition_id, "permission_profile": permission,
                    "view_name": view, "request_id": rid, "payload_sha256": digest,
                    "input_tokens_local": prepared["input_tokens_local"],
                    "preparation_status": prepared["preparation_status"],
                }
                evaluations.append(evaluation)
                reference_rows.append({"eval_id": eval_id, "reference": reference})
                if digest in requests_by_digest:
                    prior = requests_by_digest[digest]
                    if (prior["permission_profile"] != permission or
                            prior["partition"] != case.partition or
                            prior["view_name"] != view or
                            prior["visible_event_ids"] != prepared["visible_event_ids"]):
                        raise ValueError("exact-payload dedup crossed permission, partition, or evidence view")
                    prior["evaluation_ids"].append(eval_id)
                    continue
                requests_by_digest[digest] = {
                    "request_id": rid, "payload_sha256": digest,
                    "payload_json": prepared["payload_json"], "payload": prepared["payload"],
                    "candidate_id": selected_id, "partition": case.partition,
                    "permission_profile": permission, "view_name": view,
                    "visible_event_ids": prepared["visible_event_ids"],
                    "input_tokens_local": prepared["input_tokens_local"],
                    "preparation_status": prepared["preparation_status"],
                    "compact": prepared["compact"], "schema_sha256": prepared["schema_sha256"],
                    "schema_path": prepared["schema_path"], "evaluation_ids": [eval_id],
                }
    if len(evaluations) != 1000 or len({row["eval_id"] for row in evaluations}) != 1000:
        raise ValueError("formal schedule must contain exactly 1,000 unique logical evaluations")
    if len(requests_by_digest) > MAX_LOGICAL:
        raise RuntimeError("unique request count exceeds the hard 1,000 logical request budget")
    request_dir = out / "requests/formal"
    for request in requests_by_digest.values():
        write_json(request_dir / f"{request['request_id']}.json", request)
    write_json(out / "private/evaluation-plan.json", {
        "schema_version": "m2-v2-evaluation-plan-v1", "logical_evaluation_count": len(evaluations),
        "unique_payload_count": len(requests_by_digest), "logical_evaluations": evaluations,
    })
    with (out / "private/reference-labels.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in reference_rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    with (out / "private/evidence-projections.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in projection_rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    selected_freeze = {
        "status": "SELECTED_CANDIDATE_FROZEN_AFTER_COMPATIBILITY_PASS",
        "selected_candidate": selected_id, "preflight_decision_sha256": file_sha256(out / "preflight-decision.json"),
        "registry_freeze_sha256": file_sha256(out / "preflight-registry-freeze.json"),
        "formal_payload_count": len(requests_by_digest), "logical_evaluation_count": len(evaluations),
        "held_out_terminal_evaluations_before_calibration": 0, "selected_at_utc": utc_now(),
    }
    write_json(out / "selected-candidate-freeze.json", selected_freeze)
    sources = [
        CONFIG_PATH, CANDIDATES_PATH, USER_TEMPLATE, SYSTEM_FULL, SYSTEM_COMPACT, FULL_SCHEMA,
        COMPACT_SCHEMA, ROOT / "src/colluscope/m2_v2_contract.py",
        ROOT / "src/colluscope/m2_v2_reference.py", ROOT / "src/colluscope/m2_monitor.py",
        ROOT / "src/colluscope/m2_corpus.py", ROOT / "src/colluscope/gguf_tokenizer.py",
        ROOT / "src/colluscope/openai_compat_llamacpp.py",
        ROOT / "scripts/run_m2_v2.py", ROOT / "scripts/score_m2_v2.py",
        ROOT / "scripts/run_m1_100_extension.py", ROOT / "scripts/run_m2_monitor.py",
        ROOT / "scripts/diagnose_m2_v1_responses.py",
        ROOT / "scripts/local_llama_security.py", ROOT / "configs/m2-one-shot-splits.json",
        ROOT / "scripts/verify_m2_v2_preflight.py",
        ROOT / "scripts/run_m2_v2_repair.py", ROOT / "scripts/audit_m2_v2_preflight_results.py",
        ROOT / "scripts/plot_m2_v2_preflight.py",
        ROOT / "docs/M2_V2_PROTOCOL.md", ROOT / "docs/M2_V2_INTERFACE_DIAGNOSIS.md",
        ROOT / "docs/M2_V2_REPAIR_LOOP.md", ROOT / "docs/M2_V2_FAILURE_DIAGNOSTIC.md",
        ROOT / "tests/test_m2_v2_contract.py", ROOT / "tests/test_m2_v2_integration.py",
        ROOT / "tests/test_m2_v2_scoring.py", ROOT / "tests/test_m2_v2_runtime.py",
        ROOT / "tests/test_m2_v1_diagnosis.py", ROOT / "tests/test_m2_v2_preflight_verifier.py",
        ROOT / "tests/test_m2_v2_repair_runner.py",
        ROOT / "tests/test_m2_v2_preflight_results_audit.py",
        ROOT / ".gitignore",
    ]
    manifest = {
        "protocol_id": config["protocol_id"], "selected_candidate": selected_id,
        "prepared_at_utc": utc_now(), "frozen_git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_validation_sha256": file_sha256(out / "stage1/source-validation.json"),
        "preflight_manifest_sha256": file_sha256(out / "preflight-manifest.json"),
        "m2_v1_inventory_sha256": file_sha256(out / "stage1/m2-v1-inventory-verification.json"),
        "preflight_decision_sha256": file_sha256(out / "preflight-decision.json"),
        "selected_candidate_freeze_sha256": file_sha256(out / "selected-candidate-freeze.json"),
        "hashes": {str(path.relative_to(ROOT)): file_sha256(path) for path in sources},
        "run_artifact_hashes": {
            "private/evaluation-plan.json": file_sha256(out / "private/evaluation-plan.json"),
            "private/reference-labels.jsonl": file_sha256(out / "private/reference-labels.jsonl"),
            "private/evidence-projections.jsonl": file_sha256(out / "private/evidence-projections.jsonl"),
            "private/formal-case-map.json": file_sha256(out / "private/formal-case-map.json"),
            "stage1/source-validation.json": file_sha256(out / "stage1/source-validation.json"),
            "stage1/m2-v1-inventory-verification.json": file_sha256(
                out / "stage1/m2-v1-inventory-verification.json"),
        },
        "request_index": {r["request_id"]: r["payload_sha256"] for r in requests_by_digest.values()},
        "logical_evaluation_count": len(evaluations),
        "unique_payload_count": len(requests_by_digest), "deduplicated_evaluations":
            len(evaluations) - len(requests_by_digest),
        "formal_logical_cap": MAX_LOGICAL, "formal_http_attempt_cap": MAX_HTTP,
        "preparation_model_calls": 0,
    }
    write_json(out / "preparation-manifest.json", manifest)
    write_json(out / "environment.json", {
        "python": sys.version, "platform": platform.platform(), "captured_at_utc": utc_now(),
        "protocol_id": config["protocol_id"], "authorization_id": AUTHORIZATION_ID,
        "model_path": config["model_path"], "model_sha256": MODEL_SHA,
        "server_path": config["server_path"], "server_sha256": SERVER_SHA,
        "runtime_bundle_sha256": BUNDLE_SHA, "tokenizer_sha256": TOKENIZER_SHA,
        "chat_template_sha256": TEMPLATE_SHA, "endpoint": config["endpoint"],
        "sampling": {"temperature": config["temperature"], "top_p": config["top_p"],
                     "top_k": config["top_k"], "min_p": config["min_p"],
                     "sampler_chain": config["sampler_chain"]},
        "input_token_cap": config["input_token_cap"], "output_token_cap": config["output_token_cap"],
        "context_length": config["context_length"], "offline": True,
        "third_party_fallback": False, "api_spend_usd": 0.0,
    })
    return manifest


def _formal_states(out: Path) -> tuple[dict[str, dict[str, Any]], int]:
    states: dict[str, dict[str, Any]] = {}
    total = 0
    for event in read_jsonl(out / "requests-ledger.jsonl"):
        rid = event.get("request_id")
        if not isinstance(rid, str):
            raise ValueError("formal request ledger row has no request_id")
        state = states.setdefault(rid, {"attempts": 0, "terminal": None,
                                        "response": None, "last_retryable": False})
        if event.get("event") == "attempt_started":
            state["attempts"] += 1
            total += 1
        elif event.get("event") in {"response_returned", "response_file_recovered", "request_terminal",
                                    "request_failed", "request_interrupted"}:
            state["terminal"] = event.get("status")
            if event.get("event") in {"response_returned", "response_file_recovered"}:
                state["response"] = event
        elif event.get("event") == "attempt_failed":
            state["last_retryable"] = event.get("retryable") is True
    return states, total


def _load_formal_response(out: Path, request: dict[str, Any]) -> dict[str, Any] | None:
    path = out / "responses/formal" / f"{request['request_id']}.json"
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    raw_bytes = value.get("raw_response_body", "").encode("utf-8")
    if (value.get("payload_sha256") != request["payload_sha256"] or
            hashlib.sha256(raw_bytes).hexdigest() != value.get("raw_response_body_sha256") or
            hashlib.sha256(value.get("raw_assistant_text", "").encode("utf-8")).hexdigest() !=
            value.get("raw_assistant_text_sha256")):
        raise ValueError(f"formal response integrity failure: {request['request_id']}")
    config, _ = load_settings()
    try:
        decoded = _decode_openai_body(raw_bytes, config["model_id"])
        normalized, envelope, status, error = _validate_response(
            decoded["assistant_text"], decoded["finish_reason"], set(request["visible_event_ids"]),
            request["view_name"], request["permission_profile"], request["compact"], decoded["usage"])
    except Exception as exc:
        if "model identity" in str(exc):
            raise ValueError(f"formal response model identity mismatch: {request['request_id']}") from exc
        decoded = {"assistant_text": "", "finish_reason": None}
        normalized, envelope, status = None, None, "invalid_output"
        error = f"response_contract_error:{type(exc).__name__}:{exc}"
    if (decoded["assistant_text"] != value.get("raw_assistant_text") or
            decoded["finish_reason"] != value.get("finish_reason") or
            status != value.get("validation_status") or normalized != value.get("parsed") or
            envelope != value.get("reasoning_envelope") or error != value.get("validation_error")):
        raise ValueError(f"formal response recovery differs from independent raw validation: {request['request_id']}")
    return value


def _terminal_evaluations(out: Path, request: dict[str, Any], status: str,
                          response_sha256: str | None = None) -> None:
    terminal_ids = {row.get("eval_id") for row in read_jsonl(out / "evaluation-ledger.jsonl")
                    if row.get("event") == "evaluation_terminal"}
    for eval_id in request["evaluation_ids"]:
        if eval_id in terminal_ids:
            continue
        append_jsonl(out / "evaluation-ledger.jsonl", {
            "event": "evaluation_terminal", "eval_id": eval_id,
            "request_id": request["request_id"], "status": status,
            "response_sha256": response_sha256, "at_utc": utc_now(),
        })


def _assert_formal_freeze(out: Path, phase: str) -> dict[str, Any]:
    manifest_path = out / "preparation-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("formal preparation manifest is required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    config, _ = load_settings()
    for relative, expected in manifest["hashes"].items():
        path = ROOT / relative
        if file_sha256(path) != expected:
            raise ValueError(f"frozen M2-V2 source artifact changed: {relative}")
    if file_sha256(out / "preflight-decision.json") != manifest["preflight_decision_sha256"]:
        raise ValueError("preflight decision changed after selected-candidate freeze")
    for relative, expected in manifest["run_artifact_hashes"].items():
        if file_sha256(out / relative) != expected:
            raise ValueError(f"prepared run artifact changed after freeze: {relative}")
    plan = json.loads((out / "private/evaluation-plan.json").read_text(encoding="utf-8"))
    if plan.get("logical_evaluation_count") != MAX_LOGICAL or len(plan.get("logical_evaluations", [])) != MAX_LOGICAL:
        raise ValueError("frozen schedule is not exactly 1,000 logical evaluations")
    request_paths = sorted((out / "requests/formal").glob("*.json"))
    if len(request_paths) != manifest["unique_payload_count"]:
        raise ValueError("frozen formal request count changed after preparation")
    for path in request_paths:
        row = json.loads(path.read_text(encoding="utf-8"))
        if hashlib.sha256(row["payload_json"].encode("utf-8")).hexdigest() != row["payload_sha256"]:
            raise ValueError(f"frozen request body hash mismatch: {path.name}")
        if manifest["request_index"].get(row["request_id"]) != row["payload_sha256"]:
            raise ValueError(f"request absent from formal manifest index: {path.name}")
    if phase == "held_out":
        gate_path = out / "calibration-freeze.json"
        if not gate_path.exists():
            raise PermissionError("F2/F3 is locked until the F1 validity gate is met")
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if (gate.get("status") != "CALIBRATION_GO" or
                gate.get("f1_validity") < config["f1_calibration_validity_threshold"] or
                gate.get("heldout_predictions_before_gate") != 0):
            raise PermissionError("calibration decision is not a valid held-out release gate")
    return manifest


def _eligible_requests(out: Path, phase: str) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    allowed = {"calibration": {"F0", "F1"}, "held_out": {"F2", "F3"}}[phase]
    plan = json.loads((out / "private/evaluation-plan.json").read_text(encoding="utf-8"))
    evals = [row for row in plan["logical_evaluations"] if row["partition"] in allowed]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in evals:
        grouped.setdefault(row["request_id"], []).append(row)
    requests = []
    for request_id in grouped:
        path = out / "requests/formal" / f"{request_id}.json"
        requests.append(json.loads(path.read_text(encoding="utf-8")))
    return requests, grouped


def execute_formal_phase(out: Path, phase: str, *, resume: bool = False) -> dict[str, Any]:
    manifest = _assert_formal_freeze(out, phase)
    evaluation_ledger = out / "evaluation-ledger.jsonl"
    request_ledger = out / "requests-ledger.jsonl"
    if not resume and (evaluation_ledger.exists() or request_ledger.exists()):
        raise FileExistsError("M2-V2 formal requests already started; pass --resume to continue")
    requests, grouped = _eligible_requests(out, phase)
    expected_evals = 500
    if sum(map(len, grouped.values())) != expected_evals:
        raise ValueError(f"{phase} phase should contain 500 logical evaluations")
    states, attempts_total = _formal_states(out)
    if attempts_total > MAX_HTTP:
        raise RuntimeError("formal HTTP-attempt hard cap has already been exceeded")
    terminal_evals = {row.get("eval_id") for row in read_jsonl(evaluation_ledger)
                      if row.get("event") == "evaluation_terminal"}
    all_done = True
    pending_requests = []
    for request in requests:
        if set(request["evaluation_ids"]) <= terminal_evals:
            continue
        response = _load_formal_response(out, request)
        state = states.get(request["request_id"], {"attempts": 0, "terminal": None,
                                                   "response": None, "last_retryable": False})
        if response is not None:
            status = response["validation_status"]
            if state.get("response") is None:
                append_jsonl(request_ledger, {"event": "response_file_recovered",
                    "request_id": request["request_id"], "status": status,
                    "response_sha256": response["raw_response_body_sha256"],
                    "at_utc": utc_now(), "recovered_without_replaying": True})
                states[request["request_id"]] = {
                    **state, "terminal": status, "response": {"status": status},
                }
            _terminal_evaluations(out, request, status, response["raw_response_body_sha256"])
            continue
        if state["terminal"] is not None:
            _terminal_evaluations(out, request, state["terminal"])
            continue
        if state["attempts"] > 0 and not (state["last_retryable"] and state["attempts"] < 2):
            append_jsonl(request_ledger, {"event": "request_interrupted", "request_id": request["request_id"],
                "status": "indeterminate_interrupted_not_replayed", "attempts_already_reserved": state["attempts"],
                "at_utc": utc_now()})
            _terminal_evaluations(out, request, "indeterminate_interrupted_not_replayed")
            continue
        pending_requests.append(request)
        all_done = False
    if not pending_requests:
        return {"phase": phase, "status": "NO_PENDING_REQUESTS", "attempts_total": attempts_total}
    if len({row["request_id"] for row in requests}) > MAX_LOGICAL:
        raise RuntimeError("formal unique-payload ceiling exceeded")
    config, registry = load_settings()
    source_server = Path(config["server_path"])
    if file_sha256(source_server) != SERVER_SHA or file_sha256(Path(config["model_path"])) != MODEL_SHA:
        raise RuntimeError("model or server identity changed before formal phase")
    server_state = None
    hard_error = None
    valid_count = 0
    invalid_count = 0
    failed_count = 0
    try:
        server_state = _start_server(out, config, f"formal-{phase}")
        _, process, api_key, _, launch_dir, _, _, _ = server_state
        for request in pending_requests:
            request_id = request["request_id"]
            if request["preparation_status"] != "prepared":
                append_jsonl(request_ledger, {"event": "request_failed", "request_id": request_id,
                    "status": "not_sent_input_over_budget", "attempts": 0, "at_utc": utc_now()})
                _terminal_evaluations(out, request, "not_sent_input_over_budget")
                failed_count += len(request["evaluation_ids"])
                continue
            payload_bytes = request["payload_json"].encode("utf-8")
            if (hashlib.sha256(payload_bytes).hexdigest() != request["payload_sha256"] or
                    json.loads(payload_bytes) != request["payload"]):
                raise ValueError(f"request payload/hash mismatch before dispatch: {request_id}")
            if attempts_total >= MAX_HTTP:
                raise RuntimeError("formal hard HTTP-attempt cap reached")
            if process.poll() is not None or _process_image(process.pid).casefold() != \
                    str(source_server.resolve()).casefold():
                raise PermissionError("server process identity changed during formal evaluation")
            rows = grouped[request_id]
            for row in rows:
                append_jsonl(evaluation_ledger, {"event": "evaluation_started",
                    "eval_id": row["eval_id"], "request_id": request_id,
                    "phase": phase, "at_utc": utc_now()})
            state = states.get(request_id, {"attempts": 0, "last_retryable": False})
            first = state.get("attempts", 0) + 1
            final_record = None
            for attempt in range(first, 3):
                if attempts_total >= MAX_HTTP:
                    raise RuntimeError("formal physical attempt cap reached")
                append_jsonl(request_ledger, {"event": "attempt_started", "request_id": request_id,
                    "attempt": attempt, "payload_sha256": request["payload_sha256"],
                    "phase": phase, "at_utc": utc_now()})
                attempts_total += 1
                started = time.perf_counter()
                try:
                    status, raw_body = _post_local(request["payload_json"], api_key,
                                                  int(config["timeout_seconds"]))
                except (TimeoutError, urllib.error.URLError, OSError) as exc:
                    retryable = attempt < 2
                    append_jsonl(request_ledger, {"event": "attempt_failed", "request_id": request_id,
                        "attempt": attempt, "status": type(exc).__name__, "error": str(exc),
                        "retryable": retryable, "at_utc": utc_now()})
                    if retryable:
                        continue
                    append_jsonl(request_ledger, {"event": "request_failed", "request_id": request_id,
                        "status": "transport_failed_after_retry", "attempts": attempt, "at_utc": utc_now()})
                    final_record = {"validation_status": "transport_failed_after_retry"}
                    break
                latency = time.perf_counter() - started
                if status in {401, 403}:
                    error_body = raw_body.decode("utf-8", errors="replace")
                    write_json(launch_dir / f"auth-error-{request_id}.json", {
                        "http_status": status, "error_body": error_body,
                        "error_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                        "request_id": request_id, "at_utc": utc_now()})
                    raise PermissionError(f"local llama.cpp auth failure HTTP {status}; stopping inference")
                if status != 200:
                    retryable = status in {408, 429} or 500 <= status <= 599
                    write_json(out / "responses/formal" / f"{request_id}.http-{attempt}.json", {
                        "request_id": request_id, "attempt": attempt, "payload_sha256": request["payload_sha256"],
                        "http_status": status, "raw_error_body": raw_body.decode("utf-8", errors="replace"),
                        "raw_error_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                        "latency_seconds": latency, "at_utc": utc_now()})
                    if retryable and attempt < 2:
                        append_jsonl(request_ledger, {"event": "attempt_failed", "request_id": request_id,
                            "attempt": attempt, "status": f"http_{status}", "retryable": True, "at_utc": utc_now()})
                        continue
                    terminal = f"http_error_{status}"
                    append_jsonl(request_ledger, {"event": "request_failed", "request_id": request_id,
                        "status": terminal, "attempts": attempt, "at_utc": utc_now()})
                    final_record = {"validation_status": terminal}
                    break
                raw_text_body = raw_body.decode("utf-8", errors="replace")
                try:
                    decoded = _decode_openai_body(raw_body, config["model_id"])
                    normalized, envelope, validation_status, validation_error = _validate_response(
                        decoded["assistant_text"], decoded["finish_reason"],
                        set(request["visible_event_ids"]), request["view_name"],
                        request["permission_profile"], request["compact"],
                        decoded["usage"])
                    model_identity_error = None
                except Exception as exc:
                    decoded = {"assistant_text": "", "finish_reason": None, "usage": None,
                               "model": None, "response_metadata": {}}
                    normalized, envelope, validation_status = None, None, "invalid_output"
                    validation_error = f"response_contract_error:{type(exc).__name__}:{exc}"
                    model_identity_error = ("response model identity missing or mismatched"
                                             if "model identity" in str(exc) else None)
                response_record = {
                    "request_id": request_id, "phase": phase,
                    "payload_sha256": request["payload_sha256"],
                    "raw_response_body": raw_text_body,
                    "raw_response_body_sha256": hashlib.sha256(raw_body).hexdigest(),
                    "raw_assistant_text": decoded["assistant_text"],
                    "raw_assistant_text_sha256": hashlib.sha256(
                        decoded["assistant_text"].encode("utf-8")).hexdigest(),
                    "parsed": normalized, "reasoning_envelope": envelope,
                    "validation_status": validation_status, "validation_error": validation_error,
                    "finish_reason": decoded["finish_reason"], "usage": decoded["usage"],
                    "model": decoded["model"], "response_metadata": decoded["response_metadata"],
                    "latency_seconds": latency, "attempt": attempt, "returned_at_utc": utc_now(),
                }
                write_json(out / "responses/formal" / f"{request_id}.json", response_record)
                append_jsonl(request_ledger, {"event": "response_returned", "request_id": request_id,
                    "phase": phase, "attempt": attempt, "status": validation_status,
                    "response_sha256": response_record["raw_response_body_sha256"],
                    "latency_seconds": latency, "usage": decoded["usage"], "at_utc": utc_now()})
                append_jsonl(request_ledger, {"event": "request_failed" if model_identity_error else "request_terminal",
                    "request_id": request_id,
                    "status": "model_identity_mismatch" if model_identity_error else validation_status,
                    "attempts": attempt, "at_utc": utc_now()})
                final_record = response_record
                if model_identity_error:
                    raise PermissionError("model identity mismatch in HTTP response; stopping inference")
                break
            if final_record is None:
                append_jsonl(request_ledger, {"event": "request_failed", "request_id": request_id,
                    "status": "transport_failure", "attempts": attempts_total, "at_utc": utc_now()})
                status_result = "transport_failure"
            else:
                status_result = final_record.get("validation_status", "transport_failure")
            _terminal_evaluations(out, request, status_result,
                                  final_record.get("raw_response_body_sha256")
                                  if final_record else None)
            if status_result == "valid":
                valid_count += len(request["evaluation_ids"])
            elif status_result == "invalid_output":
                invalid_count += len(request["evaluation_ids"])
            else:
                failed_count += len(request["evaluation_ids"])
        summary = {"phase": phase, "status": "PHASE_TERMINAL", "attempts_total": attempts_total,
                   "valid_logical_evaluations": valid_count, "invalid_logical_evaluations": invalid_count,
                   "failed_logical_evaluations": failed_count,
                   "finished_at_utc": utc_now(), "preparation_manifest_sha256": file_sha256(
                       out / "preparation-manifest.json")}
        write_json(out / f"{phase}-phase-summary.json", summary)
        return summary
    except Exception as exc:
        hard_error = {"phase": phase, "error_type": type(exc).__name__,
                      "error": str(exc), "at_utc": utc_now(),
                      "attempts_total": attempts_total}
        write_json(out / f"{phase}-phase-error.json", hard_error)
        raise
    finally:
        if server_state is not None:
            _stop_server(server_state)
