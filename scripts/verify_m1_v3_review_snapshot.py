#!/usr/bin/env python3
"""Hash-verify a non-authorizing M1 v3 review snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_set_sha256(rows: list[dict[str, str]]) -> str:
    payload = json.dumps(sorted(rows, key=lambda row: row["path"]),
                         ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify(manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "review_snapshot_only_not_preregistration_or_authorization":
        raise ValueError("manifest must explicitly remain a review snapshot")
    from colluscope.m1_package_replication_v3_runtime import FROZEN_INPUT_PATHS

    runtime_rows = manifest.get("runtime_frozen_input_hashes")
    review_rows = manifest.get("review_artifact_hashes")
    runtime_paths = manifest.get("runtime_frozen_input_paths")
    if not isinstance(runtime_rows, list) or not isinstance(review_rows, list):
        raise ValueError("manifest is missing hash lists")
    if runtime_paths != list(FROZEN_INPUT_PATHS):
        raise ValueError("manifest runtime input paths differ from the live runner's frozen set")
    checks: list[dict[str, Any]] = []
    for category, rows in (("runtime", runtime_rows), ("review", review_rows)):
        seen: set[str] = set()
        for row in rows:
            rel = row.get("path")
            if not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts:
                raise ValueError(f"unsafe relative path in {category} hash set")
            if rel in seen:
                raise ValueError(f"duplicate path in {category} hash set: {rel}")
            seen.add(rel)
            path = ROOT / rel
            actual = sha256(path) if path.is_file() else None
            checks.append({"category": category, "path": rel,
                           "expected_sha256": row.get("sha256"), "actual_sha256": actual,
                           "match": actual == row.get("sha256")})
    runtime_set = canonical_set_sha256(runtime_rows)
    review_set = canonical_set_sha256(review_rows)
    if runtime_set != manifest.get("runtime_frozen_input_set_sha256"):
        raise ValueError("runtime hash-set digest mismatch")
    if review_set != manifest.get("review_artifact_set_sha256"):
        raise ValueError("review artifact hash-set digest mismatch")
    verifier = manifest.get("verification_script", {})
    verifier_path = verifier.get("path")
    if not isinstance(verifier_path, str) or verifier_path != Path(__file__).relative_to(ROOT).as_posix():
        raise ValueError("manifest does not identify this verifier")
    verifier_hash = sha256(Path(__file__))
    if verifier_hash != verifier.get("sha256"):
        raise ValueError("verification script hash mismatch")
    failed = [row for row in checks if not row["match"]]
    if failed:
        raise ValueError(f"{len(failed)} hash checks failed")
    return {
        "status": "PASS_M1_V3_REVIEW_SNAPSHOT_HASHES",
        "manifest_sha256": sha256(manifest_path),
        "runtime_inputs_verified": len(runtime_rows),
        "review_artifacts_verified": len(review_rows),
        "verification_script_sha256": verifier_hash,
        "approval_present": manifest.get("authorization_state", {}).get("m1_specific_approval_present", False),
        "generation_ceiling": manifest.get("candidate_call_envelope", {}).get("logical_generations_max"),
        "physical_http_ceiling": manifest.get("candidate_call_envelope", {}).get("physical_http_attempts_max"),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path,
                        default=ROOT / "research/drafts/m1-package-replication-v3-review-manifest-r2-20261021.json")
    args = parser.parse_args()
    try:
        result = verify(args.manifest.resolve())
    except Exception as exc:
        print(json.dumps({"status": "FAIL_REVIEW_SNAPSHOT_HASHES",
                          "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
