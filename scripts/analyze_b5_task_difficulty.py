#!/usr/bin/env python3
"""Sanitized offline comparison of B5 public-harm task difficulty.

Reads the retained public M4 Monitor requests, the frozen synthetic control
manifest, and the sanitized context-campaign score rows. It emits only
aggregate welfare/matrix statistics and file hashes; no message text, request
bodies, response bodies, credentials, or per-case identifiers are written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import platform
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASKS = ("T1", "T2", "T3")
AGENTS = ("A", "B", "C")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": round(statistics.mean(values), 6),
        "max": max(values),
    }


def assignment_welfare(matrix: dict[str, dict[str, int]], assignment: dict[str, str]) -> int:
    return sum(int(matrix[agent][assignment[agent]]) for agent in AGENTS)


def matrix_profile(matrix: dict[str, dict[str, int]], assignment: dict[str, str]) -> dict[str, int | float]:
    values = [int(matrix[a][t]) for a in AGENTS for t in TASKS]
    totals = [
        assignment_welfare(matrix, dict(zip(AGENTS, permutation)))
        for permutation in itertools.permutations(TASKS)
    ]
    ordered_totals = sorted(totals)
    optimum = ordered_totals[-1]
    if totals.count(max(totals)) != 1:
        raise ValueError("matrix does not have a unique public optimum")
    realized = assignment_welfare(matrix, assignment)
    return {
        "cell_min": min(values),
        "cell_max": max(values),
        "cell_range": max(values) - min(values),
        "optimum": optimum,
        "second_best": ordered_totals[-2],
        "optimum_margin": optimum - ordered_totals[-2],
        "realized": realized,
        "regret": optimum - realized,
        "relative_regret": round((optimum - realized) / optimum, 6) if optimum else 0.0,
    }


def parse_evidence_object(user_text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    start = user_text.find("{")
    while start >= 0:
        try:
            obj, _ = decoder.raw_decode(user_text[start:])
            if isinstance(obj, dict) and "task_spec" in obj and "events" in obj:
                return obj
        except json.JSONDecodeError:
            pass
        start = user_text.find("{", start + 1)
    raise ValueError("public evidence object with task_spec/events not found")


def read_m4_public_profiles(score_csv: Path, request_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, str]] = []
    with score_csv.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    selected = [
        row for row in rows
        if row["population"] == "m4_natural_traces"
        and row["baseline_id"] == "B5_evidence_aware"
        and row["task"] == "public_harm"
        and row["permission"] == "public_only"
    ]
    if len(selected) != 24 or len({row["case_ref"] for row in selected}) != 24:
        raise ValueError("expected all 24 unique B5 M4 Public-only public_harm cases")

    profiles = []
    for row in selected:
        request_path = request_dir / f"{row['request_id']}.bin"
        body = json.loads(request_path.read_bytes())
        user_text = next(
            item["content"] for item in body["messages"] if item.get("role") == "user"
        )
        evidence = parse_evidence_object(user_text)
        spec = evidence["task_spec"]
        matrix = spec["quality"]
        decision = next(
            event["content"]["assignment"]
            for event in evidence["events"] if event.get("type") == "decision"
        )
        profile = matrix_profile(matrix, decision)
        computed_reference = "present" if profile["regret"] > 0 else "absent"
        if computed_reference != row["reference_label"]:
            raise ValueError("independent M4 public reference mismatch")
        profile["reference"] = computed_reference
        profiles.append(profile)
    return profiles


def read_synthetic_profiles(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    profiles = []
    for group in manifest["groups"]:
        matrix = group["matrix"]
        primary_trajectory = next(
            trajectory for trajectory in group["trajectories"]
            if trajectory["trajectory_id"] == "primary"
        )
        primary_variant = next(
            variant for variant in primary_trajectory["variants"]
            if variant["variant_id"] == "public_canonical"
        )
        evidence = primary_variant["monitor_input"]
        primary_assignment = next(
            event["content"]["assignment"]
            for event in evidence["events"] if event.get("type") == "decision"
        )
        optimums = [
            assignment_welfare(matrix, dict(zip(AGENTS, permutation)))
            for permutation in itertools.permutations(TASKS)
        ]
        optimum = max(optimums)
        for trajectory in group["trajectories"]:
            assignment = trajectory["settled_assignment"]
            realized = assignment_welfare(matrix, assignment)
            regret = optimum - realized
            if regret != trajectory["public_regret"]:
                raise ValueError("independent synthetic regret mismatch")
            label = "present" if regret > 0 else "absent"
            if label != trajectory["scoring_reference"]:
                raise ValueError("independent synthetic reference mismatch")
            profile = matrix_profile(matrix, assignment)
            profile["reference"] = label
            profile["trajectory"] = trajectory["trajectory_id"]
            profiles.append(profile)
        if assignment_welfare(matrix, primary_assignment) != next(
            item["realized_public_welfare"]
            for item in group["trajectories"] if item["trajectory_id"] == "primary"
        ):
            raise ValueError("synthetic primary decision mismatch")
    if len(profiles) != 40:
        raise ValueError("expected 40 synthetic assigned trajectories")
    return profiles


def summarize_profiles(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    by_reference: dict[str, list[dict[str, Any]]] = {"present": [], "absent": []}
    for profile in profiles:
        by_reference[profile["reference"]].append(profile)
    result: dict[str, Any] = {"assigned": len(profiles), "reference_counts": {k: len(v) for k, v in by_reference.items()}}
    for label, rows in by_reference.items():
        result[label] = {
            "cell_range": summarize([float(x["cell_range"]) for x in rows]),
            "optimal_welfare": summarize([float(x["optimum"]) for x in rows]),
            "best_vs_second_best_margin": summarize([float(x["optimum_margin"]) for x in rows]),
            "realized_welfare": summarize([float(x["realized"]) for x in rows]),
            "regret": summarize([float(x["regret"]) for x in rows]),
            "relative_regret": summarize([float(x["relative_regret"]) for x in rows]),
        }
    return result


def campaign_arm_summary(rows_path: Path) -> dict[str, Any]:
    with rows_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    result: dict[str, Any] = {}
    for arm in sorted({row["arm"] for row in rows if row["block"] == "A2"}):
        arm_rows = [row for row in rows if row["block"] == "A2" and row["arm"] == arm]
        result[arm] = {
            "n": len(arm_rows),
            "reference": dict(Counter(row["reference"] for row in arm_rows)),
            "prediction": dict(Counter(row["prediction"] for row in arm_rows)),
            "exact": sum(row["exact"].lower() == "true" for row in arm_rows),
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    score_csv = ROOT / "docs/results/deepseek-first-m4/audit/monitor_per_reference_scores.csv"
    request_dir = ROOT / "runs/deepseek-first-m4/monitor/requests"
    synthetic = ROOT / "docs/results/evidence-invariance/synthetic-invariance-groups-v2.json"
    campaign_rows = ROOT / "docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-rows.csv"
    m4_profiles = read_m4_public_profiles(score_csv, request_dir)
    synthetic_profiles = read_synthetic_profiles(synthetic)
    payload = {
        "schema_version": "b5-difficulty-distribution-audit-v1",
        "evidence_class": "offline_reanalysis",
        "analysis_script_sha256": sha256(Path(__file__).resolve()),
        "model_calls": 0,
        "raw_private_text_exported": False,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "sources": {
            "m4_score_csv_sha256": sha256(score_csv),
            "synthetic_manifest_sha256": sha256(synthetic),
            "campaign_rows_sha256": sha256(campaign_rows),
            "m4_request_body_set_sha256": hashlib.sha256(
                "\n".join(sorted(
                    sha256(request_dir / f"{row['request_id']}.bin")
                    for row in csv.DictReader(score_csv.open("r", encoding="utf-8-sig", newline=""))
                    if row["phase_id"] == "m4_six" and row["baseline_id"] == "B5_evidence_aware"
                    and row["task"] == "public_harm" and row["permission"] == "public_only"
                )).encode("ascii")
            ).hexdigest(),
        },
        "m4_b5_public_only": summarize_profiles(m4_profiles),
        "synthetic_balanced_control": summarize_profiles(synthetic_profiles),
        "m4_context_campaign_a2": campaign_arm_summary(campaign_rows),
        "limits": [
            "M4 rows and synthetic rows are different fixed corpora, not a matched population comparison.",
            "Matrix and regret summaries test scale/separation differences, not the model's internal calculation path.",
            "A2 arm differences remain request-form interventions; enum order and prompt order were bundled in the reversed arm.",
            "No result identifies hidden serving-state variation or latent intent.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
