#!/usr/bin/env python3
"""Export a sanitized, usage-priced request ledger for the frozen B5 run.

Raw request/response bytes remain in the ignored, ACL-restricted run directory.
The exported registry ledger contains only hashed attempt IDs, timestamps,
sanitized terminal codes, and token-derived price estimates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_ID = "b5-evidence-view-stability-120"
PRICE_PER_MILLION = {
    "input_cache_hit_offpeak": Decimal("0.003"),
    "input_cache_miss_offpeak": Decimal("0.15"),
    "output_offpeak": Decimal("0.60"),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def cost_for_usage(usage: dict[str, Any]) -> Decimal:
    prompt = usage.get("prompt_tokens")
    hit = usage.get("prompt_cache_hit_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    completion = usage.get("completion_tokens")
    values = (prompt, hit, miss, completion)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values):
        raise ValueError("PROVIDER_TOKEN_USAGE_MISSING_OR_INVALID")
    if hit + miss != prompt:
        raise ValueError("PROMPT_CACHE_USAGE_DOES_NOT_SUM_TO_PROMPT_TOKENS")
    return (
        Decimal(hit) * PRICE_PER_MILLION["input_cache_hit_offpeak"]
        + Decimal(miss) * PRICE_PER_MILLION["input_cache_miss_offpeak"]
        + Decimal(completion) * PRICE_PER_MILLION["output_offpeak"]
    ) / Decimal(1_000_000)


def export(run: Path, output: Path) -> dict[str, Any]:
    frozen_schedule = ROOT / "docs/results/research-sprint-20261021/b5-invariance-schedule-120.json"
    schedule_bytes = frozen_schedule.read_bytes()
    if (run / "schedule.json").read_bytes() != schedule_bytes:
        raise ValueError("RUN_SCHEDULE_DIFFERS_FROM_FROZEN_SCHEDULE")
    schedule = json.loads(schedule_bytes)
    rows = {row["request_id"]: row for row in schedule.get("rows", [])}
    if len(rows) != 120:
        raise ValueError("FROZEN_SCHEDULE_ROW_COUNT_MISMATCH")

    attempts = read_jsonl(run / "attempts.jsonl")
    results = read_jsonl(run / "results.jsonl")
    starts = [row for row in attempts if row.get("event") == "attempt_started"]
    terminals = [row for row in attempts if row.get("event") == "attempt_terminal"]
    start_by_id = {row.get("request_id"): row for row in starts}
    terminal_by_id = {row.get("request_id"): row for row in terminals}
    result_by_id = {row.get("request_id"): row for row in results}
    if len(starts) != len(start_by_id) or len(terminals) != len(terminal_by_id) or len(results) != len(result_by_id):
        raise ValueError("DUPLICATE_PHYSICAL_ATTEMPT_OR_RESULT")
    if set(start_by_id) != set(rows) or set(terminal_by_id) != set(rows) or set(result_by_id) != set(rows):
        raise ValueError("ASSIGNED_START_TERMINAL_RESULT_COVERAGE_MISMATCH")

    ledger_rows: list[dict[str, Any]] = []
    prompt_total = hit_total = miss_total = completion_total = 0
    for request_id, frozen in rows.items():
        start = start_by_id[request_id]
        terminal = terminal_by_id[request_id]
        result = result_by_id[request_id]
        if start.get("body_sha256") != frozen.get("http_body_sha256"):
            raise ValueError("STARTED_REQUEST_BODY_DIFFERS_FROM_FROZEN_SCHEDULE")
        request_path = (run / str(start.get("request_path", ""))).resolve()
        response_path = (run / str(result.get("response_path", ""))).resolve()
        if run.resolve() not in request_path.parents or run.resolve() not in response_path.parents:
            raise ValueError("REQUEST_OR_RESPONSE_PATH_ESCAPES_RUN_ROOT")
        request_bytes = request_path.read_bytes()
        response_bytes = response_path.read_bytes()
        if sha256(request_bytes) != start.get("body_sha256"):
            raise ValueError("REQUEST_BYTES_HASH_MISMATCH")
        if sha256(response_bytes) != result.get("response_sha256") or terminal.get("response_sha256") != result.get("response_sha256"):
            raise ValueError("RESPONSE_BYTES_HASH_MISMATCH")
        request_body = json.loads(request_bytes)
        if any(key.lower() in {"authorization", "api_key", "apikey", "secret"} for key in request_body):
            raise ValueError("AUTHENTICATION_MATERIAL_IN_REQUEST_BODY")
        if terminal.get("http_status") != result.get("http_status"):
            raise ValueError("TERMINAL_HTTP_STATUS_MISMATCH")
        metadata = result.get("envelope_metadata") or {}
        usage = metadata.get("usage") or {}
        cost = cost_for_usage(usage)
        prompt_total += usage["prompt_tokens"]
        hit_total += usage["prompt_cache_hit_tokens"]
        miss_total += usage["prompt_cache_miss_tokens"]
        completion_total += usage["completion_tokens"]
        http_status = result.get("http_status")
        if not isinstance(http_status, int) or isinstance(http_status, bool):
            raise ValueError("HTTP_STATUS_MISSING")
        if result.get("identity_mismatch") or result.get("fingerprint_drift"):
            raise ValueError("MODEL_IDENTITY_OR_FINGERPRINT_DRIFT")
        if metadata.get("returned_model") != "deepseek-flash":
            raise ValueError("RETURNED_MODEL_IDENTITY_MISMATCH")
        started_at = start.get("started_at_utc")
        response_hash = result["response_sha256"]
        attempt_identity = "\n".join((request_id, str(started_at), start["body_sha256"], response_hash)).encode("utf-8")
        ledger_rows.append({
            "experiment_id": EXPERIMENT_ID,
            "attempt_id_sha256": sha256(attempt_identity),
            "started_at_utc": started_at,
            "terminal_status": f"HTTP_{http_status}",
            "external_cost_usd": format(cost, ".12f"),
        })

    if prompt_total != hit_total + miss_total:
        raise ValueError("AGGREGATE_PROMPT_CACHE_USAGE_MISMATCH")
    ledger = {"schema_version": 1, "experiment_id": EXPERIMENT_ID, "requests": ledger_rows}
    raw = json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {
        "status": "SANITIZED_LEDGER_EXPORTED",
        "physical_attempts": len(ledger_rows),
        "http_200": sum(row["terminal_status"] == "HTTP_200" for row in ledger_rows),
        "prompt_tokens": prompt_total,
        "cache_hit_prompt_tokens": hit_total,
        "cache_miss_prompt_tokens": miss_total,
        "completion_tokens": completion_total,
        "usage_priced_offpeak_estimate_usd": format(sum((Decimal(row["external_cost_usd"]) for row in ledger_rows), Decimal(0)), ".12f"),
        "ledger_sha256": sha256(raw),
        "raw_payloads_exported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.run, args.out), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
