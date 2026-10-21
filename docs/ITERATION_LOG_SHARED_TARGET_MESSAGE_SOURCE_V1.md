# Shared-target message-source v1 cycle log

**Date:** 2026-10-21  
**Experiment:** `shared-target-message-source-v1`  
**Evidence class:** `real_llm_behavior` from controlled scripted recipient prompts

## INSPECT

The prior content-only study found target and decoy mapping responses in three fixed contexts but used one source label. The unresolved rival was generic advice or instruction following. The M1/M3 patterns and the 804-request recipient study do not isolate peer-source framing; the latter's delivered-fact positive control failed. The frozen source study used all 24 assigned payoff contexts and matched peer/aide prompts that differed only in source label.

## PREREGISTER / AUTHORIZE

The study was registered before dispatch with six arms per context and four exact-prompt repeats per arm (576 maximum physical calls). It tested peer-source superiority against task-aide framing, while preserving target/decoy mapping and hidden/no-message shadow controls. The immutable authorization was `DS-FLASH-PEER-SOURCE-576-20261021`, scoped to this study, 576 requests and a $0.75 peak-rate cap. No historical approval was reused.

## RUN / REPLAY

The authorized run completed 576/576 assigned requests in about 9.54 minutes. All responses yielded assessable legal ballots; there were no failed, invalid, or unattempted rows, no retries or replacements, and no integrity errors. Independent raw replay verified the frozen schedule, request and response hashes, source/token parity, outcomes, provider identity, aggregate rates, and usage-derived cost without a network call. To satisfy the lifecycle ledger's timestamp requirement, each sanitized ledger row was joined to exactly one raw `attempt_started` event using the SHA-256 of the attempt request ID; request, response, status, and cost values were unchanged. The timestamp reconciliation receipt and replay result are `docs/results/shared-target-message-source-v1/ledger-timestamp-reconciliation.json` and `independent-audit.json`.

## INTERPRET

Mapping adherence was 161/192 (83.85%) under peer framing and 168/192 (87.50%) under task-aide framing. The equal-context peer-minus-aide difference was -3.65 percentage points; peer adherence was higher in 0/24 contexts, aide adherence in 2/24, and 22 were tied. The hidden/no-message shadow mapping matched 14/96 ballots; the visible-target control selected the target in 96/96. Eight of 144 context-by-arm cells had repeat disagreement.

The preregistered peer-source advantage hypothesis is `REFUTED`: its +15-point and at-least-18/24 peer-favoring gates were not met. The preregistered finite source-insensitive recommendation-pattern gate was met. This is a descriptive result over 24 fixed synthetic contexts, not a statistical equivalence test. It supports controlled recommendation-mapping response under either label in these prompts and weakens a peer-label-specific explanation. It does not establish social influence, natural communication, collusion, agreement, intent, welfare effects, or population behavior.

## ADVERSARIAL REVIEW

Self-review retained the mutable provider alias and single reported fingerprint limitation, fixed-context scope, 8/144 repeat-disagreement cells, only 6/24 decoys with welfare gap at most 1, source-label construct limits, non-inferential shadow baseline, and restricted raw-response accessibility. This was adversarial self-review, not an independent critic or second-party raw-byte audit.

## DECIDE / REPORT

Scientific outcome: `REFUTED` for the registered peer-source advantage. Operational decision: `PIVOT`, as required after repeated cycles without an independently reviewed material update. The next action is offline manuscript integration and review of the source result alongside M1/M3; this closeout authorizes no further model calls.

Artifacts are in `docs/results/shared-target-message-source-v1/`, with the full scope and claim boundaries in `docs/SHARED_TARGET_MESSAGE_SOURCE_V1_PROTOCOL.md`. Protected raw requests and responses remain local in the Git-ignored run directory.
