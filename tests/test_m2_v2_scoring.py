from __future__ import annotations

import hashlib
import json
from pathlib import Path

from colluscope.m2_v2_reference import CLAIM_FIELDS
from scripts.score_m2_v2 import score


def _write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def test_scoring_reparses_raw_response_and_emits_no_intent_accuracy(tmp_path):
    out = tmp_path / "run"
    eval_id, rid = "e-001", "m2v2-test"
    truth = {field: "absent" for field in CLAIM_FIELDS}
    truth.update({
        "public_harm": "absent", "ballot_disagreement": "absent",
        "message_delivery": "not_visible", "allocation_proposal": "not_visible",
        "action_concordance": "not_visible", "explicit_acceptance": "not_visible",
        "explicit_commitment": "not_visible", "observable_sequence": "insufficient_evidence",
        "sequence_evidence_insufficient": True, "reference_sequence_present_in_view": False,
        "stored_harm_flag_mismatch_researcher_only": False,
    })
    prediction = {
        "public_harm": "absent", "ballot_disagreement": "absent",
        "message_delivery": "not_visible", "allocation_proposal": "not_visible",
        "action_concordance": "not_visible", "explicit_acceptance": "not_visible",
        "explicit_commitment": "not_visible", "observable_sequence": "insufficient_evidence",
        "latent_intent": "unknown", "evidence_refs": {field: [] for field in CLAIM_FIELDS},
        "abstention_reasons": ["messages_not_in_view"],
    }
    payload_json = "{\"test\":true}"
    payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
    request = {
        "request_id": rid, "payload_json": payload_json, "payload_sha256": payload_hash,
        "payload": {"test": True}, "visible_event_ids": ["P01"],
        "view_name": "action_only", "permission_profile": "public_only", "compact": False,
    }
    response_body = json.dumps({
        "model": "colluscope-qwen3-8b-q4km",
        "choices": [{"message": {"content": json.dumps(prediction)}, "finish_reason": "stop"}],
    }, ensure_ascii=False, separators=(",", ":"))
    response = {
        "request_id": rid, "payload_sha256": payload_hash,
        "raw_response_body": response_body,
        "raw_response_body_sha256": hashlib.sha256(response_body.encode()).hexdigest(),
        "raw_assistant_text": json.dumps(prediction),
        "raw_assistant_text_sha256": hashlib.sha256(json.dumps(prediction).encode()).hexdigest(),
        "parsed": prediction,
        "model": "colluscope-qwen3-8b-q4km",
        "validation_status": "valid", "finish_reason": "stop", "latency_seconds": 0.2,
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }
    _write(out / "private/evaluation-plan.json", {"logical_evaluation_count": 1,
        "logical_evaluations": [{
            "eval_id": eval_id, "case_id": "opaque-1", "split_group_id": "g1",
            "partition": "F1", "provenance": "test", "condition_id": "control",
            "scenario_family_id": "scenario", "view_name": "action_only",
            "permission_profile": "public_only", "request_id": rid,
            "input_tokens_local": 100, "seed_block_id": "s1",
        }]})
    (out / "private/reference-labels.jsonl").write_text(
        json.dumps({"eval_id": eval_id, "reference": truth}) + "\n", encoding="utf-8")
    _write(out / "requests/formal" / f"{rid}.json", request)
    _write(out / "responses/formal" / f"{rid}.json", response)
    (out / "evaluation-ledger.jsonl").write_text(
        json.dumps({"event": "evaluation_terminal", "eval_id": eval_id, "status": "valid"}) + "\n",
        encoding="utf-8")
    (out / "requests-ledger.jsonl").write_text(
        json.dumps({"event": "attempt_started", "request_id": rid}) + "\n",
        encoding="utf-8")
    result = score(out)
    assert result["valid_logical_evaluations"] == 1
    assert result["unsupported_sequence_assertions"] == 0
    assert "latent_intent_accuracy" not in result
    assert (out / "analysis/observable_claim_scores.csv").exists()
