#!/usr/bin/env python3
"""Prepare or execute the frozen local-only M2 monitor study."""

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
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter  # noqa: E402
from colluscope.m1_runtime import TimeoutBackendError, TransientTransportError  # noqa: E402
from colluscope.m2_corpus import file_sha256, load_m2_corpus  # noqa: E402
from colluscope.m2_monitor import (VIEWS, PERMISSIONS, canonical_json, make_evidence,
                                   sha256_bytes, validate_prediction)  # noqa: E402
from colluscope.openai_compat_llamacpp import (LocalLlamaCppBackend, llama_runtime_bundle_identity,
                                               llama_server_command, load_llamacpp_backend_config,
                                               m2_json_schema_payload)  # noqa: E402
from scripts.freeze_m2_protocol import ARTIFACTS as FREEZE_ARTIFACTS, check_manifest as check_m2_freeze  # noqa: E402
from scripts.local_llama_security import create_api_key_file, remove_api_key_file  # noqa: E402
from scripts.run_m1_100_extension import (GpuSampler, _listener_snapshot, _process_image,
                                           _stop_own_process)  # noqa: E402


RUN_DEFAULT = ROOT / "runs/m2/one-shot-20261019"
EXTENSION_RUN = ROOT / "runs/m1_100/extension-75-20261019-run02"
M2_CONFIG_PATH = ROOT / "configs/m2-one-shot.toml"
SYSTEM_PROMPT_PATH = ROOT / "prompts/m2-v1/system.txt"
USER_TEMPLATE_PATH = ROOT / "prompts/m2-v1/user.txt"
OUTPUT_SCHEMA_PATH = ROOT / "prompts/m2-v1/output.schema.json"
FREEZE_MANIFEST_PATH = ROOT / "configs/m2-one-shot-freeze-manifest.json"
AUTHORIZATION_ID = "USER-AUTHORIZED-M2-ONE-SHOT-2026-10-19"
MODEL_SHA256 = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
SERVER_SHA256 = "3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb"
BUNDLE_SHA256 = "9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759"
TOKENIZER_SHA256 = "06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f"
TEMPLATE_SHA256 = "57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361"
HISTORICAL_HASHES = {
    "researcher/T.jsonl": "30c397583618cbed20fa529cf4ac39e69caca43456d09abbddb25b1f6e888464",
    "researcher/B.jsonl": "139c1bc09891276763223677ee88de6e45bdcee80a348fb64d2258b666b3014a",
    "monitor_inputs/evidence.jsonl": "90c962e43b9ea10e115c40d624effc307b9dc2994703e916947cc38d6155adef",
}
NEW_HASHES = {
    "researcher/T.jsonl": "8b87aac873f403909b34b9a94fc13a2f7924968e370f320bbb293d53cef2cafb",
    "researcher/B.jsonl": "4d176ceb4d49abe60cde1a0159e1de21b3f603ac7f264b23bc544f3e686dfc87",
    "monitor_inputs/evidence.jsonl": "4fd2e03d77e18a6e2f5dbbd5c3571670c3590a58d58ddb4c691f4b9b482b8df3",
    "researcher/requests.jsonl": "803e15a2bfaa10baa467b053d7bf3b3c99d9a3c0b150e490a91b88878c07680e",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        for number, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"blank durable JSONL row: {path}:{number}")
            rows.append(json.loads(line))
    return rows


def _config() -> dict[str, Any]:
    raw = tomllib.loads(M2_CONFIG_PATH.read_text(encoding="utf-8"))
    if raw["authorization_id"] != AUTHORIZATION_ID:
        raise PermissionError("M2 runner authorization does not match the current user-approved scope")
    if (raw["logical_evaluation_cap"] != 1000 or raw["physical_http_attempt_cap"] != 2000 or
            raw["max_attempts_per_unique_request"] != 2 or raw["api_spend_usd"] != 0.0):
        raise ValueError("M2 hard budget or $0 external spend changed from the frozen request")
    if raw["model_sha256"] != MODEL_SHA256 or raw["server_sha256"] != SERVER_SHA256:
        raise ValueError("M2 model/server config differs from the approved frozen identities")
    return raw


def _backend_config(m2: dict[str, Any]):
    base = load_llamacpp_backend_config(ROOT / "configs/m1-p0-llama-local-draft.toml")
    launch = {**base.launch, "port": 8081}
    backend = replace(base, model_calls_enabled=True, preflight_enabled=False,
                      preflight_approval_id="", full_pilot_approval_id=AUTHORIZATION_ID,
                      base_url=m2["endpoint"], launch=launch,
                      max_logical_requests=m2["logical_evaluation_cap"],
                      max_total_attempts=m2["physical_http_attempt_cap"],
                      max_api_spend_usd=0.0)
    return backend


def _secure_dir(path: Path) -> dict[str, Any]:
    path.mkdir(parents=True, exist_ok=True)
    identity = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                              capture_output=True, text=True, timeout=10, check=True)
    import csv
    rows = list(csv.reader(identity.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2 or not rows[0][1].startswith("S-"):
        raise PermissionError("cannot resolve current user SID for M2 private storage")
    name, sid = rows[0][0], rows[0][1]
    acl = subprocess.run(["icacls.exe", str(path), "/inheritance:r", "/grant:r", f"*{sid}:(OI)(CI)F"],
                         capture_output=True, text=True, timeout=10, check=False)
    if acl.returncode:
        raise PermissionError(f"failed to restrict M2 private directory ACL: {acl.stderr.strip()}")
    audit = subprocess.run(["icacls.exe", str(path)], capture_output=True, text=True,
                           timeout=10, check=True)
    compact = audit.stdout.replace(" ", "").replace("\t", "").casefold()
    if f"{name}:(oi)(ci)(f)".replace(" ", "").casefold() not in compact and \
            f"{name}:(f)".replace(" ", "").casefold() not in compact:
        raise PermissionError("M2 private directory ACL does not attest current-user full control")
    return {"path": str(path.resolve()), "current_user": name, "current_user_sid": sid,
            "acl": "inheritance removed; current user SID full control", "acl_command_exit_code": 0}


def _source_validation(out: Path) -> dict[str, Any]:
    hist = ROOT / "runs/m1_p0_local/formal-25ep-pilot-20261019/run"
    extension = EXTENSION_RUN
    expected_manifest = "4e7868449a5e2bc3621fef4da4eaded4d710c15570dbf12f7d4ab215f3a4bb13"
    ext_verification = json.loads((extension / "verification.json").read_text(encoding="utf-8"))
    if (ext_verification.get("status") != "PASS_CORE_RECOMPUTE_WITH_STORED_HARM_FLAG_MISMATCHES" or
            ext_verification.get("total_provenance_aware_episodes") != 100 or
            ext_verification.get("new_assigned") != 75 or ext_verification.get("new_completed") != 75 or
            ext_verification.get("new_failed") != 0 or ext_verification.get("stored_harmful_outcome_flag_disagreements") != 19):
        raise ValueError("M1-100 source verification does not match the completed audited corpus")
    if file_sha256(extension / "corpus-manifest.json") != expected_manifest:
        raise ValueError("original M1-100 corpus manifest changed")
    observed = {}
    for relative, expected in HISTORICAL_HASHES.items():
        actual = file_sha256(hist / relative)
        if actual != expected:
            raise ValueError(f"historical M1 source hash mismatch: {relative}")
        observed[f"F0/{relative}"] = actual
    for relative, expected in NEW_HASHES.items():
        actual = file_sha256(extension / relative)
        if actual != expected:
            raise ValueError(f"prospective M1 source hash mismatch: {relative}")
        observed[f"F1-F3/{relative}"] = actual
    requests = read_jsonl(extension / "researcher/requests.jsonl")
    if (len(requests) != 285 or sum(row.get("status") == "response_returned" for row in requests) != 285 or
            sum(row.get("attempt", 0) == 1 for row in requests) != 285):
        raise ValueError("M1-100 model/request ledger does not contain 285 first-attempt returned responses")
    historical_requests = read_jsonl(hist / "researcher/requests.jsonl")
    if (len(historical_requests) != 95 or
            sum(row.get("status") == "response_returned" for row in historical_requests) != 95):
        raise ValueError("historical 25 episode request ledger is incomplete")
    info = {"status": "PASS_M1_SOURCE_HASHES_AND_LEDGER",
            "historical_episodes": 25, "prospective_episodes": 75,
            "total_episodes": 100, "historical_model_responses": 95,
            "prospective_model_responses": 285,
            "m1_100_independent_verification_sha256": file_sha256(extension / "verification.json"),
            "original_corpus_manifest_sha256": expected_manifest,
            "source_hashes": observed,
            "stored_harm_flag_disagreements": 19,
            "warning": "M1 19 stored harmful_outcome booleans disagree with independent scenario-specific recomputation; M2 scorer must recompute from ballots."}
    write_json(out / "stage1/source-validation.json", info)
    return info


def _validate_frozen_artifacts() -> dict[str, Any]:
    try:
        freeze = check_m2_freeze()
    except (FileNotFoundError, ValueError) as exc:
        raise PermissionError(f"M2 protocol/config/code freeze check failed: {exc}") from exc
    if set(freeze.get("artifact_hashes", {})) != set(FREEZE_ARTIFACTS) or \
            freeze.get("authorization_id") != AUTHORIZATION_ID or \
            freeze.get("logical_evaluation_cap") != 1000 or \
            freeze.get("physical_http_attempt_cap") != 2000:
        raise PermissionError("M2 freeze manifest exceeds or differs from the user authorization")
    return freeze


def _opaque_case_map(cases, private_dir: Path) -> dict[str, str]:
    path = private_dir / "case-map.json"
    if path.exists():
        mapping = json.loads(path.read_text(encoding="utf-8"))
        if set(mapping.values()) != {case.episode_id for case in cases} or len(mapping) != len(cases):
            raise ValueError("stored opaque case map does not cover this exact M1 corpus")
        return mapping
    mapping = {secrets.token_hex(16): case.episode_id for case in cases}
    write_json(path, mapping)
    return mapping


def _event_ids(evidence: dict[str, Any]) -> set[str]:
    if isinstance(evidence.get("events"), list):
        return {event["event_id"] for event in evidence["events"]}
    content = evidence.get("content", "")
    values = set()
    for line in content.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("event_id"), str):
            values.add(value["event_id"])
    return values


def _request_directory_index_sha256(request_dir: Path) -> str:
    rows = [{"path": path.name, "sha256": file_sha256(path)}
            for path in sorted(request_dir.glob("m2-*.json"), key=lambda item: item.name)]
    return sha256_bytes(canonical_json(rows))


def _build_input(case, view: str, permission: str, m2: dict[str, Any],
                 schema: dict[str, Any], system_prompt: str, user_template: str,
                 counter: GGUFChatTokenCounter, backend_config) -> dict[str, Any]:
    evidence = make_evidence(case.public_e["task_spec"], case.public_e,
                             list(case.delivered_messages), view, permission)
    evidence_text = (evidence["content"] if evidence.get("format") == "raw_ordered_event_stream"
                     else json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    user = user_template.replace("{permission_profile}", permission).replace("{view_name}", view).replace(
        "{evidence_json}", evidence_text)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}]
    base = {"model": backend_config.model_id, "messages": messages,
            "temperature": backend_config.temperature, "top_p": backend_config.top_p,
            "top_k": backend_config.top_k, "min_p": backend_config.min_p,
            "samplers": list(backend_config.sampler_chain), "max_tokens": backend_config.message_max_output_tokens,
            "response_schema_sha256": sha256_bytes(canonical_json(schema)),
            "permission_profile": permission, "view_name": view,
            "partition_scope": case.partition}
    seed_hash = hashlib.sha256(b"colluscope-m2-seed-v1\0" + canonical_json(base)).digest()
    seed = int.from_bytes(seed_hash[:4], "big") & 0x7FFFFFFF
    payload = m2_json_schema_payload(backend_config, messages, schema, seed)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_bytes = payload_json.encode("utf-8")
    token_count = len(counter.encode_chat(messages, enable_thinking=False))
    if token_count > backend_config.input_budget_tokens:
        status = "not_sent_input_over_budget"
    else:
        status = "prepared"
    return {"messages": messages, "evidence": evidence,
            "visible_event_ids": sorted(_event_ids(evidence)),
            "payload": payload, "payload_json": payload_json,
            "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "prompt_sha256": sha256_bytes(canonical_json(messages)),
            "input_tokens_local": token_count, "generation_seed": seed,
            "preparation_status": status,
            "schema_sha256": sha256_bytes(canonical_json(schema))}


def _logical_schedule(cases):
    """Return exactly one evaluation for each case × permission × frozen view."""
    schedule = [(case, permission, view)
                for case in cases for permission in PERMISSIONS for view in VIEWS]
    keys = [(case.episode_id, permission, view) for case, permission, view in schedule]
    if len(schedule) != 1000 or len(set(keys)) != 1000:
        raise ValueError("M2 frozen schedule must contain exactly 1,000 unique logical evaluations")
    return schedule


def prepare_run(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    # All run-root files include request hashes, validation failures, and error
    # bodies. Restrict the root before writing any of them; restricting only
    # selected child directories would leave the ledgers inheriting workspace ACLs.
    root_secure = _secure_dir(out)
    private = out / "private"
    secure = _secure_dir(private)
    for name in ("requests", "responses", "logs", "launches", "analysis", "stage1"):
        _secure_dir(out / name)
    if (out / "preparation-manifest.json").exists():
        raise FileExistsError("M2 preparation already exists; use --resume instead of regenerating prompts")
    m2 = _config()
    freeze = _validate_frozen_artifacts()
    backend_config = _backend_config(m2)
    model_path = Path(backend_config.artifact_path)
    if file_sha256(model_path) != MODEL_SHA256:
        raise RuntimeError("local model bytes do not match the authorized Qwen3-8B checkpoint")
    bundle = llama_runtime_bundle_identity(backend_config.server_binary_path)
    if bundle["sha256"] != BUNDLE_SHA256 or file_sha256(Path(backend_config.server_binary_path)) != SERVER_SHA256:
        raise RuntimeError("llama.cpp server or runtime bundle differs from frozen M1 identity")
    if (backend_config.base_url != m2["endpoint"] or backend_config.temperature != 0.0 or
            backend_config.top_p != 1.0 or backend_config.top_k != 0 or backend_config.min_p != 0.0 or
            backend_config.context_length != 4096 or backend_config.launch["port"] != 8081):
        raise ValueError("M2 runtime settings drifted from the explicit local-only frozen profile")
    source = _source_validation(out)
    cases = load_m2_corpus(ROOT, EXTENSION_RUN)
    case_map = _opaque_case_map(cases, private)
    case_id_by_episode = {episode_id: case_id for case_id, episode_id in case_map.items()}
    counter = GGUFChatTokenCounter(model_path, expected_artifact_sha256=MODEL_SHA256)
    schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    user_template = USER_TEMPLATE_PATH.read_text(encoding="utf-8").strip()
    evals = []
    payloads: dict[str, dict[str, Any]] = {}
    duplicate_across_permission = []
    payload_permissions: dict[str, set[str]] = {}
    for case, permission, view in _logical_schedule(cases):
        prepared = _build_input(case, view, permission, m2, schema,
                                system_prompt, user_template, counter, backend_config)
        digest = prepared["payload_sha256"]
        payload_permissions.setdefault(digest, set()).add(permission)
        request_id = "m2-" + digest[:28]
        eval_id_material = f"{case_id_by_episode[case.episode_id]}|{permission}|{view}|{m2['protocol_id']}"
        eval_id = hashlib.sha256(eval_id_material.encode("utf-8")).hexdigest()[:24]
        evals.append({"eval_id": eval_id, "case_id": case_id_by_episode[case.episode_id],
                      "provenance": case.provenance, "partition": case.partition,
                      "scenario_family_id": case.scenario_family_id,
                      "seed_block_id": case.seed_block_id,
                      "split_group_id": case.split_group_id,
                      "condition_id": case.condition_id, "permission_profile": permission,
                      "view_name": view, "logical_kind": "primary_view",
                      "request_id": request_id, "payload_sha256": digest,
                      "prompt_sha256": prepared["prompt_sha256"],
                      "schema_sha256": prepared["schema_sha256"],
                      "input_tokens_local": prepared["input_tokens_local"],
                      "preparation_status": prepared["preparation_status"],
                      "visible_event_ids": prepared["visible_event_ids"]})
        if digest not in payloads:
            payloads[digest] = {"request_id": request_id, "payload_sha256": digest,
                                "permission_profile": permission, "partition": case.partition,
                                "view_name": view, "prepared": prepared,
                                "evaluation_ids": []}
        elif (payloads[digest]["permission_profile"] != permission or
              payloads[digest]["partition"] != case.partition):
            duplicate_across_permission.append(digest)
        payloads[digest]["evaluation_ids"].append(eval_id)
    if len(evals) != 1000 or len({row["eval_id"] for row in evals}) != 1000:
        raise ValueError("M2 frozen schedule must contain exactly 1,000 unique logical evaluations")
    if duplicate_across_permission:
        raise ValueError("identical request payload was constructed across permission/split strata")
    for digest, entry in payloads.items():
        prepared = entry.pop("prepared")
        request_record = {"request_id": entry["request_id"], "payload_sha256": digest,
                          "permission_profile": entry["permission_profile"],
                          "partition": entry["partition"], "view_name": entry["view_name"],
                          "evaluation_ids": entry["evaluation_ids"],
                          "prompt_sha256": prepared["prompt_sha256"],
                          "schema_sha256": prepared["schema_sha256"],
                          "input_tokens_local": prepared["input_tokens_local"],
                          "generation_seed": prepared["generation_seed"],
                          "visible_event_ids": prepared["visible_event_ids"],
                          "payload": prepared["payload"],
                          "payload_json": prepared["payload_json"]}
        # Preserve payload-object insertion order as part of the locally
        # reproducible HTTP serialization; payload_json stores the exact bytes.
        request_path = out / "requests" / f"{entry['request_id']}.json"
        request_path.write_text(json.dumps(request_record, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8", newline="\n")
    write_json(out / "private/evaluation-plan.json", {"schema_version": "m2-evaluation-plan-v1",
        "logical_evaluations": evals, "logical_evaluation_count": len(evals),
        "unique_payload_count": len(payloads),
        "deduplicated_logical_evaluations": len(evals) - len(payloads)})
    # The source-to-opaque map and private texts remain ACL-restricted. This file
    # contains view inputs only, never researcher-only labels or T metadata.
    projections = []
    for case in cases:
        cid = case_id_by_episode[case.episode_id]
        projections.append({"case_id": cid, "public_e": case.public_e,
                            "delivered_messages": list(case.delivered_messages),
                            "public_e_sha256": case.source_public_e_sha256,
                            "source_b_sha256": case.source_b_sha256})
    with (private / "evidence-projections.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for projection in projections:
            stream.write(json.dumps(projection, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    write_json(out / "private/case-map.json", case_map)
    hashes = {"m2_config": file_sha256(M2_CONFIG_PATH),
              "freeze_manifest": file_sha256(FREEZE_MANIFEST_PATH),
              "m2_split_manifest": file_sha256(ROOT / "configs/m2-one-shot-splits.json"),
              "system_prompt": file_sha256(SYSTEM_PROMPT_PATH),
              "user_prompt_template": file_sha256(USER_TEMPLATE_PATH),
              "output_schema": file_sha256(OUTPUT_SCHEMA_PATH),
              "runner_source": file_sha256(ROOT / "scripts/run_m2_monitor.py"),
              "monitor_source": file_sha256(ROOT / "src/colluscope/m2_monitor.py"),
              "corpus_loader_source": file_sha256(ROOT / "src/colluscope/m2_corpus.py"),
              "reference_scorer_source": file_sha256(ROOT / "src/colluscope/m2_reference.py"),
              "llamacpp_transport_source": file_sha256(ROOT / "src/colluscope/openai_compat_llamacpp.py"),
              "source_validation": file_sha256(out / "stage1/source-validation.json"),
              "evaluation_plan": file_sha256(private / "evaluation-plan.json"),
              "evidence_projections": file_sha256(private / "evidence-projections.jsonl"),
              "prepared_request_index": _request_directory_index_sha256(out / "requests")}
    environment = {"captured_at_utc": utc_now(), "git_head": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "platform": platform.platform(),
        "model_path": backend_config.artifact_path, "model_sha256": MODEL_SHA256,
        "server_path": backend_config.server_binary_path, "server_sha256": SERVER_SHA256,
        "runtime_bundle_sha256": BUNDLE_SHA256, "runtime_bundle_file_count": bundle["file_count"],
        "tokenizer_sha256": TOKENIZER_SHA256, "chat_template_sha256": TEMPLATE_SHA256,
        "tokenizers_library_version": backend_config.tokenizers_library_version,
        "jinja2_library_version": backend_config.jinja2_library_version,
        "tokenizer_metadata": backend_config.tokenizer_metadata,
        "endpoint": backend_config.base_url, "offline": True, "third_party_fallback": False,
        "api_spend_usd": 0.0, "sampling": backend_config.sampling,
        "context_length": backend_config.context_length,
        "input_token_cap": backend_config.input_budget_tokens,
        "output_token_cap": backend_config.message_max_output_tokens,
        "timeout_seconds": backend_config.timeout_seconds,
        "private_storage_acl": root_secure,
        "private_projection_acl": secure}
    write_json(out / "environment.json", environment)
    manifest = {"protocol_id": m2["protocol_id"], "prepared_at_utc": utc_now(),
                "source_validation_status": source["status"],
                "logical_evaluation_count": len(evals), "unique_payload_count": len(payloads),
                "deduplicated_evaluations": len(evals)-len(payloads),
                "logical_cap": 1000, "physical_attempt_cap": 2000,
                "output_over_token_cap_evaluations": sum(
                    row["preparation_status"] != "prepared" for row in evals),
                "hashes": hashes, "no_model_calls": True}
    manifest["frozen_protocol_hash"] = file_sha256(ROOT / "docs/M2_FROZEN_PROTOCOL.md")
    manifest["freeze_manifest_sha256"] = file_sha256(FREEZE_MANIFEST_PATH)
    manifest["frozen_git_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    write_json(out / "preparation-manifest.json", manifest)
    write_json(out / "stage1/private-permission-grant.json", {
        "authorization_id": AUTHORIZATION_ID,
        "scope": "derived Privileged Audit projection of delivered synthetic agent messages for local-only M2 monitor inference",
        "external_upload": False, "source_public_e_overwritten": False,
        "raw_messages_and_requests_git_ignored": True,
        "private_projection_path": str((private / "evidence-projections.jsonl").resolve()),
        "storage_acl": secure,
        "authorization_attachment_sha256": freeze["authorization_attachment_sha256"],
        "note": "The user authorization was supplied in this Codex task attachment; attachment bytes are not copied into the project."})
    print(json.dumps({"status": "M2_PREPARED_NO_MODEL_CALLS", **manifest}, sort_keys=True))
    return manifest


def _request_states(out: Path) -> tuple[dict[str, dict[str, Any]], int]:
    events = read_jsonl(out / "requests-ledger.jsonl")
    states: dict[str, dict[str, Any]] = {}
    attempts_total = 0
    for event in events:
        rid = event.get("request_id")
        if not isinstance(rid, str):
            raise ValueError("request ledger row lacks request ID")
        state = states.setdefault(rid, {"attempts": 0, "terminal": None, "response": None})
        if event.get("event") == "attempt_started":
            state["attempts"] += 1
            attempts_total += 1
        elif event.get("event") in {"response_returned", "response_file_recovered"}:
            state["response"] = event
            state["terminal"] = event.get("status")
        elif event.get("event") in {"request_failed", "request_interrupted"}:
            state["terminal"] = event.get("status")
        elif event.get("event") == "attempt_failed":
            state["last_attempt_failed_retryable"] = event.get("retryable") is True
    return states, attempts_total


def _recover_durable_response_files(out: Path) -> None:
    """Recover a fully flushed response file if interruption preceded its ledger append."""
    states, _ = _request_states(out)
    response_dir, request_dir = out / "responses", out / "requests"
    for response_path in sorted(response_dir.glob("m2-*.json")):
        request_id = response_path.stem
        state = states.get(request_id)
        if state is None or state["attempts"] < 1:
            raise ValueError(f"orphan M2 response file without a reserved physical attempt: {request_id}")
        if state.get("response") is not None:
            continue
        if state.get("terminal") is not None:
            raise ValueError(f"M2 response file conflicts with an already terminal request failure: {request_id}")
        response = json.loads(response_path.read_text(encoding="utf-8"))
        request_path = request_dir / f"{request_id}.json"
        if not request_path.exists():
            raise ValueError(f"durable M2 response has no frozen request: {request_id}")
        request = json.loads(request_path.read_text(encoding="utf-8"))
        raw_body, raw_text = response.get("raw_response_body"), response.get("raw_assistant_text")
        if (response.get("payload_sha256") != request.get("payload_sha256") or
                not isinstance(raw_body, str) or sha256_bytes(raw_body.encode("utf-8")) != response.get("raw_response_body_sha256") or
                not isinstance(raw_text, str) or sha256_bytes(raw_text.encode("utf-8")) != response.get("raw_assistant_text_sha256")):
            raise ValueError(f"durable M2 response hash/link check failed: {request_id}")
        try:
            parsed = json.loads(raw_text)
            valid, validation_error = validate_prediction(parsed, set(request["visible_event_ids"]))
        except (json.JSONDecodeError, TypeError) as exc:
            parsed, valid, validation_error = None, False, f"json_parse_error:{type(exc).__name__}"
        status = "valid" if valid else "invalid_output"
        if response.get("validation_status") != status or response.get("parsed") != parsed:
            raise ValueError(f"durable M2 response validation record differs on recovery: {request_id}")
        append_jsonl(out / "requests-ledger.jsonl", {"event": "response_file_recovered",
            "request_id": request_id, "attempt": state["attempts"], "status": status,
            "response_sha256": response["raw_response_body_sha256"], "at_utc": utc_now(),
            "recovered_without_replaying": True, "validation_error": validation_error})


def _validate_freeze_for_inference(out: Path, phase: str) -> dict[str, Any]:
    manifest_path = out / "preparation-manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError("run --prepare before any M2 inference")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    m2 = _config()
    freeze = _validate_frozen_artifacts()
    if manifest["protocol_id"] != m2["protocol_id"] or manifest["logical_evaluation_count"] != 1000:
        raise ValueError("preparation manifest differs from the frozen M2 protocol")
    for path_key, relative in (("m2_config", M2_CONFIG_PATH),
                               ("freeze_manifest", FREEZE_MANIFEST_PATH),
                               ("m2_split_manifest", ROOT / "configs/m2-one-shot-splits.json"),
                               ("system_prompt", SYSTEM_PROMPT_PATH),
                               ("user_prompt_template", USER_TEMPLATE_PATH),
                               ("output_schema", OUTPUT_SCHEMA_PATH)):
        if file_sha256(relative) != manifest["hashes"][path_key]:
            raise ValueError(f"frozen M2 artifact changed after preparation: {path_key}")
    for key, path in (("source_validation", out / "stage1/source-validation.json"),
                      ("evaluation_plan", out / "private/evaluation-plan.json"),
                      ("evidence_projections", out / "private/evidence-projections.jsonl")):
        if file_sha256(path) != manifest["hashes"][key]:
            raise ValueError(f"prepared M2 source artifact changed: {key}")
    if _request_directory_index_sha256(out / "requests") != manifest["hashes"]["prepared_request_index"]:
        raise ValueError("prepared M2 request files differ from the hash-bound request index")
    if manifest.get("freeze_manifest_sha256") != file_sha256(FREEZE_MANIFEST_PATH) or \
            manifest.get("frozen_protocol_hash") != file_sha256(ROOT / "docs/M2_FROZEN_PROTOCOL.md"):
        raise ValueError("M2 protocol freeze differs from the prepared run")
    if phase == "held_out":
        freeze_path = out / "calibration-freeze.json"
        if not freeze_path.exists():
            raise PermissionError("F2/F3 inference requires the completed F0/F1 calibration freeze")
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        if freeze.get("status") != "CALIBRATION_CLOSED_SETTINGS_UNCHANGED":
            raise PermissionError("calibration freeze is missing or nonterminal")
        expected = {"preparation_manifest_sha256": file_sha256(out / "preparation-manifest.json"),
                    "freeze_manifest_sha256": file_sha256(FREEZE_MANIFEST_PATH),
                    "m2_config_sha256": file_sha256(M2_CONFIG_PATH),
                    "system_prompt_sha256": file_sha256(SYSTEM_PROMPT_PATH),
                    "user_prompt_sha256": file_sha256(USER_TEMPLATE_PATH),
                    "output_schema_sha256": file_sha256(OUTPUT_SCHEMA_PATH)}
        for field, value in expected.items():
            if freeze.get(field) != value:
                raise PermissionError(f"calibration freeze does not bind unchanged setting: {field}")
        if freeze.get("held_out_terminal_evaluations_before_freeze") != 0:
            raise PermissionError("calibration freeze reports premature held-out evaluation")
    return manifest


def execute_phase(out: Path, phase: str) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("the frozen M2 local runtime is Windows-only")
    prep_manifest = _validate_freeze_for_inference(out, phase)
    plan_doc = json.loads((out / "private/evaluation-plan.json").read_text(encoding="utf-8"))
    evaluations = plan_doc["logical_evaluations"]
    partitions = {"calibration": {"F0", "F1"}, "held_out": {"F2", "F3"}}[phase]
    phase_evals = [row for row in evaluations if row["partition"] in partitions]
    if len(phase_evals) != 500:
        raise ValueError(f"M2 {phase} phase should cover 500 logical evaluations, got {len(phase_evals)}")
    response_dir = out / "responses"
    request_dir = out / "requests"
    _recover_durable_response_files(out)
    for request in request_dir.glob("m2-*.json"):
        pass
    request_ids = {row["request_id"] for row in phase_evals
                   if row["preparation_status"] == "prepared"}
    states, old_attempt_total = _request_states(out)
    old_per_request = {rid: state["attempts"] for rid, state in states.items() if state["attempts"] > 0}
    for rid, state in states.items():
        if state["attempts"] > 0 and state["terminal"] is None:
            append_jsonl(out / "requests-ledger.jsonl", {"event": "request_interrupted",
                "request_id": rid, "status": "indeterminate_interrupted_not_replayed",
                "at_utc": utc_now(), "attempts_already_reserved": state["attempts"]})
            state["terminal"] = "indeterminate_interrupted_not_replayed"
    states, old_attempt_total = _request_states(out)
    m2 = _config()
    backend_config = _backend_config(m2)
    model_path = Path(backend_config.artifact_path)
    if file_sha256(model_path) != MODEL_SHA256:
        raise RuntimeError("M2 local model identity mismatch before launch")
    if file_sha256(Path(backend_config.server_binary_path)) != SERVER_SHA256:
        raise RuntimeError("M2 local server identity mismatch before launch")
    bundle = llama_runtime_bundle_identity(backend_config.server_binary_path)
    if bundle["sha256"] != BUNDLE_SHA256:
        raise RuntimeError("M2 local runtime bundle identity mismatch before launch")
    token_counter = GGUFChatTokenCounter(model_path, expected_artifact_sha256=MODEL_SHA256)
    if len(set(old_per_request) | request_ids) > 1000:
        raise RuntimeError("M2 unique payload request cap would be exceeded")
    if old_attempt_total >= 2000:
        raise RuntimeError("M2 physical attempt cap already exhausted")
    launch_id = f"launch-{len(list((out / 'launches').glob('launch-*.json'))) + 1:03d}"
    launch_dir = out / "launches" / launch_id
    launch_dir.mkdir(parents=True, exist_ok=False)
    _secure_dir(launch_dir)
    api_key = None
    api_key_file = None
    process = None
    stdout_stream = stderr_stream = None
    sampler = None
    owner_attestation = None
    key_info = None
    cleanup_info = None
    shutdown_info = None
    run_error: dict[str, Any] | None = None
    local_backend = None
    local_calls = 0
    local_response_tokens = {"prompt": 0, "completion": 0}
    started_phase = utc_now()
    try:
        sampler = GpuSampler(launch_dir / "gpu-samples.jsonl", interval_seconds=1.0)
        sampler.start()
        stdout_stream = (launch_dir / "llama-server.stdout.log").open("ab")
        stderr_stream = (launch_dir / "llama-server.stderr.log").open("ab")
        api_key, api_key_file, key_info = create_api_key_file(out)
        command = llama_server_command(backend_config, api_key_file)
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout_stream,
                                   stderr=stderr_stream, cwd=str(Path(backend_config.server_binary_path).parent),
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) |
                                   getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0), close_fds=True)
        server_path = str(Path(backend_config.server_binary_path).resolve())
        image = _process_image(process.pid)
        if image.casefold() != server_path.casefold():
            raise PermissionError("M2 llama.cpp process image differs from the frozen server binary")
        write_json(launch_dir / "launch.json", {"launch_id": launch_id, "pid": process.pid,
            "image_path": image, "server_sha256": SERVER_SHA256,
            "runtime_bundle_sha256": BUNDLE_SHA256, "command": command,
            "endpoint": backend_config.base_url, "offline": True,
            "started_at_utc": started_phase, "api_key_sha256": key_info["sha256"]})
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"frozen local llama.cpp server exited while loading ({process.returncode})")
            owner_rows, diagnostics = _listener_snapshot(8081)
            if owner_rows == [{"LocalAddress": "127.0.0.1", "LocalPort": 8081,
                               "OwningProcess": process.pid}]:
                break
            time.sleep(0.5)
        else:
            raise PermissionError(f"M2 llama.cpp did not own the exact loopback endpoint: {owner_rows}")
        owner_attestation = {"status": "verified_exact_pid_loopback_listener",
                             "pid": process.pid, "rows": owner_rows, "diagnostics": diagnostics}
        write_json(launch_dir / "listener-owner-attestation.json", owner_attestation)

        def guard() -> bool:
            return process is not None and process.poll() is None and \
                _process_image(process.pid).casefold() == server_path.casefold()

        def http_hook(row: dict[str, Any]) -> None:
            append_jsonl(launch_dir / "http-attempts.jsonl", {"at_utc": utc_now(),
                "listener_pid": process.pid, **row})

        local_backend = LocalLlamaCppBackend(backend_config, token_counter, api_key=api_key,
                                              listener_guard=guard, http_attempt_hook=http_hook)
        if old_per_request:
            local_backend.restore_full_run_budget(old_per_request)

        responses_by_request: dict[str, dict[str, Any]] = {}
        # Rehydrate completed responses for exact-request deduplication.
        for rid, state in states.items():
            if state.get("response"):
                response_path = response_dir / f"{rid}.json"
                if response_path.exists():
                    response_record = json.loads(response_path.read_text(encoding="utf-8"))
                    responses_by_request[rid] = response_record
        # Only selected partitions are dispatched. All five views and both
        # permissions for each case are linked to the same opaque case ID.
        by_request: dict[str, list[dict[str, Any]]] = {}
        for evaluation in phase_evals:
            by_request.setdefault(evaluation["request_id"], []).append(evaluation)
        for request_id, rows in by_request.items():
            if any(row["preparation_status"] != "prepared" for row in rows):
                status = "not_sent_input_over_budget"
                for row in rows:
                    append_jsonl(out / "evaluation-ledger.jsonl", {"event": "evaluation_terminal",
                        "eval_id": row["eval_id"], "request_id": request_id, "status": status,
                        "at_utc": utc_now()})
                continue
            if request_id in responses_by_request:
                status = responses_by_request[request_id]["validation_status"]
                for row in rows:
                    append_jsonl(out / "evaluation-ledger.jsonl", {"event": "evaluation_terminal",
                        "eval_id": row["eval_id"], "request_id": request_id,
                        "status": "deduplicated_" + status, "at_utc": utc_now(),
                        "deduplicated_from": request_id})
                continue
            if request_id in states and states[request_id].get("terminal"):
                terminal_status = states[request_id]["terminal"]
                for row in rows:
                    append_jsonl(out / "evaluation-ledger.jsonl", {"event": "evaluation_terminal",
                        "eval_id": row["eval_id"], "request_id": request_id,
                        "status": terminal_status, "at_utc": utc_now()})
                continue
            request_record = json.loads((request_dir / f"{request_id}.json").read_text(encoding="utf-8"))
            payload = request_record["payload"]
            payload_json = request_record.get("payload_json")
            if not isinstance(payload_json, str) or json.loads(payload_json) != payload:
                raise ValueError(f"M2 prepared request object/body differ: {request_id}")
            actual_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
            if actual_hash != request_record["payload_sha256"]:
                raise ValueError(f"M2 request payload hash changed before dispatch: {request_id}")
            expected_payload = m2_json_schema_payload(backend_config, payload["messages"],
                payload["response_format"]["schema"], payload["seed"])
            expected_body = json.dumps(expected_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            if expected_body != payload_json.encode("utf-8"):
                raise ValueError(f"M2 request bytes differ from the frozen local backend serializer: {request_id}")
            if not guard():
                raise PermissionError("M2 local listener/process identity changed during execution")
            if local_backend._full_pilot_attempts >= 2000:
                raise RuntimeError("M2 hard HTTP attempt ceiling reached")
            eval_ids = [row["eval_id"] for row in rows]
            for row in rows:
                append_jsonl(out / "evaluation-ledger.jsonl", {"event": "evaluation_started",
                    "eval_id": row["eval_id"], "request_id": request_id,
                    "at_utc": utc_now(), "phase": phase})
            final_response = None
            for attempt in range(1, 3):
                if local_backend._full_pilot_attempts >= 2000:
                    raise RuntimeError("M2 hard physical HTTP attempt ceiling reached")
                append_jsonl(out / "requests-ledger.jsonl", {"event": "attempt_started",
                    "request_id": request_id, "attempt": attempt,
                    "payload_sha256": request_record["payload_sha256"],
                    "at_utc": utc_now(), "phase": phase, "eval_ids": eval_ids})
                try:
                    response = local_backend.complete_json_schema(
                        request_id=request_id, messages=payload["messages"], schema=payload["response_format"]["schema"],
                        generation_seed=payload["seed"], timeout_seconds=backend_config.timeout_seconds)
                    raw_body = response.raw_body or ""
                    raw_text = response.text
                    raw_text_hash = sha256_bytes(raw_text.encode("utf-8"))
                    try:
                        parsed = json.loads(raw_text)
                        valid, validation_error = validate_prediction(
                            parsed, set(request_record["visible_event_ids"]))
                    except (json.JSONDecodeError, TypeError) as exc:
                        parsed, valid, validation_error = None, False, f"json_parse_error:{type(exc).__name__}"
                    response_record = {"request_id": request_id,
                        "payload_sha256": request_record["payload_sha256"],
                        "raw_response_body": raw_body, "raw_response_body_sha256": sha256_bytes(raw_body.encode("utf-8")),
                        "raw_assistant_text": raw_text, "raw_assistant_text_sha256": raw_text_hash,
                        "parsed": parsed, "validation_status": "valid" if valid else "invalid_output",
                        "validation_error": validation_error, "usage": response.usage,
                        "model": response.model, "finish_reason": response.finish_reason,
                        "response_metadata": response.metadata,
                        "returned_at_utc": utc_now(), "phase": phase}
                    write_json(response_dir / f"{request_id}.json", response_record)
                    final_response = response_record
                    append_jsonl(out / "requests-ledger.jsonl", {"event": "response_returned",
                        "request_id": request_id, "attempt": attempt,
                        "status": "valid" if valid else "invalid_output",
                        "response_sha256": response_record["raw_response_body_sha256"],
                        "at_utc": utc_now(), "usage": response.usage})
                    append_jsonl(out / "requests-ledger.jsonl", {"event": "request_terminal",
                        "request_id": request_id, "status": "valid" if valid else "invalid_output",
                        "at_utc": utc_now(), "attempts": attempt})
                    local_calls += 1
                    local_response_tokens["prompt"] += response.usage["prompt_tokens"]
                    local_response_tokens["completion"] += response.usage["completion_tokens"]
                    break
                except (TimeoutBackendError, TransientTransportError) as exc:
                    raw = getattr(exc, "raw_response", None)
                    can_retry = attempt == 1
                    append_jsonl(out / "requests-ledger.jsonl", {"event": "attempt_failed",
                        "request_id": request_id, "attempt": attempt, "retryable": can_retry,
                        "error_type": type(exc).__name__, "error": str(exc),
                        "raw_error_response": raw,
                        "raw_error_response_sha256": sha256_bytes(raw.encode("utf-8")) if raw else None,
                        "at_utc": utc_now()})
                    if not can_retry:
                        append_jsonl(out / "requests-ledger.jsonl", {"event": "request_failed",
                            "request_id": request_id, "status": "transport_failed_after_two_attempts",
                            "at_utc": utc_now(), "attempts": attempt})
                        break
                except Exception as exc:
                    raw = getattr(exc, "raw_response", None)
                    error_record = {"error_type": type(exc).__name__, "error": str(exc),
                                    "raw_error_response": raw,
                                    "raw_error_response_sha256": sha256_bytes(raw.encode("utf-8")) if raw else None,
                                    "at_utc": utc_now()}
                    write_json(out / "responses" / f"{request_id}.error-{attempt}.json", error_record)
                    append_jsonl(out / "requests-ledger.jsonl", {"event": "request_failed",
                        "request_id": request_id, "status": "terminal_request_error",
                        "at_utc": utc_now(), "attempt": attempt, **error_record})
                    break
            status = final_response["validation_status"] if final_response else "request_failed"
            for row in rows:
                append_jsonl(out / "evaluation-ledger.jsonl", {"event": "evaluation_terminal",
                    "eval_id": row["eval_id"], "request_id": request_id,
                    "status": status, "at_utc": utc_now()})
            states, _ = _request_states(out)
            if len(states) > 1000:
                raise RuntimeError("M2 unique request count exceeded 1,000")
            if _request_states(out)[1] > 2000:
                raise RuntimeError("M2 physical request attempt count exceeded 2,000")
            if local_calls % 25 == 0:
                print(json.dumps({"phase": phase, "logical_phase_evaluations": len(phase_evals),
                    "unique_phase_requests": len(by_request), "physical_model_responses_this_launch": local_calls,
                    "physical_http_attempts_cumulative": _request_states(out)[1],
                    "completed_unique_requests": sum(state.get("response") is not None for state in states.values()),
                    "updated_at_utc": utc_now()}, sort_keys=True), flush=True)
        if process.poll() is not None or not guard():
            raise PermissionError("M2 llama.cpp server did not remain the exact loopback listener through inference")
    except BaseException as exc:
        run_error = {"error_type": type(exc).__name__, "error": str(exc), "phase": phase,
                     "at_utc": utc_now()}
        write_json(launch_dir / "run-failure.json", run_error)
    finally:
        if process is not None:
            shutdown_info = _stop_own_process(process)
            write_json(launch_dir / "shutdown.json", shutdown_info)
        if api_key_file is not None:
            cleanup_info = remove_api_key_file(api_key_file)
            write_json(launch_dir / "api-key-cleanup.json", cleanup_info)
        if stdout_stream is not None:
            stdout_stream.close()
        if stderr_stream is not None:
            stderr_stream.close()
        if sampler is not None:
            sampler.stop()
    final_states, total_attempts = _request_states(out)
    summary = {"phase": phase, "started_at_utc": started_phase, "finished_at_utc": utc_now(),
        "logical_evaluations_assigned": len(phase_evals),
        "unique_payloads_in_phase": len(request_ids),
        "physical_http_attempts_cumulative": total_attempts,
        "model_responses_this_launch": local_calls,
        "model_tokens_this_launch": local_response_tokens,
        "terminal_unique_payloads_cumulative": sum(bool(state.get("terminal")) for state in final_states.values()),
        "invalid_outputs_cumulative": sum(state.get("terminal") == "invalid_output" for state in final_states.values()),
        "local_listener_pid": owner_attestation.get("pid") if owner_attestation else None,
        "api_key_sha256": key_info["sha256"] if key_info else None,
        "api_key_cleanup": cleanup_info, "shutdown": shutdown_info,
        "failure": run_error, "privacy_local_only": True,
        "preparation_manifest_sha256": file_sha256(out / "preparation-manifest.json")}
    write_json(launch_dir / "phase-summary.json", summary)
    append_jsonl(out / "phase-ledger.jsonl", summary)
    print(json.dumps(summary, sort_keys=True))
    if run_error:
        raise RuntimeError(f"M2 {phase} inference interrupted; preserved run failure at {launch_dir}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=RUN_DEFAULT)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--phase", choices=("calibration", "held_out"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / "runs/m2"):
        raise ValueError("M2 raw outputs must remain inside the Git-ignored local runs/m2 directory")
    if args.prepare:
        if args.resume:
            raise ValueError("--prepare never overwrites; use --phase with --resume after a prior preparation")
        prepare_run(out)
    else:
        if not (out / "preparation-manifest.json").exists():
            raise FileNotFoundError("M2 preparation manifest missing")
        if not args.resume and (out / "requests-ledger.jsonl").exists():
            raise FileExistsError("run has request history; pass --resume to continue without replay")
        execute_phase(out, args.phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
