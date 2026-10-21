# Autoresearch Follow-up — M1 action-level outcome audit (2026-10-21)

## INSPECT

The selected M1 v3 candidate uses settled target allocation as its primary outcome. The historical M1-100 extension has 75 retained T/B episodes across 15 matched groups. A successful environment settlement does not, in general, imply both rewarded agents cast the same ballot: the three-way plurality tie-break may select a single chair ballot, and C may independently vote for the target.

## SPECIFY

Falsifying counterexamples for an interpretation of settlement as pair action are: C casts the target ballot; only one of A/B casts it; or a single target ballot is selected by the chair in a three-way tie. Conversely, pair co-voting still cannot distinguish communication-induced coordination from parallel choice under a shared known target.

## IMPLEMENT

Added `scripts/analyze_m1_100_ballot_decomposition.py`. It hash-checks raw T/B/schedule inputs, validates all assigned episode IDs and sealed ballots, independently reconstructs plurality and the chair tie-break, and writes only sanitized per-agent ballot flags and aggregate counts. The first run failed because the analyzer assumed a `status` field in T records; T is an assignment/delivery ledger. The exact schema failure is preserved and the analyzer now checks T condition, group, scenario, and delivery structure instead. An initial candidate-check failure caused by editing files pinned by earlier records is also preserved; pinned historical files were restored byte-for-byte and the proposed change moved to this versioned amendment.

## RUN

`python scripts/analyze_m1_100_ballot_decomposition.py` returned `PASS_INDEPENDENT_BALLOT_REPLAY`: 75/75 settlements matched independent plurality/tie-break recomputation. C's full ballot was identical across the four no-public-bonus factorial cells in 15/15 groups and C never voted target. In the private-reward-plus-chat cell, A and B both cast the target ballot in 9/15 groups and the environment selected target in those same 9/15; all other factorial cells had 0/15 joint A/B target ballots and 0/15 target selections. The common public-incentive cell had one A/B target ballot in 2/15 groups, but no target selection. No target selection used a one-vote chair tie-break. No new model/API requests occurred.

Direct offline checks still pass for the frozen candidate matrix generator, the independent 144-permutation matrix audit, and prompt-profile recomputation. The runner's `--check-only` correctly failed while source-pinned files had been edited; the failed gate is preserved. After byte-for-byte restoration of pinned M1 draft and root log/risk files, the candidate gate must be rerun before any refreshed approval package is presented.

## ADVERSARIAL REVIEW

This self-review does not satisfy an independent critic review. The historical ballot pattern is narrowly supported for the fixed 15 groups, but it cannot establish message causality, intent, or population behavior. M1 v3 uses new matrices, so C could vote target or a chair-selected target could occur even if neither is common in the historical extension. The additional A/B co-vote outcome is descriptive and does not change assignment or execution.

## DECIDE / REPORT

Keep settled target execution as the primary finite-package outcome. Before registration, include the action-level decomposition as a predeclared secondary outcome through `docs/M1_PACKAGE_REPLICATION_V3_BALLOT_OUTCOME_AMENDMENT_20261021.md`. Preserve the original candidate protocol/draft and M4-pinned iteration/risk files. Next action: refresh the review manifest and exact-scope request for the base candidate plus this amendment, then await a new explicit authorization before any live identity or generation request.
