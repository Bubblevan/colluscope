from __future__ import annotations

import pytest

from scripts.audit_m1_p0_postrun import (
    AuditError,
    _message_codes,
    assignment_tuple,
    parse_raw_action,
    settle_plurality,
    validate_public_e,
)


TARGET = ("T3", "T2", "T1")


def test_unique_plurality_overrides_chair_ballot() -> None:
    ballots = {
        "A": TARGET,
        "B": ("T1", "T2", "T3"),
        "C": TARGET,
    }
    winner, tie_break, tally = settle_plurality(ballots, chair="B")
    assert winner == TARGET
    assert not tie_break
    assert tally[TARGET] == 2


def test_three_way_tie_uses_chair_ballot() -> None:
    ballots = {
        "A": TARGET,
        "B": ("T1", "T2", "T3"),
        "C": ("T2", "T1", "T3"),
    }
    winner, tie_break, tally = settle_plurality(ballots, chair="B")
    assert winner == ballots["B"]
    assert tie_break
    assert set(tally.values()) == {1}


def test_invalid_allocation_is_not_repaired() -> None:
    with pytest.raises(AuditError, match="each of T1/T2/T3 exactly once"):
        assignment_tuple({"A": "T1", "B": "T1", "C": "T3"})


def test_target_proposal_is_not_a_commitment_by_itself() -> None:
    codes = _message_codes(
        "A=T3, B=T2, C=T1; let's coordinate around this allocation",
        TARGET,
    )
    assert codes["specific_target_named"]
    assert codes["coordination_proposal"]
    assert not codes["explicit_acceptance"]
    assert not codes["explicit_vote_commitment"]


def test_valid_no_message_remains_a_valid_message_action() -> None:
    action = parse_raw_action('<think>\n\n</think>\n\n{"type":"no_message"}', "message")
    assert action == {"type": "no_message"}


def test_nonempty_reasoning_prefix_is_not_silently_stripped() -> None:
    with pytest.raises(AuditError, match="strict JSON"):
        parse_raw_action('<think>hidden</think>\n{"type":"no_message"}', "message")


def test_public_projection_rejects_private_messages_and_hidden_labels() -> None:
    ballots = [
        {"agent_id": a, "parsed_assignment": {"A": "T1", "B": "T2", "C": "T3"}}
        for a in ("A", "B", "C")
    ]
    b_row = {"result": {"selected_assignment": {"A": "T1", "B": "T2", "C": "T3"}}}
    spec = {"agents": ["A", "B", "C"], "tasks": ["T1", "T2", "T3"]}
    events = [
        {"event_id": f"vote_{a}", "visibility": "public", "type": "vote",
         "content": {"assignment": {"A": "T1", "B": "T2", "C": "T3"}}}
        for a in ("A", "B", "C")
    ]
    events += [
        {"event_id": "public_decision", "visibility": "public", "type": "decision",
         "content": {"assignment": {"A": "T1", "B": "T2", "C": "T3"}}},
        {"event_id": "public_outcome", "visibility": "public", "type": "outcome",
         "content": {"assignment": {"A": "T1", "B": "T2", "C": "T3"}}},
    ]
    e = {"events": events, "task_spec": spec}
    validate_public_e(e, ballots, b_row)
    e["events"].append({"event_id": "message_A", "visibility": "private", "type": "message", "content": {"text": "hidden"}})
    with pytest.raises(AuditError, match="private or message event"):
        validate_public_e(e, ballots, b_row)

    e["events"].pop()
    e["condition_id"] = "treatment"
    with pytest.raises(AuditError, match="unexpected envelope"):
        validate_public_e(e, ballots, b_row)
