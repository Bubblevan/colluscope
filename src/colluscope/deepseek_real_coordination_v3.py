"""V3 batch identity wrapper around the unchanged V2 behavioral protocol.

V3 is a fresh, separately registered execution after V2 stopped before any
provider response. It preserves the same fixed matrices, conditions, prompts,
and 40-request schedule while assigning unique request IDs. No V2 data are
rewritten or treated as behavior observations.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import deepseek_real_coordination_v2 as v2
from .deepseek_real_coordination_v2 import (  # re-export the frozen task logic
    MAX_COST_USD,
    MAX_REQUESTS,
    MODEL,
    OUTPUT_LIMIT,
    TOKENIZER_SHA256,
    analyze_actions,
    fact_control_passed,
    fact_control_reference,
    messages_for,
    schemas,
    validate_action,
)

EXPERIMENT_ID = "deepseek-real-coordination-40-v3"


def canonical(value: Any) -> bytes:
    return v2.canonical(value)


def sha(data: bytes) -> str:
    return v2.sha(data)


def build_schedule() -> dict[str, Any]:
    """Clone the frozen V2 schedule, namespace request IDs, and reseal it."""
    schedule = deepcopy(v2.build_schedule())
    schedule["experiment_id"] = EXPERIMENT_ID
    schedule["schema_version"] = "deepseek-real-coordination-schedule-v3"
    for row in schedule["requests"]:
        old_id = row["request_id"]
        row["request_id"] = f"v3-{old_id}"
        row["dependencies"] = [f"v3-{item}" for item in row["dependencies"]]
        for key in ("proposal_request_id", "reply_request_id"):
            if isinstance(row.get(key), str):
                row[key] = f"v3-{row[key]}"
    schedule["schedule_sha256"] = None
    schedule.pop("schedule_sha256")
    schedule["schedule_sha256"] = sha(canonical(schedule))
    return schedule
