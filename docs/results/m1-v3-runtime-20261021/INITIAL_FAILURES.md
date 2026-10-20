# M1 v3 Runtime — Preserved Failure History

This file records failures encountered while building and auditing the offline runtime. Failures are retained as evidence; no historical sample, frozen result, or acceptance rule was removed to obtain a passing result.

## Captured raw log

- `logs/researchctl-audit-initial-failure.log`: the first registry audit after a temporary `.gitignore` change failed because that file is included in a frozen historical source-hash manifest. The edit was reverted; `.gitignore` has no diff in this branch. The original M4 plan and its expected hashes were not rewritten.

## Failures reconstructed from the task transcript

The following test failures occurred during this implementation but their complete terminal output was not separately saved at the time. They are disclosed as reconstructed summaries rather than represented as raw logs:

1. **Config parser optional-key set.** The initial v3 profile test failed because the loader accepted either the base set of TOML keys or the set with both optional metadata keys, but not the valid v3 set containing only `research_scope`. The loader was narrowed to four exact permitted key sets. Regression coverage checks the offline v3 profile and rejects live-flag edits, wrong budgets, external endpoints, and a changed port.
2. **Fake-server assertion fixture.** The first parameterized transport test used a common record-count assertion for success and error cases. Error paths correctly emitted one request, while the fixture incorrectly expected the success count. The test now uses mode-specific expected counts and still asserts that malformed output, HTTP 400, and HTTP 500 remain failures with no retry.
3. **Initial full-history suite.** The complete run reported 659 passed, 2 failed, 1 skipped. One failure is `tests/test_deepseek_research_audit.py::test_committed_pilot_plan_reproduces_byte_for_byte`: the historical expected `.gitignore` source hash (`178ffbb5ecbb3460419e18a2a0d17eb91d2085603121fa402c73157ecfac1dfd`) differs from the clean tracked file hash (`fca00a4b41c0bb0d6f2582004f1d2967e3570db0384236f76bf201eb90355ce7`). The mismatch is confined to the recorded source-hash field; the frozen plan was not changed.
4. The second failure was `tests/test_researchctl_lifecycle_e2e.py::test_researchctl_zero_call_register_close_sync_audit`. Its test setup searches `research/hypotheses.json` for the absent ID `observable-evidence-boundary` and fails before invoking the CLI. The research registry was not modified to satisfy the stale fixture.
5. The one skip was an opt-in, Windows host-dependent process-owner integration check. It is not counted as a pass.

The current full-suite transcript is separately captured in `logs/full-suite.log`; its final counts and exit status are reported in the M1 v3 evidence document. Any changed result is reported there rather than replacing this history.

## Adversarial issue found after initial implementation

During final raw-evidence review, identity preflight success bodies were found to be hashed or parsed without always being written byte-for-byte before JSON parsing. A malformed HTTP 200 `/props` response could therefore lose its raw body from the append-only journal. The runner now writes successful response bytes as base64 plus SHA-256 before parsing; `test_identity_http_200_body_is_durably_logged_before_json_parsing` verifies exact recovery. No identity/model HTTP request was made to discover or reproduce this issue; the regression uses an in-memory scripted response.
