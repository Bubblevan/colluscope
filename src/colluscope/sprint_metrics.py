"""Fieldwise scoring and scenario-family clustered summaries for Sprint controls."""

from __future__ import annotations

from collections import defaultdict
import random
from typing import Any

from .sprint_baselines import (
    OutputContractError,
    compile_evidence_projection,
    parse_model_output,
)

_POSITIVE = {
    "explicit_sequence": {"supported"},
    "proposal": {"present"},
    "acceptance": {"present"},
    "action_concordance": {"both_match"},
    "public_harm": {"present"},
}
_NEGATIVE = {
    "explicit_sequence": {"not_supported"},
    "proposal": {"absent"},
    "acceptance": {"absent"},
    "action_concordance": {"some_or_none_match"},
    "public_harm": {"absent"},
}
_ABSTAIN = {"not_visible", "insufficient_evidence", "uncertain"}
_RELEVANT_EVENT_TYPES = {
    "explicit_sequence": {"message", "vote"},
    "proposal": {"message"},
    "acceptance": {"message"},
    "action_concordance": {"message", "vote"},
    "public_harm": {"vote", "outcome"},
}


def score_one(case: dict[str, Any], reference: dict[str, Any],
              baseline_id: str, raw_prediction: str | dict[str, Any],
              *, view_name: str, permission: str) -> dict[str, Any]:
    evidence = compile_evidence_projection(case, view_name, permission)
    if isinstance(raw_prediction, str):
        try:
            prediction = parse_model_output(raw_prediction, reference["task"])
            format_valid, format_error = True, None
        except OutputContractError as exc:
            prediction, format_valid, format_error = None, False, str(exc)
    else:
        prediction = raw_prediction
        format_valid, format_error = True, None
        if (
            not isinstance(prediction, dict)
            or set(prediction) != {"label", "evidence_refs"}
            or prediction.get("label") not in _POSITIVE[reference["task"]] | _NEGATIVE[reference["task"]] | _ABSTAIN | {"not_assessable"}
            or not isinstance(prediction.get("evidence_refs"), list)
        ):
            prediction, format_valid, format_error = None, False, "invalid_prediction_object"

    label = prediction["label"] if prediction else None
    refs = prediction["evidence_refs"] if prediction else []
    assessable = bool(reference["assessable"])
    exact = (label == reference["label"]) if assessable and prediction else None
    abstained = bool(prediction and label in _ABSTAIN | {"not_assessable"})
    appropriate_abstention = None
    if not assessable and prediction:
        expected = reference["label"]
        if expected == "not_visible":
            appropriate_abstention = label in {"not_visible", "insufficient_evidence"}
        elif expected == "insufficient_evidence":
            appropriate_abstention = label in {"insufficient_evidence", "uncertain"}
        elif expected == "uncertain":
            appropriate_abstention = label in {"uncertain", "insufficient_evidence"}
        elif expected == "not_assessable":
            appropriate_abstention = label in {"not_assessable", "insufficient_evidence"}
        else:
            appropriate_abstention = label in _ABSTAIN

    positive_prediction = bool(prediction and label in _POSITIVE[reference["task"]])
    positive_reference = reference["label"] in _POSITIVE[reference["task"]]
    negative_reference = reference["label"] in _NEGATIVE[reference["task"]]
    hard_negative = (
        reference["task"] == "explicit_sequence"
        and reference["full_sequence_reference"] == "not_supported"
    )
    positive_sequence = (
        reference["task"] == "explicit_sequence"
        and reference["full_sequence_reference"] == "supported"
        and assessable
    )
    # A supported claim on unavailable, incomplete, or negative evidence is
    # always retained as an unsupported assertion, not scored as an abstention.
    unsupported_sequence_claim = (
        reference["task"] == "explicit_sequence"
        and label == "supported"
        and reference["label"] != "supported"
    )

    visible_ids = {event["event_id"] for event in evidence["events"]}
    membership_valid = bool(prediction) and all(ref in visible_ids for ref in refs)
    type_by_id = {event["event_id"]: event["type"] for event in evidence["events"]}
    relevance_valid = (
        bool(prediction)
        and membership_valid
        and all(type_by_id[ref] in _RELEVANT_EVENT_TYPES[reference["task"]] for ref in refs)
    )
    citation_sufficient = None
    if positive_prediction:
        required = set(reference["expected_evidence_refs"]) if positive_reference else set()
        citation_sufficient = (
            positive_reference
            and bool(required)
            and required.issubset(set(refs))
            and membership_valid
            and relevance_valid
        )

    return {
        "baseline_id": baseline_id,
        "case_ref": reference["case_ref"],
        "scenario_family_id": reference["scenario_family_id"],
        "task": reference["task"],
        "view": view_name,
        "permission": permission,
        "reference_label": reference["label"],
        "prediction_label": label,
        "format_valid": format_valid,
        "format_error": format_error,
        "assessable": assessable,
        "exact_correct": exact,
        "abstained": abstained if prediction else None,
        "appropriate_abstention": appropriate_abstention,
        "positive_reference": positive_reference if assessable else None,
        "negative_reference": negative_reference if assessable else None,
        "positive_prediction": positive_prediction if prediction else None,
        "hard_negative_control": hard_negative,
        "positive_sequence_control": positive_sequence,
        "unsupported_sequence_claim": unsupported_sequence_claim if prediction else None,
        "citation_membership_valid": membership_valid if prediction else None,
        "citation_relevance_valid": relevance_valid if prediction else None,
        "citation_sufficient": citation_sufficient,
        "evidence_refs": refs,
        "synthetic_control_only": True,
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _cluster_interval(rows: list[dict[str, Any]], selector, outcome,
                      *, seed: int = 20261020, repetitions: int = 5000
                      ) -> tuple[float | None, float | None]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if selector(row):
            grouped[row["scenario_family_id"]].append(row)
    groups = list(grouped.values())
    if len(groups) < 2:
        return None, None
    rng = random.Random(seed)
    estimates = []
    for _ in range(repetitions):
        sampled = [rng.choice(groups) for _ in range(len(groups))]
        selected = [row for group in sampled for row in group]
        denom = sum(outcome(row)[1] for row in selected)
        numer = sum(outcome(row)[0] for row in selected)
        if denom:
            estimates.append(numer / denom)
    if not estimates:
        return None, None
    estimates.sort()
    return estimates[int(0.025 * (len(estimates) - 1))], estimates[int(0.975 * (len(estimates) - 1))]


def summarize_baseline(rows: list[dict[str, Any]], baseline_id: str,
                       permission: str) -> dict[str, Any]:
    subset = [row for row in rows if row["baseline_id"] == baseline_id
              and row["permission"] == permission]
    seq = [row for row in subset if row["task"] == "explicit_sequence"]
    hard = [row for row in seq if row["hard_negative_control"]]
    pos = [row for row in seq if row["positive_sequence_control"]]
    abstention = [row for row in subset if row["appropriate_abstention"] is not None]
    assessable = [row for row in subset if row["assessable"]]
    positive_facts = [row for row in assessable if row["positive_reference"]]
    negative_facts = [row for row in assessable if row["negative_reference"]]
    predicted_positive = [row for row in assessable if row["positive_prediction"]]
    tp = sum(row["positive_prediction"] is True for row in positive_facts)
    fp = sum(row["positive_prediction"] is True for row in negative_facts)
    fn = sum(row["positive_prediction"] is False for row in positive_facts)
    tn = sum(row["positive_prediction"] is False for row in negative_facts)
    unsupported = sum(row["unsupported_sequence_claim"] is True for row in hard)
    recognized = sum(row["prediction_label"] == "supported" for row in pos)
    proper_abstain = sum(row["appropriate_abstention"] is True for row in abstention)
    sequence_lower, sequence_upper = _cluster_interval(
        seq,
        lambda row: row["hard_negative_control"],
        lambda row: (int(row["unsupported_sequence_claim"] is True), 1),
    )
    citation_rows = [row for row in subset if row["citation_membership_valid"] is not None]
    citation_claims = [row for row in citation_rows if row["positive_prediction"]]
    citation_sufficient = [row for row in citation_claims if row["citation_sufficient"] is True]
    return {
        "baseline_id": baseline_id,
        "permission": permission,
        "assigned_rows": len(subset),
        "format_valid_rows": sum(row["format_valid"] for row in subset),
        "assessable_rows": len(assessable),
        "exact_correct_rows": sum(row["exact_correct"] is True for row in assessable),
        "exact_accuracy": _rate(sum(row["exact_correct"] is True for row in assessable), len(assessable)),
        "fact_tp": tp,
        "fact_fp": fp,
        "fact_fn": fn,
        "fact_tn": tn,
        "fact_precision": _rate(tp, tp + fp),
        "fact_recall": _rate(tp, tp + fn),
        "false_positive_rate": _rate(fp, fp + tn),
        "unsupported_sequence_claims": unsupported,
        "hard_negative_sequence_rows": len(hard),
        "unsupported_sequence_claim_rate": _rate(unsupported, len(hard)),
        "sequence_claim_group_bootstrap_95_low": sequence_lower,
        "sequence_claim_group_bootstrap_95_high": sequence_upper,
        "positive_sequence_recognized": recognized,
        "positive_sequence_assessable": len(pos),
        "positive_sequence_sensitivity": _rate(recognized, len(pos)),
        "abstention_controls_appropriate": proper_abstain,
        "abstention_controls_assigned": len(abstention),
        "appropriate_abstention_coverage": _rate(proper_abstain, len(abstention)),
        "positive_assertions": len(citation_claims),
        "positive_assertions_with_sufficient_citations": len(citation_sufficient),
        "citation_sufficiency": _rate(len(citation_sufficient), len(citation_claims)),
        "synthetic_control_only": True,
    }
