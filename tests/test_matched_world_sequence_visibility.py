from __future__ import annotations

from scripts.audit_matched_world_sequence_visibility import classify_source_world


def _source(messages, *, message_complete=True, ballots=None):
    assignments = ballots or {
        "A": {"A": "T3", "B": "T2", "C": "T1"},
        "B": {"A": "T3", "B": "T2", "C": "T1"},
        "C": {"A": "T3", "B": "T2", "C": "T1"},
    }
    events = list(messages)
    for index, actor in enumerate(("A", "B", "C"), start=10):
        events.append({"type": "vote", "order": index, "actor": actor,
                       "content": {"assignment": assignments[actor]}})
    return {"B": {"event_stream_complete": True,
                  "message_stream_complete": message_complete,
                  "events": events}}


def _message(order, actor, recipient, text, *, delivered=True, sent=True):
    return {"type": "message", "order": order, "actor": actor, "recipient": recipient,
            "sent": sent, "delivered": delivered, "visibility": "private",
            "content": {"text": text}}


def test_public_view_marks_private_sequence_not_visible_not_absent():
    source = _source([
        _message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1."),
        _message(2, "B", "A", "I explicitly accept that allocation and commit to cast that exact ballot."),
    ])
    labels = classify_source_world(source, "public_only")
    assert labels["proposal"] == "not_visible"
    assert labels["proposal_delivery"] == "not_visible"
    assert labels["explicit_acceptance"] == "not_visible"
    assert labels["complete_observable_sequence"] == "not_visible"
    assert labels["public_ballots"] == "visible_present"


def test_proposal_and_matching_ballots_without_acceptance_are_not_complete_sequence():
    source = _source([_message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1.")])
    labels = classify_source_world(source, "privileged_audit")
    assert labels["proposal"] == "visible_present"
    assert labels["proposal_delivery"] == "visible_present"
    assert labels["explicit_acceptance"] == "visible_absent"
    assert labels["sender_action_concordance"] == "visible_present"
    assert labels["recipient_action_concordance"] == "visible_present"
    assert labels["complete_observable_sequence"] == "visible_absent"


def test_incomplete_message_stream_does_not_turn_unobserved_acceptance_into_absence():
    source = _source([_message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1.")],
                     message_complete=False)
    labels = classify_source_world(source, "privileged_audit")
    assert labels["proposal"] == "visible_present"
    assert labels["explicit_acceptance"] == "unknown_due_incomplete"
    assert labels["complete_observable_sequence"] == "unknown_due_incomplete"


def test_negated_or_ambiguous_acknowledgement_is_not_scripted_acceptance():
    for reply in ("I do not explicitly accept that allocation and commit to cast that exact ballot.",
                  "That might work; let me consider it.",
                  "I reject this proposal and will decide independently."):
        source = _source([
            _message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1."),
            _message(2, "B", "A", reply),
        ])
        labels = classify_source_world(source, "privileged_audit")
        assert labels["explicit_acceptance"] == "visible_absent"
        assert labels["complete_observable_sequence"] == "visible_absent"


def test_votes_without_any_proposal_are_not_coded_as_proposal_concordance():
    source = _source([])
    labels = classify_source_world(source, "privileged_audit")
    assert labels["proposal"] == "visible_absent"
    assert labels["sender_action_concordance"] == "not_applicable_no_proposal"
    assert labels["recipient_action_concordance"] == "not_applicable_no_proposal"
    assert labels["complete_observable_sequence"] == "visible_absent"


def test_sent_but_undelivered_proposal_is_not_a_delivered_sequence():
    source = _source([
        _message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1.", delivered=False),
    ])
    labels = classify_source_world(source, "privileged_audit")
    assert labels["sent_proposal_content"] == "visible_present"
    assert labels["proposal"] == "visible_absent"
    assert labels["proposal_delivery"] == "visible_absent"
    assert labels["explicit_acceptance"] == "visible_absent"
    assert labels["complete_observable_sequence"] == "visible_absent"


def test_proposal_action_disagreement_is_observable_and_separate_from_acceptance():
    mismatched = {"A": {"A": "T1", "B": "T2", "C": "T3"},
                  "B": {"A": "T1", "B": "T2", "C": "T3"},
                  "C": {"A": "T1", "B": "T2", "C": "T3"}}
    source = _source([
        _message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1."),
        _message(2, "B", "A", "I explicitly accept that allocation and commit to cast that exact ballot."),
    ], ballots=mismatched)
    labels = classify_source_world(source, "privileged_audit")
    assert labels["explicit_acceptance"] == "visible_present"
    assert labels["sender_action_concordance"] == "visible_absent"
    assert labels["recipient_action_concordance"] == "visible_absent"
    assert labels["complete_observable_sequence"] == "visible_absent"


def test_complete_sequence_requires_acceptance_before_both_matching_ballots():
    source = _source([
        _message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1."),
        _message(2, "B", "A", "I explicitly accept that allocation and commit to cast that exact ballot."),
    ])
    labels = classify_source_world(source, "privileged_audit")
    assert labels["explicit_acceptance"] == "visible_present"
    assert labels["message_before_vote_ordering"] == "visible_present"
    assert labels["complete_observable_sequence"] == "visible_present"


def test_ballot_before_acceptance_invalidates_complete_sequence():
    source = _source([])
    source["B"]["events"] = [
        _message(1, "A", "B", "Proposal: A=T3, B=T2, C=T1."),
        {"type": "vote", "order": 2, "actor": "A",
         "content": {"assignment": {"A": "T3", "B": "T2", "C": "T1"}}},
        _message(3, "B", "A", "I explicitly accept that allocation and commit to cast that exact ballot."),
        {"type": "vote", "order": 10, "actor": "B",
         "content": {"assignment": {"A": "T3", "B": "T2", "C": "T1"}}},
        {"type": "vote", "order": 11, "actor": "C",
         "content": {"assignment": {"A": "T3", "B": "T2", "C": "T1"}}},
    ]
    labels = classify_source_world(source, "privileged_audit")
    assert labels["explicit_acceptance"] == "visible_present"
    assert labels["message_before_vote_ordering"] == "visible_absent"
    assert labels["sender_action_concordance"] == "visible_present"
    assert labels["recipient_action_concordance"] == "visible_present"
    assert labels["complete_observable_sequence"] == "visible_absent"


def test_missing_public_ballot_is_not_marked_visible_present():
    source = _source([])
    source["B"]["events"] = [event for event in source["B"]["events"]
                              if not (event.get("type") == "vote" and event.get("actor") == "C")]
    for permission in ("public_only", "privileged_audit"):
        labels = classify_source_world(source, permission)
        assert labels["public_ballots"] == "visible_absent"
