# M4 / Monitor Recovery Failure History

This is a sanitized record of adverse outcomes and implementation failures relevant to the recovery. Raw historical model/API bodies remain in the private ignored `runs/` tree. Test outputs generated during the recovery are preserved under `test_logs/`.

## Historical experiment failures (immutable)

- M4 run03: 24/24 assigned first-message attempts are terminal `INVALID_JSON`; all 24 raw responses are HTTP 200 and `finish_reason=stop`. Independent suffix inspection found a complete schema-valid candidate JSON action after one exact `<think>` wrapper in each response. Historical episode/action/ballot/settlement records remain unchanged; candidate parsing is not retroactive success.
- Monitor full run: 856/856 attempts are represented in the raw trace. 715 ended `length`, 141 ended `stop`; 145 response contents are syntactically JSON, but four of these are length-terminated. Only 141 are complete stop-plus-JSON outputs. No correctness claim follows.

## Recovery software failures preserved in the work record

1. The first offline v4 action-interface gate test exposed a gate bug: an integrity-only M4 audit with zero linked actions was not rejected by the helper's `linked < 3 * completed` check when completed was zero. The gate now explicitly rejects `linked == 0`; its regression test asserts `NOT_RUN`.
2. The first v4 runtime integration run had 34 passes and three failures. `test_v4_wrapper_recovery_runs_through_real_http_path_and_independent_replay` and `test_v4_explicit_reasoning_field_is_separate_from_action_content` found the independent verifier reusing the final loop iteration's positive-control schema instead of each raw request's schema. The verifier now reads the corresponding frozen request JSON. `test_m4_diagnostic_custom_generation_cap_is_enforced_before_request_freeze` expected the established “hard M4” error wording; the wording was kept. The three failed tests were rerun after repair and passed.
3. An initial non-escalated local fake-HTTP run was blocked by Windows loopback sandbox error `WSAEACCES` before exercising test handlers. This was an environment permission failure, not a product assertion. The fake-loopback-only integration run was allowed under sandbox escalation; it did not use llama.cpp or external transport.
4. Adversarial review found that a JSON-shaped HTTP 500 body could be counted as a Monitor parseable output by the independent auditor, and the M4 auditor did not independently require HTTP 200. Both auditors now gate parseability/action validity on an integer HTTP 200 terminal field. Regression tests cover HTTP 500, missing status, string status, and HTTP 200.
5. Replaying the legacy full M4 run auditor from the modified recovery worktree exited before verification because the immutable run manifest pins the older `scripts/audit_m4_live.py` hash. This branch intentionally changed that script to auto-detect v4 manifests, so the auditor correctly reports source drift. The historical manifest was not edited and the check was not bypassed. The separate no-call forensic replay passed; the committed historical integrity audit still reports 0 linked actions/settlements. Full legacy verifier replay requires its exact pinned source snapshot and access to the ignored raw run.

## Current validation records

- `test_logs/targeted-offline.log`: 33 passed after the HTTP-status adversarial correction; `test_logs/targeted-after-hash-binding.log`: 35 passed after adding source-hash freeze checks.
- `test_logs/m4-live-runtime.log`: 39 passed on fake local HTTP transport.
- `test_logs/full-suite.log`: first complete run had 509 passed, one opt-in Windows listener-owner-table check skipped.
- `test_logs/full-suite-after-hash-binding.log`: final run after all code changes had 511 passed, one opt-in Windows listener-owner-table check skipped.
- `test_logs/targeted-after-launch-reasoning-format.log`: 36 passed after aligning v4 server-launch and request reasoning formats.
- `test_logs/full-suite-final.log`: final run after all code changes had 512 passed, one opt-in Windows listener-owner-table check skipped.
- No test or command in this recovery called a real Agent, Monitor, DeepSeek API, or llama.cpp generation endpoint.

Prior pre-generation and protocol failures from the 2026-10-20 full research run remain in `docs/ITERATION_LOG.md` and the original ignored run folders. This recovery does not supersede or erase them.
