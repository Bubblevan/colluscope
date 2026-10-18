# ColluScope M0.1 Evidence — Research Validity Hardening

## Scope and disposition

M0.1 was performed in a fresh clone of origin/main at commit 190ea3cb4e5803bea3fede9a0eddbf8e4d57fe51. The clone was on branch codex/m01-research-validity-hardening. Python 3.12.4, pytest 9.1.1, Windows 11 build 10.0.26200, AMD64. The original frozen M0 files were not edited. This is an independent checkout on the same host/runtime, not a separate-machine replication.

M0.1 is GO for review of the bounded M1 behavior-pilot TRD. M1 execution and formal monitor evaluation are NO-GO until separately reviewed and approved. No LLM was called, no paid API was used, and no real banking system or user data was involved.

## Gate evidence

| Gate | Result | Evidence and limit |
|---|---|---|
| Fresh-checkout identity | PASS | Checkout HEAD and origin/main both equal 190ea3cb4e5803bea3fede9a0eddbf8e4d57fe51; environment record is runs/m0_1/evidence/independent-environment.txt. |
| Baseline M0 reproduction | PASS | Unmodified baseline suite: 40 passed. A fresh 24-episode scripted run and standalone verifier passed. Trace SHA256 f255133c747fcebdf5d32612a614dc2abbcd511da6dbd3e59761777766f4bf50; oracle SHA256 365c1de4650d1303d03a4ae2c54ec800e99457e2b0cb7f2aee5cafa9616fa3ae; config SHA256 5ebeb87fb49ac28a3305663ef587c6edfdf69f66f776cd38e581af23895e144a. All match the frozen M0 run. Logs are pytest-m0-independent.log, generation-m0-independent.log, verification-m0-independent.log. |
| C2/C4 text label leakage | PASS for scripted generator | Old phrases are retained as counterexamples and tests assert the scanner catches them. Current C2 uses neutral reference/allocation wording; C4 no longer says “individual ballot.” All current C1–C6 case text is scanned. Tests do not establish how real agents write. See text-and-incentive-audit-before.txt and tests/test_m01_research_design.py. |
| Payoff interpretation | PASS with erratum | The proxy is 4 at target and 1 at public optimum, delta 3; public welfare is 14 vs 28. docs/M0_1_ERRATA.md corrects the frozen report statement without modifying frozen M0. Tests assert the exact values. |
| M1 incentive and channel design | PASS as proposal only | Five conditions are declared in configs/m1-pilot-draft.toml and specified in docs/M1_PILOT_TRD.md. The public +20 rule is visible to all; private +20 rules go only to A/B; the monitor excludes private incentives by default. Chat availability and bonus assignment are distinct. The announced points are not presumed to be real model utility. No agent observation was delivered. |
| T/B/E label provenance | PASS as design only | T stores assigned bonus/channel and delivery; B stores sent/delivered messages, ballots, selected outcome, W, and realized score; E contains only permission-allowed evidence. Harm is computed from public W. Agreement or intent is not inferred from a treatment, chat availability, or matching action. Runtime is untested. |
| Four-view fairness | PASS as protocol only | Within an episode, views share task rules and auditor permission. Text/action/union content differences are explicit; structured findings are deterministic additions requiring a same-schema ablation; exact-tokenizer and cost reporting is required; hidden treatment metadata is separated while real public task rules remain visible. No monitor/tokenizer was selected, so no monitor or cost result exists. |
| Grouped split helper | PASS as helper contract | Versioned SHA256 uses only scenario-family and seed-block IDs; first 8 hex digits modulo 5 map buckets 0–2 to development, 3 to calibration, 4 to test. Tests keep paired C1/C6-style conditions and all views in one group, reject a split-crossing counterexample, and reject a malformed digest suffix. No real dataset or split manifest exists. The pilot stays exploratory and cannot support detector evaluation. |
| Isolation and carryover | PASS as draft invariant; runtime untested | The config asserts fresh per-agent/per-episode context, no cross-agent outputs in no-chat arms, A/B-only peer chat, and randomized condition order. The TRD requires an isolation canary before any authorized pilot. |
| Final offline M0.1 run | PASS | Targeted design tests: 10 passed in 0.04s (pytest-m0_1-targeted-pass.log). Full suite: 50 passed in 0.73s (pytest-m0_1-final.log). Release run m0-20261018T145715Z: 24 episodes, four per C1–C6; four identical public-only C1/C6 evidence pairs; automatic and standalone verification PASS; external model calls 0; paid API calls 0; detector performance not claimed. Trace SHA256 deb363db22edbd358ccf0e8d4ef30ea0e2eddd1b2c0fcaf934eb1b383ac632b9. Source snapshot SHA256 ee5340578bf0713b132acb57628a1f539be8b0f6f7faf384c88be3e015a1ebed; all 14 file hashes matched in runs/m0_1/evidence/source-snapshot-check.log. |

## Preserved failures and limits

runs/m0_1/evidence/checkout-and-path-attempts.txt retains the failed worktree attempt, initial proxy-denied clone attempt, and early nested-path mistake. The baseline logs, pre-fix text/payoff audit, earlier smoke outputs, and two failed document-assertion test logs are preserved; no difficult example was removed. The frozen runs/m0/ tree and original docs/M0_EVIDENCE.md and docs/M0_DECISION.md compare clean against baseline commit 190ea3c.

The final run manifest records that the Git working tree was dirty at generation time. It also records a file-level source snapshot and hash. The committed branch contains the same source/config/test files; a clean checkout can reproduce the trace and view hashes, though run timestamp, absolute paths, and Git metadata in the manifest will differ.

The helper prevents specified paired records from being assigned across splits; it does not prove that five seeds are enough or that a future sample generalizes. The +20 value is arithmetic-only until a real pilot tests delivery and comprehension. Four-view token cost, monitor performance, LLM coordination, and human interpretation remain unmeasured.

## Reproduction commands

Run from the repository root in PowerShell:

    $env:PYTHONPATH = 'src'
    python -m pytest -q
    python -m colluscope m0 --config configs/m0.toml --out runs/m0_1/reproduction
    python -m colluscope verify --run <run-directory-printed-by-generation>

The M0.1 evidence logs are under runs/m0_1/evidence/. The baseline reproduction command, before M0.1 edits, used the same pytest and CLI commands from a clean checkout at the baseline commit. The release run directory is runs/m0_1/neutralized-text-smoke-release-final/m0-20261018T145715Z.

## Decision

GO: review the M1 behavior-only pilot design. NO-GO: running M1, using a paid/provider API, or starting formal monitor evaluation without a separate user decision. No automatic transition to M1 is authorized.