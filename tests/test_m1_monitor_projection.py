from __future__ import annotations

import pytest

from colluscope.m1_monitor_projection import build_projection
from colluscope.m1_package_replication_v3_runtime import assigned_episodes, load_frozen_schedule


SCHEDULE = load_frozen_schedule()
ASSIGNED = assigned_episodes(SCHEDULE)
SCHEDULE_SHA = "79358acd02dcade31291e879d1d173e5e92e9bf5f57305c65a3d59f954ca502a"
FORBIDDEN = {
    "condition_id", "reward_assignment", "target_allocation", "payoff_matrix",
    "public_optimum", "settled_allocation", "welfare", "human_reference",
    "other_private_messages", "private_target_bonus_recipients", "seed_block_id",
}


def _chat_episode():
    return next(row for row in ASSIGNED if row["condition_id"] == "coalition_incentive_private_chat")


def _trace(assigned, messages, ballots, events=None):
    episode_id = assigned["episode_id"]
    return {
        "T": {
            "episode_id": episode_id,
            "condition_id": assigned["condition_id"],
            "assigned": {"private_chat_available": True},
        },
        "B": {"episode_id": episode_id, "peer_messages": messages, "ballots": ballots},
        "E": {"events": events or []},
    }


def _ballots():
    return [
        {"agent_id": "A", "sealed": True, "parsed_assignment": {"A": "T1", "B": "T2", "C": "T3"}},
        {"agent_id": "B", "sealed": True, "parsed_assignment": {"A": "T1", "B": "T2", "C": "T3"}},
        {"agent_id": "C", "sealed": True, "parsed_assignment": {"A": "T1", "B": "T2", "C": "T3"}},
    ]


def _vote_events(ballots):
    return [{"event_id": f"vote_{row['agent_id']}", "actor": row["agent_id"], "type": "vote",
             "content": {"assignment": row["parsed_assignment"]}}
            for row in ballots if row["sealed"]]


def test_full_assigned_slot_denominator_is_preserved_when_no_trace_exists():
    result = build_projection(SCHEDULE, ASSIGNED, {}, [], schedule_sha256=SCHEDULE_SHA)

    assert len(result["coverage"]) == 96
    assert len(result["monitor_requests"]) == 0
    assert len(result["annotation_rows"]) == 0
    assert result["summary"]["slot_state_counts"] == {"not_observed_unresolved": 96}
    assert result["summary"]["monitor_calls_sent"] == 0


def test_delivered_message_is_projected_without_treatment_metadata_and_valid_no_message_is_not_sent():
    assigned = _chat_episode()
    ballots = _ballots()
    trace = _trace(assigned, [
        {"sender": "A", "recipient": "B", "request_id": assigned["episode_id"] + "-req-00",
         "sent": True, "delivered": True, "delivery_status": "delivered_to_named_peer",
         "text": "A proposes A=T1, B=T2, C=T3."},
        {"sender": "B", "recipient": "A", "request_id": assigned["episode_id"] + "-req-01",
         "sent": False, "delivered": False, "delivery_status": "not_sent", "text": None},
    ], ballots, _vote_events(ballots))

    result = build_projection(SCHEDULE, ASSIGNED, {assigned["episode_id"]: trace}, [],
                              schedule_sha256=SCHEDULE_SHA)

    assert len(result["coverage"]) == 96
    assert result["summary"]["slot_state_counts"] == {
        "no_message": 1, "not_observed_unresolved": 94, "sent_delivered": 1,
    }
    assert {row["task"] for row in result["monitor_requests"]} == {"task_p", "task_c"}
    assert len(result["monitor_requests"]) == 2
    for request in result["monitor_requests"]:
        assert not (FORBIDDEN & set(request["input"]))
        assert request["input"]["message_text"] == "A proposes A=T1, B=T2, C=T3."
    assert all("A proposes" not in row["input"].get("message_text", "")
               for row in result["monitor_requests"] if row["task"] not in {"task_p", "task_c"})
    assert not any("A proposes" in str(row) for row in result["coverage"])


def test_proposal_task_survives_invalid_recipient_ballot_but_concordance_does_not():
    assigned = _chat_episode()
    ballots = _ballots()
    ballots[1] = {"agent_id": "B", "sealed": False, "parsed_assignment": None}
    trace = _trace(assigned, [
        {"sender": "A", "recipient": "B", "request_id": assigned["episode_id"] + "-req-00",
         "sent": True, "delivered": True, "delivery_status": "delivered_to_named_peer", "text": "A=T1, B=T2, C=T3 is my proposal."},
        {"sender": "B", "recipient": "A", "sent": False, "delivered": False,
         "delivery_status": "not_sent", "text": None},
    ], ballots, _vote_events([ballots[0], ballots[2]]))

    result = build_projection(SCHEDULE, ASSIGNED, {assigned["episode_id"]: trace}, [],
                              schedule_sha256=SCHEDULE_SHA)

    a_row = next(row for row in result["coverage"] if row["episode_id"] == assigned["episode_id"]
                 and row["sender"] == "A")
    assert a_row["task_p_eligible"] is True
    assert a_row["task_c_eligible"] is False
    assert a_row["task_c_ineligible_reason"] == "recipient_ballot_not_public_or_invalid"
    assert [row["task"] for row in result["monitor_requests"]] == ["task_p"]


def test_undelivered_private_text_never_enters_monitor_or_annotation_inputs():
    assigned = _chat_episode()
    sentinel = "PRIVATE-NOT-DELIVERED-SHOULD-NEVER-LEAVE-LOCAL"
    trace = _trace(assigned, [
        {"sender": "A", "recipient": "B", "request_id": assigned["episode_id"] + "-req-00",
         "sent": True, "delivered": False, "delivery_status": "not_delivered_peer_round_incomplete",
         "text": sentinel},
        {"sender": "B", "recipient": "A", "sent": False, "delivered": False,
         "delivery_status": "not_sent", "text": None},
    ], [], [])

    result = build_projection(SCHEDULE, ASSIGNED, {assigned["episode_id"]: trace}, [],
                              schedule_sha256=SCHEDULE_SHA)

    assert not any(sentinel in str(row) for row in result["monitor_requests"])
    assert not any(sentinel in str(row) for row in result["annotation_rows"])
    assert not any(sentinel in str(row) for row in result["coverage"])
    a_row = next(row for row in result["coverage"] if row["sender"] == "A")
    assert a_row["slot_state"] == "sent_not_delivered"
    assert a_row["task_p_eligible"] is False


def test_mismatched_public_vote_and_sealed_ballot_fail_closed():
    assigned = _chat_episode()
    ballots = _ballots()
    events = _vote_events(ballots)
    events[1]["content"]["assignment"] = {"A": "T2", "B": "T1", "C": "T3"}
    trace = _trace(assigned, [
        {"sender": "A", "recipient": "B", "sent": True, "delivered": True,
         "delivery_status": "delivered_to_named_peer", "text": "A=T1, B=T2, C=T3."},
        {"sender": "B", "recipient": "A", "sent": False, "delivered": False,
         "delivery_status": "not_sent", "text": None},
    ], ballots, events)

    with pytest.raises(ValueError, match="public vote event differs"):
        build_projection(SCHEDULE, ASSIGNED, {assigned["episode_id"]: trace}, [],
                         schedule_sha256=SCHEDULE_SHA)


def test_trace_condition_mismatch_fails_closed():
    assigned = _chat_episode()
    trace = _trace(assigned, [], [], [])
    trace["T"]["condition_id"] = "normal_cooperation"
    with pytest.raises(ValueError, match="trace treatment does not match"):
        build_projection(SCHEDULE, ASSIGNED, {assigned["episode_id"]: trace}, [],
                         schedule_sha256=SCHEDULE_SHA)


def test_message_attempt_without_output_record_is_not_recast_as_no_message():
    assigned = _chat_episode()
    payloads = [{"event": "logical_request_attempt_reserved", "request_id": assigned["episode_id"] + "-req-00",
                 "action_kind": "message", "agent_id": "A"}]
    trace = _trace(assigned, [], [], [])

    result = build_projection(SCHEDULE, ASSIGNED, {assigned["episode_id"]: trace}, payloads,
                              schedule_sha256=SCHEDULE_SHA)

    a_row = next(row for row in result["coverage"] if row["episode_id"] == assigned["episode_id"]
                 and row["sender"] == "A")
    assert a_row["slot_state"] == "request_failed_or_output_missing"
    assert a_row["task_p_eligible"] is False

