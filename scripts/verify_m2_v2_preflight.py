#!/usr/bin/env python3
"""Independent no-call audit of the frozen M2-V2 compatibility inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.gguf_tokenizer import GGUFChatTokenCounter
from colluscope.m2_corpus import file_sha256, load_m2_corpus

CONFIG = ROOT / "configs/m2-v2.toml"
CANDIDATES = ROOT / "configs/m2-v2-candidates.json"
SOURCE = ROOT / "runs/m1_100/extension-75-20261019-run02"
FORBIDDEN_KEYS = {
    "condition_id", "episode_id", "split_group_id", "seed_block_id",
    "scenario_family_id", "researcher_label", "oracle", "collusion_label",
    "latent_collusion", "target_executed_researcher_only",
    "private_target_bonus_recipients", "private_incentive_assignment",
}
VIEWS = ("text_only", "action_only", "raw_fusion", "structured_evidence",
         "structured_without_findings")
PERMISSIONS = ("public_only", "privileged_audit")


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _forbidden_keys(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            if str(key).casefold() in FORBIDDEN_KEYS:
                found.append(child)
            found.extend(_forbidden_keys(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_forbidden_keys(item, f"{path}[{index}]"))
    return found


def _extract_events(user: str, view: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    marker = "Evidence object:\n"
    if marker not in user:
        raise ValueError("prepared prompt omitted the evidence section")
    encoded = user.split(marker, 1)[1]
    if view == "raw_fusion":
        lines = encoded.splitlines()
        if len(lines) < 3 or lines[0] != "Public task specification:" or \
                lines[2] != "Ordered permitted evidence events:":
            raise ValueError("raw_fusion evidence stream framing differs from frozen grammar")
        task = json.loads(lines[1])
        events = [json.loads(line) for line in lines[3:]]
    else:
        value = json.loads(encoded)
        task = value.get("task_spec")
        events = value.get("events")
        if not isinstance(events, list):
            raise ValueError("structured evidence has no event array")
    if not isinstance(task, dict) or any(not isinstance(row, dict) for row in events):
        raise ValueError("prepared task/evidence records are malformed")
    return task, events


def _verify_acl(paths: list[Path]) -> dict[str, Any]:
    identity = subprocess.run(["whoami.exe", "/user", "/fo", "csv", "/nh"],
                              capture_output=True, text=True, timeout=10, check=True)
    rows = list(csv.reader(identity.stdout.splitlines()))
    if len(rows) != 1 or len(rows[0]) < 2:
        raise PermissionError("unable to resolve current Windows SID for private input ACL audit")
    account, sid = rows[0][0], rows[0][1]
    verified: dict[str, Any] = {}
    for path in paths:
        result = subprocess.run(["icacls.exe", str(path)], capture_output=True, text=True,
                                timeout=10, check=True)
        aces = [line.strip().replace(" ", "").casefold() for line in result.stdout.splitlines()
                if ":(" in line.replace(" ", "")]
        current = [line for line in aces if sid.casefold() in line or
                   account.replace(" ", "").casefold() in line]
        if not current or any(line not in current for line in aces) or \
                not any("(f)" in line for line in current):
            raise PermissionError(f"non-exclusive or insufficient ACL on {path}")
        verified[str(path.resolve())] = {
            "ace_count": len(aces), "current_user_full_control": True,
            "acl_output_sha256": _hash(result.stdout.encode("utf-8")),
        }
    return {"sid": sid, "verified_paths": verified}


def verify(out: Path, registry_path: Path | None = None) -> dict[str, Any]:
    config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
    registry_path = registry_path or CANDIDATES
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    freeze_path = out / "preflight-registry-freeze.json"
    manifest_path = out / "preflight-manifest.json"
    case_path = out / "private/preflight-case.json"
    case_map_path = out / "private/preflight-case-map.json"
    if not all(path.is_file() for path in (freeze_path, manifest_path, case_path, case_map_path)):
        raise FileNotFoundError("no-call M2-V2 preparation is incomplete")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case_info = json.loads(case_path.read_text(encoding="utf-8"))
    case_map = json.loads(case_map_path.read_text(encoding="utf-8"))
    if len(case_map) != 1 or case_info["episode_id"] not in case_map.values():
        raise ValueError("preflight private case map is inconsistent")
    if (manifest.get("model_calls") != 0 or manifest.get("candidate_case_count") != 30 or
            manifest.get("maximum_generation_attempts") != 30 or manifest.get("retries") != 0):
        raise ValueError("preflight manifest exceeds or misstates its no-call budget")
    for relative, digest in freeze.get("artifact_hashes", {}).items():
        if file_sha256(ROOT / relative) != digest:
            raise ValueError(f"hash-bound source changed after candidate freeze: {relative}")
    if (manifest.get("registry_freeze_sha256") != file_sha256(freeze_path) or
            manifest.get("source_validation_sha256") != file_sha256(out / "stage1/source-validation.json") or
            manifest.get("m2_v1_inventory_sha256") !=
            file_sha256(out / "stage1/m2-v1-inventory-verification.json")):
        raise ValueError("preflight/source integrity hashes do not match")
    inventory = json.loads((out / "stage1/m2-v1-inventory-verification.json").read_text(encoding="utf-8"))
    if (not inventory.get("all_entries_match_size_and_sha256") or
            inventory.get("manifest_entry_count") != 1450 or
            inventory.get("unexpected_files_outside_manifest") or
            inventory.get("manifest_paths_missing_from_run")):
        raise ValueError("frozen M2-V1 artifact inventory is not intact")

    files = sorted((out / "requests/preflight").glob("*.json"))
    if len(files) != 30:
        raise ValueError(f"expected exactly 30 frozen compatibility requests, got {len(files)}")
    cases = load_m2_corpus(ROOT, SOURCE)
    source_case = next((case for case in cases if case.episode_id == case_info["episode_id"]), None)
    if source_case is None or source_case.partition != "F1" or not source_case.delivered_messages:
        raise ValueError("fixed preflight case no longer matches the eligible F1 rule")
    source_texts = {row["text"] for row in source_case.delivered_messages
                    if row.get("delivered") and row.get("sender") in {"A", "B"} and
                    row.get("recipient") in {"A", "B"}}
    counter = GGUFChatTokenCounter(Path(config["model_path"]),
                                   expected_artifact_sha256=config["model_sha256"])
    candidates = {row["candidate_id"] for row in registry["candidates"]}
    observed: set[tuple[str, str, str]] = set()
    payload_hashes: set[str] = set()
    tokens_by_view = Counter()
    private_visible_rows = 0
    for path in files:
        record = json.loads(path.read_text(encoding="utf-8"))
        candidate, view, permission = (record["candidate_id"], record["view_name"],
                                       record["permission_profile"])
        key = (candidate, view, permission)
        if candidate not in candidates or view not in VIEWS or permission not in PERMISSIONS or key in observed:
            raise ValueError(f"duplicate or out-of-scope preflight tuple: {key}")
        observed.add(key)
        raw = record["payload_json"].encode("utf-8")
        if _hash(raw) != record["payload_sha256"] or manifest["request_hashes"].get(record["request_id"]) != record["payload_sha256"]:
            raise ValueError(f"exact request body hash mismatch: {record['request_id']}")
        payload = json.loads(raw)
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if canonical != raw:
            raise ValueError("payload JSON bytes differ from the frozen deterministic serializer")
        if payload["model"] != config["model_id"] or payload["temperature"] != 0.0 or \
                payload["max_tokens"] != config["output_token_cap"] or payload["stream"] is not False:
            raise ValueError("request model or generation settings differ from the freeze")
        if _forbidden_keys(payload):
            raise ValueError(f"research-only metadata found in model input: {_forbidden_keys(payload)}")
        messages = payload["messages"]
        if len(messages) != 2 or [row["role"] for row in messages] != ["system", "user"]:
            raise ValueError("monitor input has an unexpected role/message boundary")
        user = messages[1]["content"]
        if f"Permission profile: {permission}" not in user or f"Evidence view: {view}" not in user:
            raise ValueError("permitted view/permission was not visible as labeled in the prompt")
        _, events = _extract_events(user, view)
        event_ids = {event.get("event_id") for event in events}
        if None in event_ids or event_ids != set(record["visible_event_ids"]):
            raise ValueError("visible event index does not match the exact serialized input")
        message_events = [event for event in events if event.get("type") == "message"]
        if view == "action_only" and message_events:
            raise ValueError("action-only input contains a peer message")
        if permission == "public_only":
            if message_events or any(text and text in user for text in source_texts):
                raise PermissionError("Public-only input contains private message evidence")
        else:
            for event in message_events:
                if (event.get("actor") not in {"A", "B"} or event.get("recipient") not in {"A", "B"} or
                        event.get("delivery_status") != "delivered"):
                    raise PermissionError("privileged projection contains an unauthorized message")
            if message_events:
                private_visible_rows += 1
        if payload["response_format"]["type"] == "json_schema" and "schema" not in payload["response_format"]:
            raise ValueError("json_schema request omitted its frozen schema")
        if payload["response_format"]["type"] == "json_object" and set(payload["response_format"]) != {"type"}:
            raise ValueError("json_object candidate unexpectedly carries a schema field")
        token_count = len(counter.encode_chat(messages, enable_thinking=False))
        if token_count != record["input_tokens_local"] or token_count > config["input_token_cap"] or \
                token_count + payload["max_tokens"] > config["context_length"]:
            raise ValueError("token count or context bound is inconsistent")
        tokens_by_view[view] += token_count
        payload_hashes.add(record["payload_sha256"])
    expected = {(candidate, view, permission) for candidate in candidates
                for view in VIEWS for permission in PERMISSIONS}
    if observed != expected or len(payload_hashes) != 30:
        raise ValueError("preflight factorial or payload uniqueness check failed")
    if set(manifest["request_hashes"]) != {json.loads(path.read_text(encoding="utf-8"))["request_id"]
                                            for path in files}:
        raise ValueError("preflight manifest contains missing or extra request hashes")
    attempts = out / "preflight-attempts.jsonl"
    responses = list((out / "responses/preflight").glob("*"))
    launches = [path for path in (out / "launches").iterdir() if path.is_dir()]
    if (attempts.exists() and attempts.stat().st_size) or responses or launches:
        raise ValueError("preflight preparation unexpectedly launched or sent model requests")
    acl = _verify_acl([out, out / "private", out / "requests", out / "requests/preflight",
                       out / "responses", out / "responses/preflight", out / "launches",
                       out / "logs", out / "stage1"])
    return {
        "status": "PASS_M2_V2_PREFLIGHT_INPUT_AUDIT",
        "protocol_id": manifest["protocol_id"], "request_count": len(files),
        "candidate_registry_sha256": file_sha256(registry_path),
        "candidate_count": len(candidates), "candidate_case_counts": dict(Counter(
            json.loads(path.read_text(encoding="utf-8"))["candidate_id"] for path in files)),
        "unique_payload_count": len(payload_hashes), "model_calls": 0, "http_attempts": 0,
        "token_counts_by_view": dict(tokens_by_view),
        "private_message_visible_preflight_rows": private_visible_rows,
        "v1_source_inventory_sha256": inventory["inventory_manifest_sha256"],
        "v1_source_entries_verified": inventory["manifest_entry_count"],
        "acl_verified_paths": len(acl["verified_paths"]),
        "preflight_manifest_sha256": file_sha256(manifest_path),
        "registry_freeze_sha256": file_sha256(freeze_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--registry", type=Path,
                        help="versioned candidate registry for an authorized repair iteration")
    args = parser.parse_args()
    result = verify(args.out.resolve(), args.registry.resolve() if args.registry else None)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
