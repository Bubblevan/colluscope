# M1 Package Replication v3 — Offline Runtime Evidence

**Run date:** 2026-10-21

**Branch at implementation start:** `codex/deepseek-first-m4-research-20261020`

**Starting HEAD:** `2101ce00508ee82ee9e052376319581e9962beec`
**Evidence scope:** implementation, offline checks, and scripted local HTTP canaries only. No Qwen generation or external inference was performed for this evidence package.

## Offline gates

The final `--check-only` run returned `PASS_OFFLINE_CANDIDATE`. It recomputed 120 assigned episodes, 360 ballots, 96 communication decisions, and the 456-generation cap. It reports 24 identity HTTP requests maximum, 480 total physical HTTP maximum, external calls `0`, external spend `$0`, model calls disabled by default, and `monitor_can_see_private_messages=false`.

The same run invoked and passed all four source gates:

- Frozen schedule generation: 24 groups, 24 matrices, 120 episodes, 456 generations, and `model_outputs_consulted=false`.
- Independent matrix audit: 24 matrices and all 144 matrix/permutation checks.
- Prompt profile recomputation: both candidate designs passed.
- `researchctl audit`: integrity `PASS`, scientific validity `NOT_EVALUATED`, no open experiments, no registry errors.

The registry audit reports 352 calls / `$0.039167058` under two DeepSeek approvals from other completed work (120 and 232 respectively). Those are not M1 calls and were not issued by the offline validation commands in this evidence package.

## Tests and raw outputs

The final focused command passed **82 tests** across the v3 runtime, llama.cpp adapter, and M1 runtime suites. The fake HTTP integration used the production adapter with scripted canned responses against a local test server: one successful no-message episode (five requests) and three one-request failure cases (malformed model content, HTTP 400, HTTP 500), eight local fake-server HTTP exchanges total. No model was loaded or queried. The identity-response regression used an in-memory byte fixture, not a server or model request.

The final complete repository run reports **661 passed, 2 failed, 1 skipped**. Both failures are retained and outside the new M1 v3 tests:

1. `tests/test_deepseek_research_audit.py::test_committed_pilot_plan_reproduces_byte_for_byte` finds a stale historical `.gitignore` hash in the frozen M4 pilot plan. The plan’s recorded expected hash is `178ffbb5ecbb346041e18a2a0d17eb91d2085603121fa402c73157ecfac1dfd`; the clean tracked `.gitignore` is `fca00a4b41c0bb0d6f2582004f1d2967e3570db0384236f76bf201eb90355ce7`. The byte comparison differs inside the frozen source-hash object. Neither `.gitignore` nor the frozen M4 plan was changed by this work.
2. `tests/test_researchctl_lifecycle_e2e.py::test_researchctl_zero_call_register_close_sync_audit` stops in fixture setup because it looks for hypothesis ID `observable-evidence-boundary`, which does not exist in the current `research/hypotheses.json`. The CLI is never reached; the registry was not changed to satisfy this stale fixture.

The one skip is the opt-in, host-dependent Windows owner-table integration check. It is not counted as a pass. The exact full-suite output and exit marker are in `docs/results/m1-v3-runtime-20261021/logs/full-suite.log`; earlier full runs remain separately preserved to show repair history.

## Adversarial review and repair

Review found that a successful HTTP identity response was not always journaled as raw bytes before JSON parsing. A malformed HTTP 200 `/props` body could therefore disappear from the evidence record even though the parser failed. The runtime now writes each successful identity response to the append-only journal as base64 bytes with byte length and SHA-256 **before** parsing. The regression test feeds malformed bytes through a scripted backend and verifies exact byte recovery and the hash. The malformed response still raises a JSON parse error; it is not repaired or accepted.

The earlier full suite, config-parser key-set failure, fake-server assertion-fixture failure, and initial registry audit failure remain described in `docs/results/m1-v3-runtime-20261021/INITIAL_FAILURES.md`. No failure sample was removed or converted to success.

## Reproduction commands

Run from the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python scripts/freeze_m1_package_24_matrix_design.py --check
python scripts/audit_m1_package_24_matrix_design.py --check
python scripts/audit_m1_replication_prompt_profiles.py --check
python scripts/run_m1_package_replication_v3.py --check-only
python scripts/researchctl.py audit
python -m pytest -q tests/test_m1_package_replication_v3_runtime.py tests/test_openai_compat_llamacpp.py tests/test_m1_runtime.py
python -m pytest -q
```

The full suite intentionally remains non-green until the two unrelated historical fixture/hash inconsistencies are resolved in their own versioned maintenance work. The complete post-fix runtime test result is green.

## Identity and artifact boundaries

The candidate config records the Qwen3-8B Q4_K_M SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`, llama.cpp binary SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`, and runtime bundle SHA-256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`. These are frozen candidate values, not fresh live-process verification. The live `/props`, `/apply-template`, `/tokenize`, listener-owner, model-file and server-process checks have not been run in this task.

The run output directory is under ignored `runs/m1_100/m1-package-replication-v3/`; raw request/response and private observation traces are not staged. `git check-ignore` confirmed the path is ignored. Source fingerprints and environment details are recorded in `docs/results/m1-v3-runtime-20261021/environment.json`.
