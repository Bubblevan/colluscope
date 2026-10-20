"""Independently compare exact-request B5 raw responses with stored rows.

Only sanitized hashes, labels, status codes, and equality flags are exported.
Raw request/response bodies and private message text remain in ignored runs/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OLD_RUN = ROOT / "runs" / "deepseek-first-m4" / "monitor"
CURRENT_RUN = ROOT / "runs" / "sprint-monitor" / "m4-b5-context-sensitivity-campaign-v1-run"
SCHEDULE = ROOT / "research" / "schedules" / "m4-b5-raw-response-repeatability-v1.json"
OUT = ROOT / "docs" / "results" / "research-sprint-20261021" / "raw-response-repeatability-v3"
LABELS = {"present", "absent", "insufficient_evidence"}
EXPECTED_PAIRS = 48
EXPECTED_PERMISSION_COUNTS = {"public_only": 24, "privileged_audit": 24}
FROZEN_SCHEDULE_SHA256 = "456600dd1dd969aef75fae848a8c900f38bb60612f0dcf1315f5da03ad0770a0"


class DuplicateKeyError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def strict_json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    except DuplicateKeyError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("RAW_JSON_INVALID") from exc


def strict_prediction(response: Any) -> tuple[dict[str, Any], str]:
    if not isinstance(response, dict):
        raise ValueError("RESPONSE_ROOT_INVALID")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ValueError("CHOICE_COUNT_INVALID")
    choice = choices[0]
    if choice.get("finish_reason") != "tool_calls":
        raise ValueError("FINISH_REASON_INVALID")
    message = choice.get("message")
    if (not isinstance(message, dict) or message.get("role") != "assistant"
            or message.get("content") not in (None, "")):
        raise ValueError("ASSISTANT_MESSAGE_INVALID")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
        raise ValueError("TOOL_CALL_COUNT_INVALID")
    call = calls[0]
    function = call.get("function")
    if (call.get("type") != "function" or not isinstance(function, dict)
            or function.get("name") != "report_evidence"):
        raise ValueError("TOOL_IDENTITY_INVALID")
    args_raw = function.get("arguments")
    if not isinstance(args_raw, str):
        raise ValueError("TOOL_ARGUMENTS_INVALID")
    try:
        args = json.loads(args_raw, object_pairs_hook=unique_object)
    except DuplicateKeyError:
        raise ValueError("DUPLICATE_ARGUMENT_KEY") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError("TOOL_ARGUMENT_JSON_INVALID") from None
    if (not isinstance(args, dict) or set(args) != {"label", "evidence_refs"}
            or args.get("label") not in LABELS
            or not isinstance(args.get("evidence_refs"), list)
            or any(not isinstance(ref, str) for ref in args["evidence_refs"])):
        raise ValueError("TOOL_ARGUMENT_SCHEMA_INVALID")
    return args, args_raw


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_frozen_schedule(path: Path) -> dict[str, Any]:
    if sha_file(path) != FROZEN_SCHEDULE_SHA256:
        raise ValueError("FROZEN_SCHEDULE_HASH_MISMATCH")
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError("SCHEDULE_ROOT_INVALID")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha_file(path: Path) -> str:
    return sha(path.read_bytes())


def _stored_prediction(row: Any) -> tuple[str | None, list[str] | None, str | None]:
    if isinstance(row, dict) and isinstance(row.get("label"), str):
        label = row.get("label")
        refs = row.get("evidence_refs")
    elif isinstance(row, str):
        label, refs = row, None
    else:
        return None, None, "STORED_PREDICTION_SHAPE_INVALID"
    if label not in LABELS:
        return None, None, "STORED_LABEL_INVALID"
    if refs is not None and (not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs)):
        return None, None, "STORED_EVIDENCE_REFS_INVALID"
    return label, refs, None


def _source_hashes(old_run: Path, current_run: Path) -> dict[str, str]:
    paths = {
        "historical_plan_sha256": old_run / "freeze-v1" / "plan.jsonl",
        "historical_predictions_sha256": old_run / "predictions.jsonl",
        "current_schedule_sha256": current_run / "schedule.json",
        "current_results_sha256": current_run / "results.jsonl",
        "current_request_ledger_sha256": current_run / "request_ledger.jsonl",
    }
    return {key: sha_file(path) for key, path in paths.items()}


def _hash_multiset(values: list[str]) -> str:
    return sha(canonical(sorted(values)))


def _unique_index(rows: list[dict[str, Any]], key: str, error_code: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in indexed:
            raise ValueError(error_code)
        indexed[value] = row
    return indexed


def _audit_pairs(
    schedule: dict[str, Any], old_run: Path = OLD_RUN, current_run: Path = CURRENT_RUN
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if schedule.get("experiment_id") != "m4-b5-raw-response-repeatability-v1":
        raise ValueError("SCHEDULE_EXPERIMENT_ID_INVALID")
    if len(schedule.get("pairs", [])) != EXPECTED_PAIRS:
        raise ValueError("SCHEDULE_DENOMINATOR_INVALID")
    permission_counts = Counter(row.get("permission") for row in schedule["pairs"])
    if permission_counts != Counter(EXPECTED_PERMISSION_COUNTS):
        raise ValueError("SCHEDULE_PERMISSION_DENOMINATOR_INVALID")
    frozen_sources = schedule.get("source_manifest", {})
    current_sources = _source_hashes(old_run, current_run)

    old_plan = read_jsonl(old_run / "freeze-v1" / "plan.jsonl")
    old_predictions = read_jsonl(old_run / "predictions.jsonl")
    current_schedule = read_json(current_run / "schedule.json")
    current_results = read_jsonl(current_run / "results.jsonl")
    current_ledger = read_jsonl(current_run / "request_ledger.jsonl")
    old_prediction_by_id = _unique_index(old_predictions, "request_id", "HISTORICAL_REQUEST_ID_DUPLICATE_OR_INVALID")
    current_result_by_id = _unique_index(current_results, "request_id", "CURRENT_RESULT_REQUEST_ID_DUPLICATE_OR_INVALID")
    current_started_rows = [r for r in current_ledger if r.get("event") == "attempt_started"]
    current_attempt_by_id = _unique_index(
        current_started_rows, "request_id", "CURRENT_ATTEMPT_REQUEST_ID_DUPLICATE_OR_INVALID"
    )
    old_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row in old_plan:
        if (row.get("baseline_id") == "B5_evidence_aware"
                and row.get("task") == "public_harm"
                and row.get("population") == "m4_natural_traces"
                and row.get("permission") in {"public_only", "privileged_audit"}):
            key = (sha(str(row.get("case_ref", "")).encode("utf-8")), row["permission"])
            if key in old_by_pair:
                raise ValueError("HISTORICAL_PAIR_DUPLICATE")
            old_by_pair[key] = row
    current_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for row in current_schedule.get("rows", []):
        if (row.get("block") == "A1"
                and row.get("arm_id") in {"A1-PUBLIC", "A1-PRIVILEGED-ORIGINAL"}):
            permission = "public_only" if row["arm_id"] == "A1-PUBLIC" else "privileged_audit"
            key = (row.get("unit_sha256"), permission)
            if key in current_by_pair:
                raise ValueError("CURRENT_PAIR_DUPLICATE")
            current_by_pair[key] = row

    rows: list[dict[str, Any]] = []
    for frozen in schedule["pairs"]:
        pair_id = frozen.get("pair_sha256")
        key = (frozen.get("case_sha256"), frozen.get("permission"))
        result_row: dict[str, Any] = {
            "pair_sha256": pair_id,
            "permission": key[1],
            "integrity_status": "OK",
            "parse_status": "NOT_RUN",
            "error_code": None,
        }
        old = old_by_pair.get(key)
        current = current_by_pair.get(key)
        if old is None or current is None:
            result_row["integrity_status"] = "FAIL"
            result_row["error_code"] = "FROZEN_CASE_PERMISSION_ASSOCIATION_MISSING"
            rows.append(result_row)
            continue
        old_id = old.get("request_id")
        current_id = "m4b5_" + str(current.get("row_sha256", ""))[:24]
        old_result = old_prediction_by_id.get(old_id)
        current_result = current_result_by_id.get(current_id)
        current_attempt = current_attempt_by_id.get(current_id)
        if old_result is None or current_result is None or current_attempt is None:
            result_row["integrity_status"] = "FAIL"
            result_row["error_code"] = "STORED_RESULT_OR_ATTEMPT_MISSING"
            rows.append(result_row)
            continue

        try:
            old_req_path = old_run / "requests" / f"{old_id}.bin"
            old_res_path = old_run / "responses" / f"{old_id}.bin"
            current_req_path = current_run / "requests" / f"{current_id}.bin"
            current_res_path = (current_run / Path(current_result.get("response_path", ""))).resolve()
            if current_run.resolve() not in current_res_path.parents:
                raise ValueError("CURRENT_RESPONSE_PATH_ESCAPES_RUN")
            old_req_raw, current_req_raw = old_req_path.read_bytes(), current_req_path.read_bytes()
            old_res_raw, current_res_raw = old_res_path.read_bytes(), current_res_path.read_bytes()
            old_req_hash, current_req_hash = sha(old_req_raw), sha(current_req_raw)
            old_res_hash, current_res_hash = sha(old_res_raw), sha(current_res_raw)
            if old_req_hash != frozen.get("request_sha256") or current_req_hash != frozen.get("request_sha256"):
                raise ValueError("REQUEST_HASH_MISMATCH")
            if old_res_hash != frozen.get("historical_response_sha256") or current_res_hash != frozen.get("current_response_sha256"):
                raise ValueError("RESPONSE_HASH_MISMATCH")
            if old_req_hash != old.get("body_sha256") or current_req_hash != current_attempt.get("body_sha256"):
                raise ValueError("REQUEST_SIDECAR_HASH_MISMATCH")
            if old_res_hash != old_result.get("response_sha256") or current_res_hash != current_result.get("response_sha256"):
                raise ValueError("RESPONSE_SIDECAR_HASH_MISMATCH")
            if old_req_raw != current_req_raw:
                raise ValueError("EXACT_REQUEST_BYTES_DIFFER")
            if (old_result.get("system_fingerprint") != frozen.get("reported_system_fingerprint")
                    or current_result.get("system_fingerprint") != frozen.get("reported_system_fingerprint")):
                raise ValueError("STORED_FINGERPRINT_MISMATCH")
            if (old_result.get("status") != frozen.get("historical_status")
                    or current_result.get("status") != frozen.get("current_status")
                    or old_result.get("finish_reason") != frozen.get("historical_finish_reason")
                    or current_result.get("finish_reason") != frozen.get("current_finish_reason")):
                raise ValueError("STORED_TERMINAL_METADATA_MISMATCH")

            result_row.update({
                "request_sha256": old_req_hash,
                "historical_response_sha256": old_res_hash,
                "current_response_sha256": current_res_hash,
                "response_bytes_identical": old_res_raw == current_res_raw,
                "reported_fingerprint_equal": True,
                "historical_status": old_result.get("status"),
                "current_status": current_result.get("status"),
                "historical_finish_reason": old_result.get("finish_reason"),
                "current_finish_reason": current_result.get("finish_reason"),
            })
        except (OSError, ValueError) as exc:
            result_row["integrity_status"] = "FAIL"
            code = str(exc)
            result_row["error_code"] = code if code.isupper() and code.replace("_", "").isalnum() else "RAW_FILE_OR_HASH_CHECK_FAILED"
            rows.append(result_row)
            continue

        parsed: list[dict[str, Any] | None] = []
        raw_argument_hashes: list[str | None] = []
        raw_argument_canonical_hashes: list[str | None] = []
        stored_values: list[tuple[str | None, list[str] | None, str | None]] = []
        parse_errors: list[str | None] = []
        response_values = [old_res_raw, current_res_raw]
        result_values = [old_result, current_result]
        for raw, stored_result in zip(response_values, result_values):
            try:
                response = strict_json(raw)
                prediction, argument_text = strict_prediction(response)
                parsed.append(prediction)
                raw_argument_hashes.append(sha(argument_text.encode("utf-8")))
                raw_argument_canonical_hashes.append(sha(canonical(prediction)))
                parse_errors.append(None)
            except (ValueError, TypeError, AttributeError):
                parsed.append(None)
                raw_argument_hashes.append(None)
                raw_argument_canonical_hashes.append(None)
                parse_errors.append("STRICT_PARSE_FAILED")
            stored_source = stored_result.get("prediction") if stored_result is old_result else stored_result.get("parsed")
            stored_values.append(_stored_prediction(stored_source))

        for idx, response_raw in enumerate(response_values):
            try:
                raw_response = strict_json(response_raw)
                fp = raw_response.get("system_fingerprint") if isinstance(raw_response, dict) else None
                model = raw_response.get("model") if isinstance(raw_response, dict) else None
                if fp != frozen.get("reported_system_fingerprint"):
                    parse_errors[idx] = "RAW_FINGERPRINT_MISMATCH"
                expected_model = frozen.get("returned_model_pair", [None, None])[idx]
                if model != expected_model:
                    parse_errors[idx] = "RAW_RETURNED_MODEL_MISMATCH"
                expected_finish = frozen.get("historical_finish_reason" if idx == 0 else "current_finish_reason")
                choices = raw_response.get("choices") if isinstance(raw_response, dict) else None
                actual_finish = choices[0].get("finish_reason") if isinstance(choices, list) and choices and isinstance(choices[0], dict) else None
                if actual_finish != expected_finish:
                    parse_errors[idx] = "RAW_FINISH_REASON_MISMATCH"
            except (ValueError, TypeError, AttributeError):
                pass

        stored_match = [
            parsed[i] is not None
            and stored_values[i][2] is None
            and parsed[i].get("label") == stored_values[i][0]
            and (stored_values[i][1] is None or parsed[i].get("evidence_refs") == stored_values[i][1])
            for i in range(2)
        ]
        all_parsed = all(value is not None and error is None for value, error in zip(parsed, parse_errors))
        result_row.update({
            "parse_status": "VALID" if all_parsed else "INVALID",
            "parse_error_code": next((e for e in parse_errors if e), None),
            "historical_raw_label": parsed[0].get("label") if parsed[0] else None,
            "current_raw_label": parsed[1].get("label") if parsed[1] else None,
            "historical_stored_label": stored_values[0][0],
            "current_stored_label": stored_values[1][0],
            "historical_raw_matches_stored": stored_match[0],
            "current_raw_matches_stored": stored_match[1],
            "historical_raw_argument_sha256": raw_argument_hashes[0],
            "current_raw_argument_sha256": raw_argument_hashes[1],
            "raw_argument_bytes_equal": raw_argument_hashes[0] == raw_argument_hashes[1] if all_parsed else None,
            "canonical_arguments_equal": raw_argument_canonical_hashes[0] == raw_argument_canonical_hashes[1] if all_parsed else None,
            "raw_label_equal": (parsed[0].get("label") == parsed[1].get("label")) if all_parsed else None,
            "raw_evidence_refs_equal": (parsed[0].get("evidence_refs") == parsed[1].get("evidence_refs")) if all_parsed else None,
            "historical_stored_refs_match": stored_match[0] if stored_values[0][1] is not None else None,
            "current_stored_refs_match": stored_match[1] if stored_values[1][1] is not None else None,
        })
        if not all_parsed:
            result_row["error_code"] = result_row["parse_error_code"] or "STRICT_PARSE_FAILED"
        rows.append(result_row)

    permission_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        permission_rows[str(row.get("permission"))].append(row)
    summaries: dict[str, Any] = {}
    for permission in ("public_only", "privileged_audit"):
        group = permission_rows.get(permission, [])
        complete = [r for r in group if r.get("integrity_status") == "OK" and r.get("parse_status") == "VALID"]
        label_transitions = Counter(
            f"{r['historical_raw_label']}->{r['current_raw_label']}" for r in complete
        )
        summaries[permission] = {
            "assigned_pairs": len(group),
            "integrity_valid": sum(r.get("integrity_status") == "OK" for r in group),
            "strict_parse_valid": sum(r.get("parse_status") == "VALID" for r in group),
            "raw_matches_stored_both_responses": sum(r.get("historical_raw_matches_stored") is True and r.get("current_raw_matches_stored") is True for r in group),
            "raw_label_equal": sum(r.get("raw_label_equal") is True for r in complete),
            "raw_label_different": sum(r.get("raw_label_equal") is False for r in complete),
            "raw_evidence_refs_equal": sum(r.get("raw_evidence_refs_equal") is True for r in complete),
            "raw_evidence_refs_different": sum(r.get("raw_evidence_refs_equal") is False for r in complete),
            "raw_argument_bytes_equal": sum(r.get("raw_argument_bytes_equal") is True for r in complete),
            "canonical_arguments_equal": sum(r.get("canonical_arguments_equal") is True for r in complete),
            "response_body_bytes_equal": sum(r.get("response_bytes_identical") is True for r in group),
            "raw_label_transitions": dict(sorted(label_transitions.items())),
        }

    total_complete = [r for r in rows if r.get("integrity_status") == "OK" and r.get("parse_status") == "VALID"]
    integrity_failures = sum(r.get("integrity_status") != "OK" for r in rows)
    parse_failures = sum(r.get("parse_status") != "VALID" for r in rows if r.get("integrity_status") == "OK")
    stored_mismatches = sum(not (r.get("historical_raw_matches_stored") is True and r.get("current_raw_matches_stored") is True) for r in total_complete)
    label_differences = sum(r.get("raw_label_equal") is False for r in total_complete)
    expected_multisets = {
        "historical_selected_requests_multiset_sha256": _hash_multiset([r["request_sha256"] for r in rows if r.get("request_sha256")]),
        "historical_selected_responses_multiset_sha256": _hash_multiset([r["historical_response_sha256"] for r in rows if r.get("historical_response_sha256")]),
        "current_selected_requests_multiset_sha256": _hash_multiset([r["request_sha256"] for r in rows if r.get("request_sha256")]),
        "current_selected_responses_multiset_sha256": _hash_multiset([r["current_response_sha256"] for r in rows if r.get("current_response_sha256")]),
    }
    source_hashes_ok = (
        all(current_sources.get(k) == frozen_sources.get(k) for k in current_sources)
        and all(frozen_sources.get(k) == value for k, value in expected_multisets.items())
        and len(rows) == EXPECTED_PAIRS
        and all(r.get("request_sha256") and r.get("historical_response_sha256") and r.get("current_response_sha256") for r in rows)
    )
    if not source_hashes_ok or integrity_failures:
        decision = "INVALID_EXPERIMENT"
    elif parse_failures:
        decision = "INCONCLUSIVE"
    elif stored_mismatches:
        decision = "DOWNSTREAM_MAPPING_DISCREPANCY"
    elif label_differences:
        decision = "RAW_RESPONSE_LABEL_VARIATION_CONFIRMED_FINITE"
    else:
        decision = "NO_RAW_LABEL_VARIATION_OBSERVED"

    report = {
        "schema_version": 1,
        "experiment_id": schedule["experiment_id"],
        "status": "PASS_INDEPENDENT_RAW_RESPONSE_REPLAY" if source_hashes_ok and not integrity_failures and not parse_failures and not stored_mismatches else "FAIL_OR_INCONCLUSIVE",
        "source_snapshot_hashes_match": source_hashes_ok,
        "decision": decision,
        "assigned_pairs": len(rows),
        "integrity_failures": integrity_failures,
        "strict_parse_failures": parse_failures,
        "stored_mapping_mismatches": stored_mismatches,
        "raw_label_disagreement_pairs": label_differences,
        "raw_label_agreement_pairs": len(total_complete) - label_differences,
        "raw_argument_byte_identical_pairs": sum(r.get("raw_argument_bytes_equal") is True for r in total_complete),
        "canonical_argument_identical_pairs": sum(r.get("canonical_arguments_equal") is True for r in total_complete),
        "full_response_byte_identical_pairs": sum(r.get("response_bytes_identical") is True for r in rows),
        "per_permission": summaries,
        "interpretation_limits": [
            "The pairs are 48 finite historical/current repeats of exact request bytes with matching reported fingerprints; the service model alias is mutable and hidden provider state is unknown.",
            "Raw argument variation cannot identify which evidence-view cue caused the historical Public-to-Privileged label changes.",
            "This analysis does not measure population stochasticity, model capability, private-message comprehension, collusion, or intent.",
            "A matching stored result validates this parser/scorer mapping only for these retained responses."
        ],
        "source_hashes": current_sources,
        "frozen_schedule_sha256": FROZEN_SCHEDULE_SHA256,
    }
    return report, rows


def audit_pairs(
    schedule_path: Path, old_run: Path = OLD_RUN, current_run: Path = CURRENT_RUN
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Auditor entry point: only the externally hash-pinned schedule is accepted."""
    schedule = load_frozen_schedule(schedule_path)
    report, rows = _audit_pairs(schedule, old_run, current_run)
    report["frozen_schedule_verified"] = True
    return report, rows


def write_outputs(report: dict[str, Any], rows: list[dict[str, Any]], out_dir: Path = OUT) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "m4-b5-raw-response-repeatability-audit.json"
    rows_path = out_dir / "m4-b5-raw-response-repeatability-rows.csv"
    report_path.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    columns = sorted({key for row in rows for key in row})
    with rows_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return report_path, rows_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schedule", type=Path, default=SCHEDULE)
    parser.add_argument("--historical-run", type=Path, default=OLD_RUN)
    parser.add_argument("--current-run", type=Path, default=CURRENT_RUN)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()
    try:
        report, rows = audit_pairs(args.schedule, args.historical_run, args.current_run)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID_EXPERIMENT", "error_code": str(exc)}))
        return 1
    report_path, rows_path = write_outputs(report, rows, args.out_dir)
    print(json.dumps({
        "status": report["status"],
        "decision": report["decision"],
        "assigned_pairs": report["assigned_pairs"],
        "integrity_failures": report["integrity_failures"],
        "strict_parse_failures": report["strict_parse_failures"],
        "stored_mapping_mismatches": report["stored_mapping_mismatches"],
        "raw_label_disagreement_pairs": report["raw_label_disagreement_pairs"],
        "output_hashes": {"json": sha_file(report_path), "csv": sha_file(rows_path)},
    }, sort_keys=True))
    return 0 if report["status"] == "PASS_INDEPENDENT_RAW_RESPONSE_REPLAY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
