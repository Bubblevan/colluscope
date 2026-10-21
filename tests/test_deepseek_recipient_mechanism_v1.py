from __future__ import annotations

import json
from pathlib import Path
import sys

from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from colluscope.deepseek_recipient_mechanism_v1 import (  # noqa: E402
    TOKENIZER_SHA256, build_schedule, generate_contexts, messages_for,
    token_count, validate_semantic,
)
from run_deepseek_recipient_mechanism_v1 import (  # noqa: E402
    _contains_template_control_literal, _prompt_family_parity,
)


def test_twenty_contexts_have_unique_optimum_and_matched_x_y_outcomes():
    contexts = generate_contexts()
    assert len(contexts) == 20
    assert sum(c["focal"] == "A" for c in contexts) == 10
    for context in contexts:
        best = max(row["public_welfare"] for row in context["permutations"])
        assert sum(row["public_welfare"] == best for row in context["permutations"]) == 1
        assert context["x_welfare"] == context["y_welfare"] < best
        assert context["focal_x_score"] == context["matrix"][context["focal"]][context["y"][context["focal"]]]
        assert context["focal_x_score"] < context["focal_optimum_score"]


def test_schedule_is_exact_and_repeat_rows_are_true_prompt_duplicates():
    contexts = generate_contexts()
    rows = build_schedule(contexts)
    assert len(rows) == 804
    assert len({r["request_id"] for r in rows}) == 804
    assert {r["kind"]: sum(x["kind"] == r["kind"] for x in rows) for r in rows} == {
        "baseline": 20, "stage": 120, "ballot": 600, "positive_control": 40, "repeat": 24,
    }
    context = contexts[0]
    original = next(r for r in rows if r["request_id"] == f"{context['context_id']}-ballot-shared-actual-x")
    original_messages, _ = messages_for(original, context, {
        f"{context['context_id']}-baseline": '{"choice":"1"}',
        f"{context['context_id']}-stage-shared-actual": '{"action":"no_message","text":""}',
    })
    serialized = json.dumps(original_messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    for repeat in [r for r in rows if r["kind"] == "repeat" and r["context_id"] == context["context_id"]]:
        repeat_messages, _ = messages_for(repeat, context, {
            f"prompt:{original['request_id']}": serialized,
        })
        assert repeat_messages == original_messages


def test_dynamic_full_prompt_token_parity_and_control_token_rejection():
    path = ROOT / ".cache/deepseek-recipe/tokenizer-v41.json"
    assert __import__("hashlib").sha256(path.read_bytes()).hexdigest() == TOKENIZER_SHA256
    tokenizer = Tokenizer.from_file(str(path))
    contexts = generate_contexts()
    rows = build_schedule(contexts)
    tested = 0
    for context in contexts:
        for reward in ("none", "focal", "shared"):
            for history in ("actual", "neutral"):
                base_outputs = {
                    f"{context['context_id']}-baseline": '{"choice":"2"}',
                    f"{context['context_id']}-stage-{reward}-{history}":
                        '{"action":"send_message","text":"I would allocate the tasks this way."}',
                }
                row = next(r for r in rows if r["kind"] == "ballot" and r["context_id"] == context["context_id"]
                           and r["reward"] == reward and r["history"] == history and r["incoming"] == "x")
                ok, counts = _prompt_family_parity(tokenizer, row, context, base_outputs)
                assert ok, counts
                tested += 1
    assert tested == 120
    assert not _contains_template_control_literal([{"role": "assistant", "content": "ordinary"}])
    assert _contains_template_control_literal([{"role": "assistant", "content": "<｜Assistant｜>"}])


def test_no_message_is_valid_but_inconsistent_action_is_not_repaired():
    row = {"kind": "stage"}
    assert validate_semantic(row, {"action": "no_message", "text": ""}) == {
        "action": "no_message", "text": "",
    }
    assert validate_semantic(row, {"action": "send_message", "text": "Proposal: choose allocation 2."})["action"] == "send_message"
    try:
        validate_semantic(row, {"action": "no_message", "text": "I agree."})
    except Exception:
        pass
    else:
        raise AssertionError("inconsistent no_message text was accepted")

