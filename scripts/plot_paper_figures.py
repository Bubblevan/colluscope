"""Create the sanitized M1 behavior table and figure from the frozen audit CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "runs/m1_100/extension-75-20261019-run02/analysis/new_episode_cases.csv"
DEFAULT_OUT = ROOT / "docs/results/paper-figures"
CONDITION_ORDER = [
    "normal_cooperation",
    "common_incentive_parallel_behavior",
    "coalition_incentive_private_chat",
    "coalition_incentive_no_private_chat",
    "private_chat_no_side_bonus",
]
LABELS = [
    "Normal\ncooperation",
    "Common public\nincentive",
    "Private target\n+incentive + chat",
    "Private target\nincentive, no chat",
    "Chat, no side\nbonus",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(input_path: Path, out: Path) -> list[dict[str, object]]:
    input_path = input_path.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with input_path.open(newline="", encoding="utf-8") as stream:
        source = list(csv.DictReader(stream))
    if len(source) != 75:
        raise ValueError(f"expected all 75 prospective assigned episodes, found {len(source)}")
    if any(row.get("provenance") != "prospective_extension" for row in source):
        raise ValueError("input includes a non-prospective provenance row")
    if any(row.get("status") != "COMPLETED" for row in source):
        raise ValueError("the frozen figure expects the independently audited 75 completed episodes")

    summary: list[dict[str, object]] = []
    for condition in CONDITION_ORDER:
        rows = [row for row in source if row.get("condition_id") == condition]
        if len(rows) != 15:
            raise ValueError(f"expected 15 assigned rows for {condition}, found {len(rows)}")
        target_n = sum(row.get("target_execution", "").lower() == "true" for row in rows)
        positive_regret_n = sum(int(row["welfare_gap"]) > 0 for row in rows)
        summary.append({
            "condition_id": condition,
            "assigned_n": len(rows),
            "completed_n": sum(row.get("status") == "COMPLETED" for row in rows),
            "target_executed_n": target_n,
            "target_executed_rate_assigned": target_n / len(rows),
            "positive_regret_n": positive_regret_n,
            "positive_regret_rate_assigned": positive_regret_n / len(rows),
        })

    table_path = out / "m1_100_behavior_summary.csv"
    with table_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    x = np.arange(len(summary))
    width = 0.34
    target = [row["target_executed_rate_assigned"] * 100 for row in summary]
    regret = [row["positive_regret_rate_assigned"] * 100 for row in summary]
    fig, ax = plt.subplots(figsize=(11.5, 5.8), layout="constrained")
    bars_target = ax.bar(x - width / 2, target, width, label="Rewarded target selected",
                         color="#3b73a8")
    bars_regret = ax.bar(x + width / 2, regret, width, label="Positive welfare regret",
                         color="#d28b36")
    for bars, values in ((bars_target, target), (bars_regret, regret)):
        for bar, row, value in zip(bars, summary, values, strict=True):
            numerator = (row["target_executed_n"] if bars is bars_target
                         else row["positive_regret_n"])
            denominator = row["assigned_n"]
            ax.annotate(f"{numerator}/{denominator}",
                        (bar.get_x() + bar.get_width() / 2, value),
                        xytext=(0, 4), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Assigned episodes (%)")
    ax.set_ylim(0, 100)
    ax.set_xticks(x, LABELS)
    ax.set_title("M1 prospective extension: behavior by assigned condition (n=75)")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(out / "m1_100_behavior_by_condition.png", dpi=180)
    plt.close(fig)

    manifest = {
        "schema_version": "colluscope-paper-figures-m1-v1",
        "input": "runs/m1_100/extension-75-20261019-run02/analysis/new_episode_cases.csv",
        "input_sha256": _sha(input_path),
        "source_scope": "prospective_extension only; 75 assigned episodes; F0 excluded",
        "outcomes": {
            "target_executed_n": "independently recomputed target allocation selected",
            "positive_regret_n": "welfare_gap > 0 from scenario-specific independent replay",
            "rates_denominator": "all 15 assigned episodes in each condition",
        },
        "summary_sha256": _sha(table_path),
        "figure_sha256": _sha(out / "m1_100_behavior_by_condition.png"),
    }
    (out / "m1_100_behavior_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    summary = build(args.input, args.out)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
