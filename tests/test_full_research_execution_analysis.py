from scripts.analyze_full_research_execution import (
    _coverage_rate, _identity_probe_attempt_count, _method_coverage,
    _method_resource_rows, _normalize_prediction_rows, _paired_b4_b5,
)
import json
import copy
import pytest


def test_method_coverage_counts_only_raw_monitor_rows_and_keeps_failures():
    rows = [
        {"request_id": "ok", "baseline_id": "B2_text_only", "status": "COMPLETED",
         "prediction_label": "present", "raw_score": {"assessable": True, "exact_correct": True}},
        {"request_id": "gated", "baseline_id": "B5_evidence_aware_gated", "status": "COMPLETED",
         "prediction_label": "supported", "raw_score": {"assessable": True, "exact_correct": True}},
    ]
    progress = [
        {"request_id": "ok", "baseline_id": "B2_text_only"},
        {"request_id": "failed", "baseline_id": "B2_text_only"},
        {"request_id": "gated", "baseline_id": "B5_evidence_aware_gated"},
    ]

    result = _method_coverage(rows, "scripted_controls", progress)

    b2 = next(row for row in result if row["method"] == "B2_text_only")
    assert b2["assigned_rows"] == 2
    assert b2["parsed_predictions"] == 1
    assert b2["invalid_or_unexecuted"] == 1
    assert b2["assessable_predictions"] == 1
    assert b2["exact_correct_assessable"] == 1
    # Derived gating is an offline transformation, not a second model baseline.
    assert all(row["assigned_rows"] == 0 for row in result if row["method"].startswith("B5"))


def test_unassigned_method_cell_is_not_plotted_as_zero_completion():
    assert _coverage_rate({"assigned_rows": 0, "parsed_predictions": 0}) is None
    assert _coverage_rate({"assigned_rows": 4, "parsed_predictions": 0}) == 0.0


def test_method_coverage_exposes_hard_negative_positive_assertions():
    row = {
        "request_id": "hard-negative", "baseline_id": "B4_raw_fusion",
        "status": "COMPLETED", "prediction_label": "supported",
        "raw_score": {"assessable": True, "exact_correct": False,
                       "hard_negative_control": True, "positive_prediction": True,
                       "positive_reference": False, "unsupported_sequence_claim": True},
    }
    result = _method_coverage(
        [row], "scripted_controls",
        [{"request_id": "hard-negative", "baseline_id": "B4_raw_fusion"}],
    )
    b4 = next(item for item in result if item["method"] == "B4_raw_fusion")
    assert b4["hard_negative_predictions"] == 1
    assert b4["positive_predictions_on_hard_negatives"] == 1
    assert b4["unsupported_sequence_claims"] == 1


def test_identity_probe_counter_allows_a_failed_preflight_without_probe_file(tmp_path):
    assert _identity_probe_attempt_count([tmp_path / "not-created.jsonl"]) == 0


def test_method_resources_reconcile_attempt_time_and_peak_rate_cost():
    progress = [{
        "request_id": "r1", "baseline_id": "B2_text_only", "status": "INVALID_OUTPUT",
        "usage": {"input_tokens": 100, "output_tokens": 128},
        "cost_upper_peak_usd": 0.0001836,
    }]
    attempts = [
        {"request_id": "r1", "event": "attempt_started", "started_utc": "2026-10-20T00:00:00Z"},
        {"request_id": "r1", "event": "attempt_terminal", "ended_utc": "2026-10-20T00:00:01Z"},
    ]

    rows = _method_resource_rows(progress, attempts, "scripted_controls")

    b2 = next(row for row in rows if row["method"] == "B2_text_only")
    assert b2["assigned_rows"] == 1
    assert b2["parseable_rows"] == 0
    assert b2["peak_rate_cost_usd"] == 0.0001836
    assert b2["mean_latency_seconds"] == 1.0
    b3 = next(row for row in rows if row["method"] == "B3_action_only")
    assert b3["assigned_rows"] == 0
    assert b3["mean_latency_seconds"] is None


def test_paired_b4_b5_uses_only_common_completed_assessable_instances():
    def score(method, case, *, status="COMPLETED", assessable=True, correct=False):
        return {
            "baseline_id": method, "case_ref": case, "task": "public_harm",
            "permission": "Public-only", "status": status,
            "raw_score": {"assessable": assessable, "exact_correct": correct},
        }

    rows = [
        score("B4_raw_fusion", "common", correct=True),
        score("B5_evidence_aware", "common", correct=False),
        score("B4_raw_fusion", "b4-only"),
        score("B5_evidence_aware", "b5-only", status="INVALID_OUTPUT"),
        score("B4_raw_fusion", "not-assessable", assessable=False),
        score("B5_evidence_aware", "not-assessable", assessable=False),
    ]

    result = _paired_b4_b5(rows, "matched_worlds")

    assert result["common_assessable_instances"] == 1
    assert result["estimable"] is True
    assert result["B5_wins"] == 0
    assert result["ties"] == 0
    assert result["B4_wins"] == 1


def test_paired_b4_b5_is_not_estimable_when_completed_rows_do_not_overlap():
    rows = [
        {"baseline_id": "B4_raw_fusion", "case_ref": "one", "task": "proposal",
         "permission": "Privileged", "status": "COMPLETED",
         "raw_score": {"assessable": True, "exact_correct": True}},
        {"baseline_id": "B5_evidence_aware", "case_ref": "two", "task": "proposal",
         "permission": "Privileged", "status": "COMPLETED",
         "raw_score": {"assessable": True, "exact_correct": True}},
    ]

    result = _paired_b4_b5(rows, "scripted_controls")

    assert result["common_assessable_instances"] == 0
    assert result["estimable"] is False


def test_method_coverage_rejects_a_scored_request_missing_from_schedule_progress():
    scored = [{"request_id": "orphan", "baseline_id": "B2_text_only",
               "status": "COMPLETED", "raw_score": {"assessable": True,
                                                        "exact_correct": True}}]
    with pytest.raises(ValueError, match="unscheduled request ID"):
        _method_coverage(scored, "scripted_controls", [])


def test_row_scores_join_to_compact_audit_and_independent_aggregate(tmp_path):
    score = {
        "baseline_id": "B2_text_only", "task": "public_harm", "permission": "public_only",
        "case_ref": "synthetic-case", "assessable": True, "exact_correct": True,
        "abstained": False, "appropriate_abstention": False,
        "positive_reference": False, "positive_prediction": False,
        "unsupported_sequence_claim": False,
    }
    raw = {
        "request_id": "r1", "raw_prediction": {"label": "absent", "evidence_refs": []},
        "score": score,
    }
    (tmp_path / "raw_predictions.jsonl").write_text(json.dumps(raw) + "\n", encoding="utf-8")
    progress = [{"request_id": "r1", "baseline_id": "B2_text_only", "task": "public_harm",
                 "permission": "public_only", "status": "COMPLETED"}]
    audit = {
        "completed_predictions": 1,
        "per_request_scores": [{"request_id": "r1", "status": "COMPLETED",
                                "prediction_label": "absent", "score": None}],
        "task_view_metrics": {
            "B2_text_only|public_harm|public_only": {
                "scored_rows": 1, "assessable_rows": 1, "correct_assessable_rows": 1,
                "abstained_rows": 0, "appropriate_abstention_rows": 0,
                "positive_reference_rows": 0, "positive_prediction_rows": 0,
                "unsupported_sequence_claims": 0,
            },
        },
    }

    normalized = _normalize_prediction_rows(tmp_path, audit, progress, "scripted_controls")

    assert len(normalized) == 1
    assert normalized[0]["raw_score"]["exact_correct"] is True
    tampered = copy.deepcopy(audit)
    tampered["task_view_metrics"]["B2_text_only|public_harm|public_only"][
        "correct_assessable_rows"] = 0
    with pytest.raises(ValueError, match="do not reconcile"):
        _normalize_prediction_rows(tmp_path, tampered, progress, "scripted_controls")
