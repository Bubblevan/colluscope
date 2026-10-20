"""Freeze exact historical/current B5 request pairs without reading predictions.

The selector uses only assignment identity, request-body bytes, and reported
model fingerprints. It deliberately never opens or parses response JSON.
Outputs contain hashes and sanitized metadata only; raw runs remain local.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OLD_RUN = ROOT / "runs" / "deepseek-first-m4" / "monitor"
CURRENT_RUN = ROOT / "runs" / "sprint-monitor" / "m4-b5-context-sensitivity-campaign-v1-run"
DEFAULT_OUT = ROOT / "research" / "schedules" / "m4-b5-raw-response-repeatability-v1.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def hash_multiset(values: list[str]) -> str:
    return sha(canonical(sorted(values)))


def build_schedule(old_run: Path = OLD_RUN, current_run: Path = CURRENT_RUN) -> dict[str, Any]:
    old_plan_path = old_run / "freeze-v1" / "plan.jsonl"
    old_predictions_path = old_run / "predictions.jsonl"
    current_schedule_path = current_run / "schedule.json"
    current_results_path = current_run / "results.jsonl"
    current_ledger_path = current_run / "request_ledger.jsonl"

    old_plan = read_jsonl(old_plan_path)
    old_predictions = read_jsonl(old_predictions_path)
    current_schedule = json.loads(current_schedule_path.read_text(encoding="utf-8"))
    if not isinstance(current_schedule, dict) or not isinstance(current_schedule.get("rows"), list):
        raise ValueError("CURRENT_SCHEDULE_SCHEMA_INVALID")
    current_results = read_jsonl(current_results_path)
    current_ledger = read_jsonl(current_ledger_path)

    old_prediction_by_id = {row.get("request_id"): row for row in old_predictions}
    current_result_by_id = {row.get("request_id"): row for row in current_results}
    current_started = {
        row.get("request_id"): row for row in current_ledger
        if row.get("event") == "attempt_started"
    }
    if (len(old_prediction_by_id) != len(old_predictions)
            or len(current_result_by_id) != len(current_results)
            or len(current_started) != 232):
        raise ValueError("REQUEST_ASSOCIATION_INDEX_INVALID")

    old_selected = [
        row for row in old_plan
        if row.get("baseline_id") == "B5_evidence_aware"
        and row.get("task") == "public_harm"
        and row.get("population") == "m4_natural_traces"
        and row.get("permission") in {"public_only", "privileged_audit"}
    ]
    old_by_case_permission: dict[tuple[str, str], dict[str, Any]] = {}
    for row in old_selected:
        pair = (sha(str(row["case_ref"]).encode("utf-8")), row["permission"])
        if pair in old_by_case_permission:
            raise ValueError("HISTORICAL_CASE_PERMISSION_DUPLICATE")
        old_by_case_permission[pair] = row

    current_selected = [
        row for row in current_schedule["rows"]
        if row.get("block") == "A1"
        and row.get("arm_id") in {"A1-PUBLIC", "A1-PRIVILEGED-ORIGINAL"}
    ]
    current_by_case_permission: dict[tuple[str, str], dict[str, Any]] = {}
    for row in current_selected:
        permission = {
            "A1-PUBLIC": "public_only",
            "A1-PRIVILEGED-ORIGINAL": "privileged_audit",
        }[row["arm_id"]]
        pair = (row["unit_sha256"], permission)
        if pair in current_by_case_permission:
            raise ValueError("CURRENT_CASE_PERMISSION_DUPLICATE")
        current_by_case_permission[pair] = row

    if len(old_by_case_permission) != 48 or len(current_by_case_permission) != 48:
        raise ValueError("ASSIGNED_MATCH_DENOMINATOR_INVALID")

    selected: list[dict[str, Any]] = []
    historical_request_hashes: list[str] = []
    historical_response_hashes: list[str] = []
    current_request_hashes: list[str] = []
    current_response_hashes: list[str] = []
    status_counts: Counter[str] = Counter()
    finish_counts: Counter[str] = Counter()

    for pair_key in sorted(old_by_case_permission):
        old = old_by_case_permission[pair_key]
        current = current_by_case_permission.get(pair_key)
        if current is None:
            raise ValueError("MATCHED_CURRENT_ROW_MISSING")
        old_id = old["request_id"]
        current_id = "m4b5_" + current["row_sha256"][:24]
        old_result = old_prediction_by_id.get(old_id)
        current_result = current_result_by_id.get(current_id)
        current_attempt = current_started.get(current_id)
        if old_result is None or current_result is None or current_attempt is None:
            raise ValueError("MATCHED_RESULT_OR_ATTEMPT_MISSING")

        old_request_path = old_run / "requests" / f"{old_id}.bin"
        old_response_path = old_run / "responses" / f"{old_id}.bin"
        current_request_path = current_run / "requests" / f"{current_id}.bin"
        response_relative = Path(current_result.get("response_path", ""))
        current_response_path = (current_run / response_relative).resolve()
        if current_run.resolve() not in current_response_path.parents:
            raise ValueError("CURRENT_RESPONSE_PATH_ESCAPES_RUN")

        old_request_hash = file_sha(old_request_path)
        current_request_hash = file_sha(current_request_path)
        old_response_hash = file_sha(old_response_path)
        current_response_hash = file_sha(current_response_path)
        if old_request_hash != old.get("body_sha256"):
            raise ValueError("HISTORICAL_REQUEST_HASH_MISMATCH")
        if current_request_hash != current_attempt.get("body_sha256"):
            raise ValueError("CURRENT_REQUEST_HASH_MISMATCH")
        if old_response_hash != old_result.get("response_sha256"):
            raise ValueError("HISTORICAL_RESPONSE_HASH_MISMATCH")
        if current_response_hash != current_result.get("response_sha256"):
            raise ValueError("CURRENT_RESPONSE_HASH_MISMATCH")

        old_fingerprint = old_result.get("system_fingerprint")
        current_fingerprint = current_result.get("system_fingerprint")
        if old_request_hash != current_request_hash or old_fingerprint != current_fingerprint:
            raise ValueError("EXACT_REQUEST_FINGERPRINT_PAIR_MISSING")

        permission = pair_key[1]
        anonymous_pair = sha(f"{pair_key[0]}|{permission}".encode("utf-8"))
        selected.append({
            "pair_sha256": anonymous_pair,
            "case_sha256": pair_key[0],
            "permission": permission,
            "request_sha256": old_request_hash,
            "reported_system_fingerprint": old_fingerprint,
            "historical_response_sha256": old_response_hash,
            "current_response_sha256": current_response_hash,
            "historical_status": old_result.get("status"),
            "current_status": current_result.get("status"),
            "historical_finish_reason": old_result.get("finish_reason"),
            "current_finish_reason": current_result.get("finish_reason"),
            "returned_model_pair": [old_result.get("returned_model"), current_result.get("returned_model")],
        })
        historical_request_hashes.append(old_request_hash)
        current_request_hashes.append(current_request_hash)
        historical_response_hashes.append(old_response_hash)
        current_response_hashes.append(current_response_hash)
        status_counts[f"historical:{old_result.get('status')}"] += 1
        status_counts[f"current:{current_result.get('status')}"] += 1
        finish_counts[f"historical:{old_result.get('finish_reason')}"] += 1
        finish_counts[f"current:{current_result.get('finish_reason')}"] += 1

    selected.sort(key=lambda row: (row["permission"], row["pair_sha256"]))
    counts = Counter(row["permission"] for row in selected)
    if counts != Counter({"public_only": 24, "privileged_audit": 24}):
        raise ValueError("PERMISSION_DENOMINATOR_INVALID")

    source_bytes = {
        "historical_plan_sha256": file_sha(old_plan_path),
        "historical_predictions_sha256": file_sha(old_predictions_path),
        "current_schedule_sha256": file_sha(current_schedule_path),
        "current_results_sha256": file_sha(current_results_path),
        "current_request_ledger_sha256": file_sha(current_ledger_path),
    }
    source_bytes.update({
        "historical_selected_requests_multiset_sha256": hash_multiset(historical_request_hashes),
        "historical_selected_responses_multiset_sha256": hash_multiset(historical_response_hashes),
        "current_selected_requests_multiset_sha256": hash_multiset(current_request_hashes),
        "current_selected_responses_multiset_sha256": hash_multiset(current_response_hashes),
    })
    return {
        "schema_version": 1,
        "experiment_id": "m4-b5-raw-response-repeatability-v1",
        "selection_rule": "All 24 B5 public_harm natural-trace cases in each of public_only and privileged_audit, paired by SHA-256(case_ref); retain only the complete matched set where raw request-body bytes and reported system_fingerprint are exactly equal. Selection never reads parsed labels, tool arguments, evidence refs, or response body content.",
        "assigned_denominator": {"matched_cases": 24, "permission_pairs": {"public_only": 24, "privileged_audit": 24}, "historical_current_response_pairs": 48},
        "source_manifest": source_bytes,
        "selection_metadata_counts": {"statuses": dict(sorted(status_counts.items())), "finish_reasons": dict(sorted(finish_counts.items()))},
        "pairs": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-run", type=Path, default=OLD_RUN)
    parser.add_argument("--current-run", type=Path, default=CURRENT_RUN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    schedule = build_schedule(args.historical_run, args.current_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(json.dumps(schedule, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
    print(json.dumps({
        "status": "FROZEN_BEFORE_RAW_ARGUMENT_REVIEW",
        "experiment_id": schedule["experiment_id"],
        "pairs": schedule["assigned_denominator"],
        "selection_metadata_counts": schedule["selection_metadata_counts"],
        "schedule_sha256": file_sha(args.out),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
