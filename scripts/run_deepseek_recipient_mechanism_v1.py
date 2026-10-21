#!/usr/bin/env python3
"""Execute the frozen 804-request DeepSeek recipient-mechanism study."""
from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tokenizers import Tokenizer  # noqa: E402
from colluscope.deepseek_m4_v1 import (  # noqa: E402
    DeepSeekClient, DeepSeekRequestError, append_jsonl, canonical, now_utc,
    read_jsonl, request_cost_bound, request_payload, sha, write_once,
)
from colluscope.deepseek_recipient_mechanism_v1 import (  # noqa: E402
    EXPERIMENT_ID, MAX_COST_USD, MAX_OUTPUT_TOKENS, TOKENIZER_SHA256,
    build_schedule, freeze_tokenizer_parity, generate_contexts, messages_for,
    read_returned_content, schema_for, token_count, validate_semantic,
)
from colluscope.m2_v3_deepseek import (  # noqa: E402
    API_BASE, MODEL, _dotenv_secret, apply_private_acl,
)

SCHEDULE_PATH = ROOT / "research/schedules/deepseek-recipient-mechanism-v1.json"
CONFIG_PATH = ROOT / "configs/deepseek-recipient-mechanism-v1.json"
TOKENIZER_PATH = ROOT / ".cache/deepseek-recipe/tokenizer-v41.json"
AUTH_PATH = ROOT / "research/authorizations/DS-FLASH-RECIPIENT-804-20261021.json"
RUN_DIR = ROOT / "runs/deepseek-recipient-mechanism-v1"


def _load(path: Path) -> Any:
    return json.loads(path.read_bytes())


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_event(path: Path, event: str, **details: Any) -> None:
    append_jsonl(path, {"event": event, "at_utc": now_utc(), **details})


def verify_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], Tokenizer, dict[str, Any]]:
    schedule = _load(SCHEDULE_PATH)
    config = _load(CONFIG_PATH)
    if schedule.get("experiment_id") != EXPERIMENT_ID or schedule.get("request_count") != 804:
        raise RuntimeError("frozen schedule ID or assigned-request count mismatch")
    core = {k: v for k, v in schedule.items() if k != "schedule_sha256"}
    expected = hashlib.sha256(canonical(core)).hexdigest()
    if schedule.get("schedule_sha256") != expected:
        raise RuntimeError("frozen schedule hash mismatch")
    if config.get("experiment_id") != EXPERIMENT_ID or config.get("max_physical_attempts") != 804:
        raise RuntimeError("frozen configuration ID or request cap mismatch")
    config_core = {k: v for k, v in config.items() if k != "config_sha256"}
    if config.get("config_sha256") != hashlib.sha256(canonical(config_core)).hexdigest():
        raise RuntimeError("frozen configuration hash mismatch")
    if (config.get("model_requested") != MODEL
            or config.get("official_endpoint") != "https://api.deepseek.com/chat/completions"
            or config.get("retry_limit") != 0 or config.get("replacement_limit") != 0
            or Decimal(str(config.get("max_peak_cost_usd"))) != Decimal("1.40")):
        raise RuntimeError("configuration endpoint, model, retry, replacement, or cost ceiling drift")
    if _hash(TOKENIZER_PATH) != TOKENIZER_SHA256:
        raise RuntimeError("official V4.1 tokenizer hash mismatch")
    contexts = generate_contexts()
    if canonical(contexts) != canonical(schedule.get("contexts")):
        raise RuntimeError("schedule contexts differ from deterministic selector replay")
    requests = build_schedule(contexts)
    if canonical(requests) != canonical(schedule.get("requests")):
        raise RuntimeError("request dependency schedule differs from frozen selector replay")
    tokenizer = Tokenizer.from_file(str(TOKENIZER_PATH))
    parity = freeze_tokenizer_parity(tokenizer)
    if parity.get("status") != "PASS_STATIC_STIMULUS_PARITY":
        raise RuntimeError("static tokenizer parity gate failed")
    return schedule, config, tokenizer, parity


def _provider_key() -> str:
    key, values = _dotenv_secret(ROOT / ".env")
    if values.get("LLM_BASE_URL", API_BASE) != API_BASE or values.get("LLM_MODEL_ID", MODEL) != MODEL:
        raise RuntimeError(".env provider identity is not the frozen official DeepSeek Flash endpoint/alias")
    if not key:
        raise RuntimeError("DeepSeek credential is not configured in the local environment")
    return key


def _request_payload(messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
    payload = request_payload(interface="json_object_fallback", messages=messages,
                              tool_name="submit_choice", schema=schema,
                              output_limit=MAX_OUTPUT_TOKENS)
    if payload.get("model") != MODEL or payload.get("response_format") != {"type": "json_object"}:
        raise RuntimeError("request body differs from frozen API interface")
    return payload


def _existing_state(run_dir: Path) -> tuple[set[str], set[str], dict[str, str], dict[str, dict[str, Any]]]:
    rows = read_jsonl(run_dir / "attempts.jsonl")
    starts = {r["request_id"] for r in rows if r.get("event") == "attempt_started"}
    terminals = {r["request_id"] for r in rows if r.get("event") == "attempt_terminal"}
    if starts - terminals:
        raise RuntimeError("an earlier request lacks a terminal row; possible billing is ambiguous, so resume stops")
    outputs: dict[str, str] = {}
    responses: dict[str, dict[str, Any]] = {}
    for request_id in starts:
        content, response = read_returned_content(run_dir, request_id)
        if content is not None:
            outputs[request_id] = content
        if response is not None:
            responses[request_id] = response
        request_file = run_dir / "requests" / f"{request_id}.bin"
        if request_file.is_file():
            payload = json.loads(request_file.read_bytes())
            outputs[f"prompt:{request_id}"] = json.dumps(payload["messages"], ensure_ascii=False,
                                                           sort_keys=True, separators=(",", ":"))
    return starts, terminals, outputs, responses


def _registered_scope_check() -> None:
    budget = _load(ROOT / "research/budget.json")
    authorization = budget.get("authorization", {})
    if (authorization.get("status") != "active"
            or authorization.get("approval_id") != "DS-FLASH-RECIPIENT-804-20261021"
            or authorization.get("authorized_experiment_ids") != [EXPERIMENT_ID]
            or authorization.get("max_model_calls") != 804
            or Decimal(str(authorization.get("max_external_cost_usd"))) != Decimal("1.40")):
        raise RuntimeError("active user authorization does not match this exact experiment and hard caps")
    prereg = ROOT / "research/experiments" / EXPERIMENT_ID / "preregistration.json"
    registration = ROOT / "research/experiments" / EXPERIMENT_ID / "registration.json"
    if not prereg.is_file() or not registration.is_file():
        raise RuntimeError("experiment is not preregistered in the research registry")
    record = _load(prereg)
    manifest = _load(registration)
    if record.get("authorization", {}).get("approval_id") != authorization.get("approval_id"):
        raise RuntimeError("preregistration authorization ID mismatch")
    if manifest.get("preregistration_sha256") != _hash(prereg):
        raise RuntimeError("registered preregistration hash mismatch")


def _raw_cost_rows(run_dir: Path) -> tuple[int, Decimal, Decimal]:
    rows = read_jsonl(run_dir / "global_budget_ledger.jsonl")
    starts = [r for r in rows if r.get("event") == "physical_request_started"]
    reserved = sum((Decimal(r.get("reserved_peak_cost_usd", "0")) for r in starts), Decimal(0))
    used = sum((Decimal(r.get("estimated_peak_cost_usd", "0")) for r in rows
                if r.get("event") == "physical_request_terminal"), Decimal(0))
    return len(starts), reserved, used


def _log_skip(progress: Path, row: dict[str, Any], reason: str) -> None:
    _write_event(progress, "request_unattempted", request_id=row["request_id"],
                 kind=row["kind"], reason=reason, dependencies=row["dependencies"])


def _prompt_family_parity(tokenizer: Tokenizer, row: dict[str, Any], context: dict[str, Any],
                          outputs: dict[str, str]) -> tuple[bool, dict[str, int]]:
    counts: dict[str, int] = {}
    for incoming in ("x", "y", "neutral"):
        variant = {**row, "incoming": incoming,
                   "kind": "ballot", "request_id": f"{row['context_id']}-parity-{incoming}"}
        messages, _ = messages_for(variant, context, outputs)
        counts[incoming] = token_count(tokenizer, messages)
    return len(set(counts.values())) == 1, counts


def _contains_template_control_literal(messages: list[dict[str, str]]) -> bool:
    controls = (
        "<｜begin▁of▁sentence｜>", "<｜end▁of▁sentence｜>", "<｜System｜>",
        "<｜User｜>", "<｜Assistant｜>", "</think>",
    )
    return any(token in message.get("content", "") for message in messages for token in controls)


def run(check_only: bool = False) -> dict[str, Any]:
    schedule, config, tokenizer, parity = verify_frozen_inputs()
    _registered_scope_check()
    key = _provider_key() if not check_only else None
    if check_only:
        return {"status": "PASS_OFFLINE_PREFLIGHT", "assigned_requests": schedule["request_count"],
                "contexts": len(schedule["contexts"]), "schedule_sha256": schedule["schedule_sha256"],
                "tokenizer_sha256": TOKENIZER_SHA256, "tokenizer_parity": parity,
                "model_calls": 0}
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    apply_private_acl(RUN_DIR)
    progress = RUN_DIR / "progress.jsonl"
    client = DeepSeekClient(run_dir=RUN_DIR, budget_ledger=RUN_DIR / "global_budget_ledger.jsonl",
                            api_key=key, interface="json_object_fallback", timeout=90)
    starts, terminals, outputs, responses = _existing_state(RUN_DIR)
    rows = schedule["requests"]
    by_id = {row["request_id"]: row for row in rows}
    contexts = {ctx["context_id"]: ctx for ctx in schedule["contexts"]}
    if not (RUN_DIR / "manifest.json").exists():
        local_manifest = {
            "experiment_id": EXPERIMENT_ID, "schedule_sha256": schedule["schedule_sha256"],
            "config_sha256": _hash(CONFIG_PATH), "runtime_source_sha256": _hash(Path(__file__)),
            "tokenizer_source_commit": config["tokenizer_source_commit"],
            "tokenizer_sha256": TOKENIZER_SHA256, "local_static_parity": parity,
            "api_endpoint": "https://api.deepseek.com/chat/completions",
            "model_requested": MODEL, "temperature": 0.0, "thinking": "disabled",
            "max_output_tokens": MAX_OUTPUT_TOKENS, "retries": 0, "replacements": 0,
            "assigned_requests": 804, "physical_attempt_cap": 804,
            "hard_cost_cap_usd": "1.40", "raw_data_git_ignored": True,
            "auth_header_saved": False, "created_at_utc": now_utc(),
        }
        write_once(RUN_DIR / "manifest.json", canonical(local_manifest) + b"\n")
    else:
        current = _load(RUN_DIR / "manifest.json")
        if current.get("schedule_sha256") != schedule["schedule_sha256"] or current.get("config_sha256") != _hash(CONFIG_PATH):
            raise RuntimeError("existing local run manifest does not match frozen experiment inputs")
    if len(starts) > 804:
        raise RuntimeError("existing physical requests exceed the authorized cap")
    completed_identity = _load(RUN_DIR / "provider_identity.json") if (RUN_DIR / "provider_identity.json").exists() else None
    fatal_stop: str | None = None
    assigned_first = schedule["first_request_id"]
    first_attempts = [r for r in read_jsonl(RUN_DIR / "attempts.jsonl")
                      if r.get("event") == "attempt_started" and r.get("request_id") == assigned_first]
    if first_attempts and not (RUN_DIR / "provider_identity.json").is_file():
        raise RuntimeError("first identity request was already attempted but no provider identity was frozen; stop without resending")
    first_needed = not starts
    terminal_ids = set(terminals)
    # Preserve skipped/terminal progress across safe resumes.
    prior_progress = read_jsonl(progress)
    parity_checked = {
        (r.get("context_id"), r.get("reward"), r.get("history"))
        for r in prior_progress if r.get("event") == "dynamic_token_parity_pass"
    }
    for prior_row in rows:
        family = (prior_row["context_id"], prior_row["reward"], prior_row["history"])
        if (prior_row["kind"] == "ballot" and prior_row["incoming"] in {"x", "y", "neutral"}
                and prior_row["request_id"] in starts and family not in parity_checked):
            raise RuntimeError("a message-family request was attempted without a durable pre-send token-parity record")
    terminal_ids.update(r.get("request_id") for r in prior_progress
                        if r.get("event") in {"request_unattempted", "request_terminalized"})
    attempted_or_terminal = starts | terminal_ids
    while len(attempted_or_terminal) < 804 and fatal_stop is None:
        pending = [r for r in rows if r["request_id"] not in attempted_or_terminal]
        if not pending:
            break
        if first_needed:
            row = by_id[assigned_first]
            first_needed = False
        else:
            ready = [r for r in pending if all(dep in terminal_ids for dep in r["dependencies"])]
            if not ready:
                raise RuntimeError("frozen dependency graph deadlocked")
            row = min(ready, key=lambda r: (r["schedule_key"], r["request_id"]))
        if row["request_id"] in attempted_or_terminal:
            continue
        if any(dep not in outputs for dep in row["dependencies"]):
            _log_skip(progress, row, "dependency_terminal_without_http_200_assistant_content")
            attempted_or_terminal.add(row["request_id"])
            terminal_ids.add(row["request_id"])
            continue
        context = contexts[row["context_id"]]
        messages, local_meta = messages_for(row, context, outputs)
        if _contains_template_control_literal(messages):
            _log_skip(progress, row, "UNSUPPORTED_TEMPLATE_CONTROL_TOKEN_IN_MODEL_HISTORY")
            attempted_or_terminal.add(row["request_id"])
            terminal_ids.add(row["request_id"])
            continue
        if any(token in message["content"] for message in messages
               for token in ("Authorization", "LLM_API_KEY")):
            raise RuntimeError("credential marker detected in a model prompt")
        body = _request_payload(messages, schema_for(row))
        canonical_body = canonical(body)
        token_input = token_count(tokenizer, messages)
        if token_input > 5000:
            raise RuntimeError(f"frozen per-call prompt token ceiling exceeded: {row['request_id']}={token_input}")
        family = (row["context_id"], row["reward"], row["history"])
        if row["kind"] == "ballot" and row["incoming"] in {"x", "y", "neutral"} and family not in parity_checked:
            matched, family_counts = _prompt_family_parity(tokenizer, row, context, outputs)
            if not matched:
                _write_event(progress, "fatal_stop", reason="DYNAMIC_TOKEN_PARITY_FAILURE",
                             request_id=row["request_id"], token_counts=family_counts)
                fatal_stop = "DYNAMIC_TOKEN_PARITY_FAILURE"
                break
            _write_event(progress, "dynamic_token_parity_pass", context_id=row["context_id"],
                         reward=row["reward"], history=row["history"], token_counts=family_counts,
                         checked_before_request_id=row["request_id"])
            parity_checked.add(family)
            local_meta["incoming_family_token_counts"] = family_counts
        bound_tokens, reserve = request_cost_bound(canonical_body, MAX_OUTPUT_TOKENS)
        used_requests, reserved_cost, _ = _raw_cost_rows(RUN_DIR)
        if used_requests >= 804 or reserved_cost + reserve > Decimal("1.40"):
            _write_event(progress, "fatal_stop", reason="APPROVAL_BUDGET_CAP",
                         attempted_requests=used_requests, reserved_cost_usd=str(reserved_cost),
                         next_request_reserve_usd=str(reserve))
            fatal_stop = "APPROVAL_BUDGET_CAP"
            break
        _write_event(progress, "request_dispatching", request_id=row["request_id"],
                     kind=row["kind"], context_id=row["context_id"],
                     request_sha256=sha(canonical_body), prompt_sha256=sha(canonical(messages)),
                     tokenizer_prompt_tokens=token_input, conservative_input_bound=bound_tokens,
                     reserved_peak_cost_usd=str(reserve), metadata_not_sent=local_meta,
                     dependencies=row["dependencies"])
        outputs[f"prompt:{row['request_id']}"] = json.dumps(messages, ensure_ascii=False,
                                                          sort_keys=True, separators=(",", ":"))
        result: Any = None
        error: str | None = None
        try:
            result, _receipt = client.call(
                request_id=row["request_id"], role="agent", messages=messages,
                tool_name="submit_choice", schema=schema_for(row),
                semantic=lambda value, r=row: validate_semantic(r, value),
                metadata={"experiment_id": EXPERIMENT_ID, "context_id": row["context_id"],
                          "request_kind": row["kind"], "treatment_metadata_not_sent": row},
                output_limit=MAX_OUTPUT_TOKENS, run_request_limit=804,
            )
        except DeepSeekRequestError as exc:
            error = exc.status
        except BaseException as exc:
            error = f"UNEXPECTED_{type(exc).__name__}"
        starts, terminals, outputs_new, responses_new = _existing_state(RUN_DIR)
        outputs.update(outputs_new)
        responses.update(responses_new)
        attempted_or_terminal.add(row["request_id"])
        terminal_ids.add(row["request_id"])
        raw_content, response = read_returned_content(RUN_DIR, row["request_id"])
        if raw_content is not None:
            outputs[row["request_id"]] = raw_content
            output_path = RUN_DIR / "responses" / f"{row['request_id']}.bin"
            outputs[f"prompt:{row['request_id']}"] = json.dumps(messages, ensure_ascii=False,
                                                                 sort_keys=True, separators=(",", ":"))
        terminal_row = next((r for r in reversed(read_jsonl(RUN_DIR / "attempts.jsonl"))
                             if r.get("event") == "attempt_terminal" and r.get("request_id") == row["request_id"]), None)
        _write_event(progress, "request_terminalized", request_id=row["request_id"],
                     status=(terminal_row or {}).get("status", error or "UNKNOWN"),
                     http_status=(terminal_row or {}).get("http_status"),
                     response_content_present=raw_content is not None,
                     parser_valid=error is None,
                     response_sha256=(terminal_row or {}).get("response_sha256"),
                     actual_prompt_tokens=(terminal_row or {}).get("prompt_tokens"),
                     tokenizer_prompt_tokens=token_input,
                     estimated_peak_cost_usd=(terminal_row or {}).get("estimated_peak_cost_usd"))
        if row["request_id"] == assigned_first:
            identity = _load(RUN_DIR / "provider_identity.json") if (RUN_DIR / "provider_identity.json").exists() else None
            actual_prompt = (terminal_row or {}).get("prompt_tokens")
            if identity is None or actual_prompt != token_input:
                fatal_stop = "FIRST_REQUEST_IDENTITY_OR_TOKENIZER_MISMATCH"
                _write_event(progress, "fatal_stop", reason=fatal_stop,
                             provider_identity=identity, actual_prompt_tokens=actual_prompt,
                             tokenizer_prompt_tokens=token_input)
        elif terminal_row and terminal_row.get("http_status") == 200:
            actual_prompt = terminal_row.get("prompt_tokens")
            if actual_prompt != token_input:
                fatal_stop = "PROVIDER_TOKENIZER_MISMATCH"
                _write_event(progress, "fatal_stop", reason=fatal_stop,
                             request_id=row["request_id"], actual_prompt_tokens=actual_prompt,
                             tokenizer_prompt_tokens=token_input)
    attempted, reserved, used = _raw_cost_rows(RUN_DIR)
    unattempted = max(0, 804 - len(attempted_or_terminal))
    result = {
        "schema_version": "deepseek-recipient-mechanism-run-v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "COMPLETE" if len(attempted_or_terminal) == 804 and fatal_stop is None else
                  ("STOPPED_FATAL" if fatal_stop else "PARTIAL"),
        "fatal_stop": fatal_stop, "assigned_requests": 804,
        "physical_attempts": attempted, "terminalized_or_skipped": len(attempted_or_terminal),
        "unattempted_rows": unattempted, "retries": 0, "replacements": 0,
        "reserved_peak_cost_usd": str(reserved), "known_usage_cost_usd": str(used),
        "provider_identity": completed_identity or (_load(RUN_DIR / "provider_identity.json")
             if (RUN_DIR / "provider_identity.json").exists() else None),
        "finished_at_utc": now_utc(),
    }
    summary_path = RUN_DIR / "run-summary.json"
    if summary_path.exists():
        raise RuntimeError("summary already exists; append-only run cannot be rewritten")
    write_once(summary_path, canonical(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="verify frozen inputs; make zero model calls")
    args = parser.parse_args()
    result = run(check_only=args.check_only)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") in {"PASS_OFFLINE_PREFLIGHT", "COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
