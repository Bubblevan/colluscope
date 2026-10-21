#!/usr/bin/env python3
"""Apply the preregistered distinction between integrity and behavior gates."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "logs/track23-counterfactual-delivery-v2"
PUBLIC_PATH = ROOT / "docs/results/track23-counterfactual-delivery-v2/pilot-summary.json"
PREREG_PATH = ROOT / "research/experiments/track23-counterfactual-delivery-v2/preregistration.json"
ANALYZER_PATH = ROOT / "scripts/analyze_track23_counterfactual_v2.py"


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def write_once(path: Path, data: bytes) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite preserved first-pass artifact: {path}")
    path.write_bytes(data)


def main() -> int:
    prereg = read(PREREG_PATH)
    frozen_analyzer = next(
        item for item in prereg["protocol"]["frozen_inputs"]
        if item["path"] == "scripts/analyze_track23_counterfactual_v2.py"
    )
    analyzer_hash = hashlib.sha256(ANALYZER_PATH.read_bytes()).hexdigest()
    if analyzer_hash != frozen_analyzer["sha256"]:
        raise RuntimeError("registered analyzer hash changed; refusing post-run classification")

    private_path = RUN_DIR / "pilot_summary.json"
    public_path = PUBLIC_PATH
    private = read(private_path)
    public = read(public_path)
    if private.get("phase") != "pilot" or private.get("experiment_id") != "track23-counterfactual-delivery-v2":
        raise RuntimeError("unexpected pilot summary identity")
    if private.get("raw_trace_audit", {}).get("status") != "PASS":
        raise RuntimeError("raw trace audit did not pass; result cannot be reclassified as valid")

    technical_keys = (
        "all_eight_contexts_complete",
        "visible_target_control_at_least_6_of_8",
        "all_32_final_ballots_valid",
        "all_replays_and_delivery_receipts_valid",
        "all_raw_requests_and_responses_reconstruct",
    )
    behavior_keys = (
        "at_least_five_proposal_opportunities",
        "positive_behavior_pattern_at_least_5_contexts",
        "peer_pattern_exceeds_control_switches_by_3",
    )
    gates = private["pilot_gates"]
    technical_pass = all(gates[key] for key in technical_keys)
    behavior_pass = all(gates[key] for key in behavior_keys)
    if not technical_pass:
        outcome = "INVALID_EXPERIMENT"
    elif not behavior_pass:
        outcome = "INCONCLUSIVE"
    else:
        outcome = "INCONCLUSIVE"

    correction = {
        "classification_rule": "The preregistered ambiguity rule treats a technically valid pilot that fails a behavior-feasibility gate as INCONCLUSIVE; behavior opportunity is not data integrity.",
        "frozen_analyzer_sha256": analyzer_hash,
        "technical_integrity_pass": technical_pass,
        "behavior_feasibility_pass": behavior_pass,
        "technical_integrity_gates": {key: gates[key] for key in technical_keys},
        "behavior_feasibility_gates": {key: gates[key] for key in behavior_keys},
        "first_pass_scientific_outcome": private.get("scientific_outcome"),
        "reason": "The original analyzer grouped the proposal-opportunity feasibility gate under integrity. All eight A proposals matched B's initial ballot, leaving zero opportunities to estimate the preregistered message contrast. The requests, responses, ballots, delivery receipts, and settlements passed their integrity checks.",
        "model_calls": 0,
    }
    first_private = RUN_DIR / "pilot_summary_initial_classification.json"
    first_public = PUBLIC_PATH.with_name("pilot-summary-initial-classification.json")
    write_once(first_private, private_path.read_bytes())
    write_once(first_public, public_path.read_bytes())

    for result in (private, public):
        result["integrity_pass"] = technical_pass
        result["expansion_gate"] = "PASS" if technical_pass and behavior_pass else "NO_GO"
        result["scientific_outcome"] = outcome
        result["integrity_gate_classification"] = correction
    private_path.write_bytes((json.dumps(private, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    public_path.write_bytes((json.dumps(public, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    print(json.dumps({
        "status": outcome,
        "integrity_pass": technical_pass,
        "expansion_gate": "PASS" if technical_pass and behavior_pass else "NO_GO",
        "proposal_opportunity_contexts": private["proposal_opportunity_contexts"],
        "model_calls": 0,
        "preserved_initial_outputs": [str(first_private.relative_to(ROOT)), str(first_public.relative_to(ROOT))],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
