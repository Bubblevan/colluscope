# Iteration Follow-up — 2026-10-21 — M1 v3 Offline Runtime

This dated appendix preserves the frozen `docs/ITERATION_LOG.md` and records the M1 v3 offline runtime work.

## INSPECT

Highest risk: a request or failure could escape the experiment-specific budget, be silently replayed after interruption, or lose raw evidence before parsing. A second validity risk was treating a candidate schedule/config as permission to generate model behavior.

## SPECIFY

Counterexamples: mutate the candidate schedule or live flag; exceed any request ceiling; duplicate a reserved request; tamper with a hash chain; simulate an interrupted episode; return malformed JSON with HTTP 200; return HTTP 400/500; or supply the prior M4 approval ID. Each should fail closed, preserve its evidence, and issue no retry/replacement.

## IMPLEMENT

Added an M1 v3 scope and static offline configuration, a dedicated runner, append-only hash-chain request/group journals, schedule/budget recomputation, live registration/authorization checks, restricted ignored output storage, and scripted HTTP canaries. Added a byte-exact identity response record before JSON parsing after adversarial review exposed a malformed-HTTP-200 evidence gap.

## RUN

- Candidate `--check-only`: `PASS_OFFLINE_CANDIDATE`; 120 episodes, 360 ballots, 96 message decisions, 456 generation cap, 24 identity HTTP cap, 480 physical HTTP cap, external spend zero.
- Independent matrix verification: 24 matrices, 144 assignment/permutation checks.
- Prompt-profile recomputation and registry audit: passed.
- Final focused suite: 82 passed.
- Final full suite: 661 passed, 2 failed, 1 skipped. Both failures are retained and occur in unrelated historical test/fixture paths; details and raw output are in the runtime evidence package.
- Scripted fake HTTP canary: 8 local requests with canned responses during each full parameterized run; no model process or external endpoint was used.

## ADVERSARIAL REVIEW

Detected and fixed loss of a successful identity response body on parse failure. Regression coverage now verifies byte recovery from base64 and SHA-256. The two repository-level failures were not “fixed” by editing the historical M4 plan or research hypothesis registry. The historical M4 authorization is not transferable to M1.

## DECIDE

GO for offline implementation and preregistration review. NO-GO for live M1 v3 generation: the experiment is not registered, no fresh M1/Qwen approval exists, actual local server identity/parity was not tested, and the complete repository suite retains two unrelated failures.

## REPORT / next action

Preserve all failures and source hashes. The next highest-value action is independent review and formal registration of the exact M1 v3 protocol, followed by a new M1-specific user approval. Do not infer any model behavior until that approval and the live identity checks pass.
