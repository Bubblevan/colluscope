# M4 Live Runtime v3 — Technical Design

**Status:** offline implementation and fake-HTTP integration only. No Agent generation, monitor inference, or external API call was made for this runtime.

**Base:** 95cd6b5c5c0cc05ebf14a1be04052501b0602ad1, branch codex/sprint-execution-readiness-20261020. The runtime is a new versioned implementation; it does not rewrite the historical M4 offline-Mock runner or M4 v1/v2 reports.

## Frozen identity and launch boundary

configs/m4-live-runtime-v3.json pins the existing Qwen3-8B Q4_K_M GGUF, llama.cpp build 10068, runtime bundle, GGUF tokenizer, chat template, prompts, JSON action schemas, six scenario families, 24 matched groups, positive-control v2 stimulus and base M4 v2 config. Asset values are independently checked by verify_frozen_assets; all matched the local files during this offline validation.

The production adapter accepts only http://127.0.0.1:8081/v1, disables proxy use and redirects, requires a generated local API key, launches only the frozen local llama-server.exe, authenticates an exact /models alias probe, checks process/listener ownership before each generation, and has no external fallback. The CLI is inert unless both --execute-live and a non-empty operator approval ID are supplied. Raw output must be below Git-ignored runs/m4/ and pass current-user-only Windows ACL checks.

## Episode and information flow

The runner makes two private message-generation requests for A and B. Both are generated before either is delivered. A send is delivered only to its named peer; no_message is a valid action and is retained distinctly from a delivered neutral stimulus. The runner then submits A, B and C baseline ballots without exposing any pre-vote ballot or output to another Agent. No public interim announcement is emitted. The deterministic environment settles the ballots once all three are present; only then is public welfare, matrix optimum, regret, selected allocation and realized task scores calculated and exported as Public-only E. Private messages and focal counterfactual ballots remain researcher-side B, not E.

For a group with a complete delivered proposal, the frozen hash rule selects one eligible message without consulting ballots. Four stateless focal ballots use the same receiver and common pre-receipt context in a hash-randomized order:

1. retained own history + frozen neutral message;
2. masked own history + the actual delivered proposal;
3. masked own history + the same frozen neutral message;
4. retained own history + a preselected alternative legal allocation.

The primary token-difference contrast is arm 2 minus arm 3, which keeps own-history masking fixed. The history interaction remains the preregistered M4 hypothesis. This is a v3 measurement choice: it does not modify the frozen group schedule, matrices, incentives, seeds, action semantics, or hypotheses. All four counts are measured with the pinned GGUF tokenizer on the full rendered chat input before the corresponding focal calls. The proposal text is never edited after a ballot is observed. Token deltas are retained in all assigned/eligible denominators and binned using the frozen 0, 1, 2, 5 thresholds.

The two behavioral capability-control prompts test whether a receiver uses a newly delivered decision signal versus Signal code: NONE. They are separate from the allocation mechanism. NONE is delivered text; it is not no_message and is not No-delivery.

## Attempts, cap and recovery

Maximum per eligible group is 11 generation requests: 2 message actions + 3 sealed baseline ballots + 4 focal ballots + 2 positive-control choices. A group without an eligible proposal uses 7 calls; it receives no replacement focal actions. All 24 assigned groups remain in the denominator. The hard cap is 264 physical generation attempts, one attempt per logical request, zero retries, zero replacement groups. The separate authenticated /models identity probe is not a generation and is logged in its own identity-probe ledger.

Each request body and observation metadata is written and fsynced before the single HTTP attempt. Each raw HTTP response body is saved byte-for-byte; receipts retain finish reason, server usage when supplied, local input count, elapsed time, returned alias and parser status. Authentication headers are never written. Failed, malformed, truncated, missing-action, timed-out, interrupted, and HTTP 4xx/5xx attempts consume the assigned group/request and are terminal. No invalid response is repaired into an action.

Resume verifies frozen manifest, request and response hashes, and unique request IDs before doing anything. It never resends a started logical request. A durable episode missing its final group-ledger row is recovered from that episode without relabeling or a new generation. A completed group with a missing attempt-terminal row is rejected as an integrity error. A started group with no durable episode is recorded as a failed no-replacement group. Raw evidence remains append-only and local.

## Independent audit and implementation scope

verify_live_run replays every completed action from raw responses, checks one-to-one linkage to B records, independently settles baseline ballots, and recomputes public welfare, optimum, regret, private bonuses and realized task scores. It also checks Public-only E, group terminal statuses, request/observation/prompt hashes, tokenizer counts and the hard generation cap.

The compatibility runtime changes no upstream Colosseum or frozen M4 environment semantics. It only makes ColluScope's frozen M4 action interface executable through the pinned llama.cpp Chat Completions API and makes run evidence/recovery explicit. It is therefore a new ColluScope runtime, not an unmodified-upstream reproduction.

## Limits

- The fake HTTP server validates HTTP transport, parser, logs and replay, not Qwen behavior.
- The previously completed M4 v2 server/tokenizer parity diagnostic covered fixed Mock stimuli. It does not validate natural model-authored proposals or constitute a reason to repeat the diagnostic.
- No actual model-authored proposal length, positive-control success, token-sensitivity result, welfare effect or communication effect exists yet.
- A and B share the same informed rewarded target. Agreement on that target without a communication intervention cannot identify communication-induced coordination.
- The M4 design estimates observable ballot responses, not latent collusion intent. Target execution, private reward, welfare regret, chat availability or ballot agreement alone are not collusion labels.
- Local file hashes and append-only code paths detect ordinary corruption; they are not a signed or tamper-proof external timestamp.

## Current user-authorized execution receipt addendum (2026-10-20)

The current full-research task explicitly authorizes the 24-group M4 local run within the existing 264 physical-generation cap. This does not change the v3 intervention or experiment schedule. The CLI now additionally requires `--authorization-receipt`, verifies its attachment-scope fields, source hash, matching approval ID, allowed restricted path and Windows ACL, and binds its path/hash into the v4 run manifest. The old manifest field `live_inference_authorized_by_this_task=false` remains the invariant that the runtime cannot authorize itself; `explicit_user_authorization_received` records the current run-specific fact independently.

The local receipt is `runs/full-research-execution-20261020/authorization_receipt.json` (Git-ignored, current-user ACL only). Its reference and hash are written in the private run manifest. This schema change is provenance-only: it does not alter model prompts, endpoint, groups, matrices, incentives, seeds, schemas, sampling, or call count. Focused fake-server tests verify the receipt scope/tamper rejection and that a fake run does not claim user authorization. Current exact M4 v3 asset verification passes; the stale v1 identity-verifier NO-GO is retained as an out-of-scope historical check and is not evidence about current v3 identity.

## Full-research execution startup failure record (2026-10-20)

The first authorized M4 launch stopped before creating the llama.cpp process: `_start_server` opened `out/logs/llama-server.stdout.log` before creating `out/logs`. The preserved ignored run has 24 frozen assignments, zero started groups, zero terminal episodes, zero generation attempts, a `server_stopped/NOT_STARTED` record, `NO_KEY_CREATED`, and no listener on 127.0.0.1:8081. The exact failure is retained in `runs/m4/full-research-execution-20261020/failure-history/preflight-startup-failure-01.log`. The only permitted repair is to create the run's logs directory before opening the append-only server logs; execution must use the same frozen groups and a separate output path. This does not count as a model retry or a replacement group.

A second pre-generation attempt started the local server and verified the frozen `/models` alias, then failed to serialize the in-memory `process_guard` callable into `server_identity.json`. The run is preserved at `runs/m4/full-research-execution-20261020-run02/` with one authenticated identity GET, zero generated ballot/message requests, zero started groups, and cleanup receipts. The versioned fix persists only JSON audit fields while retaining the callable exclusively in memory for listener checks. Retry only in a new run directory.
