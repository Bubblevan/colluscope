"""Create a deterministic inventory of submission-prep deliverables and inputs."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/results/submission-prep/submission_manifest.json"
VERIFICATION = ROOT / "docs/results/submission-prep/manifest-verification.json"
BASE_COMMIT = "acf80705b8f3af6521613aef80b0c736cabb5f45"

EXACT_PATHS = (
    ".gitattributes",
    "configs/sprint-validation-scenarios.json",
    "configs/sprint-validation-groups.json",
    "docs/ITERATION_LOG.md",
    "docs/RESEARCH_RISK_REGISTER.md",
    "docs/EXPANSION_REVIEW_2026-10-20.md",
    "docs/PRE_SPRINT_WORK_DISCLOSURE.md",
    "docs/SPRINT_NEW_VALIDATION_PROTOCOL.md",
    "docs/SUBMISSION_CLAIM_EVIDENCE_AUDIT.md",
    "docs/SUBMISSION_OFFICIAL_REQUIREMENTS.md",
    "docs/SUBMISSION_FORMAT_AND_RENDER_CHECK.md",
    "docs/SUBMISSION_REPRODUCTION_INDEX.md",
    "docs/SUBMISSION_READINESS_DECISION.md",
    "docs/M0_EVIDENCE.md",
    "docs/M0_DECISION.md",
    "docs/M1_100_PROTOCOL.md",
    "docs/M1_100_EVIDENCE.md",
    "docs/M1_100_SCIENTIFIC_AUDIT.md",
    "docs/M1_100_DECISION.md",
    "docs/M1_P0_POSTRUN_SCIENTIFIC_AUDIT.md",
    "docs/M2_FINAL_SCIENTIFIC_SYNTHESIS.md",
    "docs/M2_V3_DECISION.md",
    "docs/M3_MECHANISM_PROTOCOL.md",
    "docs/M3_SCIENTIFIC_RESULTS.md",
    "docs/M3_EXECUTION_EVIDENCE.md",
    "docs/M3_REPRODUCTION.md",
    "docs/M3_DECISION.md",
    "docs/M3_BAD_CASE_AUDIT.md",
    "scripts/audit_submission_claims.py",
    "scripts/build_submission_pdf.py",
    "scripts/build_submission_manifest.py",
    "scripts/compare_submission_page_renders.py",
    "scripts/verify_submission_manifest.py",
    "scripts/freeze_submission_validation_groups.py",
    "scripts/freeze_submission_validation_scenarios.py",
    "scripts/render_m3_svg_for_submission.py",
    "scripts/validate_submission_pdf.py",
    "submission-prep/paper.md",
    "submission-prep/main.tex",
    "output/pdf/ColluScope_Submission_Candidate_2026-10-20.pdf",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tracked_path(relative: str) -> Path:
    path = ROOT / relative
    if not path.is_file():
        raise FileNotFoundError(f"required manifest input is missing: {relative}")
    return path


def main() -> int:
    files: set[str] = set(EXACT_PATHS)
    for directory in (
        ROOT / "docs/results/submission-prep",
        ROOT / "docs/results/m3-mechanism-audit-final",
        ROOT / "docs/results/paper-figures",
    ):
        files.update(
            path.relative_to(ROOT).as_posix()
            for path in directory.rglob("*")
            if path.is_file() and path.name not in {OUTPUT.name, VERIFICATION.name}
        )
    m2 = ROOT / "docs/results/m2-final-scientific-synthesis"
    files.update(
        path.relative_to(ROOT).as_posix()
        for path in m2.glob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".json"}
    )
    figure_dir = m2 / "figures"
    files.update(
        path.relative_to(ROOT).as_posix()
        for path in figure_dir.glob("*.png")
        if path.is_file()
    )

    records = []
    for relative in sorted(files):
        path = tracked_path(relative)
        records.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256(path)})

    packages = {}
    for distribution in ("reportlab", "Markdown", "Pillow", "pdfplumber"):
        try:
            packages[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            packages[distribution] = None

    manifest = {
        "manifest_id": "colluscope-submission-readiness-v1",
        "source_baseline_commit": BASE_COMMIT,
        "branch_at_manifest_generation": subprocess.run(
            ["git", "branch", "--show-current"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip(),
        "execution_environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": packages,
        },
        "model_calls_during_submission_prep": 0,
        "private_m3_raw_prompts_messages_and_responses_included": False,
        "files": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"files={len(records)}")
    print(f"manifest={OUTPUT.relative_to(ROOT).as_posix()}")
    print(f"manifest_sha256={sha256(OUTPUT)}")
    print("model_calls=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
