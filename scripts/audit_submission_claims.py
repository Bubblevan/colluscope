"""Recompute manuscript headline metrics from frozen, sanitized audit exports."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M1 = ROOT / "docs/results/paper-figures/m1_100_behavior_summary.csv"
M2 = ROOT / "docs/results/m2-final-scientific-synthesis/m2_recomputed_predictions.csv"
M3_GROUP = ROOT / "docs/results/m3-mechanism-audit-final/m3_group_results.csv"
M3_ARMS = ROOT / "docs/results/m3-mechanism-audit-final/m3_arm_summary.csv"
M3_PAIRS = ROOT / "docs/results/m3-mechanism-audit-final/m3_paired_contrasts.csv"
M3_TOKENS = ROOT / "docs/results/m3-mechanism-audit-final/m3_token_matching_summary.csv"
DEFAULT_OUT = ROOT / "docs/results/submission-prep/claim-audit.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_bool(value: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"expected a frozen boolean field, got {value!r}")


def require(condition: bool, claim: str, observed: object) -> None:
    if not condition:
        raise AssertionError(f"claim mismatch: {claim}: observed={observed!r}")


def audit() -> dict:
    m1 = read_csv(M1)
    expected_m1 = {
        "normal_cooperation": (0, 2),
        "common_incentive_parallel_behavior": (0, 1),
        "coalition_incentive_private_chat": (9, 9),
        "coalition_incentive_no_private_chat": (0, 0),
        "private_chat_no_side_bonus": (0, 1),
    }
    m1_observed = {}
    for row in m1:
        values = (int(row["target_executed_n"]), int(row["positive_regret_n"]))
        m1_observed[row["condition_id"]] = values
        require(values == expected_m1[row["condition_id"]], f"M1 prospective counts {row['condition_id']}", values)
    require(sum(int(row["assigned_n"]) for row in m1) == 75, "M1 prospective assigned denominator", 75)
    require(sum(int(row["positive_regret_n"]) for row in m1) == 13, "M1 prospective positive regret", 13)

    m2 = read_csv(M2)
    f23 = [row for row in m2 if row["partition"] in {"F2", "F3"}]
    m2_task_counts = {}
    for task in sorted({row["task"] for row in f23}):
        task_rows = [row for row in f23 if row["task"] == task]
        m2_task_counts[task] = {
            "n": len(task_rows),
            "correct": sum(as_bool(row["fact_correct"]) for row in task_rows),
        }
    expected_m2 = {
        "public_harm": (350, 158),
        "ballot_disagreement": (350, 350),
        "message_delivery": (200, 200),
        "allocation_proposal": (200, 181),
        "proposal_action_concordance": (150, 149),
    }
    for task, expected in expected_m2.items():
        observed = (m2_task_counts[task]["n"], m2_task_counts[task]["correct"])
        require(observed == expected, f"M2 F2/F3 {task} counts", observed)
    structured = [row for row in f23 if row["task"] == "public_harm" and row["view"] == "structured_evidence" and row["permission"] == "public_only"]
    require((len(structured), sum(as_bool(row["fact_correct"]) for row in structured)) == (50, 50), "M2 answer-exposed structured cell", (len(structured), sum(as_bool(row["fact_correct"]) for row in structured)))
    public_harm = [row for row in f23 if row["task"] == "public_harm"]
    always_negative_correct = sum(row["expected"] == "absent" for row in public_harm)
    require((len(public_harm), always_negative_correct) == (350, 294), "M2 always-negative public-harm baseline", (len(public_harm), always_negative_correct))

    groups = read_csv(M3_GROUP)
    eligible = [row for row in groups if as_bool(row["focal_proposal_eligible"])]
    history_yes = [row for row in eligible if as_bool(row["recipient_own_prior_matches_focal"])]
    history_no = [row for row in eligible if not as_bool(row["recipient_own_prior_matches_focal"])]
    changed_yes = sum(as_bool(row["proposal_neutral_ballot_changed"]) for row in history_yes)
    changed_no = sum(as_bool(row["proposal_neutral_ballot_changed"]) for row in history_no)
    require((len(groups), len(eligible), len(history_yes), changed_yes, len(history_no), changed_no) == (12, 8, 5, 0, 3, 3), "M3 post-hoc self-history subgroup", (len(groups), len(eligible), len(history_yes), changed_yes, len(history_no), changed_no))

    arms = {row["arm"]: row for row in read_csv(M3_ARMS)}
    arm_values = {arm: (int(row["match_count"]), int(row["changed_vs_proposal"]), float(row["mean_public_regret"])) for arm, row in arms.items()}
    require(arm_values == {
        "proposal": (8, 0, 12.0),
        "neutral": (5, 3, 9.75),
        "masked": (8, 0, 12.0),
        "no_delivery": (5, 3, 9.75),
    }, "M3 arm summary", arm_values)
    pairs = {row["contrast"]: row for row in read_csv(M3_PAIRS)}
    require(pairs["proposal_vs_neutral"]["focal_ballot_changed"] == "3", "M3 Proposal-Neutral changes", pairs["proposal_vs_neutral"]["focal_ballot_changed"])
    require(pairs["proposal_vs_no_delivery"]["focal_ballot_changed"] == "3", "M3 Proposal-No-delivery changes", pairs["proposal_vs_no_delivery"]["focal_ballot_changed"])
    token_rows = {row["arm"]: row for row in read_csv(M3_TOKENS)}
    no_delivery_delta = float(token_rows["no_delivery"]["mean_absolute_full_prompt_token_delta"])
    no_delivery_median = float(token_rows["no_delivery"]["median_absolute_full_prompt_token_delta"])
    require((no_delivery_delta, no_delivery_median) == (45.125, 45.0), "M3 No-delivery prompt token difference", (no_delivery_delta, no_delivery_median))

    input_hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in (M1, M2, M3_GROUP, M3_ARMS, M3_PAIRS, M3_TOKENS)}
    return {
        "audit_id": "submission-claim-metric-recompute-v1",
        "model_calls": 0,
        "scope": "recompute headline manuscript metrics from frozen sanitized audit CSVs; does not read or mutate private M3 raw run",
        "m1_prospective": {"assigned_n": 75, "positive_regret_n": 13, "condition_target_and_regret_counts": {key: list(value) for key, value in m1_observed.items()}},
        "m2_f2_f3": {"task_n_and_exact_correct": m2_task_counts, "structured_public_only_public_harm": {"n": len(structured), "correct": 50, "answer_exposed": True}, "always_negative_public_harm": {"n": len(public_harm), "correct": always_negative_correct}},
        "m3": {"assigned_groups": len(groups), "eligible_groups": len(eligible), "post_hoc_self_history": {"match_n": len(history_yes), "match_changed_neutral_n": changed_yes, "nonmatch_n": len(history_no), "nonmatch_changed_neutral_n": changed_no}, "arm_counts": {key: list(value) for key, value in arm_values.items()}, "no_delivery_full_prompt_abs_delta_mean": no_delivery_delta, "no_delivery_full_prompt_abs_delta_median": no_delivery_median},
        "input_sha256": input_hashes,
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    result = audit()
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(payload, encoding="utf-8", newline="\n")
    print(f"status={result['status']}")
    print(f"output={args.out}")
    print(f"output_sha256={sha256(args.out)}")
    print("model_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
