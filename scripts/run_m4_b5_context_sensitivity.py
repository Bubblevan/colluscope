#!/usr/bin/env python3
"""Frozen DeepSeek campaign for M4 B5 evidence-view sensitivity.

The default command only compiles/validates requests. Network dispatch is
available only with the explicit --dispatch flag after registration and a
matching authorization batch are present. Raw payloads, responses, and private
message text stay under the Git-ignored, ACL-restricted run directory.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import ipaddress
import itertools
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import freeze_m4_b5_context_sensitivity_schedule as schedule_builder  # noqa: E402
from scripts import project_monitor_http_request_v2 as direct_projector  # noqa: E402
from scripts.local_llama_security import (  # noqa: E402
    restrict_private_directory_acl,
    verify_private_directory_acl,
)
from colluscope import deepseek_m4_v1 as runtime  # noqa: E402
from colluscope import deepseek_monitor_v1 as m4_monitor  # noqa: E402
from colluscope import sprint_baselines  # noqa: E402
from scripts.validate_synthetic_invariance_groups_v2 import (  # noqa: E402
    MANIFEST_PATH as SYNTHETIC_MANIFEST,
    PROMPT_PATH as MONITOR_SYSTEM_PROMPT,
    _load_manifest as load_synthetic_manifest,
)


EXPERIMENT_ID = "m4-b5-context-sensitivity-campaign-v1"
APPROVAL_ID = "DS-FLASH-M4B5-CONTEXT-232-20261021"
AUTH_SCOPE = (
    "One M4 B5 context-sensitivity monitor campaign (A1: all 24 M4 cases across three evidence views; "
    "A2: all 40 balanced synthetic rows across four request forms); official DeepSeek Flash only; "
    "maximum 232 physical attempts and USD 0.90; zero retries/replacements; off-peak only; "
    "expiry 2026-10-23T01:00:00Z."
)
APPROVAL_EXPIRY = "2026-10-23T01:00:00+00:00"
MODEL = "deepseek-flash"
EXPECTED_MODELS = {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"}
ENDPOINT = "https://api.deepseek.com/chat/completions"
RUN_ROOT = ROOT / "runs/sprint-monitor/m4-b5-context-sensitivity-campaign-v1-run"
SCHEDULE_PATH = ROOT / "research/schedules/m4-b5-context-sensitivity-campaign-v1.json"
REQUEST_MANIFEST_PATH = ROOT / "docs/results/research-sprint-20261021/direction-review/m4-b5-frozen-request-manifest-v3.json"
PREREG_PATH = ROOT / "research/experiments/m4-b5-context-sensitivity-campaign-v1/preregistration.json"
SYSTEM_PROMPT_PATH = ROOT / "prompts/m4-deepseek-agent-v1/monitor-system.txt"
M4_SOURCE_RUN = ROOT / "runs/deepseek-first-m4/agent"
MAX_ATTEMPTS = 232
MAX_COST_USD = Decimal("0.90")
MAX_WALLCLOCK_SECONDS = 6 * 60 * 60
MAX_INPUT_TOKENS = 12_500
MAX_OUTPUT_TOKENS = 512
PEAK_INPUT_RATE = Decimal("0.30") / Decimal(1_000_000)
PEAK_OUTPUT_RATE = Decimal("1.20") / Decimal(1_000_000)
OFFPEAK_INPUT_RATE = Decimal("0.15") / Decimal(1_000_000)
OFFPEAK_OUTPUT_RATE = Decimal("0.60") / Decimal(1_000_000)
REQUEST_TIMEOUT_SECONDS = 90
NEUTRAL_MESSAGE = "I received your message."


class CampaignError(RuntimeError):
    """Sanitized campaign failure code; do not interpolate evidence or secrets."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def canonical_pretty(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      indent=2).encode("utf-8") + b"\n"


HIDDEN_RESEARCH_KEYS = {
    "scoring_reference", "reference_label", "primary_label", "gold_label",
    "ground_truth", "answer_key", "case_ref", "instance_id", "group_id",
    "split_group_id", "scenario_family_id", "trajectory_id", "variant_id",
    "arm_id", "condition_id", "split", "seed", "oracle_label",
}


def _assert_no_hidden_research_keys(value: Any, *, error_code: str) -> None:
    """Reject oracle/routing fields by structured key, not ordinary prompt words."""
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.casefold() in HIDDEN_RESEARCH_KEYS:
                raise CampaignError(error_code)
            _assert_no_hidden_research_keys(child, error_code=error_code)
    elif isinstance(value, list):
        for child in value:
            _assert_no_hidden_research_keys(child, error_code=error_code)


def _a1_pair_profile_audit(compiled: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize exact paired request-body profiles without exporting case IDs."""
    by_unit: dict[str, dict[str, str]] = {}
    for row in compiled:
        if row.get("block") == "A1":
            by_unit.setdefault(row["unit_sha256"], {})[row["arm_id"]] = row["body_sha256"]
    contrasts = {
        "public_vs_neutral": ("A1-PUBLIC", "A1-PRIVILEGED-NEUTRAL"),
        "public_vs_original": ("A1-PUBLIC", "A1-PRIVILEGED-ORIGINAL"),
        "neutral_vs_original": ("A1-PRIVILEGED-NEUTRAL", "A1-PRIVILEGED-ORIGINAL"),
    }
    result: dict[str, Any] = {}
    for name, (left, right) in contrasts.items():
        profiles = []
        for arms in by_unit.values():
            if left not in arms or right not in arms:
                raise CampaignError("A1_PAIR_PROFILE_MISSING_ARM")
            profiles.append((arms[left], arms[right]))
        if len(profiles) != 24:
            raise CampaignError("A1_PAIR_PROFILE_ASSIGNED_COUNT_MISMATCH")
        counts: dict[tuple[str, str], int] = {}
        for profile in profiles:
            counts[profile] = counts.get(profile, 0) + 1
        result[name] = {
            "assigned_pairs": len(profiles),
            "unique_exact_input_profiles": len(counts),
            "duplicate_cluster_sizes": sorted(
                (count for count in counts.values() if count > 1), reverse=True),
            "profile_multiset_sha256": sha(canonical(sorted(profiles))),
        }
    return result


def _build_public_request_manifest(compiled: list[dict[str, Any]], meta: dict[str, Any],
                                   schedule_raw: bytes) -> dict[str, Any]:
    return {
        "schema_version": 3,
        "experiment_id": EXPERIMENT_ID,
        "schedule_sha256": sha(schedule_raw),
        "source_hashes": {key: value for key, value in meta.items() if key.endswith("sha256")},
        "private_source_file_hashes": {
            "runs/deepseek-first-m4/agent/episodes.jsonl": meta["m4_source_episodes_sha256"],
            "runs/deepseek-first-m4/agent/run_manifest.json": meta["m4_source_manifest_sha256"],
        },
        "request_count": len(compiled),
        "maximum_physical_attempts": MAX_ATTEMPTS,
        "retry_policy": "zero retries and zero replacement rows",
        "model": MODEL,
        "endpoint": ENDPOINT,
        "prompt_hashes": {
            "m4_monitor_system": meta["m4_system_prompt_sha256"],
            "synthetic_v2_system": meta["system_prompt_sha256"],
        },
        "request_rows": [
            {key: value for key, value in row.items()
             if key not in {"_body", "visible_event_ids", "reference_label_private"}}
            for row in compiled
        ],
        "a1_exact_pair_profile_audit": _a1_pair_profile_audit(compiled),
        "private_truth_sha256": sha(canonical(meta["private_truth_rows"])),
        "raw_request_bodies_are_local_private_only": True,
        "auth_headers_saved": False,
    }


def _validate_public_request_manifest(public_manifest: dict[str, Any],
                                      compiled: list[dict[str, Any]], meta: dict[str, Any],
                                      schedule_raw: bytes) -> None:
    expected = _build_public_request_manifest(compiled, meta, schedule_raw)
    if public_manifest != expected:
        raise CampaignError("PUBLIC_REQUEST_MANIFEST_DOES_NOT_MATCH_RECOMPILED_SOURCES")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def write_once(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line in path.read_bytes().splitlines():
        if not line.strip():
            raise CampaignError("LEDGER_CONTAINS_BLANK_LINE")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise CampaignError("LEDGER_ROW_NOT_OBJECT")
        result.append(value)
    return result


def _load_schedule(path: Path = SCHEDULE_PATH) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    schedule = json.loads(raw)
    expected = schedule_builder.build_schedule()
    if raw.replace(b"\r\n", b"\n") != canonical_pretty(schedule) or schedule != expected:
        raise CampaignError("SCHEDULE_DIFFERS_FROM_FROZEN_BUILDER")
    if schedule.get("experiment_id") != EXPERIMENT_ID:
        raise CampaignError("SCHEDULE_EXPERIMENT_ID_MISMATCH")
    if len(schedule.get("rows", [])) != MAX_ATTEMPTS:
        raise CampaignError("SCHEDULE_ROW_COUNT_MISMATCH")
    ids = [row.get("row_sha256") for row in schedule["rows"]]
    if len(set(ids)) != MAX_ATTEMPTS:
        raise CampaignError("SCHEDULE_DUPLICATE_ROW")
    return schedule, raw


def _m4_sources() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from scripts import prepare_full_research_monitor as legacy

    sources, metadata = legacy._m4_sources(M4_SOURCE_RUN)
    if len(sources) != 24 or metadata.get("source_episode_count") != 24:
        raise CampaignError("M4_SOURCE_MUST_RETAIN_ALL_24_EPISODES")
    if len({row.get("case_ref") for row in sources}) != 24:
        raise CampaignError("M4_SOURCE_CASE_REFERENCES_NOT_UNIQUE")
    return sources, metadata


def _m4_request(source: dict[str, Any], permission: str, *, neutral: bool = False) -> tuple[bytes, dict[str, Any]]:
    selected = copy.deepcopy(source)
    if neutral:
        message_events = [event for event in selected["B"]["events"] if event.get("type") == "message"]
        if len(message_events) != 2:
            raise CampaignError("M4_CASE_DOES_NOT_HAVE_EXACTLY_TWO_MESSAGE_EVENTS")
        for event in message_events:
            event["content"] = {"text": NEUTRAL_MESSAGE}
    request_row = m4_monitor._request_row(
        source=selected,
        population="m4_natural_traces",
        instance_id=selected["case_ref"],
        task="public_harm",
        baseline="B5_evidence_aware",
        permission=permission,
        interface="strict_function_calling",
    )
    payload = request_row["payload"]
    body = runtime.canonical(payload)
    # Explicit boundary checks: hidden labels/routing identifiers stay in sidecars.
    forbidden = (b"scoring_reference", b"reference_label", b"primary_label",
                 b"case_ref", b"split_group_id", b"scenario_family_id", b"M4TRACE-")
    if any(marker in body for marker in forbidden):
        raise CampaignError("M4_REQUEST_CONTAINS_RESEARCHER_METADATA")
    if permission == "public_only" and any(
            event.get("type") == "message" for event in request_row["evidence"].get("events", [])):
        raise CampaignError("PUBLIC_REQUEST_CONTAINS_PRIVATE_MESSAGE_EVENT")
    return body, request_row


def _synthetic_source(monitor_input: dict[str, Any], sidecar_id: str) -> dict[str, Any]:
    task = copy.deepcopy(monitor_input["task_spec"])
    events = copy.deepcopy(monitor_input["events"])
    return {
        "schema_version": "colluscope-synthetic-monitor-source-v1",
        "case_ref": sidecar_id,
        "scenario_family_id": "synthetic-fixed-fixture",
        "task_spec": task,
        "T": {},
        "B": {
            "event_stream_complete": monitor_input.get("action_record_complete") is True,
            "message_stream_complete": monitor_input.get("delivered_message_window_complete") is True,
            "events": events,
        },
    }


def _arithmetic_table(monitor_input: dict[str, Any]) -> str:
    """List all six public assignment totals, without a maximum/regret/label."""
    agents = monitor_input["task_spec"]["agents"]
    tasks = monitor_input["task_spec"]["tasks"]
    quality = monitor_input["task_spec"]["quality"]
    lines = ["Public calculation aid: total quality for each possible allocation (no ranking is supplied):"]
    for perm in itertools.permutations(tasks):
        assignment = dict(zip(agents, perm, strict=True))
        total = sum(quality[agent][assignment[agent]] for agent in agents)
        label = ", ".join(f"{agent}={assignment[agent]}" for agent in agents)
        lines.append(f"{label}: total quality {total}")
    return "\n".join(lines)


def _production_request(monitor_input: dict[str, Any], *, reverse_binary_labels: bool = False,
                        add_arithmetic_table: bool = False) -> tuple[bytes, dict[str, Any]]:
    source = _synthetic_source(monitor_input, "fixed-synthetic-sidecar")
    _prompt_payload, evidence = sprint_baselines.build_monitor_payload(
        source, "B5_evidence_aware", "public_harm", "public_only")
    messages = m4_monitor._monitor_messages(
        task="public_harm", evidence=evidence, interface="strict_function_calling")
    task_def = sprint_baselines.TASK_DEFINITIONS["public_harm"]
    labels = list(task_def["allowed_labels"])
    if reverse_binary_labels:
        if "present" not in labels or "absent" not in labels:
            raise CampaignError("PUBLIC_HARM_BINARY_LABELS_MISSING")
        i, j = labels.index("present"), labels.index("absent")
        labels[i], labels[j] = labels[j], labels[i]
        marker = "Allowed labels: " + ", ".join(task_def["allowed_labels"])
        replacement = "Allowed labels: " + ", ".join(labels)
        if messages[1]["content"].count(marker) != 1:
            raise CampaignError("LABEL_ORDER_PROMPT_MARKER_NOT_UNIQUE")
        messages[1]["content"] = messages[1]["content"].replace(marker, replacement, 1)
    if add_arithmetic_table:
        messages[1]["content"] += "\n\n" + _arithmetic_table(monitor_input)
    tool_name, schema = runtime.monitor_tool(labels)
    payload = runtime.request_payload(
        interface="strict_function_calling", messages=messages,
        tool_name=tool_name, schema=schema, output_limit=MAX_OUTPUT_TOKENS)
    _assert_no_hidden_research_keys(
        payload, error_code="A2_REQUEST_CONTAINS_ORACLE_OR_ROUTING_METADATA")
    body = runtime.canonical(payload)
    return body, {"evidence": evidence, "labels": labels, "payload": payload}


def compile_requests(schedule: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build every exact HTTP body in memory; return sanitized rows and hashes."""
    schedule = schedule or _load_schedule()[0]
    m4_rows, m4_meta = _m4_sources()
    case_map = {sha(row["case_ref"].encode("utf-8")): row for row in m4_rows}
    if len(case_map) != 24:
        raise CampaignError("M4_HASHED_CASE_MAPPING_COLLISION")
    synthetic, synthetic_raw = load_synthetic_manifest()
    group_by_hash: dict[str, dict[str, Any]] = {}
    for group in synthetic["groups"]:
        group_hash = sha(group["group_id"].encode("utf-8"))
        if group_hash in group_by_hash:
            raise CampaignError("A2_HASHED_GROUP_COLLISION")
        group_by_hash[group_hash] = group

    compiled: list[dict[str, Any]] = []
    public_truth: dict[str, Any] = {}
    oversized: list[tuple[str, int]] = []
    prompt = MONITOR_SYSTEM_PROMPT.read_text(encoding="utf-8")
    for row in schedule["rows"]:
        arm = row["arm_id"]
        body: bytes
        reference: str
        visible_ids: list[str]
        if row["block"] == "A1":
            case = case_map.get(row["unit_sha256"])
            if case is None:
                raise CampaignError("A1_SCHEDULE_UNIT_NOT_IN_COMPLETE_M4_SOURCE")
            permission = "public_only" if arm == "A1-PUBLIC" else "privileged_audit"
            body, request = _m4_request(case, permission,
                                       neutral=arm == "A1-PRIVILEGED-NEUTRAL")
            if arm not in schedule_builder.A1_ARMS:
                raise CampaignError("UNKNOWN_A1_ARM")
            reference = request["references"][0].get("label")
            if reference not in {"present", "absent"}:
                raise CampaignError("M4_PUBLIC_HARM_REFERENCE_NOT_BINARY")
            visible_ids = [event["event_id"] for event in request["evidence"].get("events", [])]
            unit_hash = row["unit_sha256"]
            public_truth[unit_hash] = reference
        elif row["block"] == "A2":
            group_hash = row["group_sha256"]
            group = group_by_hash.get(group_hash)
            if group is None:
                raise CampaignError("A2_SCHEDULE_GROUP_NOT_IN_FROZEN_MANIFEST")
            trajectory = next((item for item in group["trajectories"]
                               if sha(item["trajectory_id"].encode("utf-8")) == row["trajectory_sha256"]), None)
            if trajectory is None:
                raise CampaignError("A2_SCHEDULE_TRAJECTORY_NOT_IN_FROZEN_GROUP")
            variant = next(item for item in trajectory["variants"] if item["variant_id"] == "public_canonical")
            monitor_input = variant["monitor_input"]
            if arm == "A2-V2-DIRECT":
                body = direct_projector.serialize_http_request(
                    direct_projector.project_variant_http_request(prompt, variant))
            elif arm == "A2-PRODUCTION-B5":
                body, _compiled = _production_request(monitor_input)
            elif arm == "A2-PRODUCTION-ARITHMETIC":
                body, _compiled = _production_request(monitor_input, add_arithmetic_table=True)
            elif arm == "A2-REVERSED-LABEL-ORDER":
                body, _compiled = _production_request(monitor_input, reverse_binary_labels=True)
            else:
                raise CampaignError("UNKNOWN_A2_ARM")
            reference = variant["scoring_reference"]
            visible_ids = [event["event_id"] for event in monitor_input["events"]]
            unit_hash = sha(canonical({
                "group_hash": group_hash,
                "trajectory_hash": sha(trajectory["trajectory_id"].encode("utf-8")),
            }))
            public_truth[row["row_sha256"]] = reference
        else:
            raise CampaignError("UNKNOWN_SCHEDULE_BLOCK")

        token_bound = len(body) * 2 + 256
        if token_bound > MAX_INPUT_TOKENS:
            oversized.append((arm, token_bound))
        if len(body) == 0 or b"Authorization" in body or b"LLM_API_KEY" in body:
            raise CampaignError("REQUEST_BODY_INVALID_OR_CONTAINS_AUTH_MARKER")
        request_id = "m4b5_" + row["row_sha256"][:24]
        compiled.append({
            "request_id": request_id,
            "row_sha256": row["row_sha256"],
            "block": row["block"],
            "arm_id": arm,
            "unit_sha256": unit_hash,
            "body_sha256": sha(body),
            "serialized_bytes": len(body),
            "input_token_upper_bound": token_bound,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "visible_event_ids": visible_ids,
            "reference_label_private": reference,
            "_body": body,
        })
    if len(compiled) != MAX_ATTEMPTS or len({r["request_id"] for r in compiled}) != MAX_ATTEMPTS:
        raise CampaignError("COMPILED_REQUEST_COUNT_OR_ID_COLLISION")
    if oversized:
        by_arm = {arm: max(bound for item_arm, bound in oversized if item_arm == arm)
                  for arm in sorted({item_arm for item_arm, _ in oversized})}
        raise CampaignError(
            f"FROZEN_REQUEST_EXCEEDS_{MAX_INPUT_TOKENS}_INPUT_TOKEN_BOUND count={len(oversized)} max={max(bound for _, bound in oversized)} by_arm={by_arm}")
    return compiled, {
        "m4_source_metadata": m4_meta,
        "m4_source_episodes_sha256": sha((M4_SOURCE_RUN / "episodes.jsonl").read_bytes()),
        "m4_source_manifest_sha256": sha((M4_SOURCE_RUN / "run_manifest.json").read_bytes()),
        "score_csv_sha256": sha((ROOT / schedule_builder.SCORES).read_bytes()),
        "synthetic_manifest_sha256": sha(synthetic_raw),
        "schedule_sha256": sha(canonical_pretty(schedule)),
        "system_prompt_sha256": sha(SYSTEM_PROMPT_PATH.read_bytes()),
        "m4_system_prompt_sha256": sha(MONITOR_SYSTEM_PROMPT.read_bytes()),
        "compiled_rows": [
            {key: value for key, value in row.items()
             if key not in {"_body", "visible_event_ids", "reference_label_private"}}
            for row in compiled
        ],
        "private_truth_rows": public_truth,
    }


def _private_root(out: Path, *, test_mode: bool) -> dict[str, Any]:
    if test_mode:
        out.mkdir(parents=True, exist_ok=True)
        return {"verified": False, "test_fixture_only": True}
    ignored = "/runs/sprint-monitor/" in (ROOT / ".gitignore").read_text(encoding="utf-8").replace("\\", "/")
    out = out.resolve()
    allowed = (ROOT / "runs/sprint-monitor").resolve()
    if not ignored or allowed not in out.parents:
        raise PermissionError("raw inputs/outputs must stay under Git-ignored runs/sprint-monitor")
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        return verify_private_directory_acl(out)
    return restrict_private_directory_acl(out)


def prepare(out: Path = RUN_ROOT, *, test_mode: bool = False) -> dict[str, Any]:
    schedule, schedule_raw = _load_schedule()
    compiled, meta = compile_requests(schedule)
    acl = _private_root(out, test_mode=test_mode)
    schedule_path = out / "schedule.json"
    if schedule_path.exists() and schedule_path.read_bytes() != schedule_raw:
        raise CampaignError("PRIVATE_SCHEDULE_BYTES_MISMATCH")
    if not schedule_path.exists():
        write_once(schedule_path, schedule_raw)
    manifest = _build_public_request_manifest(compiled, meta, schedule_raw)
    manifest_raw = canonical_pretty(manifest)
    public_manifest_path = REQUEST_MANIFEST_PATH
    if not test_mode:
        if public_manifest_path.exists() and public_manifest_path.read_bytes() != manifest_raw:
            raise CampaignError("PUBLIC_REQUEST_MANIFEST_ALREADY_DIFFERS")
        if not public_manifest_path.exists():
            write_once(public_manifest_path, manifest_raw)
    for row in compiled:
        path = out / "requests" / f"{row['request_id']}.bin"
        if path.exists():
            if sha(path.read_bytes()) != row["body_sha256"]:
                raise CampaignError("EXISTING_PRIVATE_REQUEST_BYTES_TAMPERED")
        else:
            write_once(path, row["_body"])
        meta_path = out / "requests" / f"{row['request_id']}.meta.json"
        safe_meta = {key: value for key, value in row.items()
                     if key not in {"_body", "reference_label_private", "visible_event_ids"}}
        if meta_path.exists():
            if json.loads(meta_path.read_bytes()) != safe_meta:
                raise CampaignError("EXISTING_PRIVATE_REQUEST_SIDECAR_MISMATCH")
        else:
            write_once(meta_path, canonical_pretty(safe_meta))
    return {
        "status": "PREPARED_OFFLINE_NO_CALLS",
        "assigned": len(compiled),
        "a1_requests": sum(row["block"] == "A1" for row in compiled),
        "a2_requests": sum(row["block"] == "A2" for row in compiled),
        "schedule_sha256": sha(schedule_raw),
        "request_manifest_sha256": sha(manifest_raw),
        "request_hashes": len(compiled),
        "maximum_input_bound": max(row["input_token_upper_bound"] for row in compiled),
        "peak_full_schedule_reserve_usd": str(_peak_reserve(compiled)),
        "private_acl": acl,
        "model_calls": 0,
    }


def _peak_reserve(rows: list[dict[str, Any]]) -> Decimal:
    total = Decimal(0)
    for row in rows:
        total += (Decimal(row["input_token_upper_bound"]) * PEAK_INPUT_RATE
                  + Decimal(MAX_OUTPUT_TOKENS) * PEAK_OUTPUT_RATE)
    return total


def _load_api_key() -> str:
    values: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            item = line.strip()
            if not item or item.startswith("#"):
                continue
            if item.startswith("export "):
                item = item[len("export "):].lstrip()
            if "=" not in item:
                continue
            name, value = item.split("=", 1)
            name, value = name.strip(), value.strip()
            if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
                value = value[1:-1]
            if name in values:
                raise CampaignError("DUPLICATE_ENV_KEY_NAME")
            values[name] = value
    if values.get("LLM_BASE_URL", "").rstrip("/") != "https://api.deepseek.com":
        raise CampaignError("LOCAL_PROVIDER_BASE_URL_MISMATCH")
    if values.get("LLM_MODEL_ID") != MODEL:
        raise CampaignError("LOCAL_PROVIDER_MODEL_ALIAS_MISMATCH")
    key = values.get("LLM_API_KEY", "")
    if not key:
        raise CampaignError("PROVIDER_CREDENTIAL_UNAVAILABLE")
    return key


def _is_offpeak(at: datetime | None = None) -> bool:
    current = at or utc_now()
    return not (current.weekday() < 5 and ((1 <= current.hour < 4) or (6 <= current.hour < 10)))


def _load_auth_and_registration() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    budget = json.loads((ROOT / "research/budget.json").read_bytes())
    batch_path = ROOT / f"research/authorizations/{APPROVAL_ID}.json"
    if not batch_path.is_file():
        raise CampaignError("IMMUTABLE_AUTHORIZATION_BATCH_MISSING")
    batch = json.loads(batch_path.read_bytes())
    from research.frozen_eval.evaluate_cycle_v2 import validate_authorization_batch
    if validate_authorization_batch(batch):
        raise CampaignError("AUTHORIZATION_BATCH_SCHEMA_INVALID")
    auth = budget.get("authorization", {})
    if batch.get("approval_id") != APPROVAL_ID or auth != {
            **batch, "status": "active"}:
        # The snapshot is intentionally a projection of the immutable batch.
        expected = {key: batch.get(key) for key in (
            "approval_id", "scope", "authorized_experiment_ids", "max_model_calls",
            "max_external_cost_usd", "approved_at_utc", "expires_at_utc", "source")}
        if auth.get("status") != "active" or any(auth.get(key) != value for key, value in expected.items()):
            raise CampaignError("BUDGET_SNAPSHOT_DOES_NOT_MATCH_AUTHORIZATION_BATCH")
    if (batch.get("scope") != AUTH_SCOPE
            or batch.get("authorized_experiment_ids") != [EXPERIMENT_ID]
            or batch.get("max_model_calls") != MAX_ATTEMPTS
            or float(batch.get("max_external_cost_usd", -1)) != float(MAX_COST_USD)
            or batch.get("expires_at_utc") != APPROVAL_EXPIRY.replace("+00:00", "Z")):
        raise CampaignError("AUTHORIZATION_SCOPE_MISMATCH")
    expires = datetime.fromisoformat(batch["expires_at_utc"].replace("Z", "+00:00"))
    if utc_now() >= expires or utc_now() >= datetime.fromisoformat(APPROVAL_EXPIRY):
        raise CampaignError("AUTHORIZATION_EXPIRED")
    if batch.get("approved_at_utc") is None:
        raise CampaignError("AUTHORIZATION_TIMESTAMP_MISSING")
    prereg = json.loads(PREREG_PATH.read_bytes())
    registration_path = PREREG_PATH.parent / "registration.json"
    registration = json.loads(registration_path.read_bytes())
    if prereg.get("experiment_id") != EXPERIMENT_ID:
        raise CampaignError("REGISTERED_EXPERIMENT_ID_MISMATCH")
    if prereg.get("authorization", {}).get("approval_id") != APPROVAL_ID:
        raise CampaignError("REGISTERED_APPROVAL_ID_MISMATCH")
    if prereg.get("authorization", {}).get("scope") != batch.get("scope"):
        raise CampaignError("REGISTERED_SCOPE_MISMATCH")
    if registration.get("preregistration_sha256") != sha(PREREG_PATH.read_bytes()):
        raise CampaignError("PREREGISTRATION_HASH_MISMATCH")
    if registration.get("authorization_batch_sha256") != sha(batch_path.read_bytes()):
        raise CampaignError("REGISTERED_AUTHORIZATION_HASH_MISMATCH")
    if prereg.get("budget", {}).get("max_model_calls") != MAX_ATTEMPTS:
        raise CampaignError("REGISTERED_CALL_CEILING_MISMATCH")
    if float(prereg.get("budget", {}).get("max_external_cost_usd", -1)) != float(MAX_COST_USD):
        raise CampaignError("REGISTERED_COST_CEILING_MISMATCH")
    return batch, prereg, registration


def _check_dispatch_gate(schedule: dict[str, Any], compiled: list[dict[str, Any]],
                         manifest_hash: str) -> tuple[dict[str, Any], str]:
    batch, prereg, registration = _load_auth_and_registration()
    if not _is_offpeak():
        raise CampaignError("CURRENT_TIME_IS_PEAK_RATE")
    if prereg.get("protocol", {}).get("frozen_request_manifest_sha256") != manifest_hash:
        raise CampaignError("FROZEN_REQUEST_MANIFEST_HASH_MISMATCH")
    if prereg.get("protocol", {}).get("schedule_sha256") != sha(canonical_pretty(schedule)):
        raise CampaignError("REGISTERED_SCHEDULE_HASH_MISMATCH")
    frozen = {item.get("path"): item.get("sha256")
              for item in prereg.get("protocol", {}).get("frozen_inputs", [])}
    for relative, digest in frozen.items():
        path = ROOT / relative
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise CampaignError("FROZEN_SOURCE_HASH_CHANGED")
    key = _load_api_key()
    return {"batch": batch, "prereg": prereg, "registration": registration}, key


def _http_once(body: bytes, key: str, timeout: int = REQUEST_TIMEOUT_SECONDS,
               *, endpoint: str = ENDPOINT,
               allow_loopback_test: bool = False) -> tuple[int, bytes, dict[str, str], float]:
    if endpoint != ENDPOINT:
        parsed = urlsplit(endpoint)
        try:
            loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
        except ValueError:
            loopback = False
        if (not allow_loopback_test or parsed.scheme != "http" or not loopback
                or parsed.username or parsed.password or parsed.query or parsed.fragment):
            raise CampaignError("PRODUCTION_ENDPOINT_IS_NOT_OFFICIAL_DEEPSEEK")
    request = urllib.request.Request(endpoint, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}",
    })

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            safe_headers = {name.lower(): value for name, value in response.headers.items()
                            if name.lower() in {"content-type", "x-request-id", "date"}}
            return response.status, response.read(), safe_headers, time.monotonic() - started
    except urllib.error.HTTPError as exc:
        safe_headers = {name.lower(): value for name, value in (exc.headers or {}).items()
                        if name.lower() in {"content-type", "x-request-id", "date"}}
        return exc.code, exc.read(), safe_headers, time.monotonic() - started


def _parse_response(raw: bytes) -> dict[str, Any]:
    response = json.loads(raw)
    if not isinstance(response, dict):
        raise ValueError("RESPONSE_ENVELOPE_INVALID")
    metadata = {
        "returned_model": response.get("model"),
        "system_fingerprint": response.get("system_fingerprint"),
        "usage": response.get("usage"),
        "finish_reason": (response.get("choices", [{}])[0].get("finish_reason")
                          if isinstance(response.get("choices"), list) and response["choices"] else None),
    }
    args, finish = runtime.parse_completion(
        response, interface="strict_function_calling", tool_name="report_evidence",
        schema=runtime.monitor_tool(sprint_baselines.TASK_DEFINITIONS["public_harm"]["allowed_labels"])[1])
    runtime.validate_monitor_arguments(
        "public_harm", sprint_baselines.TASK_DEFINITIONS["public_harm"]["allowed_labels"], args)
    metadata["finish_reason"] = finish
    metadata["prediction"] = args
    return metadata


def _usage_is_valid(usage: Any) -> bool:
    return (isinstance(usage, dict)
            and type(usage.get("prompt_tokens")) is int
            and type(usage.get("completion_tokens")) is int
            and 0 <= usage["prompt_tokens"] <= MAX_INPUT_TOKENS
            and 0 <= usage["completion_tokens"] <= MAX_OUTPUT_TOKENS)


def _verify_existing(run_dir: Path, schedule_raw: bytes,
                     compiled: list[dict[str, Any]], manifest_hash: str) -> dict[str, Any]:
    saved_schedule = run_dir / "schedule.json"
    if saved_schedule.exists() and saved_schedule.read_bytes() != schedule_raw:
        raise CampaignError("RESUMED_SCHEDULE_BYTES_MISMATCH")
    if not saved_schedule.exists():
        write_once(saved_schedule, schedule_raw)
    starts_path = run_dir / "request_ledger.jsonl"
    result_path = run_dir / "results.jsonl"
    starts = [row for row in read_jsonl(starts_path) if row.get("event") == "attempt_started"]
    start_ids = [row.get("request_id") for row in starts]
    if len(start_ids) != len(set(start_ids)):
        raise CampaignError("DUPLICATE_REQUEST_START_REQUIRES_STOP")
    if len(starts) > MAX_ATTEMPTS:
        raise CampaignError("ATTEMPT_HARD_CAP_EXCEEDED")
    compiled_map = {row["request_id"]: row for row in compiled}
    for start in starts:
        item = compiled_map.get(start.get("request_id"))
        if item is None or start.get("body_sha256") != item["body_sha256"]:
            raise CampaignError("STARTED_REQUEST_NOT_IN_FROZEN_MANIFEST")
        request_path = run_dir / "requests" / f"{item['request_id']}.bin"
        if not request_path.is_file() or sha(request_path.read_bytes()) != item["body_sha256"]:
            raise CampaignError("STARTED_REQUEST_BYTES_MISSING_OR_TAMPERED")
    results = read_jsonl(result_path)
    result_ids = [row.get("request_id") for row in results]
    if len(result_ids) != len(set(result_ids)) or not set(result_ids).issubset(set(start_ids)):
        raise CampaignError("RESULT_LEDGER_DUPLICATE_OR_ORPHAN")
    results_by_id = {row["request_id"]: row for row in results}
    terminal_events = [row for row in read_jsonl(starts_path) if row.get("event") == "attempt_terminal"]
    terminal_ids = [row.get("request_id") for row in terminal_events]
    if len(terminal_ids) != len(set(terminal_ids)) or not set(terminal_ids).issubset(set(start_ids)):
        raise CampaignError("TERMINAL_LEDGER_DUPLICATE_OR_ORPHAN")
    terminal_set = set(terminal_ids)
    # Recover a response already durably written before an interruption; never resend.
    for request_id in start_ids:
        if request_id not in results_by_id:
            response_path = run_dir / "responses" / f"{request_id}.bin"
            if response_path.exists():
                raw = response_path.read_bytes()
                result = {"request_id": request_id, "http_status": None,
                          "response_sha256": sha(raw), "response_path": f"responses/{request_id}.bin",
                          "status": "INTERRUPTED_AFTER_RESPONSE_BEFORE_RESULT", "parsed": None,
                          "terminal_at_utc": iso_now()}
            else:
                result = {"request_id": request_id, "http_status": None,
                          "response_sha256": None, "response_path": None,
                          "status": "INTERRUPTED_UNKNOWN_OUTCOME", "parsed": None,
                          "terminal_at_utc": iso_now()}
            append_jsonl(result_path, result)
            results_by_id[request_id] = result
        if request_id not in terminal_set:
            result = results_by_id[request_id]
            append_jsonl(starts_path, {
                "event": "attempt_terminal", "request_id": request_id,
                "status": result.get("status"), "http_status": result.get("http_status"),
                "response_sha256": result.get("response_sha256"),
                "at_utc": iso_now(), "recovered": True,
            })
            terminal_set.add(request_id)
    if terminal_set != set(start_ids):
        raise CampaignError("ATTEMPT_LEDGER_TERMINAL_COVERAGE_MISMATCH")
    for result in results_by_id.values():
        digest = result.get("response_sha256")
        if digest is not None:
            response_path = run_dir / result["response_path"]
            if not response_path.is_file() or sha(response_path.read_bytes()) != digest:
                raise CampaignError("SAVED_RESPONSE_BYTES_MISSING_OR_TAMPERED")
    terminal_by_id = {row["request_id"]: row for row in terminal_events}
    terminal_by_id.update({
        row["request_id"]: row for row in read_jsonl(starts_path)
        if row.get("event") == "attempt_terminal"
    })
    for request_id, result in results_by_id.items():
        terminal = terminal_by_id.get(request_id)
        if (terminal is None or terminal.get("status") != result.get("status")
                or terminal.get("response_sha256") != result.get("response_sha256")):
            raise CampaignError("ATTEMPT_TERMINAL_RESULT_MISMATCH")
    failed = [row for row in results_by_id.values()
              if (row.get("status") not in {"HTTP_200_VALID", "HTTP_200_INVALID_OUTPUT"}
                  or row.get("identity_mismatch") is True
                  or row.get("fingerprint_missing") is True
                  or row.get("fingerprint_drift") is True
                  or not _usage_is_valid(row.get("usage")))]
    if failed:
        raise CampaignError("PRIOR_FAILURE_OR_INTERRUPTION_TERMINAL_NO_RESUME")
    fingerprints = {row.get("system_fingerprint") for row in results_by_id.values()
                    if row.get("status") in {"HTTP_200_VALID", "HTTP_200_INVALID_OUTPUT"}}
    if None in fingerprints or len(fingerprints) > 1:
        raise CampaignError("PRIOR_FINGERPRINT_MISSING_OR_DRIFTED")
    return {"started_ids": set(start_ids), "results_by_id": results_by_id,
            "manifest_hash": manifest_hash}


def dispatch(out: Path = RUN_ROOT, *, transport: Callable[..., Any] | None = None,
             test_mode: bool = False) -> dict[str, Any]:
    schedule, schedule_raw = _load_schedule()
    compiled, meta = compile_requests(schedule)
    request_manifest_raw = REQUEST_MANIFEST_PATH.read_bytes() if not test_mode else canonical_pretty({
        "test_fixture_only": True, "request_rows": [{k: v for k, v in row.items()
        if k not in {"_body", "visible_event_ids", "reference_label_private"}} for row in compiled]})
    manifest_hash = sha(request_manifest_raw)
    if not test_mode:
        public_manifest = json.loads(request_manifest_raw)
        _validate_public_request_manifest(public_manifest, compiled, meta, schedule_raw)
    acl = _private_root(out, test_mode=test_mode)
    for row in compiled:
        request_path = out / "requests" / f"{row['request_id']}.bin"
        if not request_path.is_file() or sha(request_path.read_bytes()) != row["body_sha256"]:
            raise CampaignError("PREPARED_REQUEST_MISSING_OR_TAMPERED")
    if not test_mode:
        _check_dispatch_gate(schedule, compiled, manifest_hash)
        if _peak_reserve(compiled) > MAX_COST_USD:
            raise CampaignError("FULL_SCHEDULE_PEAK_RESERVE_EXCEEDS_COST_CAP")
    lock_path = out / "dispatch.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise CampaignError("DISPATCH_LOCK_EXISTS_MANUAL_REVIEW_REQUIRED") from exc
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(f"pid={os.getpid()} at={iso_now()}\n")
            stream.flush()
            os.fsync(stream.fileno())
        state = _verify_existing(out, schedule_raw, compiled, manifest_hash)
        attempted = state["started_ids"]
        results_by_id = state["results_by_id"]
        if len(attempted) >= MAX_ATTEMPTS:
            return {"status": "ALREADY_COMPLETE", "attempts": len(attempted), "new_attempts": 0}
        if not test_mode:
            _check_dispatch_gate(schedule, compiled, manifest_hash)
            api_key = _load_api_key()
        else:
            api_key = "fake-key-never-persisted"
        stop_reason = None
        new_attempts = 0
        expected_fingerprint = next((row.get("system_fingerprint") for row in results_by_id.values()
                                     if row.get("system_fingerprint")), None)
        cumulative_actual_cost = Decimal(0)
        for prior in results_by_id.values():
            usage = prior.get("usage")
            if isinstance(usage, dict) and type(usage.get("prompt_tokens")) is int and type(usage.get("completion_tokens")) is int:
                cumulative_actual_cost += (
                    Decimal(usage["prompt_tokens"]) * PEAK_INPUT_RATE
                    + Decimal(usage["completion_tokens"]) * PEAK_OUTPUT_RATE)
        reserve_by_id = {row["request_id"]: (
            Decimal(row["input_token_upper_bound"]) * PEAK_INPUT_RATE
            + Decimal(MAX_OUTPUT_TOKENS) * PEAK_OUTPUT_RATE) for row in compiled}
        prior_starts = [row for row in read_jsonl(out / "request_ledger.jsonl")
                        if row.get("event") == "attempt_started"]
        campaign_start = (datetime.fromisoformat(prior_starts[0]["at_utc"].replace("Z", "+00:00"))
                          if prior_starts else None)
        for item in compiled:
            request_id = item["request_id"]
            if request_id in attempted:
                continue
            current = utc_now()
            if current >= datetime.fromisoformat(APPROVAL_EXPIRY):
                stop_reason = "AUTHORIZATION_EXPIRED"
                break
            if campaign_start is not None and (current - campaign_start).total_seconds() >= MAX_WALLCLOCK_SECONDS:
                stop_reason = "WALLCLOCK_LIMIT"
                break
            if not _is_offpeak(current):
                stop_reason = "PEAK_RATE_WINDOW"
                break
            if len(attempted) >= MAX_ATTEMPTS:
                stop_reason = "HARD_PHYSICAL_ATTEMPT_CAP"
                break
            outstanding_reserve = sum(
                (reserve_by_id[row["request_id"]]
                 for row in compiled if row["request_id"] not in attempted),
                Decimal(0))
            if cumulative_actual_cost + outstanding_reserve > MAX_COST_USD:
                stop_reason = "HARD_COST_RESERVE_CAP"
                break
            if not test_mode:
                _check_dispatch_gate(schedule, compiled, manifest_hash)
            body_path = out / "requests" / f"{request_id}.bin"
            body = body_path.read_bytes()
            if sha(body) != item["body_sha256"]:
                raise CampaignError("REQUEST_CHANGED_AFTER_FREEZE")
            start_row = {
                "event": "attempt_started", "request_id": request_id,
                "row_sha256": item["row_sha256"], "arm_id": item["arm_id"],
                "block": item["block"], "unit_sha256": item["unit_sha256"],
                "body_sha256": item["body_sha256"], "endpoint_host": "api.deepseek.com",
                "model": MODEL, "max_output_tokens": MAX_OUTPUT_TOKENS,
                "input_token_upper_bound": item["input_token_upper_bound"],
                "reserved_peak_cost_usd": str(
                    Decimal(item["input_token_upper_bound"]) * PEAK_INPUT_RATE
                    + Decimal(MAX_OUTPUT_TOKENS) * PEAK_OUTPUT_RATE),
                "at_utc": iso_now(), "retry": False, "auth_header_saved": False,
            }
            # The request file and this durable reservation precede the network call.
            append_jsonl(out / "request_ledger.jsonl", start_row)
            if campaign_start is None:
                campaign_start = datetime.fromisoformat(start_row["at_utc"].replace("Z", "+00:00"))
            attempted.add(request_id)
            new_attempts += 1
            began = time.monotonic()
            status: int | None = None
            raw = b""
            headers: dict[str, str] = {}
            error_type: str | None = None
            try:
                if test_mode:
                    status, raw, headers = transport(body, api_key)
                else:
                    status, raw, headers, _ = _http_once(body, api_key)
            except Exception as exc:
                error_type = type(exc).__name__
            elapsed = round(time.monotonic() - began, 6)
            response_path = out / "responses" / f"{request_id}.bin"
            if status is not None:
                write_once(response_path, raw)
            parsed: dict[str, Any] | None = None
            parse_error: str | None = None
            metadata: dict[str, Any] = {}
            if status == 200 and raw:
                try:
                    metadata = _parse_response(raw)
                    prediction = metadata.pop("prediction")
                    parsed = {"label": prediction["label"],
                              "evidence_refs": prediction["evidence_refs"]}
                except Exception as exc:
                    parse_error = getattr(exc, "status", None) or type(exc).__name__
                    try:
                        envelope = json.loads(raw)
                        choices = envelope.get("choices", [])
                        metadata = {"returned_model": envelope.get("model"),
                                    "system_fingerprint": envelope.get("system_fingerprint"),
                                    "usage": envelope.get("usage"),
                                    "finish_reason": choices[0].get("finish_reason") if choices else None}
                    except Exception:
                        metadata = {}
            if status == 200 and not metadata:
                parse_error = parse_error or "RESPONSE_METADATA_INVALID"
            returned_model = metadata.get("returned_model")
            fingerprint = metadata.get("system_fingerprint")
            identity_mismatch = status == 200 and returned_model not in EXPECTED_MODELS
            fingerprint_missing = status == 200 and not isinstance(fingerprint, str)
            fingerprint_drift = bool(fingerprint and expected_fingerprint and fingerprint != expected_fingerprint)
            if fingerprint and expected_fingerprint is None:
                expected_fingerprint = fingerprint
            usage = metadata.get("usage")
            usage_valid = _usage_is_valid(usage)
            if usage_valid:
                actual_cost = (Decimal(usage["prompt_tokens"]) * PEAK_INPUT_RATE
                               + Decimal(usage["completion_tokens"]) * PEAK_OUTPUT_RATE)
                cumulative_actual_cost += actual_cost
            else:
                actual_cost = None
            if cumulative_actual_cost > MAX_COST_USD:
                stop_reason = "HARD_COST_CAP_EXCEEDED"
            status_name = ("TRANSPORT_ERROR" if error_type else
                           f"HTTP_{status}" if status != 200 else
                           "HTTP_200_INVALID_OUTPUT" if parse_error else "HTTP_200_VALID")
            response_record = {
                "request_id": request_id, "status": status_name, "http_status": status,
                "response_sha256": sha(raw) if status is not None else None,
                "response_path": f"responses/{request_id}.bin" if status is not None else None,
                "safe_response_headers": headers,
                "elapsed_seconds": elapsed, "transport_error_type": error_type,
                "parse_error_code": parse_error, "parsed": parsed,
                "returned_model": returned_model, "system_fingerprint": fingerprint,
                "finish_reason": metadata.get("finish_reason"), "usage": usage,
                "actual_peak_cost_usd": str(actual_cost) if actual_cost is not None else None,
                "identity_mismatch": identity_mismatch,
                "fingerprint_missing": fingerprint_missing,
                "fingerprint_drift": fingerprint_drift,
                "terminal_at_utc": iso_now(), "auth_header_saved": False,
            }
            append_jsonl(out / "results.jsonl", response_record)
            append_jsonl(out / "request_ledger.jsonl", {
                "event": "attempt_terminal", "request_id": request_id,
                "status": status_name, "http_status": status,
                "response_sha256": response_record["response_sha256"],
                "parse_error_code": parse_error, "at_utc": iso_now(),
                "transport_error_type": error_type,
            })
            results_by_id[request_id] = response_record
            if (error_type or status != 200 or identity_mismatch or fingerprint_missing
                    or fingerprint_drift or not usage_valid):
                stop_reason = stop_reason or (
                    "IDENTITY_MISMATCH" if identity_mismatch else
                    "FINGERPRINT_MISSING" if fingerprint_missing else
                    "FINGERPRINT_DRIFT" if fingerprint_drift else
                    "USAGE_MISSING_OR_INVALID" if not usage_valid else
                    "TRANSPORT_OR_HTTP_FAILURE")
                break
        pending = [row["request_id"] for row in compiled if row["request_id"] not in attempted]
        if pending:
            stop = {"status": "STOPPED_WITH_UNATTEMPTED_ROWS", "reason": stop_reason or "NOT_DISPATCHED",
                    "attempted": len(attempted), "unattempted": len(pending),
                    "pending_row_hashes": [next(row["row_sha256"] for row in compiled if row["request_id"] == rid)
                                            for rid in pending],
                    "at_utc": iso_now()}
            append_jsonl(out / "campaign_events.jsonl", {"event": "campaign_stopped", **stop})
        else:
            append_jsonl(out / "campaign_events.jsonl", {
                "event": "campaign_complete", "attempted": len(attempted),
                "at_utc": iso_now(), "manifest_sha256": manifest_hash,
            })
        if not test_mode:
            _private_root(out, test_mode=False)
        return {
            "status": "COMPLETE" if not pending else "STOPPED_WITH_UNATTEMPTED_ROWS",
            "assigned": MAX_ATTEMPTS, "attempts_total": len(attempted),
            "new_attempts": new_attempts, "unattempted": len(pending),
            "a1_attempts": sum(1 for row in compiled if row["request_id"] in attempted and row["block"] == "A1"),
            "a2_attempts": sum(1 for row in compiled if row["request_id"] in attempted and row["block"] == "A2"),
            "estimated_actual_peak_cost_usd": str(cumulative_actual_cost),
            "stop_reason": stop_reason, "manifest_sha256": manifest_hash,
            "private_acl": acl, "raw_data_local_only": True,
        }
    finally:
        lock_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=RUN_ROOT)
    parser.add_argument("--prepare", action="store_true", help="compile and freeze requests offline")
    parser.add_argument("--dispatch", action="store_true", help="send authorized requests to official DeepSeek")
    parser.add_argument("--offline-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.prepare == args.dispatch:
        parser.error("select exactly one of --prepare or --dispatch")
    if args.prepare:
        result = prepare(args.run, test_mode=args.offline_test)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    result = dispatch(args.run, test_mode=args.offline_test)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"COMPLETE", "ALREADY_COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
