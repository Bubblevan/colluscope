# Colosseum local run: retained failure history

This record supplements, but does not rewrite, the original append-only progress ledger, HTTP ledger, server logs, and upstream outputs under the ignored `reference/colosseum/experiments/collusion/outputs/colluscope-qwen3-conceptual-20261020/` path.

## Historical run failures

- Before any generation, the first server readiness check failed because the orchestrator expected a different readiness phrase than llama.cpp 10068 emitted. It was retried only because the ledger proved zero HTTP requests had been sent. Both startup logs and progress rows remain unchanged.
- During the completed baseline episode, 15 HTTP 400 continuations and one HTTP 500 parser failure are embedded as turn errors; the framework still wrote a final summary with `status=complete`.
- During the treatment episode, four HTTP 400s and one HTTP 500 occurred before the user stopped the run. Attempt 128 remains an unmatched in-flight request. The episode has no terminal summary and must not be treated as completed.
- The old `http_requests.jsonl` stored only request/response hashes, status, time and byte count. The absent raw bodies, generated arguments and finish reasons are a historical collection gap, not files omitted from this audit.

## This audit's own failed checks

1. **First independent cost parser attempt:** a broad pattern matched task IDs in later natural-language agent messages and let a quoted claimed cost overwrite a true structured cost-table value. The check failed with apparent cost mismatches. We retained the failure summary, narrowed the parser to lines whose full shape is `- ISSUE-...: cost=<number>`, and added a counterexample containing a conflicting quoted claim. The corrected parser then matched all 48 explicit costs.
2. **First runtime compatibility test attempt:** the fake upstream tool processor returned a separate updated context list; the checker inspected the original list and missed an environment callback error. The test failed. The adapter now inspects the returned processed context, and the counterexample passes by raising before the turn can be treated as successful.
3. **First freeze metadata version:** a no-call pair freeze was created before the standalone read-only verifier was added. The runner source was restored byte-for-byte to the hash in that freeze; the verifier is a separate script. The frozen manifest validates and records 180 as the hard cap. No model process or request was started.

These failures were repaired without modifying old experiment assignments, conditions, rewards, model/runtime identity, original raw output, or acceptance criteria. Test output and the post-run audit are saved in `docs/results/colosseum-local-audit-20261020/`.

## Submission-branch offline recheck

- The first full `python -m pytest -q` recheck stalled at the first async compatibility test. A faulthandler trace showed Windows asyncio blocked while creating its loopback `socketpair` in `socket.accept`; no model request or test coroutine had run. Selecting the Windows Selector loop and then moving loop creation to a worker thread did not remove the sandbox-specific socketpair stall. These failed harness attempts are preserved in `docs/results/colosseum-local-audit-20261020/submission-recheck-failure-history.txt`.
- The final mock-test harness drives only immediate test coroutines without an event loop, patches Terrarium's blocking bridge to invoke its mock synchronously, and raises if any coroutine yields an external awaitable. This is limited to unit tests; it does not change the runtime adapter or claim to validate concurrent scheduling.
- The next completed runtime-suite attempt passed 10/12 tests; the two raw-capture tests failed because Python's default temporary directory is outside this workspace's writable roots. Their failure output is retained in the same file. Restricting scratch directories to the repository root fixed this environment issue.
- Current targeted Colosseum suite: **17 passed, 8 subtests passed**. The full repository suite is **not green in this sandbox**: `python -m pytest -q` reported 307 passed, 16 failed, 6 errors, 1 skipped, and 8 subtests passed. The errors include unavailable ignored M1 source data; the failures include local HTTP test servers blocked by the sandbox. These are not recast as Colosseum passes and are not repaired by excluding cases.

The historical HTTP ledger, progress ledger, upstream run artifacts, server logs and original private messages remain local and byte-unchanged. The newly committed failure mapping contains hashes and pseudonymized state only.
