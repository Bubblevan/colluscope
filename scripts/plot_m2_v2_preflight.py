#!/usr/bin/env python3
"""Export sanitized compatibility tables and plot the M2-V2 interface gate."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "runs/m2-v2/recovery-20261019/study/analysis/preflight-independent-response-audit.json"
DEFAULT_IMAGE = ROOT / "docs/images/M2_V2_compatibility_gate.png"
DEFAULT_RESULTS = ROOT / "docs/results"


def export(summary_path: Path, image_path: Path, results_dir: Path) -> dict:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("decision") != "NO_GO_INTERFACE":
        raise ValueError("the frozen compatibility gate summary is not a NO_GO_INTERFACE result")
    candidates = summary["candidate_results"]
    rows = []
    for result in candidates:
        valid = result["status_counts"].get("valid", 0)
        invalid = result["status_counts"].get("invalid_output", 0)
        rows.append({"candidate_id": result["candidate_id"], "valid": valid,
                     "invalid": invalid, "total": valid + invalid,
                     "valid_rate": valid / (valid + invalid),
                     "all_ten_valid_gate": result["all_ten_valid"]})
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "m2_v2_preflight_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    with (results_dir / "m2_v2_candidate_compatibility.csv").open(
            "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    by_view = []
    for key, counts in summary["status_counts_by_view_permission"].items():
        view, permission = key.split("|", 1)
        valid, invalid = counts.get("valid", 0), counts.get("invalid_output", 0)
        by_view.append({"view": view, "permission": permission, "valid": valid,
                        "invalid": invalid, "total": valid + invalid})
    with (results_dir / "m2_v2_view_permission_compatibility.csv").open(
            "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(by_view[0]))
        writer.writeheader()
        writer.writerows(by_view)
    bad_cases = summary["bad_cases"]
    bad_fields = ["candidate_id", "view_name", "permission_profile", "status", "error",
                  "error_class", "all_detected_violations", "claim_values", "citation_count", "citation_prefix_counts",
                  "unknown_citation_prefix_counts", "citation_counts_by_claim",
                  "citation_prefix_counts_by_claim", "unknown_citation_prefix_counts_by_claim",
                  "abstention_reason_count",
                  "abstention_reasons_valid"]
    with (results_dir / "m2_v2_bad_case_diagnostics.csv").open(
            "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=bad_fields)
        writer.writeheader()
        for case in bad_cases:
            safe_case = dict(case)
            for key in ("claim_values", "citation_prefix_counts", "unknown_citation_prefix_counts",
                        "citation_counts_by_claim", "citation_prefix_counts_by_claim",
                        "unknown_citation_prefix_counts_by_claim", "all_detected_violations"):
                safe_case[key] = json.dumps(safe_case[key], ensure_ascii=False, sort_keys=True)
            writer.writerow(safe_case)

    labels = ["C1 · full schema", "C2 · JSON object", "C3 · compact schema"]
    values = [row["valid"] for row in rows]
    figure, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
    colors = ["#2979A8", "#2979A8", "#9A5B5B"]
    bars = axis.bar(labels, values, color=colors, width=0.58)
    axis.axhline(10, color="#A62D2D", linestyle="--", linewidth=1.8,
                 label="Interface gate: 10 of 10 valid")
    axis.set_ylim(0, 10.8)
    axis.set_ylabel("Strictly valid outputs (of 10 fixed inputs)")
    axis.set_title("M2-V2 compatibility screen")
    axis.grid(axis="y", alpha=0.22)
    axis.set_axisbelow(True)
    axis.legend(loc="upper right", frameon=False)
    for bar, row in zip(bars, rows):
        axis.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                  f"{row['valid']}/10", ha="center", va="bottom", fontsize=12)
    figure.text(0.01, -0.01,
                "Same fixed F1 case across five views × two permissions. Interface validity only; not monitor accuracy.",
                ha="left", fontsize=9, color="#444444")
    image_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(image_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
    return {"candidate_csv": str(results_dir / "m2_v2_candidate_compatibility.csv"),
            "view_permission_csv": str(results_dir / "m2_v2_view_permission_compatibility.csv"),
            "bad_case_csv": str(results_dir / "m2_v2_bad_case_diagnostics.csv"),
            "summary_json": str(results_dir / "m2_v2_preflight_summary.json"),
            "figure": str(image_path), "candidate_valid_counts": values}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    print(json.dumps(export(args.summary, args.image, args.results_dir), sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
