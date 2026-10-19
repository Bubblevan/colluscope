"""Read the GGUF header and tokenizer metadata without loading model tensors.

This is intentionally a narrow metadata reader for provenance and local
tokenizer construction. It never seeks into or decodes tensor payloads.
"""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO


class GGUFFormatError(ValueError):
    """The file does not contain a supported, complete GGUF metadata header."""


_SCALAR_FORMATS: dict[int, tuple[str, int]] = {
    0: ("uint8", 1),
    1: ("int8", 1),
    2: ("uint16", 2),
    3: ("int16", 2),
    4: ("uint32", 4),
    5: ("int32", 4),
    6: ("float32", 4),
    7: ("bool", 1),
    10: ("uint64", 8),
    11: ("int64", 8),
    12: ("float64", 8),
}
_TYPE_NAMES = {**{key: value[0] for key, value in _SCALAR_FORMATS.items()}, 8: "string", 9: "array"}
_MAX_METADATA_ITEMS = 20_000_000
_MAX_STRING_BYTES = 1_073_741_824


@dataclass(frozen=True)
class GGUFArray:
    element_type: str
    length: int
    sha256: str
    values: tuple[Any, ...] | None = None


@dataclass(frozen=True)
class GGUFDocument:
    path: str
    file_size_bytes: int
    version: int
    tensor_count: int
    metadata_kv_count: int
    metadata: dict[str, Any]


def _read_exact(stream: BinaryIO, size: int) -> bytes:
    if size < 0 or size > _MAX_STRING_BYTES:
        raise GGUFFormatError(f"invalid GGUF field size: {size}")
    data = stream.read(size)
    if len(data) != size:
        raise GGUFFormatError("truncated GGUF metadata header")
    return data


def _uint64(stream: BinaryIO) -> int:
    return struct.unpack("<Q", _read_exact(stream, 8))[0]


def _uint32(stream: BinaryIO) -> int:
    return struct.unpack("<I", _read_exact(stream, 4))[0]


def _string(stream: BinaryIO) -> tuple[str, bytes]:
    prefix = _read_exact(stream, 8)
    size = struct.unpack("<Q", prefix)[0]
    if size > _MAX_STRING_BYTES:
        raise GGUFFormatError(f"GGUF string exceeds safety bound: {size}")
    raw = _read_exact(stream, size)
    try:
        value = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise GGUFFormatError("GGUF metadata string is not valid UTF-8") from exc
    return value, prefix + raw


def _scalar(stream: BinaryIO, type_id: int) -> tuple[Any, bytes]:
    if type_id == 8:
        return _string(stream)
    if type_id not in _SCALAR_FORMATS:
        raise GGUFFormatError(f"unsupported GGUF metadata type id: {type_id}")
    name, size = _SCALAR_FORMATS[type_id]
    raw = _read_exact(stream, size)
    if type_id == 7:
        value = raw[0]
        if value not in (0, 1):
            raise GGUFFormatError(f"invalid GGUF boolean value: {value}")
        return bool(value), raw
    fmt = {1: "b", 2: "H", 3: "h", 4: "I", 5: "i", 6: "f",
           10: "Q", 11: "q", 12: "d"}[type_id]
    return struct.unpack("<" + fmt, raw)[0], raw


def read_gguf(path: Path, *, capture_arrays: frozenset[str] = frozenset()) -> GGUFDocument:
    """Parse GGUF header metadata; capture selected arrays, hash every array.

    Array hashes cover the encoded array elements (including each string's
    length prefix), which makes tokenizer provenance independently checkable
    without putting the full vocabulary into a report.
    """
    path = Path(path)
    file_size = path.stat().st_size
    with path.open("rb") as stream:
        if _read_exact(stream, 4) != b"GGUF":
            raise GGUFFormatError("GGUF magic bytes are absent")
        version = _uint32(stream)
        if version not in {2, 3}:
            raise GGUFFormatError(f"unsupported GGUF version: {version}")
        tensor_count = _uint64(stream)
        metadata_count = _uint64(stream)
        if metadata_count > 1_000_000 or tensor_count > 10_000_000:
            raise GGUFFormatError("GGUF header counts exceed safety bounds")

        metadata: dict[str, Any] = {}
        for _ in range(metadata_count):
            key, _key_raw = _string(stream)
            if key in metadata:
                raise GGUFFormatError(f"duplicate GGUF metadata key: {key}")
            type_id = _uint32(stream)
            if type_id != 9:
                value, _raw = _scalar(stream, type_id)
                metadata[key] = value
                continue

            element_type_id = _uint32(stream)
            if element_type_id == 9 or element_type_id not in _TYPE_NAMES:
                raise GGUFFormatError(f"unsupported GGUF array element type: {element_type_id}")
            count = _uint64(stream)
            if count > _MAX_METADATA_ITEMS:
                raise GGUFFormatError(f"GGUF array exceeds safety bound: {key} ({count})")
            digest = hashlib.sha256()
            values: list[Any] | None = [] if key in capture_arrays else None
            for _item in range(count):
                value, raw = _scalar(stream, element_type_id)
                digest.update(raw)
                if values is not None:
                    values.append(value)
            metadata[key] = GGUFArray(_TYPE_NAMES[element_type_id], count, digest.hexdigest(),
                                      tuple(values) if values is not None else None)

        # Metadata always precedes tensor information. We deliberately do not
        # parse or map any tensor descriptors or weight bytes.
        if stream.tell() > file_size:
            raise GGUFFormatError("GGUF metadata offset exceeds the file size")

    return GGUFDocument(str(path), file_size, version, tensor_count, metadata_count, metadata)


def _summarize_value(value: Any) -> Any:
    if isinstance(value, GGUFArray):
        return {"type": "array", "element_type": value.element_type,
                "length": value.length, "sha256": value.sha256}
    if isinstance(value, str):
        return {"type": "string", "length_utf8_bytes": len(value.encode("utf-8")),
                "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest()}
    return value


def summarize_gguf(document: GGUFDocument) -> dict[str, Any]:
    """Return a compact, JSON-safe identity summary for evidence manifests."""
    keys = (
        "general.architecture", "general.name", "general.file_type",
        "general.quantization_version", "tokenizer.ggml.model", "tokenizer.ggml.pre",
        "tokenizer.ggml.tokens", "tokenizer.ggml.merges", "tokenizer.ggml.token_type",
        "tokenizer.ggml.bos_token_id", "tokenizer.ggml.eos_token_id",
        "tokenizer.ggml.unknown_token_id", "tokenizer.ggml.add_bos_token",
        "tokenizer.ggml.add_eos_token", "tokenizer.chat_template",
    )
    metadata = {key: _summarize_value(document.metadata[key])
                for key in keys if key in document.metadata}
    return {
        "path": document.path,
        "file_size_bytes": document.file_size_bytes,
        "gguf_version": document.version,
        "tensor_count": document.tensor_count,
        "metadata_kv_count": document.metadata_kv_count,
        "metadata": metadata,
        "weights_loaded": False,
    }


def canonical_summary_json(document: GGUFDocument) -> str:
    return json.dumps(summarize_gguf(document), ensure_ascii=False, sort_keys=True, indent=2)
