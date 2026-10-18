"""Pre-registered, metadata-only scenario/seed grouping for later studies.

This module assigns dataset partitions; it is not used by the M0 generator or
monitor projections. Group keys and split names must stay outside monitor input.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Iterable

SPLIT_VERSION = "colluscope-m1-split-v1"
SPLIT_NAMES = ("development", "calibration", "test")


def split_group_id(scenario_family_id: str, seed_block_id: str) -> str:
    """Hash the shared scenario/seed block; intentionally accepts no condition/view ID."""
    if not isinstance(scenario_family_id, str) or not scenario_family_id.strip():
        raise ValueError("scenario_family_id must be a non-empty string")
    if not isinstance(seed_block_id, str) or not seed_block_id.strip():
        raise ValueError("seed_block_id must be a non-empty string")
    payload = f"{SPLIT_VERSION}|{scenario_family_id.strip()}|{seed_block_id.strip()}"
    return sha256(payload.encode("utf-8")).hexdigest()


def split_for_group(group_id: str) -> str:
    """Deterministically map whole groups to a nominal 60/20/20 split."""
    if not isinstance(group_id, str) or len(group_id) != 64:
        raise ValueError("group_id must be a 64-character SHA256 hex digest")
    try:
        int(group_id, 16)  # Validate the entire digest, not just the bucket prefix.
        bucket = int(group_id[:8], 16) % 5
    except ValueError as exc:
        raise ValueError("group_id must be hexadecimal") from exc
    return "development" if bucket < 3 else "calibration" if bucket == 3 else "test"


def validate_group_splits(records: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Reject any record whose split does not match its precomputed group.

    Extra keys such as condition IDs are ignored and cannot affect assignment.
    The returned mapping is research metadata and must not be passed to monitors.
    """
    seen: dict[str, str] = {}
    count = 0
    for row in records:
        count += 1
        group_id = split_group_id(row.get("scenario_family_id"), row.get("seed_block_id"))
        expected = split_for_group(group_id)
        actual = row.get("split")
        if actual != expected:
            raise ValueError(f"scenario/seed group {group_id} must stay in {expected}, got {actual!r}")
        previous = seen.setdefault(group_id, actual)
        if previous != actual:
            raise ValueError(f"scenario/seed group {group_id} crosses dataset splits")
    if count == 0:
        raise ValueError("at least one split record is required")
    return seen
