"""Independently audit the local, no-call preparation for M4 B5 repeatability.

The audit emits hashes and aggregate counts only. It never prints request text,
private messages, credentials, or local user identifiers.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import run_m4_b5_context_sensitivity as source_runtime  # noqa: E402
RUN_ROOT = ROOT / "runs/sprint-monitor/m4-b5-view-repeatability-v2-run"
SCHEDULE_PATH = ROOT / "research/drafts/m4-b5-view-repeatability-v2-schedule.json"
INPUT_RATE = Decimal("0.15")
OUTPUT_RATE = Decimal("0.60")
MAX_OUTPUT = 512
MAX_INPUT_UPPER_BOUND = 12_500
EXPECTED_REQUEST_KEYS = {
    "model", "messages", "temperature", "thinking", "max_tokens",
    "stream", "tools", "tool_choice",
}
FORBIDDEN_RESEARCH_KEYS = {
    "assignment_id", "unit_sha256", "source_row_sha256", "repeat",
    "reference_label", "reference_answer", "condition_id", "treatment_id",
    "target_task", "public_optimal_welfare", "welfare_regret", "harm_label",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError(code)


def audit() -> dict[str, Any]:
    schedule_raw = SCHEDULE_PATH.read_bytes()
    schedule = json.loads(schedule_raw)
    manifest_path = RUN_ROOT / "request_manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    rows = manifest.get("request_rows")
    assignments = schedule.get("rows")
    require(isinstance(rows, list) and isinstance(assignments, list), "ROW_LIST_MISSING")
    require(manifest.get("experiment_id") == "m4-b5-view-repeatability-v2", "EXPERIMENT_ID_MISMATCH")
    require(len(rows) == len(assignments) == 144, "ASSIGNED_COUNT_MISMATCH")
    require(manifest.get("schedule_file_sha256") == sha(schedule_raw), "SCHEDULE_HASH_MISMATCH")
    require(manifest.get("schedule_object_sha256") == schedule.get("schedule_sha256"), "SCHEDULE_OBJECT_HASH_MISMATCH")
    require(manifest.get("raw_payloads_local_only") is True, "RAW_PAYLOAD_POLICY_MISMATCH")
    require(manifest.get("auth_headers_saved") is False, "AUTH_HEADER_POLICY_MISMATCH")
    require(manifest.get("endpoint") == "https://api.deepseek.com/chat/completions", "ENDPOINT_MISMATCH")
    require(manifest.get("model") == "deepseek-flash", "MANIFEST_MODEL_MISMATCH")
    require(manifest.get("temperature") == 0, "MANIFEST_TEMPERATURE_MISMATCH")
    require(manifest.get("thinking") == {"type": "disabled"}, "MANIFEST_THINKING_MISMATCH")
    require(manifest.get("max_output_tokens") == MAX_OUTPUT, "MANIFEST_OUTPUT_LIMIT_MISMATCH")
    require(manifest.get("retry_policy") == "zero retries; zero replacements; each attempt-start consumes its slot", "RETRY_POLICY_MISMATCH")

    source_paths = {
        "m4_episodes_sha256": source_runtime.M4_SOURCE_RUN / "episodes.jsonl",
        "m4_run_manifest_sha256": source_runtime.M4_SOURCE_RUN / "run_manifest.json",
        "m4_system_prompt_sha256": source_runtime.SYSTEM_PROMPT_PATH,
        "monitor_compiler_sha256": ROOT / "src/colluscope/deepseek_monitor_v1.py",
        "provider_runtime_sha256": ROOT / "src/colluscope/deepseek_m4_v1.py",
    }
    source_hashes = manifest.get("source_hashes")
    require(isinstance(source_hashes, dict), "SOURCE_HASHES_MISSING")
    require(set(source_hashes) == set(source_paths), "SOURCE_HASH_SET_MISMATCH")
    for name, path in source_paths.items():
        require(path.is_file() and sha(path.read_bytes()) == source_hashes[name], f"SOURCE_HASH_MISMATCH:{name}")

    try:
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(manifest_path.relative_to(ROOT))],
            cwd=ROOT, check=False,
        ).returncode == 0
    except OSError:
        ignored = False
    require(ignored, "RAW_RUN_DIRECTORY_NOT_GIT_IGNORED")

    by_assignment = {row.get("assignment_id"): row for row in rows if isinstance(row, dict)}
    require(len(by_assignment) == 144, "DUPLICATE_OR_MISSING_ASSIGNMENT_IDS")
    expected_ids = {row.get("assignment_id") for row in assignments if isinstance(row, dict)}
    require(len(expected_ids) == 144 and set(by_assignment) == expected_ids, "SCHEDULE_MANIFEST_ASSIGNMENT_MISMATCH")

    profiles: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    view_counts = {"public_only": 0, "privileged_original": 0}
    cost_reserve = Decimal("0")
    maximum_input_upper_bound = 0
    body_hash_count = 0
    for assignment in assignments:
        row = by_assignment[assignment["assignment_id"]]
        require(row.get("unit_sha256") == assignment.get("unit_sha256"), "UNIT_BINDING_MISMATCH")
        require(row.get("source_row_sha256") == assignment.get("source_row_sha256"), "SOURCE_BINDING_MISMATCH")
        require(row.get("view") == assignment.get("view"), "VIEW_BINDING_MISMATCH")
        require(row.get("repeat") == assignment.get("repeat"), "REPEAT_BINDING_MISMATCH")
        body_path = RUN_ROOT / "requests" / f"{row['request_id']}.bin"
        body = body_path.read_bytes()
        body_hash = sha(body)
        require(body_hash == row.get("body_sha256"), "REQUEST_BODY_HASH_MISMATCH")
        require(row.get("serialized_bytes") == len(body), "REQUEST_BODY_LENGTH_MISMATCH")
        upper = row.get("input_token_upper_bound")
        require(type(upper) is int and upper == len(body) * 2 + 256, "INPUT_UPPER_BOUND_MISMATCH")
        require(upper <= MAX_INPUT_UPPER_BOUND, "INPUT_UPPER_BOUND_EXCEEDED")
        request = json.loads(body)
        require(set(request) == EXPECTED_REQUEST_KEYS, "UNEXPECTED_REQUEST_FIELDS")
        require(request.get("model") == "deepseek-flash", "MODEL_ALIAS_MISMATCH")
        require(request.get("temperature") == 0, "TEMPERATURE_MISMATCH")
        require(request.get("thinking") == {"type": "disabled"}, "THINKING_MODE_MISMATCH")
        require(request.get("max_tokens") == MAX_OUTPUT, "OUTPUT_LIMIT_MISMATCH")
        require(request.get("stream") is False, "STREAM_MODE_MISMATCH")
        request_keys = {key.lower() for key in walk_keys(request)}
        require(not (request_keys & FORBIDDEN_RESEARCH_KEYS), "HIDDEN_RESEARCH_METADATA_IN_REQUEST")
        require(b"Authorization:" not in body and b"api_key" not in body.lower(), "AUTH_MATERIAL_IN_REQUEST_BODY")
        view = row.get("view")
        require(view in view_counts, "UNKNOWN_VIEW")
        view_counts[view] += 1
        profiles[(row["unit_sha256"], view)].append({"repeat": row["repeat"], "body_sha256": body_hash})
        maximum_input_upper_bound = max(maximum_input_upper_bound, upper)
        cost_reserve += (Decimal(upper) * INPUT_RATE + Decimal(MAX_OUTPUT) * OUTPUT_RATE) / Decimal(1_000_000)
        body_hash_count += 1

    require(view_counts == {"public_only": 72, "privileged_original": 72}, "VIEW_DENOMINATOR_MISMATCH")
    require(len(profiles) == 48, "CONTEXT_VIEW_PROFILE_COUNT_MISMATCH")
    for values in profiles.values():
        require(len(values) == 3, "REPEAT_DENOMINATOR_MISMATCH")
        require(len({item["repeat"] for item in values}) == 3, "REPEAT_INDEX_DUPLICATE")
        require(len({item["body_sha256"] for item in values}) == 1, "REPEATED_REQUEST_BYTES_DIFFER")
    units_by_view = {
        view: {unit for unit, profile_view in profiles if profile_view == view}
        for view in view_counts
    }
    require(units_by_view["public_only"] == units_by_view["privileged_original"] == {row["unit_sha256"] for row in assignments}, "PAIRED_CONTEXT_SET_MISMATCH")

    return {
        "status": "PASS_OFFLINE_PREPARATION_INDEPENDENT_AUDIT",
        "experiment_id": manifest["experiment_id"],
        "evidence_class": "offline_reanalysis",
        "model_calls": 0,
        "assigned_physical_attempts": 144,
        "request_bodies_hash_checked": body_hash_count,
        "context_view_profiles": len(profiles),
        "identical_repeat_profiles": len(profiles),
        "view_counts": view_counts,
        "maximum_conservative_input_upper_bound": maximum_input_upper_bound,
        "input_bound_definition": "2 * serialized UTF-8 request bytes + 256 framing tokens; not provider tokenizer output",
        "maximum_output_tokens": MAX_OUTPUT,
        "offpeak_worst_case_cost_reserve_usd": str(cost_reserve),
        "raw_run_directory_git_ignored": ignored,
        "raw_private_payloads_printed": False,
        "request_manifest_sha256": sha(manifest_raw),
        "source_hashes": source_hashes,
        "schedule_file_sha256": sha(schedule_raw),
        "schedule_object_sha256": schedule.get("schedule_sha256"),
    }


if __name__ == "__main__":
    try:
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": f"{type(exc).__name__}:{exc}"}, ensure_ascii=False, indent=2))
        raise
