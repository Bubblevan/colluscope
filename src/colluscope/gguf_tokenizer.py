"""Local Qwen BPE and GGUF chat-template counter for llama.cpp requests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jinja2
import tokenizers
from jinja2 import Environment, StrictUndefined
from tokenizers import AddedToken, Tokenizer, decoders, models, pre_tokenizers

from .gguf_metadata import GGUFArray, read_gguf


_CAPTURED_ARRAYS = frozenset({
    "tokenizer.ggml.tokens", "tokenizer.ggml.merges", "tokenizer.ggml.token_type",
})


class GGUFChatTokenCounter:
    """Build a tokenizer from GGUF metadata, without reading model tensors.

    The implementation is restricted to the GGUF `gpt2`/`qwen2` tokenizer
    metadata found in the target Qwen3 artifact. Parity with the installed
    llama.cpp renderer/tokenizer must still be established by the approved
    live preflight before the count is used for a research run.
    """

    def __init__(self, path: Path, *, expected_artifact_sha256: str | None = None):
        self.path = Path(path)
        self.tokenizers_library_version = tokenizers.__version__
        self.jinja2_library_version = jinja2.__version__
        self.document = read_gguf(self.path, capture_arrays=_CAPTURED_ARRAYS)
        self.metadata = self.document.metadata
        self.architecture = self._string("general.architecture")
        tokenizer_model = self._string("tokenizer.ggml.model")
        tokenizer_pre = self._string("tokenizer.ggml.pre")
        if tokenizer_model != "gpt2" or tokenizer_pre != "qwen2":
            raise ValueError(f"unsupported GGUF tokenizer metadata: {tokenizer_model}/{tokenizer_pre}")

        token_array = self._array("tokenizer.ggml.tokens", "string")
        merge_array = self._array("tokenizer.ggml.merges", "string")
        type_array = self._array("tokenizer.ggml.token_type", "int32")
        if token_array.values is None or merge_array.values is None or type_array.values is None:
            raise ValueError("GGUF tokenizer arrays were not captured")
        if len(token_array.values) != len(type_array.values):
            raise ValueError("GGUF tokenizer token/type array lengths differ")
        if len(set(token_array.values)) != len(token_array.values):
            raise ValueError("GGUF tokenizer vocabulary contains duplicate token strings")

        vocab = {piece: index for index, piece in enumerate(token_array.values)}
        merges: list[tuple[str, str]] = []
        for merge in merge_array.values:
            if not isinstance(merge, str) or " " not in merge:
                raise ValueError("GGUF BPE merge entry is malformed")
            merges.append(tuple(merge.split(" ", 1)))
        self.tokenizer = Tokenizer(models.BPE(vocab, merges, unk_token=None))
        self.tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
        self.tokenizer.decoder = decoders.ByteLevel()
        special_tokens = [AddedToken(piece, normalized=False, special=True)
                          for piece, token_type in zip(token_array.values, type_array.values)
                          if token_type in (3, 4)]
        self.tokenizer.add_special_tokens(special_tokens)

        self.chat_template = self._string("tokenizer.chat_template")
        self.chat_template_sha256 = hashlib.sha256(self.chat_template.encode("utf-8")).hexdigest()
        tokenizer_identity = {
            "model": tokenizer_model,
            "pre": tokenizer_pre,
            "tokens_sha256": token_array.sha256,
            "merges_sha256": merge_array.sha256,
            "token_type_sha256": type_array.sha256,
            "bos_token_id": self.metadata.get("tokenizer.ggml.bos_token_id"),
            "eos_token_id": self.metadata.get("tokenizer.ggml.eos_token_id"),
            "add_bos_token": self.metadata.get("tokenizer.ggml.add_bos_token", False),
        }
        self.tokenizer_sha256 = hashlib.sha256(
            json.dumps(tokenizer_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.tokenizer_id = f"gguf-embedded:{self.architecture}:{tokenizer_model}/{tokenizer_pre}"
        self.tokenizer_revision = f"sha256:{self.tokenizer_sha256}"
        self.artifact_sha256 = self._hash_file(self.path)
        if expected_artifact_sha256 is not None and self.artifact_sha256 != expected_artifact_sha256.lower():
            raise ValueError("GGUF artifact SHA256 differs from the frozen model manifest")

        self._bos_token_id = self.metadata.get("tokenizer.ggml.bos_token_id")
        self._add_bos = self.metadata.get("tokenizer.ggml.add_bos_token", False) is True
        if self._add_bos and (not isinstance(self._bos_token_id, int) or
                              not 0 <= self._bos_token_id < len(token_array.values)):
            raise ValueError("GGUF BOS metadata is inconsistent with its token vocabulary")

        self._jinja = Environment(undefined=StrictUndefined, autoescape=False)
        self._jinja.globals["raise_exception"] = self._raise_template_exception

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _raise_template_exception(message: str) -> None:
        raise ValueError(f"GGUF chat template rejected the request: {message}")

    def _string(self, key: str) -> str:
        value = self.metadata.get(key)
        if not isinstance(value, str):
            raise ValueError(f"required GGUF string metadata is absent: {key}")
        return value

    def _array(self, key: str, element_type: str) -> GGUFArray:
        value: Any = self.metadata.get(key)
        if not isinstance(value, GGUFArray) or value.element_type != element_type:
            raise ValueError(f"required GGUF array metadata is absent or malformed: {key}")
        return value

    def render_chat(self, messages: list[dict[str, str]], *, enable_thinking: bool = False) -> str:
        if len(messages) != 2 or [row.get("role") for row in messages] != ["system", "user"]:
            raise ValueError("frozen M1-P0 role mapping must be exactly system then user")
        if any(set(row) != {"role", "content"} or not isinstance(row["content"], str)
               for row in messages):
            raise ValueError("frozen M1-P0 messages must contain only role and string content")
        context = {
            "messages": messages,
            "add_generation_prompt": True,
            "enable_thinking": enable_thinking,
            "tools": [],
        }
        rendered = self._jinja.from_string(self.chat_template).render(**context)
        if not rendered:
            raise ValueError("GGUF chat template rendered an empty prompt")
        return rendered

    def encode_chat(self, messages: list[dict[str, str]], *, enable_thinking: bool = False) -> list[int]:
        rendered = self.render_chat(messages, enable_thinking=enable_thinking)
        token_ids = self.tokenizer.encode(rendered, add_special_tokens=False).ids
        if self._add_bos and (not token_ids or token_ids[0] != self._bos_token_id):
            token_ids.insert(0, self._bos_token_id)
        return token_ids

    def count_chat_tokens(self, messages: list[dict[str, str]]) -> int:
        return len(self.encode_chat(messages, enable_thinking=False))
