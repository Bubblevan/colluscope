#!/usr/bin/env python3
"""Post-hoc profile-level join of already audited M4 B5 response repeats.

This is a no-call, descriptive reanalysis. It reads the hash-verified sanitized
raw-response audit rows and the frozen local M4 B5 campaign ledgers. It never
reads or emits request/response bodies or private message text.
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
REPEAT_ROWS = ROOT / "docs/results/research-sprint-20261021/raw-response-repeatability-v5/m4-b5-raw-response-repeatability-rows.csv"
REPEAT_AUDIT = ROOT / "docs/results/research-sprint-20261021/raw-response-repeatability-v5/m4-b5-raw-response-repeatability-audit.json"
CAMPAIGN = ROOT / "runs/sprint-monitor/m4-b5-context-sensitivity-campaign-v1-run"
OUTPUT = ROOT / "docs/results/research-sprint-20261021/m4-b5-existing-profile-repeatability-20261021.json"

EXPECTED_HASHES = {
    "repeat_rows": "2ca94b277f71dafb0d81534e9cb7b83b31ba9ab4cb99b2d4f16b2ecb44efcc62",
    "repeat_audit": "1926e9c60f565ef6b18ab1c3df7cd17326694b0e6cb88899fa7b500b67d7f62d",
    "campaign_schedule": "c44585532b18e8def0488c4f3de42be1c4a04009566b396251c3da2659043c3c",
    "campaign_attempt_ledger": "882e7f00b1e99a515eb352ab4828b071ccf3b763e212d095af16f6e1cc5c1715",
    "campaign_result_ledger": "25f5436374657a991d55cf2cc58af84623d2233c2d12fb3d004608079824bade",
}
VALID_LABELS = {"present", "absent", "insufficient_evidence"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    paths = {
        "repeat_rows": REPEAT_ROWS,
        "repeat_audit": REPEAT_AUDIT,
        "campaign_schedule": CAMPAIGN / "schedule.json",
        "campaign_attempt_ledger": CAMPAIGN / "request_ledger.jsonl",
        "campaign_result_ledger": CAMPAIGN / "results.jsonl",
    }
    hashes = {key: sha256(path) for key, path in paths.items()}
    for key, expected in EXPECTED_HASHES.items():
        if hashes[key] != expected:
            raise SystemExit(f"frozen input hash mismatch: {key}")

    audit = json.loads(REPEAT_AUDIT.read_text(encoding="utf-8"))
    if (
        audit.get("status") != "PASS_INDEPENDENT_RAW_RESPONSE_REPLAY"
        or audit.get("frozen_schedule_verified") is not True
        or audit.get("integrity_failures") != 0
        or audit.get("strict_parse_failures") != 0
        or audit.get("stored_mapping_mismatches") != 0
        or audit.get("assigned_pairs") != 48
    ):
        raise SystemExit("upstream raw-response audit is not a clean 48-pair replay")

    with REPEAT_ROWS.open("r", encoding="utf-8", newline="") as handle:
        repeats = list(csv.DictReader(handle))
    if len(repeats) != 48:
        raise SystemExit("repeatability rows do not match the frozen 48-pair denominator")

    observations: dict[str, list[str]] = defaultdict(list)
    permission_by_body: dict[str, str] = {}
    current_by_body: dict[str, list[str]] = defaultdict(list)
    historical_disagreements = Counter()
    for row in repeats:
        body_hash = row["request_sha256"]
        permission = row["permission"]
        if len(body_hash) != 64 or permission not in {"public_only", "privileged_audit"}:
            raise SystemExit("invalid sanitized profile key or permission")
        if row["integrity_status"] != "OK" or row["parse_status"] != "VALID":
            raise SystemExit("a raw-response pair failed the frozen integrity/parse audit")
        if row["reported_fingerprint_equal"] != "True" or row["raw_label_equal"] not in {"True", "False"}:
            raise SystemExit("an exact-request or fingerprint comparison is not valid")
        labels = [row["historical_raw_label"], row["current_raw_label"]]
        if any(label not in VALID_LABELS for label in labels):
            raise SystemExit("a raw label falls outside the frozen canonical label set")
        if body_hash in permission_by_body and permission_by_body[body_hash] != permission:
            raise SystemExit("one exact body hash appears under multiple permission names")
        permission_by_body[body_hash] = permission
        observations[body_hash].extend(labels)
        current_by_body[body_hash].append(row["current_raw_label"])
        historical_disagreements[permission] += row["raw_label_equal"] == "False"

    # Join A1 exact body hashes to the frozen current-run views by hashed source
    # unit. The unit IDs remain internal and never appear in the output.
    schedule = json.loads((CAMPAIGN / "schedule.json").read_text(encoding="utf-8"))
    attempts = read_jsonl(CAMPAIGN / "request_ledger.jsonl")
    results = read_jsonl(CAMPAIGN / "results.jsonl")
    if len(schedule["rows"]) != 232 or len(attempts) != 464 or len(results) != 232:
        raise SystemExit("the frozen campaign denominator is incomplete")
    attempt_by_row = {
        row["row_sha256"]: row for row in attempts if row.get("event") == "attempt_started"
    }
    result_by_id = {row["request_id"]: row for row in results}
    a1_counts = Counter(row["arm_id"] for row in schedule["rows"] if row["block"] == "A1")
    expected_arms = {
        "A1-PUBLIC": 24,
        "A1-PRIVILEGED-NEUTRAL": 24,
        "A1-PRIVILEGED-ORIGINAL": 24,
    }
    if dict(a1_counts) != expected_arms:
        raise SystemExit("the frozen A1 assigned arm counts changed")

    paired_by_unit: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    campaign_current_by_body: dict[str, Counter[str]] = defaultdict(Counter)
    for row in schedule["rows"]:
        if row["block"] != "A1" or row["arm_id"] not in {"A1-PUBLIC", "A1-PRIVILEGED-ORIGINAL"}:
            continue
        attempt = attempt_by_row[row["row_sha256"]]
        request_id = "m4b5_" + row["row_sha256"][:24]
        result = result_by_id[request_id]
        if result.get("status") != "HTTP_200_VALID" or result.get("parsed", {}).get("label") not in VALID_LABELS:
            raise SystemExit("an assigned A1 public/original response is not valid")
        view = "public_only" if row["arm_id"] == "A1-PUBLIC" else "privileged_audit"
        body_hash = attempt["body_sha256"]
        if body_hash not in observations or permission_by_body[body_hash] != view:
            raise SystemExit("campaign body profile is absent from the audited exact-repeat set")
        if result["parsed"]["label"] not in current_by_body[body_hash]:
            raise SystemExit("campaign result label does not match exact-body current audit outputs")
        campaign_current_by_body[body_hash][result["parsed"]["label"]] += 1
        paired_by_unit[row["unit_sha256"]][view] = (body_hash, result["parsed"]["label"])

    if len(paired_by_unit) != 24 or any(set(v) != {"public_only", "privileged_audit"} for v in paired_by_unit.values()):
        raise SystemExit("A1 public/original pairing is incomplete")
    expected_current_by_body = {body: Counter(labels) for body, labels in current_by_body.items()}
    if dict(campaign_current_by_body) != expected_current_by_body:
        raise SystemExit("A1 campaign current labels do not exactly reconcile to audit rows by body profile")

    clusters: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    assignment_changes = 0
    for views in paired_by_unit.values():
        pub_hash, pub_label = views["public_only"]
        priv_hash, priv_label = views["privileged_audit"]
        assignment_changes += pub_label != priv_label
        clusters[pub_hash].append((priv_hash, pub_label, priv_label))
    if len(clusters) != 23:
        raise SystemExit("expected 23 unique Public-only profiles after one known collision")

    profile_counts = Counter(permission_by_body.values())
    profile_stability: dict[str, dict[str, int]] = {}
    for permission in ("public_only", "privileged_audit"):
        profile_hashes = [h for h, p in permission_by_body.items() if p == permission]
        profile_stability[permission] = {
            "unique_profiles": len(profile_hashes),
            "unanimous_across_retained_historical_and_current_observations": sum(
                len(set(observations[h])) == 1 for h in profile_hashes
            ),
            "nonunanimous_across_retained_historical_and_current_observations": sum(
                len(set(observations[h])) > 1 for h in profile_hashes
            ),
            "observation_count_distribution": {
                str(n): sum(len(observations[h]) == n for h in profile_hashes)
                for n in sorted({len(observations[h]) for h in profile_hashes})
            },
        }

    determinate_clusters = 0
    stable_changed_clusters = 0
    unstable_clusters = 0
    current_changed_clusters = 0
    for public_hash, members in clusters.items():
        linked_privileged = {item[0] for item in members}
        involved = {public_hash, *linked_privileged}
        stable = all(len(set(observations[h])) == 1 for h in involved)
        if not stable:
            unstable_clusters += 1
        else:
            determinate_clusters += 1
            public_mode = observations[public_hash][0]
            privileged_modes = [observations[h][0] for h in linked_privileged]
            stable_changed_clusters += any(mode != public_mode for mode in privileged_modes)
        if any(public_label != privileged_label for _, public_label, privileged_label in members):
            current_changed_clusters += 1

    public_repeat_rows = [row for row in repeats if row["permission"] == "public_only"]
    privileged_repeat_rows = [row for row in repeats if row["permission"] == "privileged_audit"]
    if len(public_repeat_rows) != 24 or len(privileged_repeat_rows) != 24:
        raise SystemExit("frozen permission denominators changed")

    report = {
        "status": "PASS_POSTHOC_EXISTING_DATA_PROFILE_REANALYSIS",
        "evidence_class": "offline_reanalysis",
        "analysis_timing": "post_hoc_exploratory_after_campaign_and_profile_collision_audits",
        "model_api_calls": 0,
        "raw_request_response_bodies_or_private_text_emitted": False,
        "source_hashes": hashes,
        "upstream_audit": {
            "status": audit["status"],
            "pairs": audit["assigned_pairs"],
            "integrity_failures": audit["integrity_failures"],
            "strict_parse_failures": audit["strict_parse_failures"],
            "stored_mapping_mismatches": audit["stored_mapping_mismatches"],
        },
        "repeated_exact_request_profiles": {
            "profiles_by_permission": profile_counts,
            "historical_current_discordant_assigned_pairs": dict(historical_disagreements),
            "unique_profile_stability": profile_stability,
            "reported_fingerprint_equal_for_all_pairs": True,
        },
        "current_campaign_a1_view_contrast": {
            "assigned_contexts": 24,
            "unique_public_profiles": len(clusters),
            "current_assignment_level_public_to_privileged_original_label_changes": assignment_changes,
            "current_unique_public_profile_clusters_with_any_linked_change": current_changed_clusters,
        },
        "combined_historical_current_profile_comparison": {
            "unique_public_profile_clusters": len(clusters),
            "clusters_with_unanimous_labels_for_public_and_all_linked_privileged_profiles": determinate_clusters,
            "unanimous_clusters_with_public_privileged_mode_change": stable_changed_clusters,
            "clusters_with_any_nonunanimous_exact_body_profile": unstable_clusters,
            "candidate_v2_gate_context": "The candidate's 18/23 determinate-cluster rule is not met by these retained cross-run observations. This is not a substitute for its planned within-campaign interleaved repeats.",
        },
        "interpretation": (
            "The retained exact-request comparisons show frequent label variation within the same Public-only body profile across historical/current observations. "
            "This weakens a simple view-only reading of the finite current contrast and reduces the expected information value of another repeat campaign. "
            "Because repeats span separate runs, they do not identify same-window stochasticity, hidden provider-state changes, or the cause of view differences."
        ),
        "decision": "DEPRIORITIZE_NEW_REPEATABILITY_CALLS_PENDING_A_MORE_DECISIVE_QUESTION",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
