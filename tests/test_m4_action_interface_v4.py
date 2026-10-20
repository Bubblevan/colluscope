import pytest

from colluscope.m4_action_interface_v4 import ActionInterfaceError, extract_action_text, parse_action
from colluscope.m4_live_runtime import M4RequestFailure, _validate_action


@pytest.mark.parametrize("content,expected,source,wrappers", [
    ('{"type":"no_message"}', {"type": "no_message"}, "content_json", 0),
    ('{"type":"send_message","text":"A=T3, B=T2, C=T1"}',
     {"type": "send_message", "text": "A=T3, B=T2, C=T1"}, "content_json", 0),
    ('<think>short reasoning</think>\n{"type":"no_message"}',
     {"type": "no_message"}, "single_leading_think_wrapper", 1),
    ('<think>short reasoning</think>\n{"type":"send_message","text":"proposal"}',
     {"type": "send_message", "text": "proposal"}, "single_leading_think_wrapper", 1),
])
def test_extract_action_variants_and_no_message_is_valid(content, expected, source, wrappers):
    action, receipt = parse_action({"content": content}, "message", _validate_action)
    assert action == expected
    assert receipt["source"] == source
    assert receipt["wrapper_count"] == wrappers


def test_valid_ballot_and_positive_control_after_reasoning_wrapper():
    ballot, _ = parse_action({"content": '<think>r</think>{"type":"ballot","assignment":{"A":"T1","B":"T2","C":"T3"}}'},
                             "ballot", _validate_action)
    control, _ = parse_action({"content": '<think>r</think>{"choice":"T2"}'},
                              "positive_control", _validate_action)
    assert ballot["type"] == "ballot"
    assert control == {"choice": "T2"}


@pytest.mark.parametrize("content", [
    '<think>reasoning {"type":"no_message"}',
    '<think>one</think><think>two</think>{"type":"no_message"}',
    '<think>reasoning</think>{"type":"no_message"} trailing prose',
    'prefix <think>reasoning</think>{"type":"no_message"}',
    '<think>reason</think><think>another wrapper</think>',
    '<think>reason</think>{"type":"no_message","type":"send_message","text":"x"}',
])
def test_wrapper_rejects_missing_duplicate_or_trailing_structure(content):
    with pytest.raises(ActionInterfaceError):
        extract_action_text({"content": content})


@pytest.mark.parametrize("message,kind", [
    ({"content": '<think>r</think>{"type":"ballot","assignment":{"A":"T1","B":"T1","C":"T3"}}'}, "ballot"),
    ({"content": '<think>r</think>{"type":"send_message","text":""}'}, "message"),
    ({"content": '<think>r</think>{"choice":"T9"}'}, "positive_control"),
    ({"content": '<think>r</think>{"type":"no_message","text":"contradictory"}'}, "message"),
])
def test_exact_json_suffix_still_fails_invalid_or_contradictory_action(message, kind):
    with pytest.raises(M4RequestFailure):
        parse_action(message, kind, _validate_action)


def test_reasoning_content_is_never_used_as_action_fallback():
    with pytest.raises(ActionInterfaceError):
        extract_action_text({"content": "", "reasoning_content": '{"type":"no_message"}'})


def test_separated_reasoning_is_hashed_but_not_returned_in_receipt():
    _, receipt = parse_action({"content": '{"type":"no_message"}',
                               "reasoning_content": "private reasoning phrase"}, "message", _validate_action)
    assert receipt["source"] == "content_json"
    assert receipt["reasoning_content_present"] is True
    assert receipt["reasoning_content_sha256"]
    assert "private reasoning phrase" not in str(receipt)


def test_offline_m4_diagnostic_materializes_exact_18_cross_family_requests():
    from scripts.run_m4_interface_diagnostic import _prompts

    rows = _prompts()
    assert len(rows) == 18
    assert {row["action_kind"] for row in rows} == {"message", "ballot", "positive_control"}
    assert all(sum(candidate["action_kind"] == kind for candidate in rows) == 6
               for kind in {"message", "ballot", "positive_control"})
    assert len({row["group"]["scenario_family_id"] for row in rows}) == 6
    assert all("condition_id" not in row["prompt"] and "reference_answer" not in row["prompt"]
               for row in rows)


def test_m4_diagnostic_custom_generation_cap_is_enforced_before_request_freeze(tmp_path):
    import json
    from colluscope import m4_live_runtime as live

    out = tmp_path / "run"
    out.mkdir()
    for index in range(18):
        live.append_jsonl(out / "attempts.jsonl", {"event": "attempt_started", "request_id": str(index)})
    config, *_ = live.load_live_config(live.LIVE_CONFIG_V4)
    client = live.GenerationClient(out=out, config=config, api_key="unused",
                                   token_counter=live._CharacterTokenCounter(),
                                   endpoint="http://127.0.0.1:8081/v1",
                                   max_generation_attempts=18,
                                   transport=lambda *_a, **_k: pytest.fail("generation cap must reject before transport"))
    before = set((out / "requests").glob("*")) if (out / "requests").exists() else set()
    with pytest.raises(live.M4RequestFailure, match="hard M4"):
        client.generate("diagnostic-19", "g", "message", "A", "prompt", {"agent_id": "A"},
                        arm="test")
    after = set((out / "requests").glob("*")) if (out / "requests").exists() else set()
    assert before == after


def test_independent_diagnostic_replay_grammar_and_actions_have_counterexamples():
    from scripts.audit_m4_interface_diagnostic import _extract_action, _strict_json, _valid_action

    text, source = _extract_action({"content": '<think>reason</think>\n{"type":"no_message"}'})
    assert source == "single_leading_think_wrapper"
    assert _valid_action(_strict_json(text), "message")
    assert not _valid_action({"type": "no_message", "text": "extra"}, "message")
    assert not _valid_action({"type": "ballot", "assignment": {"A": "T1", "B": "T1", "C": "T3"}}, "ballot")
    with pytest.raises(ValueError):
        _strict_json('{"type":"no_message","type":"send_message"}')
    with pytest.raises(ValueError):
        _extract_action({"content": '<think>reason {"type":"no_message"}'})


def test_m4_diagnostic_manifest_binds_runner_auditor_and_runtime_sources():
    from scripts.audit_m4_interface_diagnostic import _verify_artifact_hashes
    from scripts.run_m4_interface_diagnostic import ARTIFACT_PATHS, _artifact_hashes

    hashes = _artifact_hashes()
    assert "scripts/run_m4_interface_diagnostic.py" in hashes
    assert "scripts/audit_m4_interface_diagnostic.py" in hashes
    assert "src/colluscope/m4_action_interface_v4.py" in hashes
    _verify_artifact_hashes(hashes)
    hashes["scripts/run_m4_interface_diagnostic.py"] = "0" * 64
    with pytest.raises(ValueError, match="artifact hashes"):
        _verify_artifact_hashes(hashes)
    assert len(ARTIFACT_PATHS) >= 8


def test_v4_sets_deepseek_reasoning_format_at_server_and_request_layers_without_changing_v3():
    from colluscope.m4_live_runtime import LIVE_CONFIG, LIVE_CONFIG_V4, load_live_config

    legacy, *_ = load_live_config(LIVE_CONFIG)
    v4, *_ = load_live_config(LIVE_CONFIG_V4)
    assert legacy["runtime"]["reasoning_format"] == "none"
    assert v4["runtime"]["reasoning_format"] == "deepseek"
    assert v4["action_interface"]["reasoning_format"] == "deepseek"


def test_m4_independent_auditor_requires_http_200_even_when_error_body_is_valid_json():
    from scripts.audit_m4_interface_diagnostic import _http_success

    assert _http_success({"http_status": 200})
    assert not _http_success({"http_status": 500})
    assert not _http_success({"http_status": None})
