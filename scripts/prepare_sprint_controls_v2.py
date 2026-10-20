#!/usr/bin/env python3
"""Freeze supplementary synthetic adversarial controls and offline payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.sprint_baselines import (  # noqa: E402
    build_monitor_payload, canonical_json, compile_evidence_projection,
    deterministic_prediction, provenance_gate,
)
from colluscope.sprint_controls_v2 import (  # noqa: E402
    cases, construction_rows, deterministic_prediction_v2, references_v2, split_manifest,
)
from colluscope.sprint_metrics import score_one, summarize_baseline  # noqa: E402

OUT = ROOT / "data/sprint-baseline-v2"
TASKS = ("explicit_sequence", "proposal", "acceptance", "action_concordance", "public_harm")
LLM_CELLS = (
    ("B2_text_only", "public_only"),
    ("B2_text_only", "privileged_audit"),
    ("B3_action_only", "public_only"),
    ("B4_raw_fusion", "public_only"),
    ("B4_raw_fusion", "privileged_audit"),
    ("B5_evidence_aware", "public_only"),
    ("B5_evidence_aware", "privileged_audit"),
)


def _jsonl(rows: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")) + "\n" for row in rows).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_artifacts() -> dict[str, bytes]:
    controls = cases()
    truth = construction_rows(controls)
    references = references_v2(controls)
    splits = split_manifest(controls)
    truth_by_ref = {row["case_ref"]: row for row in truth}
    if len(controls) != 10 or len(truth_by_ref) != 10 or len(references) != 350:
        raise ValueError("supplementary-control family/case/reference schedule changed")
    if set(splits["development_families"]).intersection(splits["prospective_evaluation_families"]):
        raise ValueError("development and evaluation construction families overlap")

    requests: list[dict[str, Any]] = []
    for case in controls:
        family = case["scenario_family_id"]
        group = next(row for row in splits["groups"] if row["scenario_family_id"] == family)
        for baseline, permission in LLM_CELLS:
            for task in TASKS:
                payload, evidence = build_monitor_payload(case, baseline, task, permission)
                payload_bytes = canonical_json(payload)
                if any(key in payload_bytes.decode("utf-8").casefold() for key in (
                    case["case_ref"].casefold(), group["split_group_id"].casefold(),
                    "construction_oracle_sentinel", "private_reward_target", "expected_labels",
                )):
                    raise ValueError(f"hidden or routing data entered v2 model payload for {case['case_ref']}")
                requests.append({
                    "request_id": hashlib.sha256(
                        f"sprint-control-v2|{case['case_ref']}|{baseline}|{permission}|{task}".encode("utf-8")
                    ).hexdigest(),
                    "case_ref": case["case_ref"], "scenario_family_id": family,
                    "split_group_id": group["split_group_id"], "partition": group["partition"],
                    "baseline_id": baseline, "permission": permission, "task": task,
                    "status": "NOT_DISPATCHED_NO_AUTHORIZATION",
                    "payload_sha256": _sha(payload_bytes), "payload_bytes": len(payload_bytes),
                    "evidence_projection_sha256": _sha(canonical_json(evidence)),
                    "mechanical_ledger_sha256": (
                        _sha(canonical_json(evidence.get("mechanical_ledger")))
                        if baseline == "B5_evidence_aware" else None
                    ),
                    "synthetic_only": True,
                })

    adversarial: list[dict[str, Any]] = []
    by_ref = {row["case_ref"]: row for row in controls}
    conflict_case = by_ref["SC2-EVAL-CITATION-01"]
    conflict_evidence = compile_evidence_projection(
        conflict_case, "evidence_aware", "privileged_audit", include_mechanical_facts=True)
    conflict_raw = {"label": "supported", "evidence_refs": ["M99", "P01"]}
    adversarial.append({
        "case_ref": conflict_case["case_ref"], "task": "explicit_sequence",
        "construction_family": conflict_case["scenario_family_id"],
        "raw_prediction": conflict_raw,
        "gate_result": provenance_gate(conflict_raw, "explicit_sequence", conflict_evidence),
        "synthetic_prediction_fixture_not_model_output": True,
    })
    unsupported_case = by_ref["SC2-EVAL-ASSERT-01"]
    unsupported_evidence = compile_evidence_projection(
        unsupported_case, "evidence_aware", "privileged_audit", include_mechanical_facts=True)
    unsupported_raw = {"label": "supported", "evidence_refs": ["P01", "P02"]}
    adversarial.append({
        "case_ref": unsupported_case["case_ref"], "task": "explicit_sequence",
        "construction_family": unsupported_case["scenario_family_id"],
        "raw_prediction": unsupported_raw,
        "gate_result": provenance_gate(unsupported_raw, "explicit_sequence", unsupported_evidence),
        "synthetic_prediction_fixture_not_model_output": True,
    })
    if not (adversarial[0]["gate_result"]["citation_membership_valid"] is False
            and adversarial[0]["gate_result"]["gate_reason"] == "citation_not_visible"
            and adversarial[1]["gate_result"]["citation_membership_valid"] is True
            and adversarial[1]["gate_result"]["gate_reason"] == "source_sequence_not_sufficient"):
        raise ValueError("B5 provenance gate failed the frozen invalid/unsupported citation counterexamples")

    ref_index = {(row["case_ref"], row["task"], row["view"], row["permission"]): row for row in references}
    deterministic_scores: list[dict[str, Any]] = []
    for case in controls:
        for permission in ("public_only", "privileged_audit"):
            for task in TASKS:
                reference = ref_index[(case["case_ref"], task, "evidence_aware", permission)]
                for baseline, predictor in (
                    ("B0_always_negative", lambda c, t, p: deterministic_prediction(
                        c, "B0_always_negative", t, p, "evidence_aware")),
                    ("B1_refusal_aware_v2", lambda c, t, p: deterministic_prediction_v2(
                        c, t, p, "evidence_aware")),
                ):
                    deterministic_scores.append(score_one(
                        case, reference, baseline, predictor(case, task, permission),
                        view_name="evidence_aware", permission=permission,
                    ))
    deterministic_summaries = []
    for baseline in ("B0_always_negative", "B1_refusal_aware_v2"):
        for permission in ("public_only", "privileged_audit"):
            summary = summarize_baseline(deterministic_scores, baseline, permission)
            summary["result_scope"] = "ten prospective synthetic cases; offline sanity only"
            deterministic_summaries.append(summary)

    artifacts = {
        "controls.jsonl": _jsonl(controls),
        "construction-truth.jsonl": _jsonl(truth),
        "observable-references.jsonl": _jsonl(references),
        "split-manifest.json": (json.dumps(splits, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "payload-schedule.jsonl": _jsonl(requests),
        "adversarial-gate-cases.jsonl": _jsonl(adversarial),
        "offline-deterministic-scores.jsonl": _jsonl(deterministic_scores),
        "offline-deterministic-summary.json": (json.dumps(
            deterministic_summaries, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    }
    hashes = {name: _sha(content) for name, content in sorted(artifacts.items())}
    receipt = {
        "schema_version": "sprint-baseline-v2-preparation-receipt-v1",
        "cases": len(controls), "synthetic_control_only": True,
        "reference_rows": len(references), "scheduled_payload_rows": len(requests),
        "offline_deterministic_score_rows": len(deterministic_scores),
        "development_families": len(splits["development_families"]),
        "prospective_evaluation_families": len(splits["prospective_evaluation_families"]),
        "model_calls": 0, "external_network_calls": 0,
        "latent_collusion_gold_labels": 0,
        "claim_scope": "offline construction, evidence projection, scorer and gate sanity only",
        "artifact_sha256": hashes,
    }
    artifacts["preparation-receipt.json"] = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return artifacts


def write_or_verify(verify: bool = False) -> dict[str, Any]:
    expected = build_artifacts()
    if verify:
        for name, content in expected.items():
            path = OUT / name
            if not path.is_file() or path.read_bytes() != content:
                raise ValueError(f"supplementary control artifact mismatch: {name}")
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for name, content in expected.items():
            path = OUT / name
            if path.exists() and path.read_bytes() != content:
                raise FileExistsError(f"refusing to overwrite changed frozen v2 artifact: {path}")
            path.write_bytes(content)
    return json.loads(expected["preparation-receipt.json"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    receipt = write_or_verify(args.verify)
    print(json.dumps({key: receipt[key] for key in (
        "cases", "reference_rows", "scheduled_payload_rows", "development_families",
        "prospective_evaluation_families", "model_calls", "external_network_calls",
        "latent_collusion_gold_labels")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
