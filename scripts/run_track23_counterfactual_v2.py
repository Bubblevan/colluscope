#!/usr/bin/env python3
"""Execute the frozen sender-authored Track 2.3 cycle, one gated phase at a time."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tokenizers import Tokenizer  # noqa: E402
import colluscope.deepseek_m4_v1 as deepseek_client_module  # noqa: E402
from colluscope.deepseek_m4_v1 import (  # noqa: E402
    DeepSeekClient, DeepSeekRequestError, agent_tool, append_jsonl,
    canonical, monitor_tool, now_utc, read_jsonl, request_payload, sha,
    validate_agent_arguments, validate_monitor_arguments,
)
from colluscope.m2_v3_deepseek import _dotenv_secret, apply_private_acl  # noqa: E402
from colluscope.track23_counterfactual_v1 import action_prompt, settle  # noqa: E402
from colluscope.track23_counterfactual_v2 import (  # noqa: E402
    ARMS, EXPERIMENT_ID, INPUT_BOUND, MAIN_REPEATS, MONITOR_LABELS,
    NEUTRAL_TEXT, OUTPUT_LIMIT, PILOT_REPEATS, monitor_prompt,
    monitor_tool_v2, outcome_for, parse_proposal, recipient_prompt,
    sender_prompt, validate_monitor_v2, researcher_evidence_packet,
    ordinary_evidence_packet, filter_monitor_payload,
)
from freeze_track23_counterfactual_v2 import (  # noqa: E402
    SCHEDULE_PATH, TOKENIZER_PATH, preflight,
)

AUTH_ID = "DS-FLASH-TRACK23-YOKED-4500-20261021"
AUTH_PATH = ROOT / "research/authorizations" / f"{AUTH_ID}.json"
PREREG_PATH = ROOT / "research/experiments" / EXPERIMENT_ID / "preregistration.json"
REGISTRATION_PATH = ROOT / "research/experiments" / EXPERIMENT_ID / "registration.json"
RUN_DIR = ROOT / "logs" / EXPERIMENT_ID
MAX_ATTEMPTS = 4500
MAX_COST_USD = Decimal("1.95")
PROJECT_CALL_CAP = 6500
PROJECT_COST_CAP = Decimal("3.00")
INPUT_RATE_PEAK = Decimal("0.30")
OUTPUT_RATE_PEAK = Decimal("1.20")
MAX_CYCLE_MINUTES = 360
PILOT_MINUTES = 60
REQUEST_TIMEOUT_SECONDS = 90
ACTIVE_PHASE: str | None = None
ACTIVE_PHASE_STARTED: float | None = None
AUTH_EXPIRY: datetime | None = None
RUN_STARTED_UTC: datetime | None = None


def read_json(path: Path):
    return json.loads(path.read_bytes())


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_usage() -> dict:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/researchctl.py"), "audit"],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("researchctl audit failed before dispatch")
    report = json.loads(result.stdout)
    if report.get("integrity_check") != "PASS":
        raise RuntimeError("research registry integrity is not PASS")
    return report["new_iteration_usage"]


def assert_freeze() -> tuple[dict, Tokenizer, dict]:
    schedule = read_json(SCHEDULE_PATH)
    schedule_core = {key: value for key, value in schedule.items() if key != "schedule_sha256"}
    if sha(canonical(schedule_core)) != schedule.get("schedule_sha256"):
        raise RuntimeError("frozen schedule digest mismatch")
    prereg = read_json(PREREG_PATH)
    registration = read_json(REGISTRATION_PATH)
    auth = read_json(AUTH_PATH)
    if prereg.get("experiment_id") != EXPERIMENT_ID or registration.get("experiment_id") != EXPERIMENT_ID:
        raise RuntimeError("experiment identity mismatch")
    if prereg.get("authorization_batch_sha256") != file_sha(AUTH_PATH):
        raise RuntimeError("immutable authorization hash mismatch")
    if registration.get("preregistration_sha256") != file_sha(PREREG_PATH):
        raise RuntimeError("registered preregistration changed after freeze")
    if prereg.get("protocol", {}).get("frozen_schedule_sha256") != schedule["schedule_sha256"]:
        raise RuntimeError("registered schedule hash mismatch")
    if auth.get("approval_id") != AUTH_ID or auth.get("max_model_calls") != MAX_ATTEMPTS:
        raise RuntimeError("authorization scope mismatch")
    expiry = datetime.fromisoformat(auth["expires_at_utc"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expiry:
        raise RuntimeError("authorization expired")
    for row in prereg["protocol"]["frozen_inputs"]:
        path = ROOT / row["path"]
        if not path.is_file() or file_sha(path) != row["sha256"]:
            raise RuntimeError(f"frozen input changed: {row['path']}")
    offline = preflight(schedule)
    if offline.get("status") != "PASS_OFFLINE_PREFLIGHT":
        raise RuntimeError("offline preflight did not pass")
    return schedule, Tokenizer.from_file(str(TOKENIZER_PATH)), prereg


def assigned_requests(schedule: dict) -> list[dict]:
    rows = []
    for context in schedule["pilot"]:
        prefix = f"pilot-{context['context_id']}"
        for agent in ("A", "B", "C"):
            rows.append({"request_id": f"{prefix}-baseline-{agent}", "phase": "pilot", "context_id": context["context_id"], "role": "agent", "agent": agent, "stage": "initial", "arm": None, "replicate": 0})
        rows.append({"request_id": f"{prefix}-message-A", "phase": "pilot", "context_id": context["context_id"], "role": "agent", "agent": "A", "stage": "message", "arm": None, "replicate": 0})
        for arm in context["branch_orders"][0]:
            rows.append({"request_id": f"{prefix}-B-{arm}-r01", "phase": "pilot", "context_id": context["context_id"], "role": "agent", "agent": "B", "stage": "revision", "arm": arm, "replicate": 1})
    for context in schedule["main"]:
        prefix = f"main-{context['context_id']}"
        for agent in ("A", "B", "C"):
            rows.append({"request_id": f"{prefix}-baseline-{agent}", "phase": "main", "context_id": context["context_id"], "role": "agent", "agent": agent, "stage": "initial", "arm": None, "replicate": 0})
        rows.append({"request_id": f"{prefix}-message-A", "phase": "main", "context_id": context["context_id"], "role": "agent", "agent": "A", "stage": "message", "arm": None, "replicate": 0})
        for replicate, order in enumerate(context["branch_orders"], start=1):
            for arm in order:
                rows.append({"request_id": f"{prefix}-B-{arm}-r{replicate:02d}", "phase": "main", "context_id": context["context_id"], "role": "agent", "agent": "B", "stage": "revision", "arm": arm, "replicate": replicate})
    heldout = schedule["monitor_plan"]["researcher_heldout_contexts"]
    for context_id in heldout:
        for method in ("dialogue_only", "action_payoff_only", "dialogue_action", "plus_factor"):
            rows.append({"request_id": f"monitor-researcher-{context_id}-{method}", "phase": "monitors", "context_id": context_id, "role": "monitor", "view": "researcher", "method": method})
    for context_id in schedule["monitor_plan"]["ordinary_observer_contexts"]:
        for arm in ARMS:
            for method in ("dialogue_only", "action_payoff_only", "dialogue_action", "plus_factor"):
                rows.append({"request_id": f"monitor-observer-{context_id}-{arm}-{method}", "phase": "monitors", "context_id": context_id, "role": "monitor", "view": "ordinary_single_branch", "arm": arm, "method": method})
    if len(rows) != schedule["maximum_frozen_schedule_requests"]:
        raise RuntimeError(f"assigned request count mismatch: {len(rows)}")
    return rows


def prepare_run(schedule: dict, prereg: dict, usage_before: dict) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    apply_private_acl(RUN_DIR)
    manifest_path = RUN_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        if manifest.get("schedule_sha256") != schedule["schedule_sha256"]:
            raise RuntimeError("existing private run directory belongs to another freeze")
    else:
        manifest = {
            "experiment_id": EXPERIMENT_ID,
            "authorization_id": AUTH_ID,
            "registered_preregistration_sha256": file_sha(PREREG_PATH),
            "schedule_sha256": schedule["schedule_sha256"],
            "source_schedule_sha256": schedule["source_schedule_sha256"],
            "tokenizer_sha256": file_sha(TOKENIZER_PATH),
            "project_usage_before": usage_before,
            "run_started_at_utc": now_utc(),
            "status": "RUNNING",
        }
        manifest_path.write_bytes(canonical(manifest) + b"\n")
    assigned_path = RUN_DIR / "assigned_requests.jsonl"
    if not assigned_path.exists():
        for row in assigned_requests(schedule):
            append_jsonl(assigned_path, {"event": "assigned", **row})


def load_events() -> list[dict]:
    return read_jsonl(RUN_DIR / "events.jsonl")


def find_context(schedule: dict, phase: str, context_id: str) -> dict:
    contexts = schedule["pilot"] if phase == "pilot" else schedule["main"]
    return next(row for row in contexts if row["context_id"] == context_id)


def recipient_request_text(body: bytes) -> str:
    payload = json.loads(body)
    user = payload["messages"][1]["content"]
    prefix = "Submit your final ballot. Observation (JSON):\n"
    if not user.startswith(prefix):
        raise RuntimeError("unexpected recipient prompt shape")
    return user[len(prefix):]


def check_hidden_target_not_disclosed(context: dict, messages: list[dict[str, str]]) -> None:
    if context["visible_target_to_AB"]:
        return
    content = "\n".join(message["content"] for message in messages)
    target_literal = json.dumps(context["target"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if target_literal in content:
        raise RuntimeError("hidden target appears in a recipient prompt")


def call_model(
    *, client: DeepSeekClient, tokenizer: Tokenizer, request_id: str, role: str,
    context: dict, stage: str, arm: str | None, replicate: int,
    messages: list[dict[str, str]], kind: str, allowed_refs: set[str] | None = None,
) -> tuple[dict, dict, bytes, Decimal]:
    if ACTIVE_PHASE_STARTED is None or ACTIVE_PHASE is None:
        raise RuntimeError("a phase must be opened before dispatch")
    now = datetime.now(timezone.utc)
    if RUN_STARTED_UTC is None or (now - RUN_STARTED_UTC).total_seconds() >= MAX_CYCLE_MINUTES * 60:
        raise RuntimeError("six-hour cycle wall-clock gate reached before request start")
    phase_cap = PILOT_MINUTES if ACTIVE_PHASE == "pilot" else MAX_CYCLE_MINUTES
    if time.monotonic() - ACTIVE_PHASE_STARTED >= phase_cap * 60:
        raise RuntimeError(f"{ACTIVE_PHASE} wall-clock gate reached before request start")
    if AUTH_EXPIRY is None or now > AUTH_EXPIRY:
        raise RuntimeError("authorization expired before request start")
    if kind == "monitor":
        tool_name, schema = monitor_tool_v2()
        semantic = lambda value: validate_monitor_v2(value, allowed_refs or set())
    else:
        tool_name, schema = agent_tool(kind)
        semantic = lambda value: validate_agent_arguments(kind, value)
    body = canonical(request_payload(
        interface="strict_function_calling", messages=messages,
        tool_name=tool_name, schema=schema, output_limit=OUTPUT_LIMIT,
    ))
    prompt_bound = len(tokenizer.encode(body.decode("utf-8")).ids) + 256
    if prompt_bound > INPUT_BOUND:
        raise RuntimeError(f"request {request_id} exceeds {INPUT_BOUND}-token input bound")
    reserve = (Decimal(prompt_bound) * INPUT_RATE_PEAK + Decimal(OUTPUT_LIMIT) * OUTPUT_RATE_PEAK) / Decimal(1_000_000)
    attempts_path = RUN_DIR / "attempts.jsonl"
    attempts = read_jsonl(attempts_path)
    started_count = sum(row.get("event") == "attempt_started" for row in attempts)
    prior_reserve = sum((Decimal(row["reserved_cost_usd"]) for row in load_events()
                         if row.get("event") == "request_reserved"), Decimal("0"))
    if started_count >= MAX_ATTEMPTS:
        raise RuntimeError("authorization attempt ceiling reached")
    if int(usage_before_calls()) + started_count + 1 > PROJECT_CALL_CAP:
        raise RuntimeError("cumulative project call cap would be exceeded")
    if prior_reserve + reserve > MAX_COST_USD:
        raise RuntimeError("new-cycle peak-rate reservation would exceed $1.95")
    request_hash = sha(body)
    append_jsonl(RUN_DIR / "events.jsonl", {
        "event": "request_reserved", "request_id": request_id,
        "context_id": context["context_id"], "phase": context["phase"],
        "role": role, "stage": stage, "arm": arm, "replicate": replicate,
        "request_sha256": request_hash, "input_token_bound": prompt_bound,
        "reserved_cost_usd": str(reserve), "reserved_at_utc": now_utc(),
    })
    try:
        result, meta = client.call(
            request_id=request_id,
            role=role,
            messages=messages,
            tool_name=tool_name,
            schema=schema,
            semantic=semantic,
            metadata={"experiment_id": EXPERIMENT_ID, "context_id": context["context_id"],
                      "stage": stage, "arm": arm, "replicate": replicate},
            output_limit=OUTPUT_LIMIT,
            expected_request_sha256=request_hash,
            run_request_limit=MAX_ATTEMPTS,
        )
    except DeepSeekRequestError as exc:
        append_jsonl(RUN_DIR / "events.jsonl", {
            "event": "request_failed", "request_id": request_id,
            "context_id": context["context_id"], "stage": stage, "arm": arm,
            "replicate": replicate, "status": exc.status, "fatal": exc.fatal,
            "occurred_at_utc": now_utc(),
        })
        raise
    response_path = RUN_DIR / "responses" / f"{request_id}.bin"
    response = json.loads(response_path.read_bytes())
    usage = response.get("usage", {})
    prompt_tokens = int(usage.get("prompt_tokens", meta.get("prompt_tokens", 0)))
    completion_tokens = int(usage.get("completion_tokens", meta.get("completion_tokens", 0)))
    known_peak_cost = (Decimal(prompt_tokens) * INPUT_RATE_PEAK
                       + Decimal(completion_tokens) * OUTPUT_RATE_PEAK) / Decimal(1_000_000)
    append_jsonl(RUN_DIR / "events.jsonl", {
        "event": "request_completed", "request_id": request_id,
        "context_id": context["context_id"], "stage": stage, "arm": arm,
        "replicate": replicate, "status": "COMPLETED",
        "provider_model": meta["returned_model"],
        "system_fingerprint": meta["system_fingerprint"],
        "request_sha256": request_hash, "response_sha256": file_sha(response_path),
        "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
        "prompt_cache_hit_tokens": usage.get("prompt_cache_hit_tokens"),
        "prompt_cache_miss_tokens": usage.get("prompt_cache_miss_tokens"),
        "uncached_peak_cost_usd": str(known_peak_cost), "completed_at_utc": now_utc(),
    })
    return result, meta, body, known_peak_cost


def usage_before_calls() -> int:
    manifest = read_json(RUN_DIR / "manifest.json")
    return int(manifest["project_usage_before"]["model_calls"])


def run_pilot(client: DeepSeekClient, tokenizer: Tokenizer, schedule: dict) -> None:
    global ACTIVE_PHASE, ACTIVE_PHASE_STARTED
    if any(row.get("event") == "attempt_started" for row in read_jsonl(RUN_DIR / "attempts.jsonl")):
        raise RuntimeError("pilot already has a started physical attempt; resumption is prohibited")
    phase_start = time.monotonic()
    ACTIVE_PHASE, ACTIVE_PHASE_STARTED = "pilot", phase_start
    append_jsonl(RUN_DIR / "events.jsonl", {"event": "phase_started", "phase": "pilot", "at_utc": now_utc()})
    for context in schedule["pilot"]:
        baselines: dict[str, dict[str, str]] = {}
        for agent in ("A", "B", "C"):
            rid = f"pilot-{context['context_id']}-baseline-{agent}"
            action, _, _, _ = call_model(client=client, tokenizer=tokenizer, request_id=rid,
                                         role="agent", context=context, stage="initial", arm=None,
                                         replicate=0, messages=action_prompt(context, agent, stage="initial"),
                                         kind="ballot")
            baselines[agent] = action["assignment"]
            append_jsonl(RUN_DIR / "events.jsonl", {"event": "baseline_ballot", "context_id": context["context_id"],
                                                    "agent": agent, "ballot": action["assignment"], "request_id": rid})
        sender_id = f"pilot-{context['context_id']}-message-A"
        sender_action, _, _, _ = call_model(client=client, tokenizer=tokenizer, request_id=sender_id,
                                            role="agent", context=context, stage="message", arm=None,
                                            replicate=0, messages=sender_prompt(context, baselines["A"]),
                                            kind="message")
        sender_text = sender_action.get("text", "")
        proposal = parse_proposal(sender_text)
        if proposal is None:
            raise RuntimeError(f"sender message format was invalid in {context['context_id']}; no replacement")
        message_hash = hashlib.sha256(sender_text.encode("utf-8")).hexdigest()
        append_jsonl(RUN_DIR / "events.jsonl", {"event": "sender_message", "context_id": context["context_id"],
                                                "sender_text": sender_text, "proposal": proposal,
                                                "message_sha256": message_hash, "request_id": sender_id})
        for arm in context["branch_orders"][0]:
            rid = f"pilot-{context['context_id']}-B-{arm}-r01"
            messages = recipient_prompt(context, baselines["B"], arm, sender_text)
            check_hidden_target_not_disclosed(context, messages)
            delivery_at = now_utc() if arm in {"PEER", "AIDE", "NEUTRAL"} else None
            if arm in {"PEER", "AIDE", "NEUTRAL"}:
                delivered_text = sender_text if arm in {"PEER", "AIDE"} else NEUTRAL_TEXT
                append_jsonl(RUN_DIR / "events.jsonl", {"event": "message_delivery", "context_id": context["context_id"],
                                                        "arm": arm, "message_sha256": hashlib.sha256(delivered_text.encode("utf-8")).hexdigest(),
                                                        "delivered_before_request": True, "delivery_at_utc": delivery_at})
            else:
                append_jsonl(RUN_DIR / "events.jsonl", {"event": "message_withheld", "context_id": context["context_id"],
                                                        "arm": arm, "withheld_message_sha256": message_hash})
            action, meta, body, _ = call_model(client=client, tokenizer=tokenizer, request_id=rid,
                                               role="agent", context=context, stage="revision", arm=arm,
                                               replicate=1, messages=messages, kind="ballot")
            final_b = action["assignment"]
            outcome = outcome_for(context, baselines, final_b)
            prompt_text = recipient_request_text(body)
            prompt_obj = json.loads(prompt_text)
            visible_message = prompt_obj.get("peer_message", {})
            if arm in {"PEER", "AIDE"}:
                receipt_match = visible_message.get("visible_text") == sender_text and visible_message.get("delivery_status") == "delivered"
            elif arm == "NEUTRAL":
                receipt_match = visible_message.get("visible_text") == NEUTRAL_TEXT and visible_message.get("delivery_status") == "delivered"
            else:
                receipt_match = visible_message.get("delivery_status") == "none"
            if not receipt_match:
                raise RuntimeError("sender message delivery receipt mismatch")
            append_jsonl(RUN_DIR / "events.jsonl", {
                "event": "branch_ballot", "context_id": context["context_id"], "arm": arm,
                "replicate": 1, "ballot": final_b, "outcome": outcome,
                "proposal_adopted_with_change": bool(proposal != baselines["B"] and final_b == proposal),
                "request_id": rid, "request_sha256": sha(body),
                "message_sha256": message_hash if arm in {"PEER", "AIDE"} else None,
                "delivery_at_utc": delivery_at,
                "delivery_receipt_match": receipt_match,
                "request_completed_at_utc": meta.get("at_utc", now_utc()),
            })
        if time.monotonic() - phase_start > PILOT_MINUTES * 60:
            raise RuntimeError("pilot 60-minute timebox reached")
    append_jsonl(RUN_DIR / "events.jsonl", {"event": "phase_completed", "phase": "pilot", "at_utc": now_utc()})
    (RUN_DIR / "phase_pilot_complete.json").write_bytes(canonical({"phase": "pilot", "completed_at_utc": now_utc()}) + b"\n")


def require_phase_summary(phase: str) -> dict:
    path = RUN_DIR / f"{phase}_summary.json"
    if not path.is_file():
        raise RuntimeError(f"{phase} analysis summary is missing")
    return read_json(path)


def run_main(client: DeepSeekClient, tokenizer: Tokenizer, schedule: dict) -> None:
    global ACTIVE_PHASE, ACTIVE_PHASE_STARTED
    pilot = require_phase_summary("pilot")
    if pilot.get("expansion_gate") != "PASS" or pilot.get("integrity_pass") is not True:
        raise RuntimeError("registered pilot gates did not pass; main phase is not authorized by the protocol")
    if not (RUN_DIR / "phase_pilot_complete.json").exists():
        raise RuntimeError("pilot phase completion marker is missing")
    if any(row.get("event") == "attempt_started" for row in read_jsonl(RUN_DIR / "attempts.jsonl")):
        # The pilot has attempts. Main IDs are checked separately to prevent resume.
        prior_ids = {row.get("request_id") for row in read_jsonl(RUN_DIR / "attempts.jsonl") if row.get("event") == "attempt_started"}
        if any(request_id.startswith("main-") for request_id in prior_ids):
            raise RuntimeError("main already has a started attempt; resumption is prohibited")
    phase_start = time.monotonic()
    ACTIVE_PHASE, ACTIVE_PHASE_STARTED = "main", phase_start
    append_jsonl(RUN_DIR / "events.jsonl", {"event": "phase_started", "phase": "main", "at_utc": now_utc()})
    for context in schedule["main"]:
        baselines: dict[str, dict[str, str]] = {}
        for agent in ("A", "B", "C"):
            rid = f"main-{context['context_id']}-baseline-{agent}"
            action, _, _, _ = call_model(client=client, tokenizer=tokenizer, request_id=rid,
                                         role="agent", context=context, stage="initial", arm=None,
                                         replicate=0, messages=action_prompt(context, agent, stage="initial"),
                                         kind="ballot")
            baselines[agent] = action["assignment"]
            append_jsonl(RUN_DIR / "events.jsonl", {"event": "baseline_ballot", "context_id": context["context_id"],
                                                    "agent": agent, "ballot": action["assignment"], "request_id": rid})
        sender_id = f"main-{context['context_id']}-message-A"
        sender_action, _, _, _ = call_model(client=client, tokenizer=tokenizer, request_id=sender_id,
                                            role="agent", context=context, stage="message", arm=None,
                                            replicate=0, messages=sender_prompt(context, baselines["A"]),
                                            kind="message")
        sender_text = sender_action.get("text", "")
        proposal = parse_proposal(sender_text)
        if proposal is None:
            raise RuntimeError(f"sender message format was invalid in {context['context_id']}; no replacement")
        message_hash = hashlib.sha256(sender_text.encode("utf-8")).hexdigest()
        append_jsonl(RUN_DIR / "events.jsonl", {"event": "sender_message", "context_id": context["context_id"],
                                                "sender_text": sender_text, "proposal": proposal,
                                                "message_sha256": message_hash, "request_id": sender_id})
        for replicate, order in enumerate(context["branch_orders"], start=1):
            for arm in order:
                rid = f"main-{context['context_id']}-B-{arm}-r{replicate:02d}"
                messages = recipient_prompt(context, baselines["B"], arm, sender_text)
                check_hidden_target_not_disclosed(context, messages)
                delivery_at = now_utc() if arm in {"PEER", "AIDE", "NEUTRAL"} else None
                if arm in {"PEER", "AIDE", "NEUTRAL"}:
                    append_jsonl(RUN_DIR / "events.jsonl", {"event": "message_delivery", "context_id": context["context_id"],
                                                            "arm": arm, "replicate": replicate,
                                                            "message_sha256": message_hash if arm in {"PEER", "AIDE"} else hashlib.sha256(NEUTRAL_TEXT.encode("utf-8")).hexdigest(),
                                                            "delivered_before_request": True, "delivery_at_utc": delivery_at})
                else:
                    append_jsonl(RUN_DIR / "events.jsonl", {"event": "message_withheld", "context_id": context["context_id"],
                                                            "replicate": replicate, "arm": arm,
                                                            "withheld_message_sha256": message_hash})
                action, meta, body, _ = call_model(client=client, tokenizer=tokenizer, request_id=rid,
                                                   role="agent", context=context, stage="revision", arm=arm,
                                                   replicate=replicate, messages=messages, kind="ballot")
                final_b = action["assignment"]
                outcome = outcome_for(context, baselines, final_b)
                prompt_obj = json.loads(recipient_request_text(body))
                visible_message = prompt_obj.get("peer_message", {})
                if arm in {"PEER", "AIDE"}:
                    receipt_match = visible_message.get("visible_text") == sender_text and visible_message.get("delivery_status") == "delivered"
                elif arm == "NEUTRAL":
                    receipt_match = visible_message.get("visible_text") == NEUTRAL_TEXT and visible_message.get("delivery_status") == "delivered"
                else:
                    receipt_match = visible_message.get("delivery_status") == "none"
                if not receipt_match:
                    raise RuntimeError("sender message delivery receipt mismatch")
                append_jsonl(RUN_DIR / "events.jsonl", {
                    "event": "branch_ballot", "context_id": context["context_id"], "arm": arm,
                    "replicate": replicate, "ballot": final_b, "outcome": outcome,
                    "proposal_adopted_with_change": bool(proposal != baselines["B"] and final_b == proposal),
                    "request_id": rid, "request_sha256": sha(body),
                    "message_sha256": message_hash if arm in {"PEER", "AIDE"} else None,
                    "delivery_at_utc": delivery_at,
                    "delivery_receipt_match": receipt_match,
                    "request_completed_at_utc": meta.get("at_utc", now_utc()),
                })
        if time.monotonic() - phase_start > MAX_CYCLE_MINUTES * 60:
            raise RuntimeError("six-hour cycle timebox reached")
    append_jsonl(RUN_DIR / "events.jsonl", {"event": "phase_completed", "phase": "main", "at_utc": now_utc()})
    (RUN_DIR / "phase_main_complete.json").write_bytes(canonical({"phase": "main", "completed_at_utc": now_utc()}) + b"\n")


def run_monitors(client: DeepSeekClient, tokenizer: Tokenizer, schedule: dict) -> None:
    global ACTIVE_PHASE, ACTIVE_PHASE_STARTED
    main = require_phase_summary("main")
    if main.get("integrity_pass") is not True or main.get("complete_contexts") != 40:
        raise RuntimeError("monitor phase requires 40 complete, integrity-passing main contexts")
    if not (RUN_DIR / "phase_main_complete.json").exists():
        raise RuntimeError("main phase completion marker is missing")
    if any(row.get("request_id", "").startswith("monitor-") for row in read_jsonl(RUN_DIR / "attempts.jsonl") if row.get("event") == "attempt_started"):
        raise RuntimeError("monitor phase already has a started request; resumption is prohibited")
    events = load_events()
    summaries = {row["context_id"]: row for row in main["contexts"]}
    contexts = {row["context_id"]: row for row in schedule["main"]}
    phase_start = time.monotonic()
    ACTIVE_PHASE, ACTIVE_PHASE_STARTED = "monitors", phase_start
    append_jsonl(RUN_DIR / "events.jsonl", {"event": "phase_started", "phase": "monitors", "at_utc": now_utc()})
    for context_id in schedule["monitor_plan"]["researcher_heldout_contexts"]:
        context = contexts[context_id]
        summary = summaries[context_id]
        payload = researcher_evidence_packet(context, summary)
        for method in ("dialogue_only", "action_payoff_only", "dialogue_action", "plus_factor"):
            rid = f"monitor-researcher-{context_id}-{method}"
            messages = monitor_prompt(method, filter_monitor_payload(payload, method))
            refs = evidence_refs(filter_monitor_payload(payload, method))
            action, _, _, _ = call_model(client=client, tokenizer=tokenizer, request_id=rid,
                                         role="monitor", context=context, stage="monitor", arm=method,
                                         replicate=0, messages=messages, kind="monitor", allowed_refs=refs)
            append_jsonl(RUN_DIR / "events.jsonl", {"event": "monitor_result", "request_id": rid,
                                                    "view": "researcher", "context_id": context_id,
                                                    "method": method, "result": action})
    for context_id in schedule["monitor_plan"]["ordinary_observer_contexts"]:
        context = contexts[context_id]
        summary = summaries[context_id]
        first_replicate = [row for row in summary["branch_observations"] if row["replicate"] == 1]
        for arm in ARMS:
            branch = next(row for row in first_replicate if row["arm"] == arm)
            payload = ordinary_evidence_packet(context, summary, branch)
            for method in ("dialogue_only", "action_payoff_only", "dialogue_action", "plus_factor"):
                rid = f"monitor-observer-{context_id}-{arm}-{method}"
                messages = monitor_prompt(method, filter_monitor_payload(payload, method), single_branch=True)
                refs = evidence_refs(filter_monitor_payload(payload, method))
                action, _, _, _ = call_model(client=client, tokenizer=tokenizer, request_id=rid,
                                             role="monitor", context=context, stage="monitor", arm=arm,
                                             replicate=1, messages=messages, kind="monitor", allowed_refs=refs)
                append_jsonl(RUN_DIR / "events.jsonl", {"event": "monitor_result", "request_id": rid,
                                                        "view": "ordinary_single_branch", "context_id": context_id,
                                                        "arm": arm, "method": method, "result": action})
        if time.monotonic() - phase_start > MAX_CYCLE_MINUTES * 60:
            raise RuntimeError("six-hour cycle timebox reached")
    append_jsonl(RUN_DIR / "events.jsonl", {"event": "phase_completed", "phase": "monitors", "at_utc": now_utc()})
    (RUN_DIR / "phase_monitors_complete.json").write_bytes(canonical({"phase": "monitors", "completed_at_utc": now_utc()}) + b"\n")


def evidence_refs(payload: dict) -> set[str]:
    found: set[str] = set()
    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str):
                found.add(value["id"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(payload)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("pilot", "main", "monitors"))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if not args.check_only and not args.phase:
        parser.error("--phase is required unless --check-only is supplied")
    schedule, tokenizer, prereg = assert_freeze()
    global AUTH_EXPIRY, RUN_STARTED_UTC
    AUTH_EXPIRY = datetime.fromisoformat(read_json(AUTH_PATH)["expires_at_utc"].replace("Z", "+00:00"))
    check_report = preflight(schedule)
    if args.check_only:
        print(json.dumps(check_report, ensure_ascii=False, indent=2))
        return 0
    usage_before = audit_usage()
    if int(usage_before["model_calls"]) + MAX_ATTEMPTS > PROJECT_CALL_CAP:
        raise RuntimeError("the complete authorization would breach the current lifetime request ceiling")
    if Decimal(str(usage_before["external_cost_usd"])) + MAX_COST_USD > PROJECT_COST_CAP:
        raise RuntimeError("the complete authorization would breach the current lifetime cost ceiling")
    prepare_run(schedule, prereg, usage_before)
    RUN_STARTED_UTC = datetime.fromisoformat(read_json(RUN_DIR / "manifest.json")["run_started_at_utc"].replace("Z", "+00:00"))
    secret, _ = _dotenv_secret(ROOT / ".env")
    if not secret:
        raise RuntimeError("DeepSeek credential is unavailable; no request was started")
    # The legacy client has a 900-call default and a byte-based cost bound.
    # The registered runner enforces the stricter 4,500-call, tokenizer-based
    # $1.95 peak ceiling before every request; these module values only prevent
    # the legacy internal guard from contradicting that frozen grant.
    deepseek_client_module.GLOBAL_REQUEST_LIMIT = MAX_ATTEMPTS
    deepseek_client_module.GLOBAL_COST_LIMIT = Decimal("10.00")
    client = DeepSeekClient(run_dir=RUN_DIR, budget_ledger=RUN_DIR / "budget_ledger.jsonl",
                            api_key=secret, interface="strict_function_calling",
                            timeout=REQUEST_TIMEOUT_SECONDS)
    try:
        if args.phase == "pilot":
            run_pilot(client, tokenizer, schedule)
        elif args.phase == "main":
            run_main(client, tokenizer, schedule)
        else:
            run_monitors(client, tokenizer, schedule)
    except Exception as exc:
        append_jsonl(RUN_DIR / "events.jsonl", {
            "event": "phase_aborted", "phase": args.phase,
            "error_type": type(exc).__name__, "error_message": str(exc)[:500],
            "at_utc": now_utc(),
        })
        manifest_path = RUN_DIR / "manifest.json"
        manifest = read_json(manifest_path)
        manifest["status"] = "ABORTED"
        manifest["aborted_phase"] = args.phase
        manifest["aborted_at_utc"] = now_utc()
        manifest_path.write_bytes(canonical(manifest) + b"\n")
        print(json.dumps({"phase": args.phase, "status": "ABORTED", "error_type": type(exc).__name__,
                          "error_message": str(exc)[:500], "model_calls_started": sum(
                              row.get("event") == "attempt_started" for row in read_jsonl(RUN_DIR / "attempts.jsonl"))}, indent=2))
        return 2
    print(json.dumps({"phase": args.phase, "status": "COMPLETED", "model_calls_started": sum(
        row.get("event") == "attempt_started" for row in read_jsonl(RUN_DIR / "attempts.jsonl"))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
