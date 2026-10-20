# Submission Candidate Reproduction Index

Run commands from `reference/m1-p0-local-qwen-integration` in PowerShell. These commands call no model. Python version used for this preparation: 3.12.4 on Windows 11; PDF output uses ReportLab/Pillow/Markdown. Exact package lock details and PDF builder hashes are included in the submission manifest.

## Candidate-specific checks

```powershell
python scripts/freeze_submission_validation_scenarios.py --check
python scripts/freeze_submission_validation_groups.py --check
python scripts/audit_submission_claims.py
python scripts/render_m3_svg_for_submission.py
python scripts/build_submission_pdf.py
python scripts/validate_submission_pdf.py
python scripts/build_submission_manifest.py
python scripts/verify_submission_manifest.py
```

The M3 SVG converter refuses input whose SHA differs from the frozen audit figure. Scenario/group freeze and claim audit are deterministic. `audit_submission_claims.py` recomputes the paper's headline M1 prospective counts, M2 F2/F3 task/view scores and M3 arm/self-history/token figures from frozen sanitized audit exports; it does not access the ACL-restricted M3 private run. The PDF builder pins its metadata timestamp (`SOURCE_DATE_EPOCH`) and two independent builds produced byte-identical outputs in the recorded environment. The manifest lists hashes of included source, sanitized evidence and output files; its companion verifier rechecks file presence, hash, size, privacy-path exclusion and agreement with the PDF validation record. The verifier output is intentionally excluded from the manifest to avoid a self-reference. To check page rendering against a reviewed copy, render each PDF with `pdftoppm` to `page-1.png` through `page-5.png`, then run `python scripts/compare_submission_page_renders.py <previous-page-dir> <current-page-dir>`.

## Historical audit commands

These reproduce the existing independent audit paths and may require ignored local runs/dependencies:

```powershell
$env:PYTHONPATH = 'src'
python scripts/audit_m1_100.py --run runs/m1_100/extension-75-20261019-run02
python scripts/audit_m2_final.py --help
python scripts/audit_m3_mechanism.py --help
```

M1 and M3 raw data and all private messages remain local/ignored; do not select a `docs/` output path for an audit that could emit private data. M2 final result generation is offline-only and must be directed to an empty dedicated output folder if rerun. The M3 audit reads the ACL-restricted run and writes a new audit folder; preserve its raw-attempt logs and do not overwrite `docs/results/m3-mechanism-audit-final/`.

The final pre-existing audit/reproduction reports are:

- M0: `docs/M0_EVIDENCE.md`, `docs/M0_DECISION.md`, `runs/m0/evidence/pytest-m0-final-3.log`.
- M1: `docs/M1_100_EVIDENCE.md`, `docs/M1_100_SCIENTIFIC_AUDIT.md`, `docs/M1_100_DECISION.md` and `docs/M1_P0_POSTRUN_SCIENTIFIC_AUDIT.md`.
- M2: `docs/M2_FINAL_SCIENTIFIC_SYNTHESIS.md`, `docs/M2_V3_DECISION.md`, `docs/results/m2-final-scientific-synthesis/m2_final_audit_summary.json`.
- M3: `docs/M3_MECHANISM_PROTOCOL.md`, `docs/M3_SCIENTIFIC_RESULTS.md`, `docs/M3_EXECUTION_EVIDENCE.md`, `docs/M3_REPRODUCTION.md`, `docs/M3_DECISION.md`, `docs/results/m3-mechanism-audit-final/`.

## Raw-data boundary

The public candidate bundle contains sanitized summaries, code, source hashes and manifest references. It cannot reproduce every M3 row from the pushed repository alone because the complete raw prompts, private messages and responses are excluded and ACL restricted. Controlled reviewer access must be arranged explicitly; private text is not published as a convenience. Historical M0-M3 run outputs and hashes are not rewritten by submission preparation.

The latest expansion review and positive-control decision are recorded in `docs/EXPANSION_REVIEW_2026-10-20.md`. It is planning documentation only: no M4 or reference baseline was run, and the 24-group validation freeze remains unchanged.
