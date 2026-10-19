from __future__ import annotations

import hashlib
import json

import pytest

from colluscope.m2_monitor import CLAIM_FIELDS
from scripts.audit_m2_v2_preflight_results import (
    AuditError, _error_class, _model_output_summary, _recompute,
)


def _fixture():
    parsed = {
        "public_harm": "not_visible", "ballot_disagreement": "not_visible",
        "message_delivery": "not_visible", "allocation_proposal": "not_visible",
        "action_concordance": "not_visible", "explicit_acceptance": "not_visible",
        "explicit_commitment": "not_visible", "observable_sequence": "insufficient_evidence",
        "latent_intent": "unknown", "evidence_refs": {field: [] for field in CLAIM_FIELDS},
        "abstention_reasons": ["actions_not_in_view", "messages_not_in_view"],
    }
    raw_text = json.dumps(parsed, separators=(",", ":"))
    usage = {"prompt_tokens": 100, "completion_tokens": 100}
    body = {"model": "monitor", "choices": [{"message": {"content": raw_text},
             "finish_reason": "stop"}], "usage": usage}
    body_text = json.dumps(body, separators=(",", ":"))
    payload = '{"model":"monitor","messages":[]}'
    payload_sha = hashlib.sha256(payload.encode()).hexdigest()
    request = {"payload_json": payload, "payload_sha256": payload_sha,
               "visible_event_ids": [], "view_name": "text_only",
               "permission_profile": "public_only", "compact": False}
    response = {"raw_response_body": body_text,
                "raw_response_body_sha256": hashlib.sha256(body_text.encode()).hexdigest(),
                "payload_sha256": payload_sha, "raw_assistant_text_sha256": hashlib.sha256(
                    raw_text.encode()).hexdigest(), "finish_reason": "stop", "usage": usage,
                "model": "monitor", "parsed": parsed, "validation_status": "valid",
                "validation_error": None, "reasoning_envelope": "none",
                "returned_at_utc": "2026-10-19T14:00:02+00:00"}
    return request, response


def test_preflight_response_audit_recomputes_raw_status():
    request, response = _fixture()
    result = _recompute(request, response, "monitor")
    assert result["status"] == "valid"
    assert result["error"] is None


def test_preflight_response_audit_rejects_tampered_raw_body():
    request, response = _fixture()
    response["raw_response_body"] += " "
    with pytest.raises(AuditError, match="raw_response_body_hash_mismatch"):
        _recompute(request, response, "monitor")


def test_failure_classification_separates_syntax_citations_and_view_errors():
    assert _error_class("invalid_json:bad input") == "syntax_prefix_or_truncation"
    assert _error_class("unknown_evidence_ref:ballot_disagreement") == "evidence_reference_violation"
    assert _error_class("messages_not_in_view_inapplicable") == "view_permission_mismatch"


def test_bad_case_projection_does_not_export_arbitrary_abstention_text():
    summary = _model_output_summary({
        "public_harm": "present", "abstention_reasons": ["private raw text should not appear"],
        "evidence_refs": {"public_harm": ["P01"]},
    }, {"P01"})
    assert summary["claim_values"]["public_harm"] == "present"
    assert summary["abstention_reason_count"] == 1
    assert summary["abstention_reasons_valid"] is False
    assert summary["citation_prefix_counts_by_claim"]["public_harm"] == {"P": 1}
    assert "private raw text" not in json.dumps(summary)
