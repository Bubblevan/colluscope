from __future__ import annotations

import itertools
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from colluscope.m3_mechanism import (
    COUNTERFACTUAL_ARMS, FAMILY_IDS, build_schedule, counterfactual_observation,
    matched_masked_message, matched_neutral_message, parse_complete_allocation,
    select_focal_message,
)


ROOT = Path(__file__).resolve().parents[1]


def test_frozen_schedule_uses_twelve_fresh_seeds_and_all_families_evenly():
    scenarios = json.loads((ROOT / "configs/m1-100-scenarios.json").read_text(encoding="utf-8"))
    splits = json.loads((ROOT / "configs/m1-100-splits.json").read_text(encoding="utf-8"))
    schedule = build_schedule(scenarios, splits)
    assert len(schedule) == 12
    assert len({row["group_id"] for row in schedule}) == 12
    assert {row["scenario_family_id"] for row in schedule} == set(FAMILY_IDS)
    assert [sum(row["scenario_family_id"] == family for row in schedule)
            for family in FAMILY_IDS] == [4, 4, 4]
    prior = {group["seed_block_id"] for partition in ("F0", "F1", "F2", "F3")
             for group in splits[partition]["groups"]}
    assert not ({row["seed_block_id"] for row in schedule} & prior)
    assert schedule == build_schedule(scenarios, splits)
    assert {tuple(row["arm_order"]) for row in schedule} <= set(itertools.permutations(COUNTERFACTUAL_ARMS))
    assert len({tuple(row["arm_order"]) for row in schedule}) > 1
    assert [row["chair"] for row in schedule].count("A") == 4
    assert [row["chair"] for row in schedule].count("B") == 4
    assert [row["chair"] for row in schedule].count("C") == 4


def test_literal_proposal_parser_rejects_incomplete_conflicting_and_non_bijective_maps():
    assert parse_complete_allocation("Suggested map: A=T3; B: T2; C = T1") == {
        "A": "T3", "B": "T2", "C": "T1"}
    assert parse_complete_allocation("A=T3, B=T2") is None
    assert parse_complete_allocation("A=T1, B=T1, C=T3") is None
    assert parse_complete_allocation("A=T1, A=T2, B=T3, C=T2") is None
    assert parse_complete_allocation("Please choose a good allocation.") is None


def test_focal_selection_is_hash_stable_and_uses_only_delivered_eligible_messages():
    first = {"event_id": "message_A", "sender": "A", "recipient": "B", "sent": True,
             "delivered": True, "text": "A=T3, B=T2, C=T1"}
    second = {"event_id": "message_B", "sender": "B", "recipient": "A", "sent": True,
              "delivered": True, "text": "A=T1, B=T3, C=T2"}
    not_delivered = {"event_id": "message_C", "sender": "A", "recipient": "B", "sent": True,
                     "delivered": False, "text": "A=T3, B=T2, C=T1"}
    one = select_focal_message("group-1", [first, second, not_delivered])
    two = select_focal_message("group-1", [not_delivered, second, first])
    assert one == two
    assert one in (first, second)
    assert select_focal_message("group-1", [not_delivered]) is None


class _FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        return SimpleNamespace(ids=re.findall(r"[A-Za-z0-9]+|[^\w\s]", text))


class _FakeCounter:
    tokenizer = _FakeTokenizer()


def test_neutral_and_masked_transformations_are_deterministic_and_do_not_retain_mapping():
    text = "I suggest A=T3, B=T2, C=T1 for the allocation."
    prompt_count = lambda candidate: 100 + len(candidate)
    neutral1 = matched_neutral_message(text, _FakeCounter(), prompt_count)
    neutral2 = matched_neutral_message(text, _FakeCounter(), prompt_count)
    masked1 = matched_masked_message(text, _FakeCounter(), prompt_count)
    masked2 = matched_masked_message(text, _FakeCounter(), prompt_count)
    assert neutral1 == neutral2
    assert masked1 == masked2
    assert parse_complete_allocation(neutral1["text"]) is None
    assert parse_complete_allocation(masked1["text"]) is None
    assert not re.search(r"(?<![A-Za-z0-9_])T[123](?![A-Za-z0-9_])", masked1["text"], re.I)
    assert neutral1["candidate_bank_sha256"]
    assert "message_token_delta" in neutral1 and "prompt_token_delta" in neutral1


def test_counterfactual_prompts_change_only_the_selected_inbound_message():
    proposal = {
        "agent_id": "B",
        "task_spec": {"agents": ["A", "B", "C"], "chair": "A", "quality": {"frozen": True}},
        "your_private_task_score_rule": "frozen private incentive text",
        "your_previous_message_action": {"type": "no_message"},
        "private_peer_channel": {"recipient": "A", "messages_received": [
            {"sender": "A", "text": "A=T3, B=T2, C=T1"},
            {"sender": "C", "text": "constant unrelated context"},
        ]},
    }
    neutral = counterfactual_observation(proposal, "A", "neutral", "I have nothing further to add.")
    masked = counterfactual_observation(proposal, "A", "masked", "A=[MASK], B=[MASK], C=[MASK]")
    no_delivery = counterfactual_observation(proposal, "A", "no_delivery")
    assert proposal["private_peer_channel"]["messages_received"][0]["text"] == "A=T3, B=T2, C=T1"
    assert neutral["private_peer_channel"]["messages_received"][1] == proposal["private_peer_channel"]["messages_received"][1]
    assert masked["private_peer_channel"]["messages_received"][1] == proposal["private_peer_channel"]["messages_received"][1]
    for candidate in (neutral, masked, no_delivery):
        assert candidate["agent_id"] == proposal["agent_id"]
        assert candidate["task_spec"] == proposal["task_spec"]
        assert candidate["your_private_task_score_rule"] == proposal["your_private_task_score_rule"]
        assert candidate["your_previous_message_action"] == proposal["your_previous_message_action"]
        assert "condition_id" not in candidate and "expected_mapping" not in candidate
    assert [row["sender"] for row in no_delivery["private_peer_channel"]["messages_received"]] == ["C"]
    with pytest.raises(ValueError, match="exactly once"):
        counterfactual_observation(proposal, "D", "neutral", "neutral")
