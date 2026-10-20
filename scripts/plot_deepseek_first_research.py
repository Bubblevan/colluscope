#!/usr/bin/env python3
"""Render sanitized figures from the independent DeepSeek-first audit outputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/results/deepseek-first-m4/audit"
OUT = ROOT / "docs/results/deepseek-first-m4/figures"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(audit: Path = AUDIT, out: Path = OUT) -> dict[str, str]:
    analysis = json.loads((audit / "postrun_analysis_v2.json").read_bytes())
    with (audit / "agent_group_outcomes.csv").open(encoding="utf-8", newline="") as f:
        groups = list(csv.DictReader(f))
    if len(groups) != 24:
        raise ValueError("expected all 24 assigned Agent groups")
    if analysis["monitor"]["assigned_monitor_requests"] != 376:
        raise ValueError("expected the complete frozen 376-row Monitor denominator")
    out.mkdir(parents=True, exist_ok=True)

    family_order = [f"m4_family_{i}" for i in range(1, 7)]
    fig, ax = plt.subplots(figsize=(8.4, 4.8), constrained_layout=True)
    for x, family in enumerate(family_order):
        values = [int(row["public_regret"]) for row in groups if row["family"] == family]
        if len(values) != 4:
            raise ValueError(f"expected four assigned groups for {family}")
        jitter = [-0.075, -0.025, 0.025, 0.075]
        ax.scatter([x + j for j in jitter], values, s=46, color="#245a83", zorder=3)
        mean = sum(values) / len(values)
        ax.plot([x - 0.18, x + 0.18], [mean, mean], color="#b74332", linewidth=2.4, zorder=4)
        ax.text(x, 8.65, f"n=4 · mean={mean:.2f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(family_order)), [f"F{i}" for i in range(1, 7)])
    ax.set_ylabel("Public regret relative to family-specific optimum")
    ax.set_xlabel("Frozen payoff-matrix family")
    ax.set_title("DeepSeek Agent outcomes: every assigned group shown")
    ax.set_ylim(0, 10)
    ax.grid(axis="y", color="#d9dee5", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.savefig(out / "agent_regret_by_family.png", dpi=220)
    plt.close(fig)

    focal = analysis["agent"]["focal_counterfactual_fixed_peer_settlement"]["summary_by_arm"]
    focal_order = ["masked_history_neutral", "masked_history_proposal",
                   "retained_history_alternative", "retained_history_neutral"]
    focal_labels = ["Masked + neutral", "Masked + proposal", "History + alternative", "History + neutral"]
    fig, ax = plt.subplots(figsize=(9.0, 4.8), constrained_layout=True)
    x = list(range(len(focal_order)))
    width = 0.36
    ballot_counts = [focal[arm]["focal_ballot_changed"] for arm in focal_order]
    settlement_counts = [focal[arm]["selected_allocation_changed"] for arm in focal_order]
    bars1 = ax.bar([i - width / 2 for i in x], ballot_counts, width=width,
                   color="#4c78a8", label="Focal ballot changed")
    bars2 = ax.bar([i + width / 2 for i in x], settlement_counts, width=width,
                   color="#f2a541", label="Selected allocation changed")
    for bars in (bars1, bars2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.25,
                    f"{int(bar.get_height())}/16", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, focal_labels)
    ax.set_ylim(0, 13)
    ax.set_ylabel("Proposal-eligible focal contexts (n=16 per arm)")
    ax.set_title("Ballot changes do not map one-for-one to settlement changes")
    ax.legend(frameon=False)
    ax.grid(axis="y", color="#d9dee5", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.savefig(out / "focal_ballot_vs_settlement_changes.png", dpi=220)
    plt.close(fig)

    refs = analysis["monitor"]["per_reference_accuracy_by_population_and_method"]
    population_order = ["m4_natural_traces", "scripted_synthetic_controls", "matched_indistinguishable_worlds"]
    pop_labels = ["Natural M4 traces", "Scripted controls", "Matched worlds"]
    fig, ax = plt.subplots(figsize=(8.4, 4.8), constrained_layout=True)
    width = 0.34
    colors = {"B4_raw_fusion": "#4c78a8", "B5_evidence_aware": "#f2a541"}
    labels = {"B4_raw_fusion": "B4 raw fusion", "B5_evidence_aware": "B5 evidence-aware"}
    for method_index, method in enumerate(("B4_raw_fusion", "B5_evidence_aware")):
        rows = {(row["population"], row["baseline_id"]): row for row in refs}
        xs, ys, ns = [], [], []
        for i, population in enumerate(population_order):
            row = rows[(population, method)]
            xs.append(i + (method_index - 0.5) * width)
            ys.append(row["accuracy"] * 100)
            ns.append(row["reference_rows"])
        bars = ax.bar(xs, ys, width=width, color=colors[method], label=labels[method])
        for bar, n in zip(bars, ns):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                    f"{bar.get_height():.1f}%\nn={n}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(3), pop_labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Exact individual observable-reference labels (%)")
    ax.set_title("Monitor exactness by population (populations kept separate)")
    ax.legend(frameon=False)
    ax.grid(axis="y", color="#d9dee5", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.savefig(out / "monitor_reference_accuracy_by_population.png", dpi=220)
    plt.close(fig)

    pair_tally = analysis["monitor"]["paired_exact_accuracy_tally"]
    fig, ax = plt.subplots(figsize=(7.2, 4.2), constrained_layout=True)
    categories = ["Both exact", "B4 only", "B5 only", "Neither exact"]
    values = [pair_tally["both_correct"], pair_tally["B4_only_correct"],
              pair_tally["B5_only_correct"], pair_tally["neither_correct"]]
    bars = ax.bar(categories, values, color=["#719b74", "#4c78a8", "#f2a541", "#999999"])
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1, str(value), ha="center", fontsize=9)
    ax.set_ylim(0, max(values) + 12)
    ax.set_ylabel("Assessable matched pairs (n=126)")
    ax.set_title("B4/B5 paired all-reference exactness; descriptive only")
    ax.grid(axis="y", color="#d9dee5", linewidth=0.8)
    ax.set_axisbelow(True)
    fig.savefig(out / "monitor_paired_correctness.png", dpi=220)
    plt.close(fig)

    manifest = {
        "schema_version": "deepseek-first-figures-v1",
        "source_sha256": {
            "postrun_analysis_v2.json": _sha(audit / "postrun_analysis_v2.json"),
            "agent_group_outcomes.csv": _sha(audit / "agent_group_outcomes.csv"),
            "plot_deepseek_first_research.py": _sha(Path(__file__)),
        },
        "figures_sha256": {name: _sha(out / name) for name in (
            "agent_regret_by_family.png", "focal_ballot_vs_settlement_changes.png",
            "monitor_reference_accuracy_by_population.png", "monitor_paired_correctness.png")},
        "raw_message_text_or_provider_payloads_used": False,
        "interpretation": "Descriptive figures from sanitized independent audit outputs; no latent-collusion or method-superiority claim.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest["figures_sha256"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=AUDIT)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    hashes = render(args.audit, args.out)
    print(json.dumps({"status": "PASS_SANITIZED_FIGURES", "figures_sha256": hashes}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
