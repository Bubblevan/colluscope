#!/usr/bin/env python3
"""Bounded B2-B5 dispatcher; default and only current mode is offline mock."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from colluscope.sprint_baselines import (  # noqa: E402
    BlindProjectionError,
    build_monitor_payload,
    canonical_json,
    compile_evidence_projection,
    parse_model_output,
    provenance_gate,
    sha256_json,
    _acceptance_event,
    _b1_prediction,
    _proposal_from_evidence,
)
from colluscope.sprint_controls import scripted_cases  # noqa: E402
from colluscope.sprint_metrics import score_one  # noqa: E402
from colluscope.sprint_replay import reference_for_case  # noqa: E402
from colluscope.monitor_aggregate_budget import (  # noqa: E402
    AggregateBudget, AggregateBudgetError,
)
from scripts.prepare_sprint_baselines import (  # noqa: E402
    LLM_CELLS,
    PROTOCOL,
    TASKS,
    _make_llm_schedule,
)
from scripts.local_llama_security import (  # noqa: E402
    restrict_private_directory_acl,
    verify_private_directory_acl,
)

CONFIG_PATH = ROOT / "configs/sprint-monitor-runtime-v1.toml"
TASK_ALLOWLIST = {"explicit_sequence", "proposal", "acceptance", "action_concordance", "public_harm"}
VIEW_BY_BASELINE = {
    "B2_text_only": "text_only",
    "B3_action_only": "action_only",
    "B4_raw_fusion": "raw_fusion",
    "B5_evidence_aware": "evidence_aware",
}
FORBIDDEN_TEXT_MARKERS = (
    "CONSTRUCTION_ORACLE_SENTINEL",
    "REFERENCE_ORACLE_SENTINEL",
    "POISON_PRIVATE_TARGET_SENTINEL",
    "FINDING_ORACLE_SENTINEL",
    "WELFARE_GAP_SENTINEL",
    "PUBLIC_HARM_SENTINEL",
    "TARGET_EXECUTION_SENTINEL",
)


class RuntimeIntegrityError(RuntimeError):
    pass


class LiveDispatchDisabled(PermissionError):
    pass


class TransportFailure(RuntimeError):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class BuiltRequest:
    request_id: str
    case_ref: str
    family_id: str
    baseline_id: str
    permission: str
    task: str
    view_name: str
    source: dict[str, Any]
    prompt_payload: dict[str, Any]
    http_payload: dict[str, Any]
    evidence: dict[str, Any]
    prompt_sha256: str
    body_sha256: str
    input_upper_bound: int
    reserve_usd: float
    evidence_compile_seconds: float


@dataclass(frozen=True)
class HTTPResult:
    status: int
    body: bytes
    safe_headers: dict[str, str]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            raise RuntimeIntegrityError(f"blank append-only ledger row: {path}:{line_number}")
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeIntegrityError(f"ledger row is not an object: {path}:{line_number}")
        result.append(value)
    return result


def _load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    required = {
        "protocol_id", "status", "model_alias", "endpoint", "expected_response_models",
        "temperature", "max_output_tokens", "max_input_token_upper_bound",
        "chat_framing_token_margin", "timeout_seconds", "max_logical_requests",
        "max_http_attempts", "max_attempts_per_logical_request", "hard_estimated_cost_usd",
        "input_usd_per_million_tokens_peak_cache_miss", "output_usd_per_million_tokens_peak",
        "pricing_verified_date", "pricing_source", "pricing_policy", "live_dispatch_enabled",
        "authorization_id", "private_run_root", "retry_policy", "external_fallback",
        "control_cases", "request_schedule", "system_prompt", "user_prompt", "task_definitions",
    }
    if set(raw) != required:
        raise RuntimeIntegrityError(f"runtime config keys differ from frozen contract: {sorted(set(raw)^required)}")
    if (raw["model_alias"] != "deepseek-flash"
            or raw["endpoint"] != "https://api.deepseek.com/chat/completions"
            or raw["external_fallback"] is not False
            or raw["expected_response_models"] != ["deepseek-flash", "DeepSeek-V4.1-Flash-1017"]):
        raise RuntimeIntegrityError("model or endpoint differs from the only configured provider target")
    if (not 1 <= raw["max_logical_requests"] <= 856
            or not 1 <= raw["max_http_attempts"] <= 856
            or raw["max_attempts_per_logical_request"] != 1
            or raw["max_output_tokens"] != 128
            or not 0 < raw["hard_estimated_cost_usd"] <= 3.0):
        raise RuntimeIntegrityError("call/token/cost budget differs from the frozen ceiling")
    if raw["retry_policy"] != "zero retries; interrupted/failed requests are terminal and never replaced":
        raise RuntimeIntegrityError("retry policy is not the frozen no-retry policy")
    if (raw["input_usd_per_million_tokens_peak_cache_miss"] != 0.30
            or raw["output_usd_per_million_tokens_peak"] != 1.20
            or raw["pricing_source"] != "https://api-docs.deepseek.com/quick_start/pricing/"
            or raw["pricing_policy"] != "peak cache-miss input and peak output; no cache-hit discount"
            or raw["max_input_token_upper_bound"] != 8192
            or raw["chat_framing_token_margin"] != 128):
        raise RuntimeIntegrityError("price or conservative token-bound assumptions differ from reviewed freeze")
    return raw


def _request_cost_bound(config: dict[str, Any], input_upper_bound: int) -> float:
    return (input_upper_bound * config["input_usd_per_million_tokens_peak_cache_miss"]
            + config["max_output_tokens"] * config["output_usd_per_million_tokens_peak"]) / 1_000_000


def _valid_mapping(mapping: Any) -> bool:
    return (isinstance(mapping, dict) and set(mapping) == {"A", "B", "C"}
            and set(mapping.values()) == {"T1", "T2", "T3"})


def _validate_payload(payload: dict[str, Any], row: dict[str, Any]) -> None:
    if set(payload) != {"model", "messages", "temperature", "max_tokens"}:
        raise BlindProjectionError("HTTP body contains fields outside the frozen allowlist")
    if payload["model"] != "deepseek-flash":
        raise BlindProjectionError("unexpected model ID in monitor body")
    body = _json_bytes(payload).decode("utf-8")
    lower = body.casefold()
    for marker in FORBIDDEN_TEXT_MARKERS:
        if marker.casefold() in lower:
            raise BlindProjectionError(f"hidden-data canary leaked into request: {marker}")
    # One frozen synthetic family label equals a permitted task-vocabulary item
    # (`explicit_sequence`), which is present in the prompt schema for every task.
    # Allow only this known vocabulary collision while scanning actual routing IDs.
    identifiers = [row["case_ref"], row["split_group_id"]]
    family_id = row["scenario_family_id"]
    if family_id.casefold() not in {item.casefold() for item in TASK_ALLOWLIST}:
        identifiers.append(family_id)
    for identifier in identifiers:
        if identifier and identifier.casefold() in lower:
            raise BlindProjectionError("routing or split identifier entered monitor request")
    banned_keys = {
        "T", "construction_truth", "reference_answer", "reference_answers", "expected_labels",
        "scoring_results", "case_ref", "scenario_family_id", "split_group_id", "partition",
        "condition_id", "seed", "group_id", "private_reward_target", "welfare_gap",
        "target_executed", "public_harm", "findings", "authorization_id",
    }

    def walk(value: Any, path: str = "$payload") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).casefold() in {item.casefold() for item in banned_keys}:
                    raise BlindProjectionError(f"banned hidden field in request: {path}.{key}")
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(payload)


def build_schedule(config: dict[str, Any] | None = None) -> list[BuiltRequest]:
    config = config or _load_config()
    cases = scripted_cases()
    by_ref = {case["case_ref"]: case for case in cases}
    frozen_rows = _make_llm_schedule(cases)
    if len(frozen_rows) != 280 or len({row["request_id"] for row in frozen_rows}) != 280:
        raise RuntimeIntegrityError("frozen Monitor schedule is not exactly 280 unique logical rows")
    requests: list[BuiltRequest] = []
    for row in frozen_rows:
        source = by_ref[row["case_ref"]]
        baseline, task, permission = row["baseline_id"], row["task"], row["permission"]
        compile_started = time.perf_counter()
        prompt_payload, evidence = build_monitor_payload(source, baseline, task, permission)
        compile_seconds = time.perf_counter() - compile_started
        prompt_bytes = _json_bytes(prompt_payload)
        if _sha(prompt_bytes) != row["payload_sha256"]:
            raise RuntimeIntegrityError(f"frozen prompt payload hash mismatch: {row['request_id']}")
        http_payload = {"model": config["model_alias"], **prompt_payload}
        _validate_payload(http_payload, row)
        http_bytes = _json_bytes(http_payload)
        input_upper = len(http_bytes) + config["chat_framing_token_margin"]
        if input_upper > config["max_input_token_upper_bound"]:
            raise RuntimeIntegrityError(
                f"prompt upper bound exceeds frozen input ceiling: {row['request_id']} "
                f"({input_upper}>{config['max_input_token_upper_bound']})"
            )
        requests.append(BuiltRequest(
            request_id=row["request_id"], case_ref=row["case_ref"],
            family_id=row["scenario_family_id"], baseline_id=baseline,
            permission=permission, task=task, view_name=VIEW_BY_BASELINE[baseline],
            source=source, prompt_payload=prompt_payload, http_payload=http_payload,
            evidence=evidence, prompt_sha256=_sha(prompt_bytes), body_sha256=_sha(http_bytes),
            input_upper_bound=input_upper,
            reserve_usd=_request_cost_bound(config, input_upper),
            evidence_compile_seconds=compile_seconds,
        ))
    total_reserve = sum(item.reserve_usd for item in requests)
    if total_reserve > config["hard_estimated_cost_usd"]:
        raise RuntimeIntegrityError(
            f"full schedule worst-case estimate exceeds hard cost ceiling: ${total_reserve:.9f}"
        )
    return requests


def _ensure_private_run_root(out: Path, config: dict[str, Any], *, create: bool) -> dict[str, Any]:
    root = (ROOT / config["private_run_root"]).resolve()
    target = out.resolve()
    if root not in target.parents and target != root:
        raise PermissionError("raw run output must remain under the Git-ignored sprint monitor root")
    ignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if f"/{config['private_run_root']}/" not in ignore_text.replace("\\", "/"):
        raise PermissionError("private run root is not explicitly Git-ignored")
    if create:
        target.mkdir(parents=True, exist_ok=True)
    if not target.is_dir():
        raise FileNotFoundError("private run directory is unavailable")
    if os.name != "nt":
        raise PermissionError("ACL verification is only frozen for the Windows execution host")
    acl = (restrict_private_directory_acl(target) if create and not any(target.iterdir())
           else verify_private_directory_acl(target))
    if acl.get("verified") is not True:
        raise PermissionError("private run-directory ACL check failed")
    return acl


def _read_existing_state(out: Path, requests: list[BuiltRequest], *,
                         max_attempts: int = 280
                         ) -> tuple[dict[str, dict[str, Any]], set[str], dict[str, dict[str, Any]]]:
    progress = _read_jsonl(out / "progress.jsonl")
    attempts = _read_jsonl(out / "attempts.jsonl")
    terminal: dict[str, dict[str, Any]] = {}
    for row in progress:
        request_id = row.get("request_id")
        if request_id in terminal:
            raise RuntimeIntegrityError(f"duplicate terminal ledger row: {request_id}")
        terminal[request_id] = row
    by_request = {item.request_id: item for item in requests}
    started: set[str] = set()
    closed: set[str] = set()
    terminal_events: dict[str, dict[str, Any]] = {}
    for event in attempts:
        request_id = event.get("request_id")
        if request_id not in by_request:
            raise RuntimeIntegrityError("attempt ledger contains an ID outside the frozen schedule")
        request = by_request[request_id]
        if event.get("body_sha256") != request.body_sha256:
            raise RuntimeIntegrityError("attempt ledger request hash differs from frozen body")
        if event.get("event") == "attempt_started":
            if request_id in started:
                raise RuntimeIntegrityError("a logical request has more than one HTTP attempt")
            request_path = event.get("request_path")
            if request_path != f"requests/{request_id}.json":
                raise RuntimeIntegrityError("attempt start points outside its opaque request file")
            exact_path = out / request_path
            if not exact_path.is_file() or _sha(exact_path.read_bytes()) != request.body_sha256:
                raise RuntimeIntegrityError("attempt start has no matching durable request bytes")
            if abs(float(event.get("reserve_usd", -1.0)) - request.reserve_usd) > 1e-12:
                raise RuntimeIntegrityError("attempt start cost reservation differs from frozen request")
            started.add(request_id)
        elif event.get("event") == "attempt_terminal":
            if request_id not in started or request_id in closed:
                raise RuntimeIntegrityError("attempt terminal has no unique start event")
            closed.add(request_id)
            terminal_events[request_id] = event
            response_sha = event.get("response_sha256")
            if response_sha is not None:
                response_path = out / "responses" / f"{request_id}.json"
                if not response_path.is_file() or _sha(response_path.read_bytes()) != response_sha:
                    raise RuntimeIntegrityError("terminal attempt response bytes are missing or tampered")
    for request_id, row in terminal.items():
        event = terminal_events.get(request_id)
        if event is not None and row.get("status") != event.get("transport_status"):
            raise RuntimeIntegrityError("progress terminal status differs from the append-only HTTP terminal")
    if len(started) > max_attempts:
        raise RuntimeIntegrityError("restored HTTP attempt count exceeds configured phase cap")
    # A terminal HTTP ledger with no progress row means the process stopped between
    # the two durable appends. It must be recovered as terminal and never resent.
    terminal_without_progress = {
        request_id: terminal_events[request_id]
        for request_id in closed - set(terminal)
    }
    return terminal, started - closed, terminal_without_progress


def _extract_model_text(body: dict[str, Any]) -> tuple[str, str | None]:
    choices = body.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("response must contain exactly one choice")
    choice = choices[0]
    finish_reason = choice.get("finish_reason")
    message = choice.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ValueError("response choice must contain assistant text content")
    return message["content"], finish_reason if isinstance(finish_reason, str) else None


def _safe_response_headers(headers: Any) -> dict[str, str]:
    allow = {"content-type", "retry-after", "x-request-id", "date"}
    return {key.lower(): str(value) for key, value in headers.items()
            if key.lower() in allow}


def urllib_transport(endpoint: str, body: bytes, api_key: str, timeout: int) -> HTTPResult:
    request = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            return HTTPResult(response.status, response.read(), _safe_response_headers(response.headers))
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read()
        finally:
            exc.close()
        return HTTPResult(exc.code, raw, _safe_response_headers(exc.headers or {}))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TransportFailure(type(exc).__name__, str(exc)) from exc


def mock_transport(_endpoint: str, _body: bytes, _api_key: str, _timeout: int) -> HTTPResult:
    """Transport canary only: a constant, deliberately uninformative prediction."""
    response = {
        "id": "offline-mock-response",
        "model": "deepseek-flash",
        "system_fingerprint": "offline-mock-not-a-model",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant",
                                 "content": '{"label":"not_visible","evidence_refs":[]}'}}],
    }
    return HTTPResult(200, _json_bytes(response), {"content-type": "application/json"})


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                indent=2).encode("utf-8") + b"\n")


def _terminalize(out: Path, request: BuiltRequest, status: str, **fields: Any) -> dict[str, Any]:
    record = {"request_id": request.request_id, "case_ref": request.case_ref,
              "baseline_id": request.baseline_id, "permission": request.permission,
              "task": request.task, "status": status, **fields}
    _append_jsonl(out / "progress.jsonl", record)
    return record


def _score_response(request: BuiltRequest, raw_text: str, *, baseline_label: str,
                    output_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    prediction = parse_model_output(raw_text, request.task)
    reference = reference_for_case(request.source, request.task,
                                  request.view_name, request.permission)
    raw_score = score_one(request.source, reference, baseline_label, prediction,
                          view_name=request.view_name, permission=request.permission)
    gated = provenance_gate(prediction, request.task, request.evidence)
    gated_prediction = {**prediction, "label": gated["gated_label"]}
    gated_score = score_one(request.source, reference, f"{baseline_label}_gated",
                            gated_prediction, view_name=request.view_name,
                            permission=request.permission)
    # Exact reference and raw prediction are researcher-only; they are never in HTTP body.
    _write_json(output_dir / "references" / f"{request.request_id}.json", reference)
    proposal = _proposal_from_evidence(request.evidence)
    acceptance = _acceptance_event(request.evidence, proposal) if proposal else None
    _append_jsonl(output_dir / "audit_layers.jsonl", {
        "request_id": request.request_id,
        "raw_llm_prediction": prediction,
        "deterministic_event_reconstruction": _b1_prediction(request.evidence, request.task),
        "message_language_interpretation": {
            "method": "frozen literal full-allocation and explicit-acceptance codebook",
            "proposal_present": proposal is not None,
            "proposal_source_event_id": proposal[0]["event_id"] if proposal else None,
            "explicit_acceptance_present": acceptance is not None,
            "acceptance_source_event_id": acceptance["event_id"] if acceptance else None,
        },
        "provenance_validation": gated,
        "raw_score": raw_score,
        "gated_score": gated_score,
        "reference_label_is_researcher_only": True,
    })
    return ({"request_id": request.request_id, "raw_prediction": prediction,
             "reference_label": reference["label"], "reference_assessable": reference["assessable"],
             "score": raw_score},
            {"request_id": request.request_id, "raw_label": prediction["label"],
             "gated_label": gated["gated_label"], "gate_reason": gated["gate_reason"],
             "citation_membership_valid": gated["citation_membership_valid"],
             "score": gated_score})


def run_schedule(out: Path, *, mode: str = "mock", config_path: Path = CONFIG_PATH,
                 transport: Callable[[str, bytes, str, int], HTTPResult] | None = None,
                 approval_id: str | None = None, secure_storage: bool = True,
                 test_mode: bool = False,
                 requests_override: list[BuiltRequest] | None = None,
                 budget_ledger: AggregateBudget | None = None,
                 phase_id: str | None = None) -> dict[str, Any]:
    config = _load_config(config_path)
    if mode not in {"mock", "live"}:
        raise ValueError("mode must be mock or live")
    api_key = ""
    if mode == "live":
        if not config["live_dispatch_enabled"] or not config["authorization_id"]:
            raise LiveDispatchDisabled("live monitor inference is frozen off; no user approval is recorded")
        if approval_id != config["authorization_id"]:
            raise LiveDispatchDisabled("CLI approval ID does not match the separately approved config")
        if test_mode and transport is None:
            raise LiveDispatchDisabled("test-mode live path requires an injected fake transport")
        if not test_mode and (transport is not None or not secure_storage):
            raise LiveDispatchDisabled("production live dispatch forbids injected transports and ACL bypass")
        if not test_mode and (budget_ledger is None or phase_id is None):
            raise LiveDispatchDisabled("production live dispatch requires the shared aggregate request/cost ledger")
        if budget_ledger is not None and phase_id is None:
            raise LiveDispatchDisabled("aggregate budget use requires an explicit approved phase ID")
        verified = datetime.strptime(config["pricing_verified_date"], "%Y-%m-%d").date()
        if (datetime.now(timezone.utc).date() - verified).days > 7:
            raise LiveDispatchDisabled("official pricing check is older than seven days; refresh it before approval")
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise LiveDispatchDisabled("DEEPSEEK_API_KEY must be provided by the approved operator environment")
    if transport is None:
        transport = mock_transport if mode == "mock" else urllib_transport

    requests = requests_override if requests_override is not None else build_schedule(config)
    request_ids = [item.request_id for item in requests]
    if not requests or len(request_ids) != len(set(request_ids)):
        raise RuntimeIntegrityError("request schedule must be nonempty and use unique request IDs")
    if requests_override is not None:
        if len(requests) > config["max_logical_requests"]:
            raise RuntimeIntegrityError("frozen override schedule exceeds its phase request ceiling")
        for request in requests:
            if _sha(_json_bytes(request.http_payload)) != request.body_sha256:
                raise RuntimeIntegrityError("frozen override HTTP body does not match its stored hash")
            _validate_payload(request.http_payload, {
                "case_ref": request.case_ref,
                "split_group_id": request.source.get("split_group_id", request.case_ref),
                "scenario_family_id": request.family_id,
            })
    if secure_storage:
        acl = _ensure_private_run_root(out, config, create=True)
    else:
        acl = {"verified": False, "test_fixture_only": True}
        out.mkdir(parents=True, exist_ok=True)

    expected_ids = {item.request_id for item in requests}
    existing, incomplete, terminal_without_progress = _read_existing_state(
        out, requests, max_attempts=config["max_http_attempts"])
    if not set(existing).issubset(expected_ids):
        raise RuntimeIntegrityError("progress ledger includes an evaluation outside the frozen schedule")
    for request_id, event in sorted(terminal_without_progress.items()):
        request = next(item for item in requests if item.request_id == request_id)
        recovered_status = str(event.get("transport_status") or "TERMINAL_ATTEMPT_RECOVERED")
        _terminalize(out, request, recovered_status,
                     body_sha256=request.body_sha256,
                     response_sha256=event.get("response_sha256"),
                     recovered_after_terminal_attempt=True,
                     retry_count=0)
        existing[request_id] = {"request_id": request_id, "status": recovered_status}
    for request_id in sorted(incomplete):
        request = next(item for item in requests if item.request_id == request_id)
        _append_jsonl(out / "attempts.jsonl", {
            "event": "attempt_terminal", "request_id": request_id,
            "body_sha256": request.body_sha256, "http_status": None,
            "transport_status": "INTERRUPTED_UNKNOWN_NO_RETRY",
            "auth_header_saved": False, "response_sha256": None,
        })
        _terminalize(out, request, "INTERRUPTED_UNKNOWN_NO_RETRY",
                     body_sha256=request.body_sha256, retry_count=0)
        existing[request_id] = {"request_id": request_id,
                                "status": "INTERRUPTED_UNKNOWN_NO_RETRY"}

    budget_orphan_stop_reason: str | None = None
    if budget_ledger is not None and phase_id is not None:
        try:
            orphan_ids = budget_ledger.reconcile_phase(
                phase_id=phase_id,
                local_attempts=_read_jsonl(out / "attempts.jsonl"),
                local_progress=_read_jsonl(out / "progress.jsonl"),
            )
        except AggregateBudgetError as exc:
            raise RuntimeIntegrityError(f"aggregate budget reconciliation failed: {exc}") from exc
        if orphan_ids:
            budget_orphan_stop_reason = "durable global reservation lacks a local attempt; no replay"
            by_id = {item.request_id: item for item in requests}
            for request_id in orphan_ids:
                if request_id not in by_id:
                    raise RuntimeIntegrityError("aggregate budget orphan is outside the frozen request schedule")
                _terminalize(out, by_id[request_id], "GLOBAL_RESERVED_NO_LOCAL_ATTEMPT_NO_REPLAY",
                             retry_count=0, no_replay=True)
                existing[request_id] = {"request_id": request_id,
                                        "status": "GLOBAL_RESERVED_NO_LOCAL_ATTEMPT_NO_REPLAY"}

    frozen_manifest = {
        "schema_version": "sprint-monitor-runtime-v1",
        "runtime_revision": "sprint-monitor-runtime-v1.3",
        "mode": "live_fake_transport_test" if test_mode else mode,
        "requested_mode": mode,
        "fake_transport_only": test_mode or mode == "mock",
        "protocol_id": PROTOCOL,
        "runtime_config_sha256": _sha(config_path.read_bytes()),
        "request_count": len(requests),
        "request_schedule_sha256": _sha(_json_bytes([
            {"request_id": item.request_id, "body_sha256": item.body_sha256}
            for item in requests
        ])),
        "max_http_attempts": config["max_http_attempts"],
        "planned_full_schedule_cost_upper_bound_usd": round(sum(r.reserve_usd for r in requests), 12),
        "cost_policy": "reserve peak cache-miss input and peak output before dispatch",
        "endpoint": config["endpoint"],
        "model_alias": config["model_alias"],
        "aggregate_budget": ({
            "execution_id": budget_ledger.execution_id,
            "phase_id": phase_id,
            "ledger_path": str(budget_ledger.ledger_path),
            "global_request_cap": 856,
            "global_cost_cap_usd": 3.0,
        } if budget_ledger is not None else None),
        "prompt_hashes": {
            path: _sha((ROOT / path).read_bytes()) for path in (
                "prompts/sprint-baseline-v1/system.txt",
                "prompts/sprint-baseline-v1/user.txt",
                "prompts/sprint-baseline-v1/tasks.json",
            )
        },
        "runtime_code_sha256": {
            path: _sha((ROOT / path).read_bytes()) for path in (
                "scripts/run_sprint_monitor.py",
                "scripts/prepare_sprint_baselines.py",
                "scripts/local_llama_security.py",
                "scripts/audit_sprint_monitor_live.py",
                "scripts/audit_sprint_monitor_mock.py",
                "src/colluscope/sprint_baselines.py",
                "src/colluscope/sprint_controls.py",
                "src/colluscope/sprint_metrics.py",
                "src/colluscope/sprint_replay.py",
                "src/colluscope/monitor_aggregate_budget.py",
                "scripts/prepare_full_research_monitor.py",
                "scripts/run_full_research_monitor.py",
                "scripts/audit_full_research_monitor.py",
            )
        },
        "private_storage_acl": acl,
        "credential_material_saved": False,
        "real_model_or_api_calls_in_this_task": 0 if mode == "mock" or test_mode else None,
        "mock_outputs_are_model_evidence": False,
    }
    manifest_path = out / "run_manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("schema_version", "runtime_revision", "mode", "protocol_id", "runtime_config_sha256",
                    "request_count", "request_schedule_sha256", "endpoint", "model_alias",
                    "aggregate_budget", "prompt_hashes", "runtime_code_sha256"):
            if old.get(key) != frozen_manifest.get(key):
                raise RuntimeIntegrityError(f"resume manifest mismatch for {key}")
    else:
        _write_json(manifest_path, frozen_manifest)

    attempts_started = len([row for row in _read_jsonl(out / "attempts.jsonl")
                            if row.get("event") == "attempt_started"])
    prior_identities = {
        (row.get("returned_model"), row.get("system_fingerprint"))
        for row in _read_jsonl(out / "attempts.jsonl")
        if row.get("event") == "attempt_terminal" and row.get("returned_model")
    }
    if len(prior_identities) > 1:
        raise RuntimeIntegrityError("stored provider model/fingerprint changed within the run")
    run_identity = next(iter(prior_identities), None)
    logical_started = attempts_started
    reserved_usd = sum(float(row.get("reserve_usd", 0.0)) for row in _read_jsonl(out / "attempts.jsonl")
                       if row.get("event") == "attempt_started")
    fatal_reason: str | None = budget_orphan_stop_reason
    terminal_count = len(existing)

    for request in requests:
        if request.request_id in existing:
            continue
        if fatal_reason:
            _terminalize(out, request, "NOT_SENT_AFTER_STOP", stop_reason=fatal_reason,
                         retry_count=0)
            terminal_count += 1
            continue
        if (logical_started >= config["max_logical_requests"]
                or attempts_started >= config["max_http_attempts"]):
            _terminalize(out, request, "BUDGET_EXHAUSTED", retry_count=0)
            terminal_count += 1
            continue
        if reserved_usd + request.reserve_usd > config["hard_estimated_cost_usd"]:
            _terminalize(out, request, "COST_BUDGET_EXHAUSTED",
                         remaining_budget_usd=max(0.0, config["hard_estimated_cost_usd"] - reserved_usd),
                         retry_count=0)
            terminal_count += 1
            fatal_reason = "hard cost ceiling reached"
            continue

        request_path = out / "requests" / f"{request.request_id}.json"
        if request_path.exists():
            if _sha(request_path.read_bytes()) != request.body_sha256:
                raise RuntimeIntegrityError("existing exact request bytes do not match frozen request hash")
        else:
            request_path.parent.mkdir(parents=True, exist_ok=True)
            request_path.write_bytes(_json_bytes(request.http_payload))
        body_bytes = request_path.read_bytes()
        if _sha(body_bytes) != request.body_sha256:
            raise RuntimeIntegrityError("request bytes changed after persistence")

        if budget_ledger is not None and phase_id is not None:
            try:
                budget_ledger.reserve(
                    phase_id=phase_id, request_id=request.request_id,
                    body_sha256=request.body_sha256, reserve_usd=request.reserve_usd,
                    phase_request_cap=config["max_logical_requests"],
                    phase_cost_cap_usd=config["hard_estimated_cost_usd"],
                )
            except AggregateBudgetError as exc:
                raise RuntimeIntegrityError(f"aggregate budget denied dispatch: {exc}") from exc

        _append_jsonl(out / "attempts.jsonl", {
            "event": "attempt_started", "request_id": request.request_id,
            "body_sha256": request.body_sha256, "request_path": f"requests/{request.request_id}.json",
            "attempt_index": 1, "reserve_usd": request.reserve_usd,
            "input_upper_bound": request.input_upper_bound,
            "request_body_bytes": len(body_bytes),
            "evidence_compile_seconds": request.evidence_compile_seconds,
            "endpoint": config["endpoint"], "auth_header_saved": False,
            "retry_count": 0, "started_utc": datetime.now(timezone.utc).isoformat(),
        })
        attempts_started += 1
        logical_started += 1
        reserved_usd += request.reserve_usd
        try:
            result = transport(config["endpoint"], body_bytes, api_key, config["timeout_seconds"])
        except BaseException as exc:
            if not isinstance(exc, (Exception, KeyboardInterrupt, SystemExit)):
                raise
            error_kind = getattr(exc, "kind", type(exc).__name__)
            raw_error = {"error_type": error_kind, "error_message": str(exc)}
            response_bytes = _json_bytes(raw_error)
            response_hash = _sha(response_bytes)
            error_response_path = out / "responses" / f"{request.request_id}.json"
            error_response_path.parent.mkdir(parents=True, exist_ok=True)
            error_response_path.write_bytes(response_bytes)
            _append_jsonl(out / "attempts.jsonl", {
                "event": "attempt_terminal", "request_id": request.request_id,
                "body_sha256": request.body_sha256, "http_status": None,
                "transport_status": "INTERRUPTED_UNKNOWN_NO_RETRY" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "TRANSPORT_ERROR",
                "response_sha256": response_hash, "auth_header_saved": False,
                "retry_count": 0, "ended_utc": datetime.now(timezone.utc).isoformat(),
            })
            _terminalize(out, request,
                         "INTERRUPTED_UNKNOWN_NO_RETRY" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "TRANSPORT_ERROR",
                         body_sha256=request.body_sha256, response_sha256=response_hash,
                         error_type=error_kind, retry_count=0)
            if budget_ledger is not None and phase_id is not None:
                budget_ledger.terminal(
                    phase_id=phase_id, request_id=request.request_id,
                    status="INTERRUPTED_UNKNOWN_NO_RETRY" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "TRANSPORT_ERROR",
                    actual_cost_usd=None, http_status=None,
                )
            existing[request.request_id] = {"request_id": request.request_id, "status": "TRANSPORT_ERROR"}
            terminal_count += 1
            fatal_reason = error_kind
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                fatal_reason = "interrupt after attempt start"
            continue

        response_hash = _sha(result.body)
        response_path = out / "responses" / f"{request.request_id}.json"
        response_path.parent.mkdir(parents=True, exist_ok=True)
        response_path.write_bytes(result.body)
        terminal_status = "COMPLETED"
        details: dict[str, Any] = {
            "http_status": result.status,
            "response_sha256": response_hash,
            "safe_response_headers": result.safe_headers,
            "retry_count": 0,
        }
        parsed: dict[str, Any] | None = None
        if result.status != 200:
            terminal_status = f"HTTP_ERROR_{result.status}"
            fatal_reason = f"provider HTTP {result.status}; no retry/fallback"
        else:
            try:
                parsed = json.loads(result.body)
                if not isinstance(parsed, dict):
                    raise ValueError("response root is not an object")
                returned_model = parsed.get("model")
                fingerprint = parsed.get("system_fingerprint")
                details.update({"returned_model": returned_model,
                                "system_fingerprint": fingerprint})
                if mode == "live" and returned_model not in config["expected_response_models"]:
                    terminal_status = "MODEL_IDENTITY_MISMATCH"
                    fatal_reason = "returned model identity differs from frozen allowlist"
                elif mode == "live" and (not isinstance(fingerprint, str) or not fingerprint):
                    terminal_status = "MODEL_FINGERPRINT_MISSING"
                    fatal_reason = "provider system_fingerprint missing"
                elif run_identity is not None and run_identity != (returned_model, fingerprint):
                    terminal_status = "MODEL_IDENTITY_DRIFT"
                    fatal_reason = "returned model or system fingerprint changed within the run"
                else:
                    run_identity = (returned_model, fingerprint)
                    text, finish_reason = _extract_model_text(parsed)
                    details["finish_reason"] = finish_reason
                    if finish_reason not in {"stop", "end_turn"}:
                        terminal_status = "INVALID_OUTPUT"
                        details["parse_error"] = f"unexpected finish_reason: {finish_reason}"
                    else:
                        try:
                            raw_score, gated_score = _score_response(
                                request, text, baseline_label=request.baseline_id,
                                output_dir=out / "analysis",
                            )
                            _append_jsonl(out / "raw_predictions.jsonl", raw_score)
                            _append_jsonl(out / "gated_predictions.jsonl", gated_score)
                            details["prediction_label"] = raw_score["raw_prediction"]["label"]
                            details["citation_membership_valid"] = raw_score["score"]["citation_membership_valid"]
                            details["gated_label"] = gated_score["gated_label"]
                        except Exception as exc:
                            terminal_status = "INVALID_OUTPUT"
                            details["parse_error"] = f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                terminal_status = "INVALID_RESPONSE_JSON"
                details["parse_error"] = f"{type(exc).__name__}: {exc}"

        usage = parsed.get("usage") if isinstance(parsed, dict) else None
        if isinstance(usage, dict):
            input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
            output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
            details["usage"] = {"input_tokens": input_tokens, "output_tokens": output_tokens}
            if type(input_tokens) is int and type(output_tokens) is int:
                actual_cost = (input_tokens * config["input_usd_per_million_tokens_peak_cache_miss"]
                               + output_tokens * config["output_usd_per_million_tokens_peak"]) / 1_000_000
                details["cost_upper_peak_usd"] = actual_cost
                total_tokens = usage.get("total_tokens")
                if (input_tokens < 0 or output_tokens < 0
                        or (type(total_tokens) is int and total_tokens != input_tokens + output_tokens)):
                    terminal_status = "INVALID_USAGE_ACCOUNTING"
                    fatal_reason = "provider-reported token usage is negative or internally inconsistent"
                    details["cost_upper_peak_usd"] = request.reserve_usd
                elif input_tokens > config["max_input_token_upper_bound"] or output_tokens > config["max_output_tokens"]:
                    terminal_status = "TOKEN_BUDGET_EXCEEDED"
                    fatal_reason = "provider-reported usage exceeded pre-dispatch token bound"
                elif actual_cost > request.reserve_usd + 1e-12:
                    terminal_status = "REQUEST_COST_RESERVE_EXCEEDED"
                    fatal_reason = "provider-reported peak cost exceeded the request reservation"
            else:
                details["cost_upper_peak_usd"] = request.reserve_usd
        else:
            details["usage"] = None
            details["cost_upper_peak_usd"] = request.reserve_usd

        _append_jsonl(out / "attempts.jsonl", {
            "event": "attempt_terminal", "request_id": request.request_id,
            "body_sha256": request.body_sha256, "http_status": result.status,
            "transport_status": terminal_status, "response_sha256": response_hash,
            "safe_response_headers": result.safe_headers, "auth_header_saved": False,
            "returned_model": details.get("returned_model"),
            "system_fingerprint": details.get("system_fingerprint"),
            "retry_count": 0, "ended_utc": datetime.now(timezone.utc).isoformat(),
        })
        _terminalize(out, request, terminal_status, body_sha256=request.body_sha256,
                     response_path=f"responses/{request.request_id}.json", **details)
        if budget_ledger is not None and phase_id is not None:
            usage_obj = parsed.get("usage") if isinstance(parsed, dict) else None
            has_valid_usage = (
                isinstance(usage_obj, dict)
                and type(usage_obj.get("prompt_tokens", usage_obj.get("input_tokens"))) is int
                and type(usage_obj.get("completion_tokens", usage_obj.get("output_tokens"))) is int
                and usage_obj.get("prompt_tokens", usage_obj.get("input_tokens")) >= 0
                and usage_obj.get("completion_tokens", usage_obj.get("output_tokens")) >= 0
                and terminal_status != "INVALID_USAGE_ACCOUNTING"
            )
            budget_ledger.terminal(
                phase_id=phase_id, request_id=request.request_id,
                status=terminal_status,
                actual_cost_usd=(details.get("cost_upper_peak_usd") if has_valid_usage else None),
                http_status=result.status,
            )
        existing[request.request_id] = {"request_id": request.request_id, "status": terminal_status}
        terminal_count += 1
        if terminal_status != "COMPLETED" and fatal_reason is None and terminal_status.startswith(("HTTP_ERROR", "MODEL_", "TOKEN_")):
            fatal_reason = terminal_status

    final_rows = _read_jsonl(out / "progress.jsonl")
    if len(final_rows) != len(requests) or {row.get("request_id") for row in final_rows} != expected_ids:
        raise RuntimeIntegrityError("not every assigned schedule row has exactly one terminal status")
    terminal_map = {row["request_id"]: row for row in final_rows}
    if len(terminal_map) != len(final_rows):
        raise RuntimeIntegrityError("duplicate schedule row terminalization")
    attempt_rows = _read_jsonl(out / "attempts.jsonl")
    started_ids = {row["request_id"] for row in attempt_rows if row.get("event") == "attempt_started"}
    request_by_id = {request.request_id: request for request in requests}
    reported_cost = 0.0
    missing_usage_reserve = 0.0
    usage_rows = 0
    for request_id in started_ids:
        row = terminal_map[request_id]
        usage_row = row.get("usage")
        if (isinstance(usage_row, dict)
                and type(usage_row.get("input_tokens")) is int
                and type(usage_row.get("output_tokens")) is int
                and usage_row["input_tokens"] >= 0 and usage_row["output_tokens"] >= 0
                and row.get("status") != "INVALID_USAGE_ACCOUNTING"):
            usage_rows += 1
            reported_cost += (usage_row["input_tokens"] * config["input_usd_per_million_tokens_peak_cache_miss"]
                              + usage_row["output_tokens"] * config["output_usd_per_million_tokens_peak"]) / 1_000_000
        else:
            missing_usage_reserve += request_by_id[request_id].reserve_usd
    is_fake_transport = mode == "mock" or test_mode
    all_completed = all(r["status"] == "COMPLETED" for r in final_rows)
    summary = {
        "status": ("OFFLINE_MOCK_COMPLETE" if mode == "mock" and all_completed else
                   "FAKE_LIVE_TRANSPORT_COMPLETE" if test_mode and all_completed else
                   "TERMINALIZED_WITH_FAILURES"),
        "mode": "live_fake_transport_test" if test_mode else mode,
        "requested_mode": mode,
        "fake_transport_only": is_fake_transport,
        "assigned_rows": len(requests),
        "terminal_rows": len(final_rows),
        "completed_rows": sum(row["status"] == "COMPLETED" for row in final_rows),
        "failed_or_unexecuted_rows": sum(row["status"] != "COMPLETED" for row in final_rows),
        "logical_http_requests": attempts_started,
        "transport_invocations": attempts_started,
        "physical_http_attempts": 0 if is_fake_transport else attempts_started,
        "fake_transport_attempt_slots": attempts_started if is_fake_transport else 0,
        "retries": 0,
        "real_model_or_api_calls": 0 if is_fake_transport else attempts_started,
        "reserved_peak_cost_usd": round(reserved_usd, 12),
        "provider_reported_usage_rows": usage_rows,
        "provider_reported_peak_cost_usd": round(reported_cost, 12),
        "missing_usage_reserved_upper_usd": round(missing_usage_reserve, 12),
        "conservative_total_peak_cost_usd": round(reported_cost + missing_usage_reserve, 12),
        "hard_cost_ceiling_usd": config["hard_estimated_cost_usd"],
        "no_request_or_response_contains_auth_header": all(
            not row.get("auth_header_saved", True)
            for row in _read_jsonl(out / "attempts.jsonl")
        ),
        "provider_error_stop_reason": fatal_reason,
        "deterministic_evidence_compile_seconds": round(
            sum(request.evidence_compile_seconds for request in requests), 6),
        "request_body_bytes_total": sum(len(_json_bytes(request.http_payload)) for request in requests),
        "monitor_tokenizer_measurement": (
            "not available for hosted model; conservative bound is UTF-8 HTTP body bytes plus 128 framing tokens"
        ),
        "returned_model_identity": list(run_identity) if run_identity else None,
        "mock_is_behavior_evidence": False,
        "aggregate_budget": budget_ledger.summary() if budget_ledger is not None else None,
    }
    if secure_storage:
        final_acl = verify_private_directory_acl(out)
        manifest_after = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_after["private_storage_acl_final"] = final_acl
        _write_json(manifest_path, manifest_after)
    _write_json(out / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "runs/sprint-monitor/mock-e2e-v1")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--approval-id", default=None)
    args = parser.parse_args()
    result = run_schedule(args.out, mode=args.mode, config_path=args.config,
                          approval_id=args.approval_id)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["failed_or_unexecuted_rows"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
