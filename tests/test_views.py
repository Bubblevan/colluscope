from copy import deepcopy
import inspect
import json
import re

import pytest

from colluscope.generation import generate_corpus, make_episode
from colluscope.views import (
    VIEW_NAMES, build_all_views, build_view_record, canonical_json,
    evidence_sha256, monitor_evidence, semantic_signature,
)


def _all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _all_strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _all_strings(item)


def test_four_views_apply_type_allowlists_and_share_only_public_rules():
    trace, _ = make_episode("C1", 1)
    views = build_all_views(trace, monitor_can_see_private=False)
    assert set(views) == set(VIEW_NAMES)
    assert all(v["evidence"]["task_spec"] == trace["task_spec"] for v in views.values())
    text_types = {e["type"] for e in views["text_only"]["evidence"]["events"]}
    action_types = {e["type"] for e in views["action_only"]["evidence"]["events"]}
    raw_types = {e["type"] for e in views["raw_fusion"]["evidence"]["events"]}
    assert text_types <= {"message", "reference_assignment"}
    assert action_types <= {"vote", "decision", "outcome"}
    assert raw_types == text_types | action_types
    assert all(e["visibility"] == "public" for e in views["raw_fusion"]["evidence"]["events"])
    assert views["structured_evidence"]["evidence"]["events"] == views["raw_fusion"]["evidence"]["events"]


def test_c2_public_reference_cue_is_not_smuggled_into_shared_action_only_rules():
    c1, _ = make_episode("C1", 2)
    c2, _ = make_episode("C2", 2)
    c1_views = build_all_views(c1, monitor_can_see_private=False)
    c2_views = build_all_views(c2, monitor_can_see_private=False)
    assert c1_views["action_only"]["evidence"]["task_spec"] == c2_views["action_only"]["evidence"]["task_spec"]
    assert all("public_reference_assignment" not in v["evidence"]["task_spec"] for v in c2_views.values())
    assert any(e["type"] == "reference_assignment" for e in c2_views["text_only"]["evidence"]["events"])
    assert all(e["type"] != "reference_assignment" for e in c2_views["action_only"]["evidence"]["events"])
    assert any(e["type"] == "reference_assignment" for e in c2_views["raw_fusion"]["evidence"]["events"])


def test_oracle_labels_and_policy_names_are_absent_from_every_view_record():
    traces, oracles = generate_corpus()
    forbidden = ("mechanism_id", "assigned_coalition", "assigned_channel", "scripted_policy_id",
                 "construction_truth", "outcome_truth", "policy_id", "collusion_success")
    for trace, oracle in zip(traces, oracles, strict=True):
        for record in build_all_views(trace, monitor_can_see_private=False).values():
            serialized = " ".join(_all_strings(record)).lower()
            assert "model_kind" not in record
            assert "scripted" not in serialized
            for marker in forbidden:
                assert marker not in serialized, (trace["episode_id"], marker)
                assert re.search(r"(?<![a-z0-9])c[1-6](?![a-z0-9])", serialized) is None
        # The public route identifier is opaque and never carries C1/C2 labels.
        assert not trace["episode_id"].lower().startswith(tuple(f"{m.lower()}-" for m in "C1 C2 C3 C4 C5 C6".split()))


def test_monitor_projection_api_cannot_accept_oracle_and_oracle_permutation_changes_nothing():
    traces, oracles = generate_corpus()
    trace = traces[0]
    before = build_all_views(trace, monitor_can_see_private=False)
    signature = inspect.signature(monitor_evidence)
    assert "oracle" not in signature.parameters
    changed = deepcopy(oracles)
    for i, oracle in enumerate(reversed(changed)):
        oracle["mechanism_id"] = f"permuted-{i}"
        oracle["assigned_coalition"] = ["C"]
        oracle["assigned_channel"] = "mutated"
        oracle["scripted_policy_id"] = "mutated"
        oracle["construction_truth"] = {"arbitrary": i}
    after = build_all_views(trace, monitor_can_see_private=False)
    assert before == after


def test_c1_c6_have_identical_monitor_evidence_but_different_oracle_mechanisms():
    c1, o1 = make_episode("C1", 3)
    c6, o6 = make_episode("C6", 3)
    assert o1["mechanism_id"] != o6["mechanism_id"]
    public_views_1 = build_all_views(c1, monitor_can_see_private=False)
    public_views_6 = build_all_views(c6, monitor_can_see_private=False)
    for name in VIEW_NAMES:
        assert evidence_sha256(public_views_1[name]) == evidence_sha256(public_views_6[name])
        assert public_views_1[name]["evidence"] == public_views_6[name]["evidence"]
    privileged_1 = build_all_views(c1, monitor_can_see_private=True)
    privileged_6 = build_all_views(c6, monitor_can_see_private=True)
    assert privileged_1["action_only"]["evidence"] == privileged_6["action_only"]["evidence"]
    assert privileged_1["raw_fusion"]["evidence"] != privileged_6["raw_fusion"]["evidence"]


def test_private_agent_channel_and_monitor_permission_are_independent():
    c1, _ = make_episode("C1", 2)  # scripted agents have private messages
    c2, _ = make_episode("C2", 2)  # no private event exists in the trace
    assert any(e["visibility"] == "private" for e in c1["events"])
    assert not any(e["visibility"] == "private" for e in c2["events"])
    hidden = build_all_views(c1, monitor_can_see_private=False)
    allowed = build_all_views(c1, monitor_can_see_private=True)
    assert all(e["visibility"] != "private" for e in hidden["raw_fusion"]["evidence"]["events"])
    assert any(e["visibility"] == "private" for e in allowed["text_only"]["evidence"]["events"])
    assert any(e["visibility"] == "private" for e in allowed["raw_fusion"]["evidence"]["events"])
    assert all(e["visibility"] != "private" for e in allowed["action_only"]["evidence"]["events"])
    assert not build_all_views(c2, monitor_can_see_private=True)["raw_fusion"]["evidence"]["events"] or all(
        e["visibility"] == "public"
        for e in build_all_views(c2, monitor_can_see_private=True)["raw_fusion"]["evidence"]["events"]
    )


def test_structured_findings_have_valid_provenance_and_recompute_only_raw_facts():
    trace, _ = make_episode("C1", 1)
    raw = build_view_record(trace, "raw_fusion", monitor_can_see_private=False)["evidence"]
    structured = build_view_record(trace, "structured_evidence", monitor_can_see_private=False)["evidence"]
    assert structured["task_spec"] == raw["task_spec"]
    assert structured["events"] == raw["events"]
    known_ids = {event["event_id"] for event in raw["events"]}
    assert structured["findings"]
    for finding in structured["findings"]:
        assert finding["supporting_event_ids"]
        assert set(finding["supporting_event_ids"]) <= known_ids
        assert finding["supporting_task_spec_fields"]
    gap = next(f for f in structured["findings"] if f["kind"] == "public_welfare_gap_recomputed")
    assert gap["value"] == 14
    assert "mechanism_id" not in canonical_json(structured).decode()


def _rename_trace(trace, mapping):
    renamed = deepcopy(trace)
    spec = renamed["task_spec"]
    spec["agents"] = [mapping[a] for a in spec["agents"]]
    spec["quality"] = {mapping[a]: row for a, row in spec["quality"].items()}
    if "chair" in spec:
        spec["chair"] = mapping[spec["chair"]]
    if "public_reference_assignment" in spec:
        spec["public_reference_assignment"] = {mapping[a]: t for a, t in spec["public_reference_assignment"].items()}
    for event in renamed["events"]:
        if event["actor"] in mapping:
            event["actor"] = mapping[event["actor"]]
        if "recipients" in event:
            event["recipients"] = [mapping.get(a, a) for a in event["recipients"]]
        content = event["content"]
        for field in ("assignment",):
            if field in content:
                content[field] = {mapping[a]: t for a, t in content[field].items()}
        if "individual_quality" in content:
            content["individual_quality"] = {
                mapping[a]: score for a, score in content["individual_quality"].items()
            }
        if "claim_assignment" in content:
            pass  # positional in the public agent order, which is unchanged
        if isinstance(content.get("text"), str):
            for old, new in mapping.items():
                content["text"] = content["text"].replace(f"{old}=", f"{new}=")
    renamed["final_assignment"] = {mapping[a]: t for a, t in renamed["final_assignment"].items()}
    renamed["public_outcome"]["assignment"] = {
        mapping.get(a, a): t for a, t in renamed["public_outcome"]["assignment"].items()
    }
    renamed["public_outcome"]["individual_quality"] = {
        mapping.get(a, a): score
        for a, score in renamed["public_outcome"]["individual_quality"].items()
    }
    return renamed


@pytest.mark.parametrize("mechanism", ["C1", "C2", "C3", "C4", "C5", "C6"])
def test_renaming_agent_ids_preserves_view_semantics(mechanism):
    trace, _ = make_episode(mechanism, 2)
    renamed = _rename_trace(trace, {"A": "Agent-Z", "B": "Agent-X", "C": "Agent-Y"})
    for name in VIEW_NAMES:
        original_record = build_view_record(trace, name, monitor_can_see_private=False)
        renamed_record = build_view_record(renamed, name, monitor_can_see_private=False)
        assert semantic_signature(original_record) == semantic_signature(renamed_record)


def test_reordering_event_ids_does_not_change_structured_semantics_or_findings():
    trace, _ = make_episode("C3", 4)
    changed = deepcopy(trace)
    for i, event in enumerate(changed["events"]):
        event["event_id"] = f"renamed-event-{100 - i}"
    before = build_view_record(trace, "structured_evidence", monitor_can_see_private=False)
    after = build_view_record(changed, "structured_evidence", monitor_can_see_private=False)
    assert semantic_signature(before) == semantic_signature(after)
    before_findings = [{k: v for k, v in f.items() if k != "supporting_event_ids"}
                       for f in before["evidence"]["findings"]]
    after_findings = [{k: v for k, v in f.items() if k != "supporting_event_ids"}
                      for f in after["evidence"]["findings"]]
    assert before_findings == after_findings


def test_bad_schema_duplicate_ids_and_missing_events_fail_explicitly():
    trace, _ = make_episode("C5", 1)
    bad_version = deepcopy(trace)
    bad_version["schema_version"] = "2.0"
    with pytest.raises(ValueError, match="schema version"):
        monitor_evidence(bad_version, "raw_fusion")
    duplicate = deepcopy(trace)
    duplicate["events"][1]["event_id"] = duplicate["events"][0]["event_id"]
    with pytest.raises(ValueError, match="unique"):
        monitor_evidence(duplicate, "raw_fusion")
    missing = deepcopy(trace)
    missing["events"] = []
    with pytest.raises(ValueError, match="non-empty"):
        monitor_evidence(missing, "raw_fusion")


@pytest.mark.parametrize("view", VIEW_NAMES)
def test_every_projection_rejects_missing_outcome_or_illegal_action(view):
    trace, _ = make_episode("C1", 2)
    missing_outcome = deepcopy(trace)
    missing_outcome["events"] = [e for e in missing_outcome["events"] if e["type"] != "outcome"]
    with pytest.raises(ValueError, match="decision and one outcome"):
        monitor_evidence(missing_outcome, view)
    invalid_vote = deepcopy(trace)
    vote = next(e for e in invalid_vote["events"] if e["type"] == "vote")
    vote["content"]["assignment"] = {"A": "T1", "B": "T1", "C": "T3"}
    with pytest.raises(ValueError, match="duplicate or unknown assigned tasks"):
        monitor_evidence(invalid_vote, view)


def test_monitor_permission_requires_an_explicit_boolean():
    trace, _ = make_episode("C1", 2)
    with pytest.raises(TypeError):
        monitor_evidence(trace, "raw_fusion", monitor_can_see_private="yes")
