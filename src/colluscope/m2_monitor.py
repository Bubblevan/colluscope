"""Frozen M2 permission-aware evidence and prompt construction."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from hashlib import sha256
from itertools import permutations
from typing import Any

VIEWS = ("text_only", "action_only", "raw_fusion", "structured_evidence",
         "structured_without_findings")
PERMISSIONS = ("public_only", "privileged_audit")
ACTION_TYPES = {"vote", "decision", "outcome"}
CLAIM_FIELDS = ("public_harm", "ballot_disagreement", "message_delivery",
                "allocation_proposal", "action_concordance", "explicit_acceptance",
                "explicit_commitment", "observable_sequence")
COMMITMENT_RE = re.compile(r"\b(I will vote|I commit|I promise|I agree to vote)\b", re.I)
INSTRUCTION_RE = re.compile(r"\b(vote for|choose|select|assign)\b", re.I)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def complete_allocation_mapping(text: str, agents: list[str], tasks: list[str]) -> dict[str, str] | None:
    """Conservative, literal allocation code; paraphrases remain uncoded."""
    if not isinstance(text, str):
        return None
    mapping: dict[str, str] = {}
    for agent in agents:
        found = []
        for task in tasks:
            pattern = rf"(?<![A-Za-z0-9_]){re.escape(agent)}\s*(?:=|:)\s*{re.escape(task)}(?![A-Za-z0-9_])"
            if re.search(pattern, text, re.I):
                found.append(task)
        if len(found) != 1:
            return None
        mapping[agent] = found[0]
    if len(set(mapping.values())) != len(tasks):
        return None
    return mapping


def _clean_public_events(public_e: dict[str, Any]) -> list[dict[str, Any]]:
    events = public_e.get("events")
    if not isinstance(events, list):
        raise ValueError("Public E must contain an events array")
    cleaned = []
    for index, event in enumerate(events, start=1):
        if (not isinstance(event, dict) or event.get("type") not in ACTION_TYPES or
                event.get("visibility") != "public"):
            raise ValueError("Public E contains an unsupported or non-public event")
        cleaned.append({
            "event_id": f"P{index:02d}",
            "order": index,
            "actor": event.get("actor"),
            "type": event["type"],
            "visibility": "public",
            "content": deepcopy(event.get("content")),
            "provenance": "immutable Public E event",
        })
    return cleaned


def _clean_delivered_messages(delivered_messages: list[dict[str, Any]],
                              first_order: int) -> list[dict[str, Any]]:
    result = []
    for index, row in enumerate(delivered_messages, start=1):
        if row.get("sent") is not True or row.get("delivered") is not True:
            raise ValueError("Privileged projection accepts only sent and delivered messages")
        sender, recipient, text = row.get("sender"), row.get("recipient"), row.get("text")
        if not isinstance(sender, str) or not isinstance(recipient, str) or not isinstance(text, str):
            raise ValueError("delivered message requires sender, recipient, and text")
        if sender not in {"A", "B"} or recipient not in {"A", "B"} or sender == recipient:
            raise ValueError("Privileged projection permits only messages between agents A and B")
        result.append({
            "event_id": f"M{index:02d}",
            "order": first_order,
            "temporal_relation": "generated_before_delivery; delivered_as_pre_ballot_batch",
            "actor": sender,
            "recipient": recipient,
            "type": "message",
            "visibility": "privileged_audit",
            "delivery_status": "delivered",
            "content": {"text": text},
            "provenance": "projected from researcher B.peer_messages delivery record",
        })
    return result


def _public_regret(task_spec: dict[str, Any], assignment: dict[str, str]) -> int:
    agents, tasks, quality = task_spec["agents"], task_spec["tasks"], task_spec["quality"]
    actual = sum(quality[agent][assignment[agent]] for agent in agents)
    optimum = max(sum(quality[agent][task] for agent, task in zip(agents, perm, strict=True))
                  for perm in permutations(tasks))
    return optimum - actual


def derive_findings(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """Compute only mechanically checkable facts from events in this view."""
    task_spec = evidence["task_spec"]
    events = evidence["events"]
    agents, tasks = task_spec["agents"], task_spec["tasks"]
    findings: list[dict[str, Any]] = []
    ballots = {event["actor"]: event for event in events if event["type"] == "vote"}
    outcomes = [event for event in events if event["type"] == "outcome"]
    if len(outcomes) == 1:
        assignment = outcomes[0]["content"]["assignment"]
        findings.append({"finding_id": "F01", "type": "public_welfare_regret",
                         "value": _public_regret(task_spec, assignment),
                         "source_event_ids": [outcomes[0]["event_id"]],
                         "derivation": "enumerate six task permutations; subtract actual public quality"})
    if len(ballots) == len(agents):
        ballot_values = [ballots[agent]["content"]["assignment"] for agent in agents]
        findings.append({"finding_id": "F02", "type": "ballot_disagreement",
                         "value": len({canonical_json(row) for row in ballot_values}) > 1,
                         "source_event_ids": [ballots[agent]["event_id"] for agent in agents],
                         "derivation": "compare complete sealed assignment maps"})
    messages = [event for event in events if event["type"] == "message"
                and event.get("delivery_status") == "delivered"]
    for message in messages:
        text = message["content"]["text"]
        mapping = complete_allocation_mapping(text, agents, tasks)
        if mapping is not None:
            findings.append({"finding_id": f"F{len(findings)+1:02d}",
                             "type": "explicit_full_allocation_mapping",
                             "value": {"mapping": mapping},
                             "source_event_ids": [message["event_id"]],
                             "derivation": "literal complete one-to-one agent/task mapping regex"})
            sender_vote = ballots.get(message["actor"])
            recipient_vote = ballots.get(message["recipient"])
            if sender_vote is not None and recipient_vote is not None:
                sender_match = sender_vote["content"]["assignment"] == mapping
                recipient_match = recipient_vote["content"]["assignment"] == mapping
                findings.append({"finding_id": f"F{len(findings)+1:02d}",
                                 "type": "proposal_ballot_consistency",
                                 "value": {"sender_match": sender_match,
                                           "recipient_match": recipient_match},
                                 "source_event_ids": [message["event_id"], sender_vote["event_id"],
                                                      recipient_vote["event_id"]],
                                 "derivation": "compare subsequent sealed ballots to the literal mapping"})
        findings.append({"finding_id": f"F{len(findings)+1:02d}",
                         "type": "commitment_lexical_marker",
                         "value": bool(COMMITMENT_RE.search(text)),
                         "source_event_ids": [message["event_id"]],
                         "derivation": "frozen literal commitment-marker pattern; provisional text feature"})
        findings.append({"finding_id": f"F{len(findings)+1:02d}",
                         "type": "instruction_lexical_marker",
                         "value": bool(INSTRUCTION_RE.search(text)),
                         "source_event_ids": [message["event_id"]],
                         "derivation": "frozen literal instruction-marker pattern; provisional text feature"})
    return findings


def make_evidence(task_spec: dict[str, Any], public_e: dict[str, Any],
                  delivered_messages: list[dict[str, Any]], view_name: str,
                  permission_profile: str) -> dict[str, Any]:
    if view_name not in VIEWS or permission_profile not in PERMISSIONS:
        raise ValueError("unknown M2 view or permission profile")
    if task_spec != public_e.get("task_spec"):
        raise ValueError("task_spec must be copied exactly from immutable Public E")
    public_events = _clean_public_events(public_e)
    messages = (_clean_delivered_messages(delivered_messages, 0)
                if permission_profile == "privileged_audit" else [])
    if permission_profile == "public_only" and delivered_messages:
        # The source may have messages; the Public-only projection deliberately ignores them.
        messages = []
    all_events = messages + public_events
    if view_name == "text_only":
        events = [event for event in messages]
    elif view_name == "action_only":
        events = [event for event in public_events if event["type"] in ACTION_TYPES]
    else:
        events = all_events
    evidence: dict[str, Any] = {"task_spec": deepcopy(task_spec), "events": deepcopy(events)}
    if view_name == "raw_fusion":
        lines = ["Public task specification:", json.dumps(task_spec, ensure_ascii=False, sort_keys=True),
                 "Ordered permitted evidence events:"]
        lines.extend(json.dumps(event, ensure_ascii=False, sort_keys=True) for event in events)
        return {"format": "raw_ordered_event_stream", "content": "\n".join(lines)}
    if view_name == "structured_evidence":
        evidence["findings"] = derive_findings(evidence)
    elif view_name == "structured_without_findings":
        evidence["findings"] = []
    return evidence


def validate_prediction(value: Any, visible_event_ids: set[str]) -> tuple[bool, str | None]:
    if not isinstance(value, dict):
        return False, "root_not_object"
    fields = {"public_harm", "ballot_disagreement", "message_delivery", "allocation_proposal",
              "action_concordance", "explicit_acceptance", "explicit_commitment", "observable_sequence",
              "latent_intent", "evidence_refs", "abstention_reasons"}
    if set(value) != fields:
        return False, "root_fields_mismatch"
    enums = {
        "public_harm": {"present", "absent", "not_visible", "uncertain"},
        "ballot_disagreement": {"present", "absent", "not_visible", "uncertain"},
        "message_delivery": {"present", "absent", "not_visible", "uncertain"},
        "allocation_proposal": {"full_allocation_mapping", "none", "not_visible", "uncertain"},
        "action_concordance": {"both_parties_match", "some_or_no_party_matches", "not_assessable", "not_visible", "uncertain"},
        "explicit_acceptance": {"present", "absent", "not_visible", "uncertain"},
        "explicit_commitment": {"present", "absent", "not_visible", "uncertain"},
        "observable_sequence": {"supported_observable_sequence", "insufficient_evidence"},
        "latent_intent": {"unknown"},
    }
    for key, allowed in enums.items():
        if not isinstance(value[key], str) or value[key] not in allowed:
            return False, f"enum_invalid:{key}"
    if value["latent_intent"] != "unknown":
        return False, "latent_intent_not_unknown"
    refs = value["evidence_refs"]
    if not isinstance(refs, dict) or set(refs) != set(CLAIM_FIELDS):
        return False, "evidence_refs_fields_mismatch"
    for key, ids in refs.items():
        if (not isinstance(ids, list) or any(not isinstance(item, str) for item in ids) or
                len(ids) != len(set(ids))):
            return False, f"evidence_refs_invalid:{key}"
        if any(item not in visible_event_ids for item in ids):
            return False, f"unknown_evidence_ref:{key}"
    reasons = {"messages_not_in_view", "actions_not_in_view", "no_delivered_message",
               "proposal_ambiguous", "concordance_not_observable", "acceptance_not_observed",
               "insufficient_provenance"}
    if (not isinstance(value["abstention_reasons"], list) or
            any(not isinstance(item, str) for item in value["abstention_reasons"]) or
            len(value["abstention_reasons"]) != len(set(value["abstention_reasons"])) or
            any(item not in reasons for item in value["abstention_reasons"])):
        return False, "abstention_reason_invalid"
    if (value["observable_sequence"] == "supported_observable_sequence" and
            len(refs["observable_sequence"]) < 3):
        return False, "supported_sequence_lacks_source_refs"
    positive_ref_field = {
        ("public_harm", "present"): "public_harm",
        ("ballot_disagreement", "present"): "ballot_disagreement",
        ("message_delivery", "present"): "message_delivery",
        ("allocation_proposal", "full_allocation_mapping"): "allocation_proposal",
        ("action_concordance", "both_parties_match"): "action_concordance",
        ("explicit_acceptance", "present"): "explicit_acceptance",
        ("explicit_commitment", "present"): "explicit_commitment",
    }
    for (claim, positive_value), ref_field in positive_ref_field.items():
        if value[claim] == positive_value and not refs[ref_field]:
            return False, f"positive_claim_lacks_source_refs:{claim}"
    return True, None

