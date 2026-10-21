#!/usr/bin/env python3
"""Run only the preregistered Track 2.3 pilot; no retries or resume path."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tokenizers import Tokenizer  # noqa: E402
from colluscope.deepseek_m4_v1 import (  # noqa: E402
    DeepSeekClient, DeepSeekRequestError, agent_tool, append_jsonl, canonical,
    now_utc, read_jsonl, request_payload, sha, validate_agent_arguments,
)
from colluscope.m2_v3_deepseek import _dotenv_secret, apply_private_acl  # noqa: E402
from colluscope.track23_counterfactual_v1 import (  # noqa: E402
    ARMS, EXPERIMENT_ID, INPUT_BOUND, OUTPUT_LIMIT, action_prompt,
    choose_counterproposal, message_for, settle,
)
from freeze_track23_counterfactual_v1 import (  # noqa: E402
    SOURCE, SCHEDULE_PATH, TOKENIZER_PATH, preflight,
)

AUTH_ID = "DS-FLASH-TRACK23-900-20261021"
AUTH_PATH = ROOT / "research/authorizations" / f"{AUTH_ID}.json"
PREREG_PATH = ROOT / "research/experiments" / EXPERIMENT_ID / "preregistration.json"
REGISTRATION_PATH = ROOT / "research/experiments" / EXPERIMENT_ID / "registration.json"
RUN_DIR = ROOT / "logs" / EXPERIMENT_ID
MAX_ATTEMPTS = 900
MAX_PILOT_ATTEMPTS = 56
MAX_CYCLE_MINUTES = 180
PILOT_MINUTES = 60
MAX_COST_USD = Decimal("1.80")
INPUT_RATE_PEAK = Decimal("1.32")
OUTPUT_RATE_PEAK = Decimal("3.96")


def read_json(path: Path):
    return json.loads(path.read_bytes())


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_freeze() -> tuple[dict, Tokenizer]:
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
        raise RuntimeError("immutable authorization changed after registration")
    if prereg.get("protocol", {}).get("frozen_schedule_sha256") != schedule["schedule_sha256"]:
        raise RuntimeError("registered schedule hash mismatch")
    if auth.get("approval_id") != AUTH_ID or auth.get("max_model_calls") != MAX_ATTEMPTS:
        raise RuntimeError("authorization scope mismatch")
    expiry = datetime.fromisoformat(auth["expires_at_utc"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expiry:
        raise RuntimeError("authorization expired")
    if file_sha(SOURCE) != prereg["protocol"]["source_scenario_sha256"]:
        raise RuntimeError("scenario source hash mismatch")
    if file_sha(TOKENIZER_PATH) != prereg["protocol"]["tokenizer_sha256"]:
        raise RuntimeError("pinned tokenizer hash mismatch")
    for row in prereg["protocol"]["frozen_inputs"]:
        path = ROOT / row["path"]
        if not path.is_file() or file_sha(path) != row["sha256"]:
            raise RuntimeError(f"frozen input changed: {row['path']}")
    report = preflight(schedule)
    if report.get("status") != "PASS_OFFLINE_PREFLIGHT":
        raise RuntimeError("offline preflight did not pass")
    return schedule, Tokenizer.from_file(str(TOKENIZER_PATH))


def reserved_cost(input_bound: int) -> Decimal:
    return (Decimal(input_bound) * INPUT_RATE_PEAK
            + Decimal(OUTPUT_LIMIT) * OUTPUT_RATE_PEAK) / Decimal(1_000_000)


def request_bytes(messages: list[dict[str, str]]) -> bytes:
    tool_name, schema = agent_tool("ballot")
    return canonical(request_payload(interface="strict_function_calling", messages=messages,
                                     tool_name=tool_name, schema=schema,
                                     output_limit=OUTPUT_LIMIT))


def append_event(path: Path, event: str, **fields) -> None:
    append_jsonl(path, {"event": event, "at_utc": now_utc(), **fields})


def run_pilot() -> int:
    if RUN_DIR.exists() and any(RUN_DIR.iterdir()):
        raise RuntimeError("pilot run directory is non-empty; resumption/replacement is prohibited")
    schedule, tokenizer = assert_freeze()
    secret, _ = _dotenv_secret(ROOT / ".env")
    if not secret:
        raise RuntimeError("DeepSeek credential is unavailable; no request was started")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    apply_private_acl(RUN_DIR)
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "authorization_id": AUTH_ID,
        "registered_preregistration_sha256": file_sha(PREREG_PATH),
        "schedule_sha256": schedule["schedule_sha256"],
        "source_scenario_sha256": file_sha(SOURCE),
        "tokenizer_sha256": file_sha(TOKENIZER_PATH),
        "run_started_at_utc": now_utc(),
        "phase": "pilot",
        "status": "RUNNING",
    }
    (RUN_DIR / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    attempts_path = RUN_DIR / "attempts.jsonl"
    budget_path = RUN_DIR / "budget_ledger.jsonl"
    event_path = RUN_DIR / "events.jsonl"
    record_path = RUN_DIR / "pilot_records.jsonl"
    assigned_path = RUN_DIR / "assigned_requests.jsonl"
    cost_path = RUN_DIR / "peak_cost_ledger.jsonl"
    client = DeepSeekClient(run_dir=RUN_DIR, budget_ledger=budget_path,
                            api_key=secret, interface="strict_function_calling", timeout=90)
    started_at = time.monotonic()
    spent_peak = Decimal("0")
    assignment_count = 0
    agent_tool_name, schema = agent_tool("ballot")
    for context in schedule["pilot"]:
        for agent in ("A", "B", "C"):
            append_event(assigned_path, "assigned", request_id=f"pilot-{context['context_id']}-baseline-{agent}",
                         context_id=context["context_id"], agent=agent, stage="initial", arm=None)
        for arm in context["arms_order"]:
            append_event(assigned_path, "assigned", request_id=f"pilot-{context['context_id']}-revision-{arm}",
                         context_id=context["context_id"], agent="B", stage="revision", arm=arm)

    def one_call(request_id: str, context: dict, agent: str, stage: str,
                 messages: list[dict[str, str]], arm: str | None = None):
        nonlocal spent_peak
        assignment_count_local = sum(row.get("event") == "attempt_started" for row in read_jsonl(attempts_path))
        if assignment_count_local >= MAX_PILOT_ATTEMPTS or assignment_count_local >= MAX_ATTEMPTS:
            raise RuntimeError("frozen pilot/authorization request cap reached")
        if time.monotonic() - started_at > PILOT_MINUTES * 60:
            raise RuntimeError("pilot 60-minute gate reached")
        if datetime.now(timezone.utc) > datetime.fromisoformat("2026-10-23T00:00:00+00:00"):
            raise RuntimeError("authorization expired during pilot")
        body = request_bytes(messages)
        prompt_bound = len(tokenizer.encode(body.decode("utf-8")).ids) + 256
        if prompt_bound > INPUT_BOUND:
            raise RuntimeError(f"request {request_id} exceeds 1,200-token experiment bound")
        reserve = reserved_cost(prompt_bound)
        if spent_peak + reserve > MAX_COST_USD:
            raise RuntimeError("official peak-rate cost reserve would exceed $1.80")
        expected_hash = sha(body)
        row = {
            "request_id": request_id,
            "context_id": context["context_id"],
            "agent": agent,
            "stage": stage,
            "arm": arm,
            "expected_request_sha256": expected_hash,
            "input_token_upper_bound": prompt_bound,
            "output_token_limit": OUTPUT_LIMIT,
            "peak_cost_reserve_usd": str(reserve),
        }
        append_event(event_path, "request_prepared", **row)
        try:
            result, meta = client.call(
                request_id=request_id, role="agent", messages=messages,
                tool_name=agent_tool_name, schema=schema,
                semantic=lambda value: validate_agent_arguments("ballot", value),
                metadata={"context_id": context["context_id"], "stage": stage, "arm": arm},
                output_limit=OUTPUT_LIMIT, expected_request_sha256=expected_hash,
                run_request_limit=MAX_PILOT_ATTEMPTS,
            )
            reported_input = int(meta["prompt_tokens"])
            reported_output = int(meta["completion_tokens"])
            if reported_input > prompt_bound or reported_output > OUTPUT_LIMIT:
                raise RuntimeError("provider token usage exceeded pre-dispatch bounds")
            known_peak_cost = (Decimal(reported_input) * INPUT_RATE_PEAK
                               + Decimal(reported_output) * OUTPUT_RATE_PEAK) / Decimal(1_000_000)
            spent_peak += reserve
            append_event(cost_path, "request_cost", request_id=request_id,
                         reserve_usd=str(reserve), known_peak_usd=str(known_peak_cost),
                         input_tokens=reported_input, output_tokens=reported_output)
            append_event(event_path, "action_observed", request_id=request_id,
                         context_id=context["context_id"], agent=agent, stage=stage,
                         arm=arm, action=result, request_sha256=expected_hash,
                         provider_model=meta["returned_model"],
                         system_fingerprint=meta["system_fingerprint"])
            return result["assignment"], meta
        except DeepSeekRequestError as exc:
            attempt_rows = read_jsonl(attempts_path)
            was_started = any(r.get("event") == "attempt_started" and r.get("request_id") == request_id
                              for r in attempt_rows)
            if was_started:
                spent_peak += reserve
                append_event(cost_path, "unknown_or_failed_attempt_reserve",
                             request_id=request_id, reserve_usd=str(reserve), status=exc.status)
            append_event(event_path, "action_failed", request_id=request_id,
                         context_id=context["context_id"], agent=agent, stage=stage,
                         arm=arm, status=exc.status, fatal=exc.fatal)
            if exc.status.startswith(("HTTP_", "TRANSPORT_ERROR", "PROVIDER_", "GLOBAL_",
                                      "RUN_REQUEST_CAP", "INPUT_BOUND", "FROZEN_REQUEST_HASH")):
                raise
            return None, {"status": exc.status}

    try:
        for context in schedule["pilot"]:
            baselines: dict[str, dict[str, str]] = {}
            for agent in ("A", "B", "C"):
                rid = f"pilot-{context['context_id']}-baseline-{agent}"
                try:
                    action, _ = one_call(rid, context, agent, "initial",
                                         action_prompt(context, agent, stage="initial"))
                except DeepSeekRequestError:
                    raise
                if action is not None:
                    baselines[agent] = action
            if set(baselines) != {"A", "B", "C"}:
                append_event(event_path, "branches_unstarted", context_id=context["context_id"],
                             reason="one or more initial ballots invalid or unavailable")
                continue
            proposal = choose_counterproposal(context, baselines["B"])
            branch_actions: dict[str, dict[str, str] | None] = {}
            prompt_hashes: dict[str, bytes] = {}
            for arm in context["arms_order"]:
                message = message_for(arm, baselines["B"], proposal)
                delivery_timestamp = None
                delivery_payload_sha256 = None
                if arm in {"A_PLUS", "P_PLUS"}:
                    payload = message["visible_text"].encode("utf-8")
                    delivery_timestamp = now_utc()
                    delivery_payload_sha256 = hashlib.sha256(payload).hexdigest()
                    append_event(event_path, "delivery_attempted",
                                 context_id=context["context_id"], arm=arm, sender="A",
                                 recipient="B", payload_sha256=delivery_payload_sha256,
                                 visible_text=message["visible_text"],
                                 occurred_at_utc=delivery_timestamp,
                                 before_action_request_id=f"pilot-{context['context_id']}-revision-{arm}")
                elif arm == "P_MINUS":
                    payload = ("I propose this alternative allocation based on the public scores: "
                               + json.dumps(proposal, sort_keys=True)).encode("utf-8")
                    append_event(event_path, "message_withheld",
                                 context_id=context["context_id"], arm=arm, sender="A", recipient="B",
                                 payload_sha256=hashlib.sha256(payload).hexdigest(), visible_to_recipient=False)
                messages = action_prompt(context, "B", stage="revision", ballots=baselines, message=message)
                prompt_hashes[arm] = canonical(messages)
                rid = f"pilot-{context['context_id']}-revision-{arm}"
                action, _ = one_call(rid, context, "B", "revision", messages, arm)
                branch_actions[arm] = action
                if arm in {"A_PLUS", "P_PLUS"}:
                    terminal_rows = [row for row in read_jsonl(attempts_path)
                                     if row.get("event") == "attempt_terminal" and row.get("request_id") == rid]
                    response_exists = (RUN_DIR / "responses" / f"{rid}.bin").is_file()
                    delivered = (len(terminal_rows) == 1 and terminal_rows[0].get("http_status") == 200
                                 and response_exists)
                else:
                    delivered = False
                if arm in {"A_PLUS", "P_PLUS"} and delivered:
                    append_event(event_path, "delivery_receipt_confirmed",
                                 context_id=context["context_id"], arm=arm, sender="A", recipient="B",
                                 payload_sha256=delivery_payload_sha256,
                                 occurred_at_utc=delivery_timestamp,
                                 request_id=rid, recipient_request_sha256=sha(request_bytes(messages)))
            if prompt_hashes["N"] != prompt_hashes["P_MINUS"]:
                raise RuntimeError(f"runtime N/P- prompt parity failed for {context['context_id']}")
            outcomes = {}
            if set(baselines) == {"A", "B", "C"}:
                for arm, b_action in branch_actions.items():
                    if b_action is not None:
                        outcomes[arm] = settle(context, {**baselines, "B": b_action})
                baseline_similarity = baselines["A"] == baselines["B"]
            else:
                baseline_similarity = None
            append_event(record_path, "context_result", context_id=context["context_id"],
                         phase="pilot", visible_target_to_AB=context["visible_target_to_AB"],
                         target_regret=context["target_regret"], baseline_ballots=baselines,
                         counterproposal=proposal, branch_ballots=branch_actions,
                         branch_settlements=outcomes,
                         independent_initial_AB_agreement=baseline_similarity,
                         N_P_MINUS_identical_prompt_sha256=sha(prompt_hashes["N"]))
        final_attempts = read_jsonl(attempts_path)
        starts = [row for row in final_attempts if row.get("event") == "attempt_started"]
        terminals = [row for row in final_attempts if row.get("event") == "attempt_terminal"]
        manifest.update({
            "status": "PILOT_DISPATCH_COMPLETE",
            "run_finished_at_utc": now_utc(),
            "physical_attempts_started": len(starts),
            "terminal_attempts": len(terminals),
            "known_peak_rate_reserve_usd": str(spent_peak),
            "unstarted_assigned_requests": MAX_PILOT_ATTEMPTS - len(starts),
        })
        (RUN_DIR / "manifest.json").write_bytes(canonical(manifest) + b"\n")
        print(json.dumps({"status": manifest["status"],
                          "assigned": MAX_PILOT_ATTEMPTS,
                          "started": len(starts),
                          "terminal": len(terminals),
                          "known_peak_rate_reserve_usd": str(spent_peak),
                          "raw_run_dir": str(RUN_DIR)}, indent=2))
        return 0
    except BaseException as error:
        attempts = read_jsonl(attempts_path)
        started_count = sum(row.get("event") == "attempt_started" for row in attempts)
        manifest.update({"status": "STOPPED", "run_finished_at_utc": now_utc(),
                         "physical_attempts_started": started_count,
                         "known_peak_rate_reserve_usd": str(spent_peak),
                         "failure_type": type(error).__name__,
                         "failure_status": getattr(error, "status", "UNCLASSIFIED")})
        (RUN_DIR / "manifest.json").write_bytes(canonical(manifest) + b"\n")
        append_event(event_path, "dispatch_stopped", failure_type=type(error).__name__,
                     failure_status=getattr(error, "status", "UNCLASSIFIED"),
                     attempts_started=started_count)
        raise


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    if args.preflight == args.pilot:
        parser.error("choose exactly one of --preflight or --pilot")
    if args.preflight:
        schedule, _ = assert_freeze()
        print(json.dumps({"status": "PASS_PILOT_PRE_DISPATCH",
                          "schedule_sha256": schedule["schedule_sha256"],
                          "api_key_present": bool(_dotenv_secret(ROOT / ".env")[0]),
                          "network_calls": 0, "model_calls": 0}, indent=2))
        return 0
    return run_pilot()


if __name__ == "__main__":
    raise SystemExit(main())
