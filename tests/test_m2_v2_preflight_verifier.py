from __future__ import annotations

from scripts.verify_m2_v2_preflight import _extract_events, _forbidden_keys


def test_independent_preflight_guard_finds_nested_research_metadata():
    assert _forbidden_keys({"messages": [{"content": {"condition_id": "hidden"}}]}) == [
        "messages[0].content.condition_id"]
    assert _forbidden_keys({"task_spec": {"public_task": "visible"}}) == []


def test_independent_preflight_event_parser_matches_raw_and_structured_views():
    task = {"task_id": "public-task", "tasks": ["T1"]}
    event = {"event_id": "P01", "type": "ballot"}
    raw = "Public task specification:\n{" + '"task_id":"public-task","tasks":["T1"]}' + \
        "\nOrdered permitted evidence events:\n{" + '"event_id":"P01","type":"ballot"}'
    parsed_task, parsed_events = _extract_events("Evidence object:\n" + raw, "raw_fusion")
    assert parsed_task == task and parsed_events == [event]

    import json
    structured = json.dumps({"task_spec": task, "events": [event]})
    parsed_task, parsed_events = _extract_events("Evidence object:\n" + structured, "action_only")
    assert parsed_task == task and parsed_events == [event]
