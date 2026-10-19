#!/usr/bin/env python3
"""Recompute M2-V2 observable evidence coverage without monitor predictions."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from colluscope.m2_corpus import load_m2_corpus
from colluscope.m2_v2_reference import CLAIM_FIELDS, reference_for_v2

VIEWS = ("text_only", "action_only", "raw_fusion", "structured_evidence",
         "structured_without_findings")
PERMISSIONS = ("public_only", "privileged_audit")


def analyze(extension_run: Path, coverage_csv: Path, labels_csv: Path) -> dict[str, Any]:
    cases = load_m2_corpus(ROOT, extension_run)
    coverage: dict[tuple, dict[str, Any]] = {}
    label_counts: Counter = Counter()
    mismatch_episodes: set[str] = set()
    for case in cases:
        for view in VIEWS:
            for permission in PERMISSIONS:
                label = reference_for_v2(case, view, permission)
                key = (case.provenance, case.partition, view, permission)
                row = coverage.setdefault(key, {
                    "provenance": case.provenance, "partition": case.partition,
                    "view_name": view, "permission_profile": permission,
                    "source_episodes": 0, "actions_visible_episodes": 0,
                    "messages_visible_episodes": 0, "sequence_supported_episodes": 0,
                    "sequence_insufficient_episodes": 0,
                    "recomputed_public_harm_present": 0,
                    "recomputed_ballot_disagreement_present": 0,
                    "visible_message_delivery_present": 0,
                    "visible_allocation_mapping_present": 0,
                    "visible_commitment_marker_present": 0,
                })
                row["source_episodes"] += 1
                row["actions_visible_episodes"] += int(label["actions_visible_in_view"])
                row["messages_visible_episodes"] += int(label["messages_visible_in_view"])
                row["sequence_supported_episodes"] += int(
                    label["observable_sequence"] == "supported_observable_sequence")
                row["sequence_insufficient_episodes"] += int(label["sequence_evidence_insufficient"])
                row["recomputed_public_harm_present"] += int(label["public_harm"] == "present")
                row["recomputed_ballot_disagreement_present"] += int(
                    label["ballot_disagreement"] == "present")
                row["visible_message_delivery_present"] += int(
                    label["message_delivery"] == "present")
                row["visible_allocation_mapping_present"] += int(
                    label["allocation_proposal"] == "full_allocation_mapping")
                row["visible_commitment_marker_present"] += int(
                    label["explicit_commitment"] == "present")
                for claim in CLAIM_FIELDS:
                    label_counts[(case.provenance, case.partition, view, permission,
                                  claim, str(label[claim]))] += 1
                if label["stored_harm_flag_mismatch_researcher_only"]:
                    mismatch_episodes.add(case.episode_id)

    expected_rows = len(cases) * len(VIEWS) * len(PERMISSIONS)
    if len(cases) != 100 or len(coverage) != 40 or expected_rows != 1000:
        raise ValueError("source corpus or evidence projection coverage is incomplete")
    coverage_rows = [coverage[key] for key in sorted(coverage)]
    coverage_csv.parent.mkdir(parents=True, exist_ok=True)
    with coverage_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(coverage_rows[0]))
        writer.writeheader()
        writer.writerows(coverage_rows)
    label_rows = [
        {"provenance": key[0], "partition": key[1], "view_name": key[2],
         "permission_profile": key[3], "claim": key[4], "value": key[5], "episodes": count}
        for key, count in sorted(label_counts.items())
    ]
    labels_csv.parent.mkdir(parents=True, exist_ok=True)
    with labels_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(label_rows[0]))
        writer.writeheader()
        writer.writerows(label_rows)
    return {
        "status": "PASS_DETERMINISTIC_EVIDENCE_REPLAY",
        "source_episodes": len(cases), "view_permission_rows": expected_rows,
        "coverage_groups": len(coverage_rows), "observable_claims": len(CLAIM_FIELDS),
        "researcher_only_stored_harm_flag_mismatch_episodes": len(mismatch_episodes),
        "coverage_csv": str(coverage_csv), "claim_distribution_csv": str(labels_csv),
        "interpretation": "Counts describe reference fact availability and evidence sufficiency; they are not monitor accuracy or latent-collusion labels.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extension-run", type=Path,
                        default=ROOT / "runs/m1_100/extension-75-20261019-run02")
    parser.add_argument("--coverage-csv", type=Path,
                        default=ROOT / "docs/results/m2_v2_evidence_coverage.csv")
    parser.add_argument("--labels-csv", type=Path,
                        default=ROOT / "docs/results/m2_v2_reference_label_counts.csv")
    args = parser.parse_args()
    result = analyze(args.extension_run.resolve(), args.coverage_csv, args.labels_csv)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
