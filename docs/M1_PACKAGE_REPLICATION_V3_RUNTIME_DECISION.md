# M1 Package Replication v3 — Runtime Decision

## Decision

**GO:** offline implementation and preregistration review.

**NO-GO:** real M1 v3 model generation or a behavioral pilot.

## GO evidence

- The 24-group candidate schedule is hash-pinned and independently validates every matrix’s six permutations (144 checks total), unique public optimum, suboptimal target and regret stratum.
- The call graph recomputes to 120 assigned episodes, 360 sealed ballots and 96 message decisions: 456 model generations. Runtime enforcement uses one physical attempt per logical request, zero retries and zero replacement groups. The separate ceiling is 24 identity requests and 480 total physical HTTP attempts.
- The static config disables both model and preflight calls, has no approval ID, fixes the endpoint to `127.0.0.1:8081`, and rejects a live flag or altered budget.
- Offline schedule, independent matrix, prompt-profile and research registry gates passed. The final focused runtime/transport suite passed 82 tests, including scripted HTTP 200/malformed content, 400 and 500 paths, exact raw-identity-response logging, and pre-write output-path rejection.
- Each request attempt is durably reserved before the call; run/request journals are hash-chained; terminal and interrupted requests are not replayed; failed assigned episodes stay in the denominator.
- The final full repository suite reports 661 passed, 2 failed and 1 skipped. The two failures are a frozen M4 `.gitignore` hash mismatch and a stale lifecycle-test hypothesis ID, not M1 v3 failures. They remain visible and unresolved.

## NO-GO evidence

- `research/state.json` still has `active_experiment_id: null`; M1 v3 is not formally registered.
- There is no immutable M1-specific approval batch. The DeepSeek M4-B5 authorization names a different experiment/provider and cannot authorize Qwen or M1 v3.
- No live local llama.cpp process, listener ownership, actual `/props`, template/tokenizer parity or model-file identity was checked in this task. Fake-server tests validate transport behavior only.
- The repository-wide suite is not fully green for the two preserved historical failures above.

## Required before any M1 live command

1. Independently review and freeze the protocol, prompt/config/source hash manifest, split schedule and failure rules; register the exact `m1-reward-chat-24group-replication-v1` preregistration.
2. Obtain a fresh explicit user approval naming this M1/Qwen local experiment, at most 456 generations and 480 physical HTTP attempts, zero external spend, zero retries/replacements, endpoint `127.0.0.1:8081`, and a validity deadline.
3. Run the exact gated command only after both conditions are met:

```powershell
python scripts/run_m1_package_replication_v3.py --live --approval-id <fresh-M1-approval-id> --out runs/m1_100/m1-package-replication-v3/run-<unique-id>
```

That live command was not run. There is no M1 behavior evidence or scientific conclusion from this runtime work.
