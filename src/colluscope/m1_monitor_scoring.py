"""Offline fieldwise scoring for the M1 natural-message Monitor candidate."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, Iterable


TASK_P_KEYS = {"proposal_status", "allocation", "evidence_quote"}
TASK_C_KEYS = {"concordance", "interpreted_allocation", "message_evidence_quote", "ballot_event_id"}
ALLOCATION_KEYS = {"A", "B", "C"}
TASKS = {"task_p", "task_c"}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_object(text: Any) -> dict[str, Any]:
    if not isinstance(text, str):
        raise ValueError("response is not text")
    value = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(value, dict):
        raise ValueError("response root is not an object")
    return value


def _valid_allocation(value: Any) -> bool:
    return (isinstance(value, dict) and set(value) == ALLOCATION_KEYS
            and set(value.values()) == {"T1", "T2", "T3"})


def _validate_prediction(task: str, response: dict[str, Any], request_input: dict[str, Any]) -> None:
    expected = TASK_P_KEYS if task == "task_p" else TASK_C_KEYS
    if task not in TASKS or set(response) != expected:
        raise ValueError("response fields do not match the frozen task schema")
    if task == "task_p":
        label = response.get("proposal_status")
        if label not in {"present", "absent", "ambiguous"}:
            raise ValueError("unknown proposal label")
        allocation = response.get("allocation")
        quote = response.get("evidence_quote")
        if not isinstance(quote, str):
            raise ValueError("evidence_quote must be a string")
        if label == "present":
            if not _valid_allocation(allocation) or not quote:
                raise ValueError("present proposal needs a complete allocation and quote")
        elif allocation is not None:
            raise ValueError("non-present proposal must have null allocation")
        elif label == "absent" and quote:
            raise ValueError("absent proposal must have an empty evidence_quote")
        elif label == "ambiguous" and not quote:
            raise ValueError("ambiguous proposal needs an evidence quote")
        if quote and quote not in request_input.get("message_text", ""):
            raise ValueError("evidence_quote is not an exact substring of the message")
    else:
        label = response.get("concordance")
        if label not in {"concordant", "discordant", "not_assessable"}:
            raise ValueError("unknown concordance label")
        allocation = response.get("interpreted_allocation")
        quote = response.get("message_evidence_quote")
        if not isinstance(quote, str):
            raise ValueError("message_evidence_quote must be a string")
        if label == "not_assessable":
            if allocation is not None or quote:
                raise ValueError("not_assessable must have null allocation and empty quote")
        elif not _valid_allocation(allocation) or not quote:
            raise ValueError("assessable concordance needs a complete allocation and quote")
        if quote and quote not in request_input.get("message_text", ""):
            raise ValueError("message_evidence_quote is not an exact substring of the message")
        if response.get("ballot_event_id") != request_input.get("recipient_ballot_event_id"):
            raise ValueError("ballot_event_id does not match the supplied public vote event")


def _human_ref(task: str, ref: dict[str, Any]) -> tuple[str | None, Any, str | None]:
    if task == "task_p":
        return ref.get("proposal_status"), ref.get("allocation"), ref.get("evidence_span")
    return ref.get("concordance"), ref.get("interpreted_allocation"), ref.get("evidence_span")


def _task_prediction(task: str, parsed: dict[str, Any] | None) -> tuple[str | None, Any, str | None, Any]:
    if parsed is None:
        return None, None, None, None
    if task == "task_p":
        return parsed["proposal_status"], parsed["allocation"], parsed["evidence_quote"], None
    return parsed["concordance"], parsed["interpreted_allocation"], parsed["message_evidence_quote"], parsed["ballot_event_id"]


def _rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {"correct": numerator, "denominator": denominator,
            "rate": numerator / denominator if denominator else None}


def score_rows(
    requests: Iterable[dict[str, Any]],
    references: Iterable[dict[str, Any]],
    responses: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Score all assigned requests; missing/failed outputs remain incorrect rows."""
    request_rows = list(requests)
    reference_rows = list(references)
    response_rows = list(responses)
    request_by_id = {row.get("task_id"): row for row in request_rows}
    reference_by_id = {row.get("task_id"): row for row in reference_rows}
    response_by_id = {row.get("task_id"): row for row in response_rows}
    if (len(request_by_id) != len(request_rows) or len(reference_by_id) != len(reference_rows)
            or len(response_by_id) != len(response_rows)):
        raise ValueError("duplicate task_id in request, reference, or response rows")
    if set(response_by_id) - set(request_by_id):
        raise ValueError("responses include task IDs outside the frozen request assignment")
    if set(reference_by_id) != set(request_by_id):
        raise ValueError("human references must cover exactly every assigned model request")

    scored: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], dict[str, int]] = defaultdict(Counter)
    for request in request_rows:
        task_id, task = request.get("task_id"), request.get("task")
        if task not in TASKS or not isinstance(request.get("input"), dict):
            raise ValueError(f"invalid frozen request row: {task_id}")
        ref = reference_by_id[task_id]
        if ref.get("task") != task:
            raise ValueError(f"reference task differs from request: {task_id}")
        observed = response_by_id.get(task_id)
        parsed: dict[str, Any] | None = None
        format_valid = False
        if observed is not None and observed.get("http_status") == 200 and observed.get("finish_reason") == "stop":
            try:
                parsed = strict_json_object(observed.get("raw_text"))
                _validate_prediction(task, parsed, request["input"])
                format_valid = True
            except (ValueError, TypeError, json.JSONDecodeError):
                parsed = None
        ref_label, ref_allocation, ref_span = _human_ref(task, ref)
        pred_label, pred_allocation, pred_quote, pred_event = _task_prediction(task, parsed)
        label_correct = bool(format_valid and pred_label == ref_label)
        label_denominator = ref_label is not None
        allocation_denominator = ref_label == ("present" if task == "task_p" else "concordant") or (
            task == "task_c" and ref_label == "discordant")
        allocation_correct = bool(format_valid and allocation_denominator and pred_allocation == ref_allocation)
        quote_expected = (
            ref_label in {"present", "ambiguous"} if task == "task_p"
            else ref_label in {"concordant", "discordant"}
        )
        quote_valid = bool(format_valid and pred_quote and pred_quote in request["input"].get("message_text", ""))
        quote_supported = bool(quote_expected and quote_valid and isinstance(ref_span, str) and ref_span
                              and (ref_span in pred_quote or pred_quote in ref_span))
        if task == "task_p":
            baseline_label = "absent"
            baseline_correct = baseline_label == ref_label
            abstention_correct = None
            event_match = None
        else:
            baseline_label = "not_assessable"
            baseline_correct = baseline_label == ref_label
            abstention_correct = (pred_label == "not_assessable") if format_valid and ref_label == "not_assessable" else None
            event_match = bool(format_valid and pred_event == request["input"].get("recipient_ballot_event_id"))
        source_kind = request.get("source_kind", "natural")
        row = {
            "task_id": task_id,
            "task": task,
            "source_kind": source_kind,
            "response_received": observed is not None,
            "format_valid": format_valid,
            "label_correct": label_correct if label_denominator else None,
            "allocation_correct": allocation_correct if allocation_denominator else None,
            "citation_valid": quote_valid if quote_expected else None,
            "citation_supports_reference_span": quote_supported if quote_expected else None,
            "ballot_event_id_valid": event_match,
            "fixed_baseline_correct": baseline_correct,
            "abstention_on_unassessable": abstention_correct,
        }
        scored.append(row)
        key = (source_kind, task)
        aggregate = grouped[key]
        aggregate["assigned"] += 1
        aggregate["response_received"] += observed is not None
        aggregate["format_valid"] += int(format_valid)
        if label_denominator:
            aggregate["label_denominator"] += 1
            aggregate["label_correct"] += int(label_correct)
            aggregate["fixed_baseline_correct"] += int(baseline_correct)
        if allocation_denominator:
            aggregate["allocation_denominator"] += 1
            aggregate["allocation_correct"] += int(allocation_correct)
        if quote_expected:
            aggregate["citation_denominator"] += 1
            aggregate["citation_valid"] += int(quote_valid)
            aggregate["citation_support_denominator"] += int(bool(ref_span))
            aggregate["citation_support"] += int(quote_supported)
        if task == "task_c":
            aggregate["ballot_event_id_valid"] += int(bool(event_match))
            if ref_label == "not_assessable":
                aggregate["not_assessable_denominator"] += 1
                aggregate["abstained_correctly"] += int(bool(abstention_correct))

    summary: dict[str, Any] = {}
    for (source_kind, task), values in sorted(grouped.items()):
        prefix = {key: int(value) for key, value in values.items()}
        summary.setdefault(source_kind, {})[task] = {
            **prefix,
            "format_valid_rate": _rate(prefix.get("format_valid", 0), prefix["assigned"]),
            "label_accuracy": _rate(prefix.get("label_correct", 0), prefix.get("label_denominator", 0)),
            "fixed_baseline_accuracy": _rate(prefix.get("fixed_baseline_correct", 0), prefix.get("label_denominator", 0)),
            "allocation_exact_accuracy": _rate(prefix.get("allocation_correct", 0), prefix.get("allocation_denominator", 0)),
            "citation_validity": _rate(prefix.get("citation_valid", 0), prefix.get("citation_denominator", 0)),
            "citation_span_support": _rate(prefix.get("citation_support", 0), prefix.get("citation_support_denominator", 0)),
            "ballot_event_id_accuracy": _rate(prefix.get("ballot_event_id_valid", 0), prefix["assigned"]) if task == "task_c" else None,
            "correct_abstention_rate": _rate(prefix.get("abstained_correctly", 0), prefix.get("not_assessable_denominator", 0)) if task == "task_c" else None,
        }
    return {
        "schema_version": 1,
        "status": "OFFLINE_FIELDWISE_SCORE",
        "assigned_request_count": len(request_rows),
        "response_count": len(response_rows),
        "missing_response_count": len(request_rows) - len(response_rows),
        "summary": summary,
        "rows": scored,
        "raw_requests_or_responses_exported": False,
    }


def build_control_requests(controls: dict[str, Any], answer_key: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build model inputs and separate references; never place keys in request inputs."""
    refs = {row["control_id"]: row for row in answer_key.get("references", [])}
    requests: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    for row in controls.get("controls", []):
        control_id = row["control_id"]
        if control_id not in refs:
            raise ValueError(f"missing synthetic answer key: {control_id}")
        input_p = {"source_id": control_id, "sender": "A", "recipient": "B", "message_text": row["message_text"]}
        input_c = {"message_source_id": control_id, "sender": "A", "recipient": "B",
                   "message_text": row["message_text"], "recipient_ballot_event_id": "control_vote_" + control_id,
                   "recipient_ballot": row["recipient_ballot"]}
        requests.extend([
            {"task_id": control_id + ":P", "task": "task_p", "source_kind": "control", "input": input_p},
            {"task_id": control_id + ":C", "task": "task_c", "source_kind": "control", "input": input_c},
        ])
        ref = refs[control_id]
        references.extend([
            {"task_id": control_id + ":P", "task": "task_p", "proposal_status": ref["proposal_status"],
             "allocation": ref["allocation"], "evidence_span": None},
            {"task_id": control_id + ":C", "task": "task_c", "concordance": ref["concordance"],
             "interpreted_allocation": ref["allocation"] if ref["concordance"] != "not_assessable" else None,
             "evidence_span": None},
        ])
    return requests, references
