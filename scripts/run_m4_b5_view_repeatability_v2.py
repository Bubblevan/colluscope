#!/usr/bin/env python3
"""Prepare or dispatch the frozen M4 B5 exact-view repeatability screen.

Dispatch is disabled until a schema-valid registration and a matching,
scope-specific authorization exist. Raw request/response bytes stay under the
Git-ignored restricted run directory. `--offline-test` permits only an
injected transport pointed at loopback; it cannot use the provider key.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Callable
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import run_m4_b5_context_sensitivity as source_runtime  # noqa: E402

EXPERIMENT_ID = "m4-b5-view-repeatability-v2"
MODEL = "deepseek-flash"
EXPECTED_MODELS = {"deepseek-flash", "DeepSeek-V4.1-Flash-1017"}
ENDPOINT = "https://api.deepseek.com/chat/completions"
SCHEDULE_PATH = ROOT / "research/drafts/m4-b5-view-repeatability-v2-schedule.json"
PREREG_DRAFT = ROOT / "research/drafts/m4-b5-view-repeatability-v2-preregistration.json"
REGISTERED_ROOT = ROOT / "research/experiments" / EXPERIMENT_ID
RUN_ROOT = ROOT / "runs/sprint-monitor" / f"{EXPERIMENT_ID}-run"
MAX_ATTEMPTS = 144
MAX_COST_USD = Decimal("0.35")
MAX_INPUT_TOKENS = 12_500
MAX_OUTPUT_TOKENS = 512
MAX_WALLCLOCK_SECONDS = 4 * 60 * 60
OFFPEAK_INPUT_RATE = Decimal("0.15") / Decimal(1_000_000)
OFFPEAK_OUTPUT_RATE = Decimal("0.60") / Decimal(1_000_000)
REQUEST_TIMEOUT_SECONDS = 90


class RunnerError(RuntimeError):
    """Sanitized stop code; never include payloads, secrets, or private text."""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def canonical_pretty(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      indent=2).encode("utf-8") + b"\n"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        stream.write(canonical(row) + b"\n")
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
    output: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RunnerError("LEDGER_ROW_NOT_OBJECT")
        output.append(value)
    return output


def load_schedule() -> tuple[dict[str, Any], bytes]:
    raw = SCHEDULE_PATH.read_bytes()
    schedule = json.loads(raw)
    stored = schedule.get("schedule_sha256")
    unsigned = dict(schedule)
    unsigned.pop("schedule_sha256", None)
    if stored != sha(canonical(unsigned)):
        raise RunnerError("SCHEDULE_CANONICAL_HASH_MISMATCH")
    draft = json.loads(PREREG_DRAFT.read_bytes())
    pinned = next((x.get("sha256") for x in draft.get("frozen_inputs", [])
                   if x.get("path") == "research/drafts/m4-b5-view-repeatability-v2-schedule.json"), None)
    if pinned != sha(raw) or draft.get("protocol", {}).get("schedule_sha256") != stored:
        raise RunnerError("DRAFT_SCHEDULE_PIN_MISMATCH")
    if schedule.get("experiment_id") != EXPERIMENT_ID:
        raise RunnerError("SCHEDULE_EXPERIMENT_ID_MISMATCH")
    rows = schedule.get("rows")
    if not isinstance(rows, list) or len(rows) != MAX_ATTEMPTS:
        raise RunnerError("SCHEDULE_ASSIGNMENT_COUNT_MISMATCH")
    ids = [row.get("assignment_id") for row in rows if isinstance(row, dict)]
    if len(ids) != MAX_ATTEMPTS or len(set(ids)) != MAX_ATTEMPTS:
        raise RunnerError("SCHEDULE_ASSIGNMENT_ID_MISMATCH")
    return schedule, raw


def _compile_requests(schedule: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    contexts, source_meta = source_runtime._m4_sources()
    by_unit = {sha(row["case_ref"].encode("utf-8")): row for row in contexts}
    if len(by_unit) != 24:
        raise RunnerError("M4_SOURCE_CONTEXT_COUNT_MISMATCH")
    compiled: list[dict[str, Any]] = []
    profile_hashes: dict[tuple[str, str], set[str]] = defaultdict(set)
    source_row_map: dict[tuple[str, str], set[str]] = defaultdict(set)
    for assignment in schedule["rows"]:
        unit = assignment.get("unit_sha256")
        view = assignment.get("view")
        repeat = assignment.get("repeat")
        if unit not in by_unit or view not in {"public_only", "privileged_original"} or repeat not in {1, 2, 3}:
            raise RunnerError("ASSIGNMENT_FIELDS_INVALID")
        source = by_unit[unit]
        permission = "public_only" if view == "public_only" else "privileged_audit"
        body, request_row = source_runtime._m4_request(source, permission)
        if not body or b"Authorization" in body or b"LLM_API_KEY" in body:
            raise RunnerError("REQUEST_BODY_INVALID_OR_AUTH_MARKER_PRESENT")
        if view == "public_only" and any(
                event.get("type") == "message"
                for event in request_row.get("evidence", {}).get("events", [])):
            raise RunnerError("PUBLIC_ONLY_REQUEST_CONTAINS_MESSAGE_EVENT")
        token_bound = len(body) * 2 + 256
        if token_bound > MAX_INPUT_TOKENS:
            raise RunnerError("REQUEST_EXCEEDS_FROZEN_INPUT_TOKEN_BOUND")
        body_hash = sha(body)
        profile = (unit, view)
        profile_hashes[profile].add(body_hash)
        source_row_map[profile].add(assignment["source_row_sha256"])
        request_id = "m4b5v2_" + assignment["assignment_id"][:24]
        compiled.append({
            "request_id": request_id,
            "assignment_id": assignment["assignment_id"],
            "unit_sha256": unit,
            "view": view,
            "repeat": repeat,
            "source_row_sha256": assignment["source_row_sha256"],
            "body_sha256": body_hash,
            "serialized_bytes": len(body),
            "input_token_upper_bound": token_bound,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "_body": body,
        })
    if len(compiled) != MAX_ATTEMPTS or len({r["request_id"] for r in compiled}) != MAX_ATTEMPTS:
        raise RunnerError("COMPILED_REQUEST_COUNT_OR_ID_COLLISION")
    if any(len(values) != 1 for values in profile_hashes.values()):
        raise RunnerError("REPEATED_REQUEST_BODY_BYTES_DIFFER_WITHIN_VIEW")
    if any(len(values) != 1 for values in source_row_map.values()):
        raise RunnerError("SOURCE_ROW_PROFILE_MISMATCH")
    if len(profile_hashes) != 48:
        raise RunnerError("CONTEXT_VIEW_PROFILE_COUNT_MISMATCH")
    source_hashes = {
        "m4_episodes_sha256": sha((source_runtime.M4_SOURCE_RUN / "episodes.jsonl").read_bytes()),
        "m4_run_manifest_sha256": sha((source_runtime.M4_SOURCE_RUN / "run_manifest.json").read_bytes()),
        "m4_system_prompt_sha256": sha(source_runtime.SYSTEM_PROMPT_PATH.read_bytes()),
        "monitor_compiler_sha256": sha((ROOT / "src/colluscope/deepseek_monitor_v1.py").read_bytes()),
        "provider_runtime_sha256": sha((ROOT / "src/colluscope/deepseek_m4_v1.py").read_bytes()),
    }
    return compiled, source_hashes


def _manifest(compiled: list[dict[str, Any]], schedule_raw: bytes,
              source_hashes: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "schedule_file_sha256": sha(schedule_raw),
        "schedule_object_sha256": json.loads(schedule_raw)["schedule_sha256"],
        "source_hashes": source_hashes,
        "assigned_attempts": len(compiled),
        "retry_policy": "zero retries; zero replacements; each attempt-start consumes its slot",
        "endpoint": ENDPOINT,
        "model": MODEL,
        "temperature": 0,
        "thinking": {"type": "disabled"},
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "raw_payloads_local_only": True,
        "auth_headers_saved": False,
        "request_rows": [{k: v for k, v in row.items() if k != "_body"} for row in compiled],
    }


def _private_root(out: Path, *, test_mode: bool) -> dict[str, Any]:
    if test_mode:
        allowed = (ROOT / "runs/sprint-monitor").resolve()
        resolved = out.resolve()
        if allowed not in resolved.parents:
            raise RunnerError("OFFLINE_TEST_OUTPUT_MUST_STAY_IN_RESTRICTED_RUNS")
        acl = source_runtime._private_root(out, test_mode=False)
        return {**acl, "offline_test_only": True}
    return source_runtime._private_root(out, test_mode=False)


def prepare(out: Path = RUN_ROOT, *, test_mode: bool = False) -> dict[str, Any]:
    schedule, schedule_raw = load_schedule()
    compiled, source_hashes = _compile_requests(schedule)
    acl = _private_root(out, test_mode=test_mode)
    schedule_path = out / "schedule.json"
    if schedule_path.exists() and schedule_path.read_bytes() != schedule_raw:
        raise RunnerError("PREPARED_SCHEDULE_BYTES_MISMATCH")
    if not schedule_path.exists():
        write_once(schedule_path, schedule_raw)
    manifest_raw = canonical_pretty(_manifest(compiled, schedule_raw, source_hashes))
    manifest_path = out / "request_manifest.json"
    if manifest_path.exists() and manifest_path.read_bytes() != manifest_raw:
        raise RunnerError("PREPARED_REQUEST_MANIFEST_MISMATCH")
    if not manifest_path.exists():
        write_once(manifest_path, manifest_raw)
    for row in compiled:
        request_path = out / "requests" / f"{row['request_id']}.bin"
        if request_path.exists():
            if sha(request_path.read_bytes()) != row["body_sha256"]:
                raise RunnerError("PREPARED_REQUEST_BYTES_TAMPERED")
        else:
            write_once(request_path, row["_body"])
        safe_meta = {k: v for k, v in row.items() if k != "_body"}
        meta_path = out / "requests" / f"{row['request_id']}.meta.json"
        meta_raw = canonical_pretty(safe_meta)
        if meta_path.exists() and meta_path.read_bytes() != meta_raw:
            raise RunnerError("PREPARED_REQUEST_METADATA_MISMATCH")
        if not meta_path.exists():
            write_once(meta_path, meta_raw)
    reserve = sum((Decimal(row["input_token_upper_bound"]) * OFFPEAK_INPUT_RATE
                   + Decimal(MAX_OUTPUT_TOKENS) * OFFPEAK_OUTPUT_RATE) for row in compiled)
    if reserve > MAX_COST_USD:
        raise RunnerError("FULL_SCHEDULE_COST_RESERVE_EXCEEDS_CAP")
    return {
        "status": "PREPARED_OFFLINE_NO_CALLS",
        "experiment_id": EXPERIMENT_ID,
        "assigned": len(compiled),
        "public_only": sum(row["view"] == "public_only" for row in compiled),
        "privileged_original": sum(row["view"] == "privileged_original" for row in compiled),
        "context_view_profiles": 48,
        "request_manifest_sha256": sha(manifest_raw),
        "schedule_file_sha256": sha(schedule_raw),
        "max_input_token_bound": max(row["input_token_upper_bound"] for row in compiled),
        "offpeak_cost_reserve_usd": str(reserve),
        "private_acl": acl,
        "model_calls": 0,
    }


def _is_offpeak(at: datetime | None = None) -> bool:
    now = at or utc_now()
    return not (now.weekday() < 5 and ((1 <= now.hour < 4) or (6 <= now.hour < 10)))


def _production_gate(out: Path, schedule: dict[str, Any], schedule_raw: bytes,
                     compiled: list[dict[str, Any]], manifest_raw: bytes) -> tuple[dict[str, Any], str]:
    prereg_path = REGISTERED_ROOT / "preregistration.json"
    registration_path = REGISTERED_ROOT / "registration.json"
    if not prereg_path.is_file() or not registration_path.is_file():
        raise RunnerError("NEW_EXPERIMENT_NOT_REGISTERED")
    prereg = json.loads(prereg_path.read_bytes())
    registration = json.loads(registration_path.read_bytes())
    if prereg.get("experiment_id") != EXPERIMENT_ID:
        raise RunnerError("REGISTERED_EXPERIMENT_ID_MISMATCH")
    if registration.get("experiment_id") != EXPERIMENT_ID:
        raise RunnerError("REGISTERED_EXPERIMENT_ID_MISMATCH")
    if registration.get("preregistration_sha256") != sha(prereg_path.read_bytes()):
        raise RunnerError("REGISTERED_PREREG_HASH_MISMATCH")
    protocol = prereg.get("protocol", {})
    if protocol.get("schedule_sha256") != schedule["schedule_sha256"]:
        raise RunnerError("REGISTERED_SCHEDULE_HASH_MISMATCH")
    if protocol.get("request_manifest_sha256") != sha(manifest_raw):
        raise RunnerError("REGISTERED_REQUEST_MANIFEST_HASH_MISMATCH")
    if protocol.get("max_input_token_bound") != max(row["input_token_upper_bound"] for row in compiled):
        raise RunnerError("REGISTERED_INPUT_TOKEN_BOUND_MISMATCH")
    budget = prereg.get("budget", {})
    if (budget.get("max_model_calls") != MAX_ATTEMPTS
            or budget.get("max_physical_attempts") != MAX_ATTEMPTS
            or Decimal(str(budget.get("max_external_cost_usd", -1))) != MAX_COST_USD
            or budget.get("retries") != 0 or budget.get("replacements") != 0):
        raise RunnerError("REGISTERED_BUDGET_MISMATCH")
    frozen = {x.get("path"): x.get("sha256") for x in protocol.get("frozen_inputs", [])}
    for relative, digest in frozen.items():
        path = ROOT / relative
        if not path.is_file() or sha(path.read_bytes()) != digest:
            raise RunnerError("FROZEN_INPUT_HASH_MISMATCH")
    approval_id = prereg.get("authorization", {}).get("approval_id")
    if not isinstance(approval_id, str) or not approval_id:
        raise RunnerError("REGISTERED_APPROVAL_ID_MISSING")
    batch_path = ROOT / "research/authorizations" / f"{approval_id}.json"
    if not batch_path.is_file():
        raise RunnerError("IMMUTABLE_AUTHORIZATION_BATCH_MISSING")
    batch = json.loads(batch_path.read_bytes())
    from research.frozen_eval.evaluate_cycle_v2 import validate_authorization_batch
    if validate_authorization_batch(batch):
        raise RunnerError("AUTHORIZATION_BATCH_INVALID")
    if (batch.get("authorized_experiment_ids") != [EXPERIMENT_ID]
            or batch.get("max_model_calls") != MAX_ATTEMPTS
            or Decimal(str(batch.get("max_external_cost_usd", -1))) != MAX_COST_USD):
        raise RunnerError("AUTHORIZATION_SCOPE_MISMATCH")
    if batch.get("scope") != prereg.get("authorization", {}).get("scope"):
        raise RunnerError("REGISTERED_SCOPE_DOES_NOT_MATCH_USER_APPROVAL")
    expires = datetime.fromisoformat(batch["expires_at_utc"].replace("Z", "+00:00"))
    if utc_now() >= expires:
        raise RunnerError("AUTHORIZATION_EXPIRED")
    if not _is_offpeak():
        raise RunnerError("CURRENT_TIME_IS_PEAK_RATE")
    if registration.get("authorization_batch_sha256") != sha(batch_path.read_bytes()):
        raise RunnerError("REGISTERED_AUTHORIZATION_HASH_MISMATCH")
    budget = json.loads((ROOT / "research/budget.json").read_bytes())
    active = budget.get("authorization", {})
    for key in ("approval_id", "scope", "authorized_experiment_ids", "max_model_calls",
                "max_external_cost_usd", "approved_at_utc", "expires_at_utc", "source"):
        if active.get(key) != batch.get(key):
            raise RunnerError("BUDGET_AUTHORIZATION_SNAPSHOT_MISMATCH")
    if active.get("status") != "active":
        raise RunnerError("BUDGET_AUTHORIZATION_NOT_ACTIVE")
    key = source_runtime._load_api_key()
    return {"prereg": prereg, "registration": registration, "batch": batch}, key


def _verify_resume(out: Path, schedule_raw: bytes,
                   compiled: list[dict[str, Any]], manifest_hash: str) -> dict[str, Any]:
    saved = out / "schedule.json"
    if not saved.is_file() or saved.read_bytes() != schedule_raw:
        raise RunnerError("RESUMED_SCHEDULE_MISMATCH")
    starts = [r for r in read_jsonl(out / "request_ledger.jsonl") if r.get("event") == "attempt_started"]
    start_ids = [r.get("request_id") for r in starts]
    if len(start_ids) != len(set(start_ids)) or len(start_ids) > MAX_ATTEMPTS:
        raise RunnerError("DUPLICATE_OR_OVER_CAP_ATTEMPT_START")
    compiled_map = {r["request_id"]: r for r in compiled}
    for start in starts:
        row = compiled_map.get(start.get("request_id"))
        if row is None or start.get("body_sha256") != row["body_sha256"]:
            raise RunnerError("ATTEMPT_START_NOT_IN_FROZEN_MANIFEST")
        request_path = out / "requests" / f"{row['request_id']}.bin"
        if not request_path.is_file() or sha(request_path.read_bytes()) != row["body_sha256"]:
            raise RunnerError("STARTED_REQUEST_BYTES_MISSING_OR_TAMPERED")
    results = read_jsonl(out / "results.jsonl")
    result_ids = [r.get("request_id") for r in results]
    if len(result_ids) != len(set(result_ids)) or not set(result_ids).issubset(set(start_ids)):
        raise RunnerError("RESULT_LEDGER_DUPLICATE_OR_ORPHAN")
    terminal = [r for r in read_jsonl(out / "request_ledger.jsonl") if r.get("event") == "attempt_terminal"]
    terminal_ids = [r.get("request_id") for r in terminal]
    if len(terminal_ids) != len(set(terminal_ids)) or not set(terminal_ids).issubset(set(start_ids)):
        raise RunnerError("TERMINAL_LEDGER_DUPLICATE_OR_ORPHAN")
    recovered_ids: list[str] = []
    results_by_id = {row["request_id"]: row for row in results}
    terminal_by_id = {row["request_id"]: row for row in terminal}
    for request_id in start_ids:
        if request_id not in results_by_id:
            response_path = out / "responses" / f"{request_id}.bin"
            raw = response_path.read_bytes() if response_path.exists() else None
            recovered = {
                "request_id": request_id,
                "status": "INTERRUPTED_AFTER_RESPONSE_BEFORE_RESULT" if raw is not None else "INTERRUPTED_UNKNOWN_OUTCOME",
                "http_status": None,
                "response_sha256": sha(raw) if raw is not None else None,
                "response_path": f"responses/{request_id}.bin" if raw is not None else None,
                "parsed": None,
                "recovered_after_process_interruption": True,
                "terminal_at_utc": iso_now(),
                "auth_header_saved": False,
            }
            append_jsonl(out / "results.jsonl", recovered)
            results_by_id[request_id] = recovered
            recovered_ids.append(request_id)
        if request_id not in terminal_by_id:
            result = results_by_id[request_id]
            terminal_row = {
                "event": "attempt_terminal", "request_id": request_id,
                "status": result.get("status"), "http_status": result.get("http_status"),
                "response_sha256": result.get("response_sha256"),
                "recovered_after_process_interruption": True, "at_utc": iso_now(),
            }
            append_jsonl(out / "request_ledger.jsonl", terminal_row)
            terminal_by_id[request_id] = terminal_row
            recovered_ids.append(request_id)
    if set(results_by_id) != set(start_ids) or set(terminal_by_id) != set(start_ids):
        raise RunnerError("ATTEMPT_TERMINAL_COVERAGE_MISMATCH")
    if recovered_ids:
        append_jsonl(out / "campaign_events.jsonl", {
            "event": "interrupted_attempts_terminalized_no_resend",
            "request_ids": sorted(set(recovered_ids)), "at_utc": iso_now(),
        })
    for result in results_by_id.values():
        if result.get("response_sha256") is not None:
            response_path = out / result["response_path"]
            if not response_path.is_file() or sha(response_path.read_bytes()) != result["response_sha256"]:
                raise RunnerError("SAVED_RESPONSE_BYTES_MISSING_OR_TAMPERED")
    events = read_jsonl(out / "campaign_events.jsonl")
    if any(row.get("event") == "dispatch_stopped" for row in events):
        raise RunnerError("PRIOR_STOP_REQUIRES_MANUAL_REVIEW")
    prior_results = results_by_id
    fingerprints = {row.get("system_fingerprint") for row in results_by_id.values()
                    if row.get("http_status") == 200}
    if None in fingerprints or len(fingerprints) > 1:
        raise RunnerError("PRIOR_FINGERPRINT_MISSING_OR_DRIFTED")
    return {"started_ids": set(start_ids), "results_by_id": prior_results,
            "manifest_hash": manifest_hash, "recovered_ids": sorted(set(recovered_ids))}


def _local_test_transport(body: bytes, key: str, endpoint: str) -> tuple[int, bytes, dict[str, str]]:
    parsed = urlsplit(endpoint)
    try:
        loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if parsed.scheme != "http" or not loopback or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RunnerError("OFFLINE_TEST_ENDPOINT_MUST_BE_LOOPBACK_HTTP")
    request = urllib.request.Request(endpoint, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}",
    })

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, response_headers, new_url):
            return None

    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), urllib.request.HTTPHandler(), NoRedirect())
    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            headers = {name.lower(): value for name, value in response.headers.items()
                       if name.lower() in {"content-type", "x-request-id", "date"}}
            return response.status, response.read(), headers
    except urllib.error.HTTPError as exc:
        headers = {name.lower(): value for name, value in (exc.headers or {}).items()
                   if name.lower() in {"content-type", "x-request-id", "date"}}
        return exc.code, exc.read(), headers


def dispatch(out: Path = RUN_ROOT, *, test_mode: bool = False,
             endpoint: str = ENDPOINT,
             transport: Callable[[bytes, str, str], tuple[int, bytes, dict[str, str]]] | None = None) -> dict[str, Any]:
    schedule, schedule_raw = load_schedule()
    compiled, source_hashes = _compile_requests(schedule)
    manifest_raw = canonical_pretty(_manifest(compiled, schedule_raw, source_hashes))
    manifest_hash = sha(manifest_raw)
    acl = _private_root(out, test_mode=test_mode)
    for row in compiled:
        path = out / "requests" / f"{row['request_id']}.bin"
        if not path.is_file() or sha(path.read_bytes()) != row["body_sha256"]:
            raise RunnerError("PREPARED_REQUEST_MISSING_OR_TAMPERED")
    if (out / "request_manifest.json").read_bytes() != manifest_raw:
        raise RunnerError("PREPARED_MANIFEST_MISMATCH")
    if test_mode:
        if transport is None:
            raise RunnerError("OFFLINE_TEST_REQUIRES_INJECTED_LOOPBACK_TRANSPORT")
        parsed = urlsplit(endpoint)
        try:
            loopback = ipaddress.ip_address(parsed.hostname or "").is_loopback
        except ValueError:
            loopback = False
        if (parsed.scheme != "http" or not loopback or parsed.username or parsed.password
                or parsed.query or parsed.fragment):
            raise RunnerError("OFFLINE_TEST_ENDPOINT_MUST_BE_LOOPBACK_HTTP")
        key = "offline-test-key-never-saved"
    else:
        if endpoint != ENDPOINT:
            raise RunnerError("PRODUCTION_ENDPOINT_MUST_BE_OFFICIAL_DEEPSEEK")
        _gate, key = _production_gate(out, schedule, schedule_raw, compiled, manifest_raw)

    lock_path = out / "dispatch.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RunnerError("DISPATCH_LOCK_EXISTS_MANUAL_REVIEW_REQUIRED") from exc
    try:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(f"pid={os.getpid()} at={iso_now()}\n")
            stream.flush()
            os.fsync(stream.fileno())
        state = _verify_resume(out, schedule_raw, compiled, manifest_hash)
        attempted = state["started_ids"]
        results = state["results_by_id"]
        if len(attempted) == MAX_ATTEMPTS:
            return {"status": "ALREADY_COMPLETE", "assigned": MAX_ATTEMPTS,
                    "attempts_total": len(attempted), "new_attempts": 0,
                    "unattempted": 0}
        starts = [r for r in read_jsonl(out / "request_ledger.jsonl") if r.get("event") == "attempt_started"]
        run_start = datetime.fromisoformat(starts[0]["at_utc"].replace("Z", "+00:00")) if starts else None
        fingerprint = next((r.get("system_fingerprint") for r in results.values()
                            if r.get("system_fingerprint")), None)
        actual_cost = sum((Decimal(str(r.get("actual_offpeak_cost_usd", "0"))) for r in results.values()), Decimal(0))
        reserves = {r["request_id"]: (Decimal(r["input_token_upper_bound"]) * OFFPEAK_INPUT_RATE
                                       + Decimal(MAX_OUTPUT_TOKENS) * OFFPEAK_OUTPUT_RATE) for r in compiled}
        new_attempts = 0
        stop_reason: str | None = None
        for row in compiled:
            request_id = row["request_id"]
            if request_id in attempted:
                continue
            now = utc_now()
            if len(attempted) >= MAX_ATTEMPTS:
                stop_reason = "HARD_ATTEMPT_CAP"
                break
            if run_start and (now - run_start).total_seconds() >= MAX_WALLCLOCK_SECONDS:
                stop_reason = "WALLCLOCK_CAP"
                break
            if not test_mode:
                _gate, _fresh_key = _production_gate(out, schedule, schedule_raw, compiled, manifest_raw)
                if _fresh_key != key:
                    stop_reason = "CREDENTIAL_CHANGED_DURING_RUN"
                    break
            outstanding = sum((reserves[item["request_id"]] for item in compiled
                               if item["request_id"] not in attempted), Decimal(0))
            if actual_cost + outstanding > MAX_COST_USD:
                stop_reason = "HARD_COST_RESERVE_CAP"
                break
            body_path = out / "requests" / f"{request_id}.bin"
            body = body_path.read_bytes()
            if sha(body) != row["body_sha256"]:
                raise RunnerError("REQUEST_CHANGED_AFTER_FREEZE")
            start = {
                "event": "attempt_started", "request_id": request_id,
                "assignment_id": row["assignment_id"], "unit_sha256": row["unit_sha256"],
                "view": row["view"], "repeat": row["repeat"],
                "body_sha256": row["body_sha256"], "endpoint_host": "loopback-test" if test_mode else "api.deepseek.com",
                "model": MODEL, "max_output_tokens": MAX_OUTPUT_TOKENS,
                "input_token_upper_bound": row["input_token_upper_bound"],
                "reserved_offpeak_cost_usd": str(reserves[request_id]),
                "at_utc": iso_now(), "retry": False, "auth_header_saved": False,
            }
            append_jsonl(out / "request_ledger.jsonl", start)
            if run_start is None:
                run_start = datetime.fromisoformat(start["at_utc"].replace("Z", "+00:00"))
            attempted.add(request_id)
            new_attempts += 1
            began = time.monotonic()
            status: int | None = None
            raw = b""
            headers: dict[str, str] = {}
            error: str | None = None
            try:
                if transport is not None:
                    status, raw, headers = transport(body, key, endpoint)
                else:
                    status, raw, headers, _elapsed = source_runtime._http_once(body, key)
            except Exception as exc:
                error = type(exc).__name__
            elapsed = round(time.monotonic() - began, 6)
            response_path = out / "responses" / f"{request_id}.bin"
            if status is not None:
                write_once(response_path, raw)
            meta: dict[str, Any] = {}
            parsed: dict[str, Any] | None = None
            parse_error: str | None = None
            if status == 200 and raw:
                try:
                    meta = source_runtime._parse_response(raw)
                    prediction = meta.pop("prediction")
                    parsed = {"label": prediction["label"], "evidence_refs": prediction["evidence_refs"]}
                except Exception as exc:
                    parse_error = getattr(exc, "status", None) or type(exc).__name__
                    try:
                        envelope = json.loads(raw)
                        choices = envelope.get("choices", [])
                        meta = {"returned_model": envelope.get("model"),
                                "system_fingerprint": envelope.get("system_fingerprint"),
                                "usage": envelope.get("usage"),
                                "finish_reason": choices[0].get("finish_reason") if choices else None}
                    except Exception:
                        meta = {}
            returned_model = meta.get("returned_model")
            current_fingerprint = meta.get("system_fingerprint")
            identity_mismatch = status == 200 and returned_model not in EXPECTED_MODELS
            fingerprint_missing = status == 200 and not isinstance(current_fingerprint, str)
            fingerprint_drift = bool(current_fingerprint and fingerprint and current_fingerprint != fingerprint)
            if current_fingerprint and fingerprint is None:
                fingerprint = current_fingerprint
            usage = meta.get("usage")
            usage_valid = source_runtime._usage_is_valid(usage)
            actual = None
            if usage_valid:
                actual = (Decimal(usage["prompt_tokens"]) * OFFPEAK_INPUT_RATE
                          + Decimal(usage["completion_tokens"]) * OFFPEAK_OUTPUT_RATE)
                actual_cost += actual
            status_name = ("TRANSPORT_ERROR" if error else
                           f"HTTP_{status}_INVALID_OUTPUT" if status == 200 and parse_error else
                           "HTTP_200_VALID" if status == 200 else f"HTTP_{status}")
            result = {
                "request_id": request_id, "status": status_name, "http_status": status,
                "response_sha256": sha(raw) if status is not None else None,
                "response_path": f"responses/{request_id}.bin" if status is not None else None,
                "safe_response_headers": {k: v for k, v in headers.items()
                                          if k.lower() in {"content-type", "x-request-id", "date"}},
                "elapsed_seconds": elapsed, "transport_error_type": error,
                "parse_error_code": parse_error, "parsed": parsed,
                "returned_model": returned_model, "system_fingerprint": current_fingerprint,
                "finish_reason": meta.get("finish_reason"), "usage": usage,
                "actual_offpeak_cost_usd": str(actual) if actual is not None else None,
                "identity_mismatch": identity_mismatch,
                "fingerprint_missing": fingerprint_missing,
                "fingerprint_drift": fingerprint_drift,
                "terminal_at_utc": iso_now(), "auth_header_saved": False,
            }
            append_jsonl(out / "results.jsonl", result)
            append_jsonl(out / "request_ledger.jsonl", {
                "event": "attempt_terminal", "request_id": request_id,
                "status": status_name, "http_status": status,
                "response_sha256": result["response_sha256"], "at_utc": iso_now(),
                "transport_error_type": error, "parse_error_code": parse_error,
            })
            results[request_id] = result
            if (error or status != 200 or identity_mismatch or fingerprint_missing
                    or fingerprint_drift or not usage_valid or actual_cost > MAX_COST_USD):
                stop_reason = ("TRANSPORT_OR_HTTP_FAILURE" if error or status != 200 else
                               "IDENTITY_MISMATCH" if identity_mismatch else
                               "FINGERPRINT_MISSING" if fingerprint_missing else
                               "FINGERPRINT_DRIFT" if fingerprint_drift else
                               "USAGE_MISSING_OR_INVALID" if not usage_valid else
                               "HARD_COST_CAP_EXCEEDED")
                break
        pending = [r["request_id"] for r in compiled if r["request_id"] not in attempted]
        status = "COMPLETE" if not pending else "STOPPED_WITH_UNATTEMPTED_ROWS"
        event = {"event": "campaign_complete" if not pending else "dispatch_stopped",
                 "experiment_id": EXPERIMENT_ID, "status": status,
                 "reason": stop_reason, "attempted": len(attempted),
                 "unattempted": len(pending), "at_utc": iso_now(),
                 "manifest_sha256": manifest_hash}
        append_jsonl(out / "campaign_events.jsonl", event)
        if not test_mode:
            _private_root(out, test_mode=False)
        return {"status": status, "assigned": MAX_ATTEMPTS,
                "attempts_total": len(attempted), "new_attempts": new_attempts,
                "unattempted": len(pending), "stop_reason": stop_reason,
                "actual_offpeak_cost_usd": str(actual_cost),
                "manifest_sha256": manifest_hash, "private_acl": acl,
                "raw_data_local_only": True}
    finally:
        lock_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=RUN_ROOT)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--dispatch", action="store_true")
    parser.add_argument("--offline-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.offline_test:
        parser.error("--offline-test is only available through the injected Python test API")
    if args.prepare == args.dispatch:
        parser.error("select exactly one of --prepare or --dispatch")
    result = prepare(args.run) if args.prepare else dispatch(args.run)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("status") in {"PREPARED_OFFLINE_NO_CALLS", "COMPLETE", "ALREADY_COMPLETE"} else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as exc:
        print(f"RUNNER_ERROR:{exc}", file=sys.stderr)
        raise SystemExit(2)
