from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_m4_b5_raw_response_repeatability import (
    DuplicateKeyError,
    audit_pairs,
    _audit_pairs,
    load_frozen_schedule,
    strict_json,
    strict_prediction,
    write_outputs,
)
from scripts.freeze_m4_b5_raw_response_repeatability import build_schedule


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _response(label: str, evidence_refs: list[str] | None = None) -> bytes:
    args = json.dumps(
        {"label": label, "evidence_refs": evidence_refs or []},
        separators=(",", ":"),
    )
    response = {
        "model": "deepseek-flash",
        "system_fingerprint": "fp-fixed",
        "choices": [{
            "finish_reason": "tool_calls",
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "type": "function",
                    "function": {"name": "report_evidence", "arguments": args},
                }],
            },
        }],
    }
    return json.dumps(response, separators=(",", ":")).encode("utf-8")


def _fixture(tmp_path: Path, *, downstream_mismatch: bool = False):
    old_run = tmp_path / "old"
    current_run = tmp_path / "current"
    (old_run / "freeze-v1").mkdir(parents=True)
    (old_run / "requests").mkdir()
    (old_run / "responses").mkdir()
    (current_run / "requests").mkdir(parents=True)
    (current_run / "responses").mkdir()

    old_plan = []
    old_predictions = []
    current_rows = []
    current_results = []
    current_attempts = []
    for idx in range(24):
        case_ref = f"CASE-{idx:02d}"
        case_hash = _sha(case_ref.encode())
        for permission, arm in (("public_only", "A1-PUBLIC"), ("privileged_audit", "A1-PRIVILEGED-ORIGINAL")):
            pair_suffix = f"{idx:02d}-{permission}"
            old_id = f"old-{pair_suffix}"
            row_hash = _sha(f"row-{pair_suffix}".encode())
            current_id = "m4b5_" + row_hash[:24]
            request_bytes = json.dumps(
                {"evidence": "PRIVATE-DO-NOT-EXPORT", "case": idx, "permission": permission},
                separators=(",", ":"),
            ).encode("utf-8")
            request_hash = _sha(request_bytes)
            history_label = "present" if idx == 0 and permission == "public_only" else "absent"
            current_label = "absent" if idx == 0 and permission == "public_only" else history_label
            old_response = _response(history_label, ["E1"])
            current_response = _response(current_label, ["E1"])
            (old_run / "requests" / f"{old_id}.bin").write_bytes(request_bytes)
            (old_run / "responses" / f"{old_id}.bin").write_bytes(old_response)
            (current_run / "requests" / f"{current_id}.bin").write_bytes(request_bytes)
            response_rel = f"responses/{current_id}.bin"
            (current_run / response_rel).write_bytes(current_response)
            old_plan.append({
                "baseline_id": "B5_evidence_aware",
                "task": "public_harm",
                "population": "m4_natural_traces",
                "permission": permission,
                "case_ref": case_ref,
                "request_id": old_id,
                "body_sha256": request_hash,
            })
            old_predictions.append({
                "request_id": old_id,
                "prediction": {"label": history_label, "evidence_refs": ["E1"]},
                "response_sha256": _sha(old_response),
                "status": "VALID",
                "finish_reason": "tool_calls",
                "returned_model": "deepseek-flash",
                "system_fingerprint": "fp-fixed",
            })
            current_rows.append({
                "block": "A1",
                "arm_id": arm,
                "unit_sha256": case_hash,
                "row_sha256": row_hash,
            })
            current_results.append({
                "request_id": current_id,
                "parsed": {
                    "label": ("present" if downstream_mismatch and idx == 1 and permission == "public_only" else current_label),
                    "evidence_refs": ["E1"],
                },
                "response_path": response_rel,
                "response_sha256": _sha(current_response),
                "status": "HTTP_200_VALID",
                "http_status": 200,
                "finish_reason": "tool_calls",
                "returned_model": "deepseek-flash",
                "system_fingerprint": "fp-fixed",
            })
            current_attempts.append({
                "event": "attempt_started",
                "request_id": current_id,
                "body_sha256": request_hash,
            })

    # The frozen source campaign has 232 attempt-start rows. These synthetic
    # inert rows satisfy that source-integrity check without adding assigned
    # pairs or model outputs to the fixture denominator.
    for extra in range(232 - len(current_attempts)):
        current_attempts.append({
            "event": "attempt_started",
            "request_id": f"synthetic-unselected-{extra:03d}",
            "body_sha256": _sha(f"synthetic-unselected-{extra:03d}".encode()),
        })

    def write_jsonl(path: Path, rows: list[dict]):
        path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

    write_jsonl(old_run / "freeze-v1" / "plan.jsonl", old_plan)
    write_jsonl(old_run / "predictions.jsonl", old_predictions)
    (current_run / "schedule.json").write_text(json.dumps({"rows": current_rows}, separators=(",", ":")), encoding="utf-8")
    write_jsonl(current_run / "results.jsonl", current_results)
    write_jsonl(current_run / "request_ledger.jsonl", current_attempts)
    return old_run, current_run


def test_strict_json_rejects_duplicate_keys():
    with pytest.raises(DuplicateKeyError):
        strict_json(b'{"x":1,"x":2}')


def test_strict_prediction_rejects_duplicate_tool_argument_keys():
    response = json.loads(_response("present"))
    response["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] = (
        '{"label":"present","label":"absent","evidence_refs":[]}'
    )
    with pytest.raises(ValueError, match="DUPLICATE_ARGUMENT_KEY"):
        strict_prediction(response)


def test_raw_label_variation_is_distinguished_from_downstream_mismatch(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path)
    schedule = build_schedule(old_run, current_run)
    report, rows = _audit_pairs(schedule, old_run, current_run)

    assert report["decision"] == "RAW_RESPONSE_LABEL_VARIATION_CONFIRMED_FINITE"
    assert report["assigned_pairs"] == 48
    assert report["raw_label_disagreement_pairs"] == 1
    assert report["stored_mapping_mismatches"] == 0
    assert report["per_permission"]["public_only"]["raw_evidence_refs_equal"] == 24
    assert all(row["historical_raw_matches_stored"] and row["current_raw_matches_stored"] for row in rows)
    json_path, csv_path = write_outputs(report, rows, tmp_path / "out")
    assert b"PRIVATE-DO-NOT-EXPORT" not in json_path.read_bytes()
    assert b"PRIVATE-DO-NOT-EXPORT" not in csv_path.read_bytes()


def test_downstream_prediction_mismatch_is_not_silently_repaired(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path, downstream_mismatch=True)
    schedule = build_schedule(old_run, current_run)
    report, rows = _audit_pairs(schedule, old_run, current_run)

    assert report["decision"] == "DOWNSTREAM_MAPPING_DISCREPANCY"
    assert report["stored_mapping_mismatches"] == 1
    mismatch = next(row for row in rows if row.get("historical_raw_label") == "absent" and row.get("current_raw_label") == "absent" and row.get("current_raw_matches_stored") is False)
    assert mismatch["current_stored_label"] == "present"
    assert mismatch["current_raw_label"] == "absent"


def test_schedule_selection_does_not_depend_on_stored_labels(tmp_path: Path):
    old_run_a, current_run_a = _fixture(tmp_path / "a")
    old_run_b, current_run_b = _fixture(tmp_path / "b", downstream_mismatch=True)
    schedule_a = build_schedule(old_run_a, current_run_a)
    schedule_b = build_schedule(old_run_b, current_run_b)

    assert [row["pair_sha256"] for row in schedule_a["pairs"]] == [row["pair_sha256"] for row in schedule_b["pairs"]]
    assert [row["request_sha256"] for row in schedule_a["pairs"]] == [row["request_sha256"] for row in schedule_b["pairs"]]


def test_source_snapshot_drift_invalidates_finite_label_result(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path)
    schedule = build_schedule(old_run, current_run)
    with (current_run / "results.jsonl").open("ab") as handle:
        handle.write(b"\n")

    report, rows = _audit_pairs(schedule, old_run, current_run)

    assert report["source_snapshot_hashes_match"] is False
    assert report["decision"] == "INVALID_EXPERIMENT"
    assert len(rows) == 48


def test_schedule_must_match_external_frozen_hash(tmp_path: Path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"experiment_id": "m4-b5-raw-response-repeatability-v1", "pairs": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="FROZEN_SCHEDULE_HASH_MISMATCH"):
        load_frozen_schedule(path)


def test_pair_schedule_requires_both_frozen_permission_denominators(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path)
    schedule = build_schedule(old_run, current_run)
    schedule["pairs"][0]["permission"] = "unexpected_permission"

    with pytest.raises(ValueError, match="SCHEDULE_PERMISSION_DENOMINATOR_INVALID"):
        _audit_pairs(schedule, old_run, current_run)


def test_duplicate_request_ids_are_rejected_before_mapping(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path)
    schedule = build_schedule(old_run, current_run)
    results_path = current_run / "results.jsonl"
    rows = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line]
    rows.append(dict(rows[0]))
    results_path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

    with pytest.raises(ValueError, match="CURRENT_RESULT_REQUEST_ID_DUPLICATE_OR_INVALID"):
        _audit_pairs(schedule, old_run, current_run)


def test_duplicate_historical_prediction_ids_are_rejected(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path)
    schedule = build_schedule(old_run, current_run)
    predictions_path = old_run / "predictions.jsonl"
    rows = [json.loads(line) for line in predictions_path.read_text(encoding="utf-8").splitlines() if line]
    rows.append(dict(rows[0]))
    predictions_path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

    with pytest.raises(ValueError, match="HISTORICAL_REQUEST_ID_DUPLICATE_OR_INVALID"):
        _audit_pairs(schedule, old_run, current_run)


def test_duplicate_attempt_ids_are_rejected(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path)
    schedule = build_schedule(old_run, current_run)
    ledger_path = current_run / "request_ledger.jsonl"
    rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line]
    rows.append(dict(rows[0]))
    ledger_path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")

    with pytest.raises(ValueError, match="CURRENT_ATTEMPT_REQUEST_ID_DUPLICATE_OR_INVALID"):
        _audit_pairs(schedule, old_run, current_run)


def test_public_audit_entry_point_rejects_replacement_schedule(tmp_path: Path):
    old_run, current_run = _fixture(tmp_path)
    schedule = build_schedule(old_run, current_run)
    schedule_path = tmp_path / "schedule.json"
    schedule_path.write_text(json.dumps(schedule), encoding="utf-8")

    with pytest.raises(ValueError, match="FROZEN_SCHEDULE_HASH_MISMATCH"):
        audit_pairs(schedule_path, old_run, current_run)
