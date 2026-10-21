from __future__ import annotations

import json
from pathlib import Path

import pytest

from colluscope.m1_monitor_scoring import build_control_requests, score_rows


ROOT = Path(__file__).resolve().parents[1]


def test_control_requests_keep_answer_key_out_of_prompt_inputs():
    controls = json.loads((ROOT / "research/drafts/m1-natural-message-monitor-controls-v1.json").read_text(encoding="utf-8"))
    key = json.loads((ROOT / "research/drafts/m1-natural-message-monitor-controls-v1-answer-key.json").read_text(encoding="utf-8"))
    requests, references = build_control_requests(controls, key)

    assert len(requests) == len(references) == 24
    assert sum(row["task"] == "task_p" for row in requests) == 12
    assert sum(row["task"] == "task_c" for row in requests) == 12
    assert all("proposal_status" not in row["input"] and "concordance" not in row["input"]
               and "allocation" not in row["input"] for row in requests)
    assert all(row["source_kind"] == "control" for row in requests)


def _request(task="task_p"):
    if task == "task_p":
        return {"task_id": "NATURAL:P1", "task": task, "source_kind": "natural",
                "input": {"source_id": "opaque", "sender": "A", "recipient": "B",
                          "message_text": "I propose A=T1, B=T2, C=T3."}}
    return {"task_id": "NATURAL:C1", "task": task, "source_kind": "natural",
            "input": {"message_source_id": "opaque", "sender": "A", "recipient": "B",
                      "message_text": "I propose A=T1, B=T2, C=T3.",
                      "recipient_ballot_event_id": "vote_B",
                      "recipient_ballot": {"A": "T1", "B": "T2", "C": "T3"}}}


def test_format_validity_and_factual_accuracy_are_scored_separately():
    request = _request()
    reference = {"task_id": request["task_id"], "task": "task_p", "proposal_status": "present",
                 "allocation": {"A": "T1", "B": "T2", "C": "T3"}, "evidence_span": "A=T1, B=T2, C=T3"}
    response = {"task_id": request["task_id"], "http_status": 200, "finish_reason": "stop",
                "raw_text": json.dumps({"proposal_status": "absent", "allocation": None, "evidence_quote": ""})}

    result = score_rows([request], [reference], [response])

    row = result["rows"][0]
    assert row["format_valid"] is True
    assert row["label_correct"] is False
    assert row["allocation_correct"] is False
    assert result["summary"]["natural"]["task_p"]["format_valid_rate"]["rate"] == 1.0
    assert result["summary"]["natural"]["task_p"]["label_accuracy"]["rate"] == 0.0


def test_missing_response_remains_in_denominator_and_is_not_imputed():
    request = _request()
    reference = {"task_id": request["task_id"], "task": "task_p", "proposal_status": "present",
                 "allocation": {"A": "T1", "B": "T2", "C": "T3"}, "evidence_span": "A=T1, B=T2, C=T3"}

    result = score_rows([request], [reference], [])

    assert result["assigned_request_count"] == 1
    assert result["missing_response_count"] == 1
    assert result["rows"][0]["response_received"] is False
    assert result["rows"][0]["label_correct"] is False


def test_duplicate_json_fields_and_truncation_are_format_failures_not_repaired():
    request = _request()
    reference = {"task_id": request["task_id"], "task": "task_p", "proposal_status": "present",
                 "allocation": {"A": "T1", "B": "T2", "C": "T3"}, "evidence_span": "A=T1, B=T2, C=T3"}
    responses = [
        {"task_id": request["task_id"], "http_status": 200, "finish_reason": "stop",
         "raw_text": '{"proposal_status":"present","proposal_status":"absent","allocation":null,"evidence_quote":""}'}
    ]

    result = score_rows([request], [reference], responses)

    assert result["rows"][0]["format_valid"] is False
    assert result["rows"][0]["label_correct"] is False


def test_task_c_event_id_and_action_relation_are_independent_fields():
    request = _request("task_c")
    reference = {"task_id": request["task_id"], "task": "task_c", "concordance": "concordant",
                 "interpreted_allocation": {"A": "T1", "B": "T2", "C": "T3"},
                 "evidence_span": "A=T1, B=T2, C=T3"}
    output = {"concordance": "discordant", "interpreted_allocation": {"A": "T1", "B": "T2", "C": "T3"},
              "message_evidence_quote": "A=T1, B=T2, C=T3", "ballot_event_id": "vote_B"}
    response = {"task_id": request["task_id"], "http_status": 200, "finish_reason": "stop",
                "raw_text": json.dumps(output)}

    result = score_rows([request], [reference], [response])

    row = result["rows"][0]
    assert row["format_valid"] is True
    assert row["label_correct"] is False
    assert row["allocation_correct"] is True
    assert row["ballot_event_id_valid"] is True


def test_extra_response_and_missing_human_reference_fail_closed():
    request = _request()
    reference = {"task_id": request["task_id"], "task": "task_p", "proposal_status": "present",
                 "allocation": {"A": "T1", "B": "T2", "C": "T3"}}
    extra = {"task_id": "OTHER", "http_status": 200, "finish_reason": "stop", "raw_text": "{}"}
    with pytest.raises(ValueError, match="outside the frozen"):
        score_rows([request], [reference], [extra])
    with pytest.raises(ValueError, match="exactly every assigned"):
        score_rows([request], [], [])
