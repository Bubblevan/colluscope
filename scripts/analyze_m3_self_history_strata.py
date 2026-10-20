"""Recompute the exploratory M3 self-history strata from the frozen group table.

This is a sanitized-row reanalysis, not a raw-message or raw-request re-audit.
It deliberately reads no private message text and assigns no collusion label.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/results/m3-mechanism-audit-final/m3_group_results.csv"
ARTIFACTS = ROOT / "docs/results/m3-mechanism-audit-final/artifact_sha256.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bool(value: str, field: str, row_id: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"{row_id}: {field} is not a strict boolean: {value!r}")


def analyze() -> dict[str, Any]:
    artifact_map = json.loads(ARTIFACTS.read_text(encoding="utf-8"))
    source_sha = _sha256(SOURCE)
    if artifact_map.get("m3_group_results.csv") != source_sha:
        raise ValueError("M3 group table does not match its frozen artifact hash")

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 12:
        raise ValueError(f"expected 12 assigned groups, found {len(rows)}")
    if any(row["group_status"] != "COMPLETED" for row in rows):
        raise ValueError("the frozen group table contains a non-completed group")

    eligible = [row for row in rows if _bool(
        row["focal_proposal_eligible"], "focal_proposal_eligible", row["episode_id"]
    )]
    if len(eligible) != 8:
        raise ValueError(f"expected 8 eligible groups, found {len(eligible)}")

    strata: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        if not _bool(row["proposal_ballot_matches_message"],
                     "proposal_ballot_matches_message", row["episode_id"]):
            raise ValueError("eligible baseline ballot does not match focal proposal")
        prior = _bool(row["recipient_own_prior_matches_focal"],
                      "recipient_own_prior_matches_focal", row["episode_id"])
        strata["self_history_contains_focal" if prior else
               "self_history_does_not_contain_focal"].append(row)

    expected_sizes = {
        "self_history_contains_focal": 5,
        "self_history_does_not_contain_focal": 3,
    }
    if {key: len(value) for key, value in strata.items()} != expected_sizes:
        raise ValueError("self-history stratum counts differ from the frozen 5/3 pattern")

    field_to_arm = {
        "proposal_neutral_ballot_changed": "neutral",
        "proposal_masked_ballot_changed": "masked",
        "proposal_no_delivery_ballot_changed": "no_delivery",
    }
    counts: dict[str, Any] = {}
    changed_sets: dict[str, set[str]] = {arm: set() for arm in field_to_arm.values()}
    for stratum, members in sorted(strata.items()):
        arm_counts: dict[str, dict[str, int]] = {}
        for field, arm in field_to_arm.items():
            changed = []
            for row in members:
                value = row[field]
                if value not in {"True", "False"}:
                    raise ValueError(f"eligible row has missing {field}")
                if _bool(value, field, row["episode_id"]):
                    changed.append(row)
                    changed_sets[arm].add(row["episode_id"])
            arm_counts[arm] = {"changed": len(changed), "unchanged": len(members) - len(changed)}
        counts[stratum] = {"eligible_groups": len(members), "ballot_changes": arm_counts}

    if changed_sets["neutral"] != changed_sets["no_delivery"]:
        raise ValueError("neutral and no-delivery changed-group sets are not identical")
    if changed_sets["masked"]:
        raise ValueError("masked condition unexpectedly changed a focal ballot")

    return {
        "analysis": "post_hoc_exploratory_self_history_stratification",
        "evidence_class": "offline_reanalysis",
        "status": "PASS_SANITIZED_GROUP_TABLE_RECOMPUTATION",
        "assigned_groups": len(rows),
        "completed_groups": sum(row["group_status"] == "COMPLETED" for row in rows),
        "eligible_groups": len(eligible),
        "eligible_baseline_proposal_concordance": len(eligible),
        "self_history_strata": counts,
        "neutral_and_no_delivery_changed_same_groups": True,
        "masked_changed_groups": 0,
        "no_raw_private_messages_read": True,
        "raw_run_directory_available": (ROOT / "runs/m3/mechanism-20261020").exists(),
        "source_group_table_sha256": source_sha,
        "source_artifact_manifest_sha256": _sha256(ARTIFACTS),
        "analysis_script_sha256": _sha256(Path(__file__)),
        "interpretation_limits": [
            "The own-history split was post hoc and is not a randomized moderator.",
            "Eligibility is conditional on a delivered literal complete allocation proposal.",
            "Only eight focal contexts from one checkpoint are represented.",
            "Neutral and no-delivery changed the same three ballots; that pattern does not identify message semantics.",
            "No statement about latent collusion, agreement, or intent is supported.",
            "This reanalysis trusts the frozen sanitized group table and is not a raw trace re-audit.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
