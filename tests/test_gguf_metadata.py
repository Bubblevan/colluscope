from __future__ import annotations

import hashlib
import json
import struct

import pytest

from colluscope.gguf_metadata import GGUFArray, GGUFFormatError, read_gguf, summarize_gguf


def _gguf_string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack("<Q", len(encoded)) + encoded


def _entry(key: str, type_id: int, value: bytes) -> bytes:
    return _gguf_string(key) + struct.pack("<I", type_id) + value


def _string_array(items: list[str]) -> bytes:
    return struct.pack("<IQ", 8, len(items)) + b"".join(_gguf_string(item) for item in items)


def _int32_array(items: list[int]) -> bytes:
    return struct.pack("<IQ", 5, len(items)) + b"".join(struct.pack("<i", item) for item in items)


def _fixture(entries: list[bytes], version: int = 3) -> bytes:
    return b"GGUF" + struct.pack("<IQQ", version, 0, len(entries)) + b"".join(entries)


def test_reader_extracts_and_hashes_only_requested_arrays(tmp_path):
    tokens = ["<unk>", "hello", "world"]
    merges = ["he llo"]
    fixture = _fixture([
        _entry("general.architecture", 8, _gguf_string("qwen3")),
        _entry("tokenizer.ggml.model", 8, _gguf_string("gpt2")),
        _entry("tokenizer.ggml.tokens", 9, _string_array(tokens)),
        _entry("tokenizer.ggml.merges", 9, _string_array(merges)),
        _entry("tokenizer.ggml.token_type", 9, _int32_array([2, 1, 1])),
        _entry("tokenizer.chat_template", 8, _gguf_string("{{ messages|length }}")),
    ])
    path = tmp_path / "tiny.gguf"
    path.write_bytes(fixture)

    doc = read_gguf(path, capture_arrays=frozenset({"tokenizer.ggml.tokens"}))
    assert doc.version == 3
    assert doc.tensor_count == 0
    assert doc.metadata["general.architecture"] == "qwen3"
    token_array = doc.metadata["tokenizer.ggml.tokens"]
    merge_array = doc.metadata["tokenizer.ggml.merges"]
    assert isinstance(token_array, GGUFArray)
    assert token_array.values == tuple(tokens)
    assert token_array.length == 3
    assert token_array.sha256 == hashlib.sha256(
        _gguf_string(tokens[0]) + _gguf_string(tokens[1]) + _gguf_string(tokens[2])).hexdigest()
    assert merge_array.values is None
    assert merge_array.length == 1
    assert summarize_gguf(doc)["weights_loaded"] is False


def test_reader_rejects_bad_magic_duplicate_keys_unsupported_type_and_truncation(tmp_path):
    path = tmp_path / "bad.gguf"
    path.write_bytes(b"NOPE" + struct.pack("<IQQ", 3, 0, 0))
    with pytest.raises(GGUFFormatError, match="magic"):
        read_gguf(path)

    duplicate = _entry("general.architecture", 8, _gguf_string("qwen3"))
    path.write_bytes(_fixture([duplicate, duplicate]))
    with pytest.raises(GGUFFormatError, match="duplicate"):
        read_gguf(path)

    unsupported = _entry("bad", 99, b"")
    path.write_bytes(_fixture([unsupported]))
    with pytest.raises(GGUFFormatError, match="unsupported"):
        read_gguf(path)

    path.write_bytes(_fixture([_entry("short", 8, struct.pack("<Q", 20) + b"x")]))
    with pytest.raises(GGUFFormatError, match="truncated"):
        read_gguf(path)


def test_summary_reports_template_digest_without_embedding_raw_template(tmp_path):
    template = "{{ bos_token }}{{ messages[0].content }}"
    path = tmp_path / "template.gguf"
    path.write_bytes(_fixture([
        _entry("tokenizer.chat_template", 8, _gguf_string(template)),
    ]))
    summary = summarize_gguf(read_gguf(path))
    template_summary = summary["metadata"]["tokenizer.chat_template"]
    assert template_summary == {
        "type": "string", "length_utf8_bytes": len(template.encode("utf-8")),
        "sha256": hashlib.sha256(template.encode("utf-8")).hexdigest(),
    }
    assert template not in json.dumps(summary)
