# ColluScope Apart report: reproducibility materials

This index accompanies `colluscope_apart_2026_submission_report.md` and the rendered PDF. Every listed command is offline; none dispatches a model or provider request.

## Build the report

From the repository root:

```powershell
python scripts/build_apart_submission_pdf.py
```

The editable source is `docs/submission/colluscope_apart_2026_submission_report.md`. The output is `output/pdf/colluscope_apart_2026_submission_report.pdf`.

## Evidence index

- M1 target-choice audit: `docs/M1_100_SCIENTIFIC_AUDIT.md`.
- M3 behavioral and counterfactual results: `docs/M3_SCIENTIFIC_RESULTS.md` and `docs/results/m3-mechanism-audit-final/`.
- M4 evidence-view and repeatability analysis: `docs/M4_B5_CONTEXT_SENSITIVITY_EVIDENCE.md` and `docs/results/research-sprint-20261021/`.
- DeepSeek-first agent and monitor extension: `docs/M4_DEEPSEEK_FIRST_RESEARCH_RESULTS.md` and `docs/results/deepseek-first-m4/audit/`.
- Message-visibility V1 preregistration and stopped-run evidence: `docs/SHARED_TARGET_MESSAGE_VISIBILITY_V1_PROTOCOL.md`, `docs/results/shared-target-message-visibility-v1/`, and `research/experiments/shared-target-message-visibility-v1/`.
- Shared-target message-source study: `docs/SHARED_TARGET_MESSAGE_SOURCE_V1_PROTOCOL.md`, `docs/results/shared-target-message-source-v1/`, and `research/experiments/shared-target-message-source-v1/`. The package includes sanitized context rows, a request ledger, independent no-call replay, interpretation, adversarial self-review, and the lifecycle closure.
- Scientific direction and the proposed future causal contrast: `docs/SCIENCE_DIRECTION_HANDOFF_20261021_STMI.md`.

## No-call checks and reanalysis

```powershell
python scripts/researchctl.py audit
python scripts/freeze_shared_target_message_visibility_v1.py --check
python scripts/run_shared_target_message_visibility_v1.py --check-only
python scripts/analyze_shared_target_message_visibility_v1.py --write
python scripts/audit_shared_target_message_source_v1.py
```

`researchctl audit` verifies the record registry and pinned files; it does not evaluate scientific validity. The freeze and check-only commands do not make network requests. Re-running the analyzer requires the ACL-restricted local run directory at `logs/shared-target-message-visibility-v1/`; it reads saved responses and does not call the model.

## Access and replay limits

Raw request/response bytes and private sender messages for paid runs remain in ACL-restricted, Git-ignored local run roots. The repository includes sanitized outputs, denominators, protocol files, and provenance records, but those public-facing files alone cannot reconstruct every provider response byte-for-byte. Third-party replay of raw responses requires separately arranged access to the protected run records. Provider aliases and fingerprints are not immutable weight hashes.

The new message-visibility attempt is a pre-sprint, inconclusive result. Its authorization is consumed; the check-only commands above do not resume or repeat it.

The 576-request message-source study is a separate pre-sprint cycle. The independent replay command reads the ACL-restricted run at `runs/shared-target-message-source-v1-run/` and writes/prints a sanitized audit without network access. Its model authorization is consumed; no command in this package resumes or repeats that study.
