"""Verify every file hash and privacy boundary in the submission manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/results/submission-prep/submission_manifest.json"
DEFAULT_OUTPUT = ROOT / "docs/results/submission-prep/manifest-verification.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    failures: list[str] = []
    seen: set[str] = set()
    for record in manifest.get("files", []):
        relative = record["path"]
        normalized = Path(relative)
        if normalized.is_absolute() or ".." in normalized.parts:
            failures.append(f"unsafe path: {relative}")
            continue
        if relative in seen:
            failures.append(f"duplicate path: {relative}")
            continue
        seen.add(relative)
        path = ROOT / normalized
        if not path.is_file():
            failures.append(f"missing file: {relative}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != record["sha256"]:
            failures.append(f"hash mismatch: {relative}")
        if path.stat().st_size != record["size_bytes"]:
            failures.append(f"size mismatch: {relative}")
        posix = normalized.as_posix().lower()
        if posix.startswith("runs/m3/") or ".env" in normalized.name.lower():
            failures.append(f"private or credential path included: {relative}")

    if manifest.get("model_calls_during_submission_prep") != 0:
        failures.append("manifest does not assert zero model calls during preparation")
    if manifest.get("private_m3_raw_prompts_messages_and_responses_included") is not False:
        failures.append("manifest does not exclude private M3 raw data")
    if args.manifest.name in seen:
        failures.append("manifest recursively includes its own hash")

    pdf_record = next((r for r in manifest["files"] if r["path"].endswith(".pdf")), None)
    validation_path = ROOT / "docs/results/submission-prep/pdf-validation.json"
    if pdf_record is None or not validation_path.is_file():
        failures.append("PDF or PDF validation record missing")
    else:
        validation = json.loads(validation_path.read_text(encoding="utf-8"))
        if validation.get("pdf_sha256") != pdf_record.get("sha256"):
            failures.append("PDF hash differs from structural validation record")

    result = {
        "status": "PASS" if not failures else "FAIL",
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "file_count": len(seen),
        "model_calls": manifest.get("model_calls_during_submission_prep"),
        "private_raw_paths_included": False,
        "failures": failures,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
