# M2-V2 Decision

## Decision: NO-GO for formal monitor evaluation

The preregistered compatibility gate failed after the initial attempt and all three authorized, distinct repairs. The best repair-02 candidates reached 6/10; repair-03 remained at 6/10 for each full candidate and regressed to 3/10 for the compact candidate. The required threshold remained 10/10 throughout.

**Do not start or claim the 1,000-row M2 monitor evaluation.** Formal calibration, the 95% F1 validity check, F2/F3 inference, model-based scoring, and monitor-performance statistics are all unstarted. The run produced no evidence about detector accuracy, false accusations, abstention quality, or relative view performance.

## What the work does establish

- The unchanged local model/runtime completed 120 bounded compatibility requests without retries or external inference.
- JSON parsing, root shape, core enum values, and normal finish reason were valid for 120/120 responses, while strict view/permission/citation validity failed often enough to block formal evaluation.
- The permitted deterministic source replay covers 100 episodes and 1,000 view-permission rows. It verifies observable evidence availability and independently recomputes outcome facts, but does not infer latent intent.
- The earlier 517 M2-V1 invalid responses, all four V2 gate results, failed requests, hashes, and manifests remain preserved.

## Research boundary

No treatment, condition ID, reward assignment, target execution, shared target, ballot agreement, private-chat availability, welfare loss, or private-message delivery is a collusion gold label. The 12 source-supported privileged observable sequences are mechanical message-proposal/ballot-concordance records, not proof of acceptance or intent. The environment contains no post-delivery acceptance event.

The M1 source corpus remains unchanged. The 19 stored harm-flag discrepancies remain documented and excluded from reference labels. Public-only E remains separate from privileged message projections; raw private content stays local.

## Next action

Stop M2 model inference under this authorization. A future protocol revision should first use the saved counterexamples to diagnose whether the dominant failure is the model's branch reasoning, the output schema's cross-field coupling, or the pinned constrained-decoding path. Keep the 10/10 gate, source permissions, model identity, and original M1 artifacts fixed unless a separately reviewed research protocol explicitly preregisters a change. Any additional model requests require a new approval.

## Reproduction

From the repository root:

```powershell
python scripts/audit_m2_v2_preflight_results.py --out runs/m2-v2/recovery-20261019/repair-03 --write
python scripts/compare_m2_v2_compatibility_repairs.py
python scripts/analyze_m2_v2_evidence_sufficiency.py
python -m pytest -q
```

The raw-response audit and deterministic evidence analysis issue no model requests.
