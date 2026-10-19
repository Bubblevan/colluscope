#!/usr/bin/env python3
"""Compare the four independently audited M2-V2 compatibility gates."""
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
DEFAULT_INPUTS = [
    ROOT / "runs/m2-v2/recovery-20261019/study/analysis/preflight-independent-response-audit.json",
    ROOT / "runs/m2-v2/recovery-20261019/repair-01/analysis/preflight-independent-response-audit.json",
    ROOT / "runs/m2-v2/recovery-20261019/repair-02/analysis/preflight-independent-response-audit.json",
    ROOT / "runs/m2-v2/recovery-20261019/repair-03/analysis/preflight-independent-response-audit.json",
]
CANDIDATES = [
    "M2-V2-C1-full-json-schema",
    "M2-V2-C2-full-json-object-schema",
    "M2-V2-C3-compact-cited-json-schema",
]


def summarize(inputs: list[Path], csv_path: Path, figure_path: Path) -> list[dict]:
    if len(inputs) != 4:
        raise ValueError("expected initial gate plus exactly three frozen repairs")
    rows = []
    rounds = ["initial", "repair_01", "repair_02", "repair_03"]
    for round_name, path in zip(rounds, inputs, strict=True):
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("decision") != "NO_GO_INTERFACE":
            raise ValueError(f"unexpected gate decision in {path}")
        if report.get("physical_http_attempts") != 30 or report.get("external_model_calls") != 0:
            raise ValueError(f"unexpected attempt budget or external calls in {path}")
        found = {row["candidate_id"]: row for row in report["candidate_results"]}
        if set(found) != set(CANDIDATES):
            raise ValueError(f"candidate set differs from the frozen three-candidate set in {path}")
        for candidate in CANDIDATES:
            result = found[candidate]
            valid = result["status_counts"].get("valid", 0)
            invalid = result["status_counts"].get("invalid_output", 0)
            if valid + invalid != 10:
                raise ValueError(f"candidate denominator is not ten in {path}/{candidate}")
            rows.append({
                "round": round_name,
                "candidate_id": candidate,
                "valid": valid,
                "invalid": invalid,
                "assigned": 10,
                "valid_rate": valid / 10,
                "gate_10_of_10": valid == 10,
                "physical_http_attempts_all_candidates": 30,
                "source_summary_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            })
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    figure, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
    x = list(range(4))
    width = 0.23
    palette = ["#28658B", "#51936C", "#A55A5A"]
    for index, (candidate, color) in enumerate(zip(CANDIDATES, palette, strict=True)):
        vals = [next(row["valid"] for row in rows
                     if row["round"] == round_name and row["candidate_id"] == candidate)
                for round_name in rounds]
        bars = axis.bar([value + (index - 1) * width for value in x], vals,
                        width=width, label=candidate.split("-")[2], color=color)
        for bar, value in zip(bars, vals, strict=True):
            axis.text(bar.get_x() + bar.get_width() / 2, value + 0.13,
                      f"{value}/10", ha="center", va="bottom", fontsize=8)
    axis.axhline(10, color="#922B21", linestyle="--", linewidth=1.6,
                 label="Required gate: 10/10")
    axis.set_xticks(x, ["Initial", "Repair 01", "Repair 02", "Repair 03"])
    axis.set_ylim(0, 11.2)
    axis.set_ylabel("Strict contract-valid responses (of 10)")
    axis.set_title("M2-V2 bounded compatibility repairs")
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="lower right")
    figure.text(0.01, -0.01,
                "Each round: same ten F1 view × permission cases per candidate; validity only, not monitor accuracy.",
                ha="left", fontsize=8, color="#444444")
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(figure_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs=4, type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--csv", type=Path, default=ROOT / "docs/results/m2_v2_repair_series.csv")
    parser.add_argument("--figure", type=Path, default=ROOT / "docs/images/M2_V2_repair_series.png")
    args = parser.parse_args()
    rows = summarize(args.inputs, args.csv, args.figure)
    print(json.dumps({"csv": str(args.csv), "figure": str(args.figure),
                      "rows": rows}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
