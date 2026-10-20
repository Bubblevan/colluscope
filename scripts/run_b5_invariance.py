#!/usr/bin/env python3
"""One-shot, zero-retry DeepSeek runner for the frozen B5 stability schedule."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import freeze_b5_invariance_schedule as freezer
from scripts import project_monitor_http_request_v2 as projector
from scripts.local_llama_security import restrict_private_directory_acl, verify_private_directory_acl

SCHEDULE = freezer.OUT
PROMPT_PATH = ROOT / "prompts/m4-deepseek-agent-v1/monitor-system.txt"
RUN_ROOT = ROOT / "runs/sprint-monitor/b5-evidence-view-stability-v1"
ENDPOINT = "https://api.deepseek.com/chat/completions"
APPROVAL_ID = "DS-FLASH-1200-2P50-20261020"
EXPERIMENT_ID = "b5-evidence-view-stability-120"
STOP_AT_UTC = "2026-10-21T01:00:00+00:00"
RATE_INPUT_PEAK = 0.30 / 1_000_000
RATE_OUTPUT_PEAK = 1.20 / 1_000_000
RATE_INPUT_OFFPEAK = 0.15 / 1_000_000
RATE_OUTPUT_OFFPEAK = 0.60 / 1_000_000
MAX_CALLS = 120
FROZEN_SCHEDULE_ROWS = 120
MAX_RESERVED_USD = 0.25
REQUEST_TIMEOUT_SECONDS = 90


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def now() -> datetime:
    return datetime.now(timezone.utc)


def append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(canonical(row) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def load_schedule(path: Path = SCHEDULE) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    doc = json.loads(raw)
    if raw != json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n":
        raise RuntimeError("schedule serialization is not canonical/frozen")
    expected = freezer.build()
    if doc != expected or len(doc.get("rows", [])) != 120:
        raise RuntimeError("schedule does not equal the frozen builder output")
    return doc, raw


def frozen_request(row: dict[str, Any]) -> bytes:
    manifest = json.loads(freezer.MANIFEST.read_bytes())
    group = next(item for item in manifest["groups"] if item["group_id"] == row["group_id"])
    trajectory = next(item for item in group["trajectories"]
                      if item["trajectory_id"] == row["trajectory_id"])
    variant = next(item for item in trajectory["variants"] if item["variant_id"] == row["variant_id"])
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    payload = projector.project_variant_http_request(prompt, variant)
    body = projector.serialize_http_request(payload)
    if sha(body) != row["http_body_sha256"]:
        raise RuntimeError("projected request body differs from the frozen schedule")
    return body


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_bytes().splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def prepare_run(out: Path, *, test_mode: bool) -> dict[str, Any]:
    if test_mode:
        out.mkdir(parents=True, exist_ok=True)
        return {"verified": False, "test_fixture_only": True}
    ignored = "/runs/sprint-monitor/" in (ROOT / ".gitignore").read_text(encoding="utf-8").replace("\\", "/")
    if not ignored:
        raise PermissionError("private run root is not Git-ignored")
    out = out.resolve()
    private_root = (ROOT / "runs/sprint-monitor").resolve()
    if private_root not in out.parents:
        raise PermissionError("raw outputs must remain inside ignored runs/sprint-monitor")
    out.mkdir(parents=True, exist_ok=True)
    if not any(out.iterdir()):
        return restrict_private_directory_acl(out)
    return verify_private_directory_acl(out)


def load_api_key() -> str:
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
                raise RuntimeError("duplicate key name in local provider environment file")
            values[name] = value
    if values.get("LLM_BASE_URL", "").rstrip("/") != "https://api.deepseek.com":
        raise RuntimeError("local provider base URL is not the official DeepSeek host")
    if values.get("LLM_MODEL_ID") != "deepseek-flash":
        raise RuntimeError("local provider model alias differs from the frozen schedule")
    key = values.get("LLM_API_KEY", "")
    if not key:
        raise RuntimeError("DeepSeek credential unavailable")
    ambient = os.environ.get("DEEPSEEK_API_KEY")
    if ambient and ambient != key:
        raise RuntimeError("ambient credential does not match the authorized local environment file")
    return key


def _is_offpeak() -> bool:
    current = now()
    return not (current.weekday() < 5 and ((1 <= current.hour < 4) or (6 <= current.hour < 10)))


def _durable_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _post(body: bytes, key: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}",
    })

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                         urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    try:
        with opener.open(request, timeout=timeout) as response:
            headers = {k.lower(): v for k, v in response.headers.items()
                       if k.lower() in {"content-type", "x-request-id", "date"}}
            return response.status, response.read(), headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), {k.lower(): v for k, v in (exc.headers or {}).items()
                                     if k.lower() in {"content-type", "x-request-id", "date"}}


def _parse(response: bytes) -> dict[str, Any]:
    envelope = json.loads(response)
    choices = envelope.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("ONE_CHOICE_REQUIRED")
    choice = choices[0]
    message = choice.get("message")
    if choice.get("finish_reason") != "tool_calls":
        raise ValueError("FINISH_REASON_NOT_TOOL_CALLS")
    if not isinstance(message, dict) or not isinstance(message.get("tool_calls"), list) or len(message["tool_calls"]) != 1:
        raise ValueError("ONE_TOOL_CALL_REQUIRED")
    tool = message["tool_calls"][0].get("function", {})
    if tool.get("name") != "report_evidence" or not isinstance(tool.get("arguments"), str):
        raise ValueError("TOOL_CALL_SCHEMA_INVALID")
    args = json.loads(tool["arguments"])
    if set(args) != {"label", "evidence_refs"} or args["label"] not in {
            "present", "absent", "insufficient_evidence", "not_visible", "uncertain"}:
        raise ValueError("TOOL_ARGUMENTS_INVALID")
    if not isinstance(args["evidence_refs"], list) or any(not isinstance(x, str) for x in args["evidence_refs"]):
        raise ValueError("TOOL_ARGUMENTS_INVALID")
    return {"prediction": args, "finish_reason": choice["finish_reason"],
            "returned_model": envelope.get("model"),
            "system_fingerprint": envelope.get("system_fingerprint"),
            "usage": envelope.get("usage")}


def _envelope_metadata(response: bytes) -> dict[str, Any]:
    """Extract identity/usage before action validation so malformed actions remain attributable."""
    envelope = json.loads(response)
    choices = envelope.get("choices")
    finish_reason = (choices[0].get("finish_reason")
                     if isinstance(choices, list) and choices and isinstance(choices[0], dict)
                     else None)
    return {"returned_model": envelope.get("model"),
            "system_fingerprint": envelope.get("system_fingerprint"),
            "usage": envelope.get("usage"), "finish_reason": finish_reason}


def _check_authorization() -> None:
    budget = json.loads((ROOT / "research/budget.json").read_bytes())
    auth = budget.get("authorization", {})
    project_limits = budget.get("project_limits", {})
    expected_project_limits = {"max_model_calls": 1200, "max_external_cost_usd": 2.50}
    if project_limits != expected_project_limits:
        raise RuntimeError("project-wide limits differ from the approved ceiling")
    if (auth.get("status") != "active" or auth.get("approval_id") != APPROVAL_ID
            or auth.get("authorized_experiment_ids") != [EXPERIMENT_ID]
            or auth.get("max_model_calls") != 1200
            or float(auth.get("max_external_cost_usd", -1)) != 2.5
            or auth.get("scope") != "One synthetic B5 evidence-view stability diagnostic, DeepSeek Flash only"):
        raise RuntimeError("current research budget does not match the approved bounded experiment")
    batch_path = ROOT / f"research/authorizations/{APPROVAL_ID}.json"
    batch = json.loads(batch_path.read_bytes())
    from research.frozen_eval.evaluate_cycle_v2 import validate_authorization_batch
    errors = validate_authorization_batch(batch)
    if (errors or batch.get("authorized_experiment_ids") != [EXPERIMENT_ID]
            or batch.get("scope") != auth.get("scope")):
        raise RuntimeError("immutable authorization batch is invalid or out of scope")
    if (batch.get("max_model_calls") != 1200
            or float(batch.get("max_external_cost_usd", -1)) != 2.5
            or batch.get("approved_at_utc") != auth.get("approved_at_utc")
            or batch.get("expires_at_utc") != auth.get("expires_at_utc")):
        raise RuntimeError("budget snapshot and immutable authorization batch disagree")
    if now() >= datetime.fromisoformat(STOP_AT_UTC):
        raise RuntimeError("approval stop time has passed")
    if not _is_offpeak():
        raise RuntimeError("official off-peak pricing window has ended")
    expiry = datetime.fromisoformat(batch["expires_at_utc"].replace("Z", "+00:00"))
    if now() >= expiry:
        raise RuntimeError("authorization batch has expired")
    prereg_path = ROOT / f"research/experiments/{EXPERIMENT_ID}/preregistration.json"
    registration_path = prereg_path.parent / "registration.json"
    prereg = json.loads(prereg_path.read_bytes())
    registration = json.loads(registration_path.read_bytes())
    if (prereg.get("authorization", {}).get("approval_id") != APPROVAL_ID
            or prereg.get("budget", {}).get("max_model_calls") != MAX_CALLS
            or float(prereg.get("budget", {}).get("max_external_cost_usd", -1)) != MAX_RESERVED_USD
            or registration.get("preregistration_sha256") != sha(prereg_path.read_bytes())):
        raise RuntimeError("registered cycle ceiling or immutable preregistration hash differs")
    frozen = {item.get("path"): item.get("sha256")
              for item in prereg.get("protocol", {}).get("frozen_inputs", [])}
    required_paths = {
        "docs/B5_EVIDENCE_VIEW_STABILITY_PROTOCOL.md",
        "docs/results/research-sprint-20261021/b5-invariance-schedule-120.json",
        "docs/results/evidence-invariance/synthetic-invariance-groups-v2.json",
        "prompts/m4-deepseek-agent-v1/monitor-system.txt",
        "scripts/freeze_b5_invariance_schedule.py",
        "scripts/project_monitor_http_request_v2.py",
        "scripts/run_b5_invariance.py",
        "scripts/score_b5_invariance_run.py",
    }
    if not required_paths.issubset(frozen):
        raise RuntimeError("preregistration does not hash-pin every live execution input")
    for relative_path in required_paths:
        if sha((ROOT / relative_path).read_bytes()) != frozen[relative_path]:
            raise RuntimeError("a hash-pinned live execution input changed after preregistration")
    batch_hash = sha(batch_path.read_bytes())
    if registration.get("authorization_batch_sha256") != batch_hash:
        raise RuntimeError("registered authorization batch hash differs from current batch")


def _run_locked(out: Path, *, test_mode: bool, transport,
                schedule_path: Path, acl: dict[str, Any]) -> dict[str, Any]:
    schedule, schedule_raw = load_schedule(schedule_path)
    if schedule["dispatch"]["endpoint"] != ENDPOINT or schedule["dispatch"]["rows"] > FROZEN_SCHEDULE_ROWS:
        raise RuntimeError("frozen dispatch endpoint or count differs from hard limit")
    out = out.resolve()
    manifest_path = out / "schedule.json"
    if manifest_path.exists() and manifest_path.read_bytes() != schedule_raw:
        raise RuntimeError("restored run schedule bytes differ; refusing resume")
    if not manifest_path.exists():
        _durable_write(manifest_path, schedule_raw)
    schedule_hash = sha(schedule_raw)
    attempts_path = out / "attempts.jsonl"
    result_path = out / "results.jsonl"
    bodies: dict[str, bytes] = {}
    reservations: dict[str, float] = {}
    for row in schedule["rows"]:
        body = frozen_request(row)
        if sha(body) != row["http_body_sha256"]:
            raise RuntimeError("frozen HTTP body differs during pre-dispatch whole-schedule audit")
        bodies[row["request_id"]] = body
        reservations[row["request_id"]] = (
            len(body) * RATE_INPUT_PEAK + 512 * RATE_OUTPUT_PEAK)
    total_schedule_reserve = sum(reservations.values())
    if total_schedule_reserve > MAX_RESERVED_USD + 1e-12:
        raise RuntimeError("complete frozen schedule exceeds conservative cycle peak-cost cap")
    attempts = read_jsonl(attempts_path)
    starts = [row for row in attempts if row.get("event") == "attempt_started"]
    if len(starts) > MAX_CALLS:
        raise RuntimeError("attempt ledger exceeds the hard request cap")
    started_ids = [row.get("request_id") for row in starts]
    if len(started_ids) != len(set(started_ids)):
        raise RuntimeError("duplicate attempt detected; zero-retry policy forbids continuation")
    by_id = {row["request_id"]: row for row in schedule["rows"]}
    for start in starts:
        request_id = start.get("request_id")
        frozen_row = by_id.get(request_id)
        body = bodies.get(request_id)
        expected_path = f"requests/{request_id}.json"
        if (frozen_row is None or body is None
                or start.get("body_sha256") != frozen_row.get("http_body_sha256")
                or start.get("request_path") != expected_path
                or abs(float(start.get("reserved_peak_usd", -1)) - reservations[request_id]) > 1e-12):
            raise RuntimeError("restored pre-call ledger differs from the frozen schedule or reserve")
        saved_request = out / expected_path
        if not saved_request.is_file() or sha(saved_request.read_bytes()) != start.get("body_sha256"):
            raise RuntimeError("restored request bytes are missing or tampered")
    existing_results = read_jsonl(result_path)
    result_by_id = {row.get("request_id"): row for row in existing_results}
    terminal_ids = set(result_by_id)
    if len(result_by_id) != len(existing_results) or not terminal_ids.issubset(started_ids):
        raise RuntimeError("result ledger contains duplicate rows or lacks a durable pre-call record")
    for result in existing_results:
        if result.get("response_path"):
            response_path = (out / result["response_path"]).resolve()
            if (out not in response_path.parents or not response_path.is_file()
                    or sha(response_path.read_bytes()) != result.get("response_sha256")):
                raise RuntimeError("restored response bytes are missing or tampered")
    terminals = [row for row in attempts if row.get("event") == "attempt_terminal"]
    terminal_ids = [row.get("request_id") for row in terminals]
    if len(terminal_ids) != len(set(terminal_ids)) or not set(terminal_ids).issubset(started_ids):
        raise RuntimeError("attempt-terminal ledger is duplicated or orphaned")
    attempt_terminal = set(terminal_ids)
    for request_id in started_ids:
        if request_id not in result_by_id:
            result_by_id[request_id] = {"request_id": request_id,
                                        "status": "INTERRUPTED_UNKNOWN_OUTCOME",
                                        "http_status": None, "response_sha256": None,
                                        "response_path": None, "safe_response_headers": {},
                                        "elapsed_seconds": None,
                                        "parse_error_code": "PROCESS_INTERRUPTED_AFTER_PRECALL_RECORD",
                                        "parsed": None, "recovered_at_utc": now().isoformat()}
            append(result_path, result_by_id[request_id])
        if request_id not in attempt_terminal:
            recovered = result_by_id[request_id]
            is_unknown = recovered.get("status") == "INTERRUPTED_UNKNOWN_OUTCOME"
            append(attempts_path, {"event": "attempt_terminal", "request_id": request_id,
                                   "http_status": recovered.get("http_status"),
                                   "transport_error_type": ("INTERRUPTED_UNKNOWN_OUTCOME" if is_unknown else
                                                            recovered.get("transport_error_type")),
                                   "response_sha256": recovered.get("response_sha256"),
                                   "parse_error_code": recovered.get("parse_error_code"),
                                   "finished_at_utc": recovered.get("finished_at_utc") or now().isoformat(),
                                   "recovered_terminal_from_result": not is_unknown})
    # A started request without a terminal record is ambiguous and is never resent.
    attempted = set(started_ids)
    _check_authorization() if not test_mode else None
    key = "mock-key-for-test" if test_mode else load_api_key()
    reserved = sum(float(row.get("reserved_peak_usd", 0)) for row in attempts
                   if row.get("event") == "attempt_started")
    pending_reserve = sum(reservations[row["request_id"]] for row in schedule["rows"]
                          if row["request_id"] not in attempted)
    if reserved + pending_reserve > MAX_RESERVED_USD + 1e-12:
        raise RuntimeError("remaining schedule cannot fit the durable peak-cost cap")
    historical_fingerprints = {
        result.get("envelope_metadata", {}).get("system_fingerprint")
        for result in read_jsonl(result_path)
        if isinstance(result.get("envelope_metadata"), dict)
        and result["envelope_metadata"].get("system_fingerprint")
    }
    if len(historical_fingerprints) > 1:
        raise RuntimeError("provider fingerprint drift exists in the restored run; refusing resume")
    expected_fingerprint = next(iter(historical_fingerprints), None)
    completed = 0
    stop_reason = None
    for row in schedule["rows"]:
        request_id = row["request_id"]
        if request_id in attempted:
            continue
        if len(attempted) >= MAX_CALLS:
            stop_reason = "HARD_CALL_CAP"
            break
        if now() >= datetime.fromisoformat(STOP_AT_UTC) or not _is_offpeak():
            stop_reason = "APPROVAL_WINDOW_CLOSED"
            break
        if not test_mode:
            _check_authorization()
        body = bodies[request_id]
        input_upper_tokens = len(body)
        max_output_tokens = 512
        peak_reserve = reservations[request_id]
        # Persist request bytes and reservation before any network activity.
        request_path = out / "requests" / f"{request_id}.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        if request_path.exists():
            if request_path.read_bytes() != body:
                raise RuntimeError("stored request bytes were tampered with")
        else:
            _durable_write(request_path, body)
        start = {"event": "attempt_started", "request_id": request_id,
                 "schedule_sha256": schedule_hash, "body_sha256": sha(body),
                 "request_path": str(request_path.relative_to(out)).replace("\\", "/"),
                 "reserved_peak_usd": round(peak_reserve, 12),
                 "input_upper_bound_tokens": input_upper_tokens,
                 "max_output_tokens": max_output_tokens,
                 "started_at_utc": now().isoformat()}
        append(attempts_path, start)
        attempted.add(request_id)
        reserved += peak_reserve
        began = time.monotonic()
        status = None
        response = b""
        headers: dict[str, str] = {}
        transport_error = None
        try:
            status, response, headers = ((transport or _post)(body, key) if test_mode
                                         else _post(body, key))
        except Exception as exc:
            transport_error = type(exc).__name__
        elapsed = time.monotonic() - began
        response_path = out / "responses" / f"{request_id}.bin"
        if status is not None:
            response_path.parent.mkdir(parents=True, exist_ok=True)
            _durable_write(response_path, response)
        envelope_meta = None
        envelope_error = None
        if status == 200:
            try:
                envelope_meta = _envelope_metadata(response)
            except Exception as exc:
                envelope_error = type(exc).__name__
        response_record = {"request_id": request_id,
                           "status": "TRANSPORT_ERROR" if transport_error else "HTTP_RESPONSE",
                           "http_status": status, "response_sha256": sha(response) if status is not None else None,
                           "response_path": str(response_path.relative_to(out)).replace("\\", "/") if status is not None else None,
                           "safe_response_headers": headers, "elapsed_seconds": round(elapsed, 6),
                           "transport_error_type": transport_error,
                           "envelope_metadata": envelope_meta,
                           "envelope_error_code": envelope_error,
                           "finished_at_utc": now().isoformat()}
        parsed = None
        parse_error = None
        if status == 200 and response:
            try:
                parsed = _parse(response)
            except Exception as exc:
                parse_error = str(exc) if str(exc).isupper() else type(exc).__name__
        identity_mismatch = bool(status == 200 and (not envelope_meta
                                                     or envelope_meta.get("returned_model") != "deepseek-flash"))
        fingerprint = envelope_meta.get("system_fingerprint") if envelope_meta else None
        fingerprint_drift = bool(fingerprint and expected_fingerprint and fingerprint != expected_fingerprint)
        if fingerprint and not expected_fingerprint:
            expected_fingerprint = fingerprint
        response_record["parse_error_code"] = parse_error
        response_record["parsed"] = parsed
        response_record["identity_mismatch"] = identity_mismatch
        response_record["fingerprint_drift"] = fingerprint_drift
        append(out / "results.jsonl", response_record)
        append(attempts_path, {"event": "attempt_terminal", "request_id": request_id,
                               "http_status": status, "transport_error_type": transport_error,
                               "response_sha256": response_record["response_sha256"],
                               "parse_error_code": parse_error,
                               "finished_at_utc": response_record["finished_at_utc"]})
        completed += 1
        if transport_error or status != 200 or identity_mismatch or fingerprint_drift:
            stop_reason = ("MODEL_IDENTITY_MISMATCH" if identity_mismatch else
                           "PROVIDER_FINGERPRINT_DRIFT" if fingerprint_drift else
                           "TRANSPORT_OR_HTTP_FAILURE")
            break
    unsent = [row["request_id"] for row in schedule["rows"] if row["request_id"] not in attempted]
    if unsent:
        append(out / "stop.jsonl", {"event": "schedule_stopped", "reason": stop_reason or "NOT_DISPATCHED",
                                     "unsent_request_ids": unsent, "at_utc": now().isoformat()})
    os.environ.pop("DEEPSEEK_API_KEY", None)
    return {"status": "COMPLETE" if not unsent else "STOPPED_WITH_UNSENT_ROWS",
            "assigned": len(schedule["rows"]), "physical_attempts_this_run": completed,
            "physical_attempts_total": len(attempted), "new_results": completed,
            "unsent": len(unsent), "reserved_peak_usd": round(reserved, 8),
            "stop_reason": stop_reason, "schedule_sha256": schedule_hash,
            "private_acl": acl, "raw_data_local_only": True}


def run(out: Path = RUN_ROOT, *, test_mode: bool = False,
        transport=None, schedule_path: Path = SCHEDULE) -> dict[str, Any]:
    out = out.resolve()
    if not test_mode and out != RUN_ROOT.resolve():
        raise PermissionError("production dispatch is pinned to the sole authorized run directory")
    acl = prepare_run(out, test_mode=test_mode)
    lock_path = out / "dispatch.lock"
    try:
        descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("another dispatch holds the run lock; stale locks require manual review") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(f"pid={os.getpid()} started={now().isoformat()}\n")
            handle.flush()
            os.fsync(handle.fileno())
        return _run_locked(out, test_mode=test_mode, transport=transport,
                           schedule_path=schedule_path, acl=acl)
    finally:
        lock_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=RUN_ROOT)
    parser.add_argument("--schedule", type=Path, default=SCHEDULE)
    parser.add_argument("--offline-test", action="store_true")
    args = parser.parse_args()
    result = run(args.run, test_mode=args.offline_test, schedule_path=args.schedule)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
