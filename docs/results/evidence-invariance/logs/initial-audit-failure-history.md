# Initial Audit and Parser Failure History

This branch keeps earlier failure categories visible. These are analysis/runtime failures, not a filtered model-result set. No old run, score row, or raw response was changed.

## Historical M4 model-parser result

- The separate local Qwen M4 behavior attempt assigned 24 message generations; 24/24 returned HTTP 200 with a normal stop status but failed the frozen strict JSON action parser due to a leading reasoning wrapper. No action, ballot, or behavioral endpoint was observed. This remains a historical parser/protocol failure and is not part of the DeepSeek Monitor prediction denominator.
- Source evidence: `docs/FULL_RESEARCH_EXECUTION_EVIDENCE.md` (SHA-256 `3772e4f3678bb7c2ec491af41e58ac7c3814bf18925fd5d21aeb71dade4239ad`) and `docs/FULL_RESEARCH_EXECUTION_DECISION.md` (SHA-256 `1e48b783e60a3b3728460376ae14dbedbfe1198fdac63cf18d615d748c79c4ff`). The raw local response artifacts remain in the ignored historical run directory; this branch does not copy them.
- The DeepSeek-first Monitor protocol is a different run. The 96 selected public-harm requests in this audit all had HTTP 200, `tool_calls` finish reason, one function call, matching raw-response hashes, and a parseable label/reference list. No parser failure was found in this selected population; this result does not independently replay the remaining 280 Monitor requests.

## Initial audit-harness failures

The following exploratory errors were recorded during setup and corrected before the frozen replay. They are retained as sanitized error records; they do not represent model behavior or data failures.

| Failure | Observed error category | Resolution |
|---|---|---|
| Prototype looked up an incorrect request sidecar/request ID | `FileNotFoundError` | Resolve rows by the frozen request ID and read the matching `.meta.json` sidecar. |
| Prototype aggregation treated an integer counter as an iterable | `TypeError: 'int' object is not iterable` | Replaced the scratch aggregation with typed counters and explicit scalar accumulation. |
| First prototype did not parse | `SyntaxError` from a mismatched bracket | Rewrote the expression, then ran `py_compile` before replay. |
| Prompt and task catalog were sought under guessed paths | source-file-not-found | Use the pinned paths `prompts/m4-deepseek-agent-v1/monitor-system.txt` and `prompts/sprint-baseline-v1/tasks.json`; their hashes are checked by the audit. |

The coordinating root task also reported three separate harness/setup failures: Python dictionary syntax, indexing a `WindowsPath`, and an initial sandbox denial during worktree creation. They are classified as local analysis/tooling failures; the branch does not copy or edit the root-side files.

## Preserved run outputs

- `targeted-tests.txt`: exact stdout/stderr from the branch-local counterexample test run.
- `audit-stdout.json`: sanitized JSON from the independent 96-request replay. It contains no message text, request bodies, response bodies, or raw path.
- `synthetic-freeze-stdout.json`: exact summary from the deterministic 20-group fixture generator.
- The full prompt/response bytes and private messages remain local in the Git-ignored run directory.

## V2 implementation failures (preserved)

| Failure | Preserved log | Resolution |
|---|---|---|
| First V2 freeze raised `KeyError: 'irrelevant_short'` because `task_irrelevant_short` was split at the first underscore. | `synthetic-freeze-v2-initial-stdout.txt` | Parse the two approved style-family prefixes explicitly and validate `short` / `long`; regenerate without changing V1. |
| First V2 targeted run had 2 test failures: a prompt marker was reported as prompt-hash drift before the marker check, and the V1 preservation test tried to read message text from ballot events. | `targeted-tests-v2.txt` | Check forbidden markers before the exact prompt hash; compare only V1 `type=message` events. |
| Second V2 targeted run had 1 test failure because the marker-injection fixture changed a vote event rather than a message event. | `targeted-tests-v2-final.txt` | Select the frozen privileged-message variant, mutate only its message text, and verify rejection. |
| Adversarial source review found that the A2 primary label was derived from the otherwise opaque group ID, so the label remained computable from ID. | `synthetic-invariance-groups-v2-pre-id-audit.json` (SHA-256 `6ed6e36c53c4cfd2a81e501351842885df282780a91681d2d40c119d64e9c40d`) | Preserve the draft; final V2 uses independent frozen random IDs and an independent seeded 10/10 label assignment, with wrapper-exclusion regression tests. |

All failures were local fixture/projector defects. They were retained after correction and none involved a model request or a deleted/replaced research sample. The root-side harness failures (Python dictionary syntax, `WindowsPath` indexing, and initial worktree sandbox denial) remain classified above and were not copied from the root worktree.
