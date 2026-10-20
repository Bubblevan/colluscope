# M4-B5 campaign: full-suite failure classification

Checked on 2026-10-20 before campaign registration and before any campaign API request. Full-suite log: `docs/results/research-sprint-20261021/direction-review/campaign-full-offline-suite-final.log` (SHA-256 `3399c20631f2f5567bd7d35bfe6db0cfdb4f1755aaf4c6606333488232035a34`).

## Run result

- `621 passed`, `1 skipped`, `2 failed` in 181.93 seconds.
- The skip is the opt-in, host-dependent Windows owner-table integration check.
- The M4-B5 focused runtime suite separately passes `12/12`; it includes the new exact-input-profile and protected-source-hash checks plus local HTTP canaries.
- The initial focused-run regression (`NameError` caused by placing the list branch outside the hidden-key validator) is retained in `campaign-offline-tests-final-v2.log`; it was fixed and the same focused suite then passed.

## Failure 1: stale M4-P0 freeze hash for `.gitignore`

`tests/test_deepseek_research_audit.py::test_committed_pilot_plan_reproduces_byte_for_byte` fails because the byte-for-byte reconstruction differs only in `source_hashes[".gitignore"]`. The committed pilot plan stores `178ffbb5…`, while the checked-out, clean `HEAD` file hashes to `fca00a4b…`; all plan rows, prompt hashes, and the plan/config digest match. This is a pre-existing stale source hash in a historical frozen plan, not a change made by this campaign. The historical plan and its source are preserved; this task does not rewrite that freeze to force a green test.

## Failure 2: frozen lifecycle test fixture no longer matches current registry state

`tests/test_researchctl_lifecycle_e2e.py::test_researchctl_zero_call_register_close_sync_audit` fails at registration because it hard-codes `observable-evidence-boundary` as an open candidate, while the current registry correctly marks it `supported`. The existing test file is itself hash-pinned by the already registered B5 experiment. A temporary attempt to select an actually open candidate and respect the copied historical usage reached a later fixture limitation: the sandbox copy did not include all frozen files referenced by copied historical experiment records. Those temporary edits were reverted; changing this test would make the registered B5 input hash fail. The unmodified full-suite failure remains recorded.

The live repository's `python scripts/researchctl.py audit` passes after restoring the frozen test file, with both historical registered cycles intact. The lifecycle test fixture needs a separately versioned design that does not mutate an input of a closed experiment.

## Decision

These two failures are unrelated to the new campaign's request compiler or runtime. They remain visible and are not counted as passes. The first identifies a stale historical hash; the second identifies a frozen test fixture whose assumptions no longer match the registry and whose sandbox copier omits registered inputs. Neither is repaired by changing the old registered experiment. Campaign-specific readiness is evaluated separately from full-repository test status.
