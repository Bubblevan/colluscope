from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest
from tokenizers.pre_tokenizers import ByteLevel

from colluscope.gguf_tokenizer import GGUFChatTokenCounter
from test_gguf_metadata import _entry, _fixture, _gguf_string, _int32_array, _string_array


def _tiny_tokenizer_gguf(path):
    special = ["<|im_start|>", "<|im_end|>", "<|assistant|>", "<|notthink|>"]
    alphabet = sorted(ByteLevel.alphabet())
    pieces = alphabet + special
    kinds = [1] * len(alphabet) + [3] * len(special)
    template = (
        "{% for message in messages %}<|im_start|>{{ message.role }}:{{ message.content }}"
        "<|im_end|>{% endfor %}{% if add_generation_prompt %}<|assistant|>"
        "{% if enable_thinking is false %}<|notthink|>{% endif %}{% endif %}"
    )
    entries = [
        _entry("general.architecture", 8, _gguf_string("qwen3")),
        _entry("tokenizer.ggml.model", 8, _gguf_string("gpt2")),
        _entry("tokenizer.ggml.pre", 8, _gguf_string("qwen2")),
        _entry("tokenizer.ggml.tokens", 9, _string_array(pieces)),
        _entry("tokenizer.ggml.merges", 9, _string_array([])),
        _entry("tokenizer.ggml.token_type", 9, _int32_array(kinds)),
        _entry("tokenizer.chat_template", 8, _gguf_string(template)),
        _entry("tokenizer.ggml.add_bos_token", 7, b"\x00"),
    ]
    path.write_bytes(_fixture(entries))


def test_gguf_counter_renders_frozen_roles_and_counts_from_embedded_bpe(tmp_path):
    path = tmp_path / "counter.gguf"
    _tiny_tokenizer_gguf(path)
    counter = GGUFChatTokenCounter(path)
    messages = [{"role": "system", "content": "rules"}, {"role": "user", "content": "task"}]

    rendered = counter.render_chat(messages, enable_thinking=False)
    assert rendered == "<|im_start|>system:rules<|im_end|><|im_start|>user:task<|im_end|><|assistant|><|notthink|>"
    assert counter.count_chat_tokens(messages) == len(counter.encode_chat(messages))
    assert counter.count_chat_tokens(messages) > 0
    assert len(counter.tokenizer_sha256) == len(counter.chat_template_sha256) == 64
    assert counter.tokenizer_revision == f"sha256:{counter.tokenizer_sha256}"


def test_counter_rejects_role_drift_and_artifact_digest_mismatch(tmp_path):
    path = tmp_path / "counter.gguf"
    _tiny_tokenizer_gguf(path)
    counter = GGUFChatTokenCounter(path)
    with pytest.raises(ValueError, match="role mapping"):
        counter.render_chat([{"role": "user", "content": "task"}], enable_thinking=False)
    with pytest.raises(ValueError, match="SHA256"):
        GGUFChatTokenCounter(path, expected_artifact_sha256="0" * 64)


def test_qwen2_regex_matches_retained_llama_cpp_tokenizer_counterexample():
    root = Path(__file__).resolve().parents[1]
    model = Path(r"E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf")
    evidence = root / "runs/m1_p0_local/25ep-pilot-20261019/run/preflight/requests.jsonl"
    if not model.is_file() or not evidence.is_file():
        pytest.skip("requires the frozen local GGUF and retained live /tokenize counterexample")

    rows = [json.loads(line) for line in evidence.read_text(encoding="utf-8").splitlines()]
    template_row = next(row for row in rows if row["request_id"] == "preflight-template")
    tokenize_row = next(row for row in rows if row["request_id"] == "preflight-tokenize")
    server_render = json.loads(template_row["raw_response"])["prompt"]
    server_tokens = json.loads(tokenize_row["raw_response"])["tokens"]
    counter = GGUFChatTokenCounter(
        model, expected_artifact_sha256="d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785")
    body = json.loads(tokenize_row["request_body"])

    local_tokens = counter.tokenizer.encode(body["content"], add_special_tokens=False).ids
    assert body["content"] == server_render
    assert local_tokens == server_tokens

    # Counterexample: the previous generic GPT-2 ByteLevel pre-tokenizer does
    # not match llama.cpp's qwen2 regex despite using the same GGUF BPE table.
    counter.tokenizer.pre_tokenizer = ByteLevel(add_prefix_space=False, use_regex=True)
    generic_gpt2_tokens = counter.tokenizer.encode(body["content"], add_special_tokens=False).ids
    assert generic_gpt2_tokens != server_tokens
