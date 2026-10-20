#!/usr/bin/env python3
"""Versioned execution-only adapter for registered M4-B5 campaign v1.

The immutable preregistration pins the schedule file's raw-byte SHA-256, and
the public request manifest pins the same raw-byte hash. The original runner's
dispatch gate compares the preregistration field to a canonical-JSON hash.
This adapter verifies both frozen raw-byte hashes and changes only that
comparison value in memory. It does not rewrite the registered preregistration,
schedule, request manifest, request bodies, treatments, outcomes, or budget.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "src", ROOT / "research/frozen_eval"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from scripts import run_m4_b5_context_sensitivity as campaign  # noqa: E402

AMENDMENT_PATH = (
    ROOT / "research/experiments/m4-b5-context-sensitivity-campaign-v1/"
    "execution-amendments.jsonl"
)
AMENDMENT_ID = "M4B5-SCHEDULE-HASH-NORMALIZATION-01"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _amendment_record() -> dict[str, Any]:
    if not AMENDMENT_PATH.is_file():
        raise campaign.CampaignError("EXECUTION_AMENDMENT_RECORD_MISSING")
    lines = AMENDMENT_PATH.read_bytes().splitlines()
    if len(lines) != 1 or not lines[0].strip():
        raise campaign.CampaignError("EXECUTION_AMENDMENT_RECORD_COUNT_INVALID")
    try:
        record = json.loads(lines[0])
    except Exception as exc:
        raise campaign.CampaignError("EXECUTION_AMENDMENT_RECORD_INVALID") from exc
    if record.get("amendment_id") != AMENDMENT_ID:
        raise campaign.CampaignError("EXECUTION_AMENDMENT_ID_MISMATCH")
    if record.get("adapter_sha256") != sha(Path(__file__).read_bytes()):
        raise campaign.CampaignError("EXECUTION_AMENDMENT_ADAPTER_HASH_MISMATCH")
    frozen_runner = sha(campaign.__file__ and Path(campaign.__file__).read_bytes())
    if record.get("frozen_runner_sha256") != frozen_runner:
        raise campaign.CampaignError("EXECUTION_AMENDMENT_FROZEN_RUNNER_HASH_MISMATCH")
    return record


def _install_registered_schedule_hash_adapter() -> None:
    original_loader = campaign._load_auth_and_registration

    def amended_loader():
        batch, prereg, registration = original_loader()
        amendment = _amendment_record()
        prereg_path = campaign.PREREG_PATH
        prereg_raw = prereg_path.read_bytes()
        schedule, schedule_raw = campaign._load_schedule()
        raw_file_hash = sha(schedule_raw)
        canonical_object_hash = sha(campaign.canonical_pretty(schedule))
        manifest = json.loads(campaign.REQUEST_MANIFEST_PATH.read_bytes())
        prereg_raw_hash = prereg.get("protocol", {}).get("schedule_sha256")
        schedule_frozen_hash = next((item.get("sha256") for item in prereg.get("protocol", {}).get(
            "frozen_inputs", []) if item.get("path") == campaign.SCHEDULE_PATH.relative_to(ROOT).as_posix()), None)
        if (amendment.get("registered_preregistration_sha256") != sha(prereg_raw)
                or amendment.get("request_manifest_sha256") != sha(campaign.REQUEST_MANIFEST_PATH.read_bytes())
                or amendment.get("raw_schedule_file_sha256") != raw_file_hash
                or amendment.get("canonical_schedule_object_sha256") != canonical_object_hash
                or prereg_raw_hash != raw_file_hash
                or schedule_frozen_hash != raw_file_hash
                or manifest.get("schedule_sha256") != raw_file_hash):
            raise campaign.CampaignError("EXECUTION_AMENDMENT_HASH_BINDING_MISMATCH")
        amended = copy.deepcopy(prereg)
        amended["protocol"]["schedule_sha256"] = canonical_object_hash
        return batch, amended, registration

    campaign._load_auth_and_registration = amended_loader


def preflight() -> dict[str, Any]:
    _install_registered_schedule_hash_adapter()
    schedule, _schedule_raw = campaign._load_schedule()
    rows, _meta = campaign.compile_requests(schedule)
    manifest_raw = campaign.REQUEST_MANIFEST_PATH.read_bytes()
    _gate, api_key = campaign._check_dispatch_gate(schedule, rows, sha(manifest_raw))
    if len(rows) != campaign.MAX_ATTEMPTS or len(api_key) == 0:
        raise campaign.CampaignError("EXECUTION_AMENDMENT_PREFLIGHT_INCOMPLETE")
    return {
        "status": "PREFLIGHT_PASS_NO_REQUEST_SENT",
        "experiment_id": campaign.EXPERIMENT_ID,
        "amendment_id": AMENDMENT_ID,
        "requests_ready": len(rows),
        "physical_attempt_cap": campaign.MAX_ATTEMPTS,
        "peak_cost_reserve_usd": str(campaign._peak_reserve(rows)),
        "model_alias": campaign.MODEL,
        "endpoint": campaign.ENDPOINT,
        "credential_configured": True,
        "network_requests_sent": 0,
    }


def dispatch() -> dict[str, Any]:
    _install_registered_schedule_hash_adapter()
    return campaign.dispatch()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preflight", action="store_true")
    group.add_argument("--dispatch", action="store_true")
    args = parser.parse_args()
    result = preflight() if args.preflight else dispatch()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status") in {"PREFLIGHT_PASS_NO_REQUEST_SENT", "COMPLETE", "ALREADY_COMPLETE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
