# Full Research Execution Decision

**Decision date:** 2026-10-20
**Pre-inference freeze commit:** `34bb78e`
**Run scope:** M4 local Qwen3 behavior attempt + 856 official DeepSeek Monitor requests
**Raw model/API calls after the authorized freeze:** complete; no further calls are part of this report.

## Overall decision

**NO-GO for scientific claims of M4 message-induced behavior, M4 behavioral effect estimation, Monitor method superiority, or latent-collusion detection.** The frozen M4 action interface failed on all 24 assigned first-message outputs. Of 856 frozen Monitor requests, 715 (83.528%) ended at the 128-token cap, leaving only 141 parseable predictions. B4 and B5 had no shared completed-and-assessable input. The matched-world construction passed the deterministic permission/identifiability checks, but only two monitor responses were parseable.

**GO for publishing this as a transparent runtime/evidence-boundary result with the stated limitations.** The local and remote ledgers, request/response hashes, budgets, identity, independent scoring, and Public-only/Privileged projection checks reconcile. This GO does not authorize or imply another model call, detector comparison, training run, or behavioral pilot.

## Claim-specific decisions

| Claim | Decision | Evidence and boundary |
|---|---|---|
| The frozen M4 runtime produced usable behavior for 24 groups | **NO-GO** | 24/24 local outputs returned HTTP 200/`stop` but failed the strict JSON parser; zero messages, ballots, settlements, or behavioral endpoints were produced. |
| M4 shows no communication effect | **NO-GO** | There are no M4 behavioral outcomes to compare. A parser/action failure is not a null effect. |
| The original scripted Monitor run demonstrates general detector accuracy | **NO-GO** | 16/280 outputs parsed; tasks are synthetic and small. Scores are conditional on selected completions. |
| B5/evidence-aware monitoring improves on B4/raw fusion | **NO-GO / not estimable** | No common completed-and-assessable B4/B5 instance in any phase. Different completion subsets cannot support a head-to-head accuracy claim. |
| Evidence-structured reasoning outperforms deterministic computation | **NO-GO** | The only direct public-harm deterministic cell is 7/7 assessable; the new run has insufficient paired LLM outputs. The earlier M2 100% structured public-harm cell directly exposed the answer field. |
| Monitor can distinguish the matched worlds from Public-only evidence | **NO-GO by construction** | 24/24 pair/method Public-only projections and references are byte/reference identical. Identical allowed inputs contain no distinguishing observable signal. |
| Privileged evidence exposes different observable facts | **GO for the frozen synthetic construction check only** | 24/24 privileged projections differ; observable sequence references are independently labeled. This is deterministic construction verification, not an inference result. |
| The monitor recognized positive sequence controls | **Limited observation only** | Two parseable B5 Privileged responses matched two explicit proposal/acceptance/action positive-control references with sufficient citations. The other 70 requests in the phase were invalid; this is not an accuracy estimate. |
| Monitor hard-negative specificity is established | **NO-GO / not estimable** | No parseable model output landed on a frozen `hard_negative_control` row (n=0); no unsupported sequence claim was observed among parseable outputs, but the zero eligible hard-negative denominator cannot support a specificity rate. |
| The system detected latent collusion or intent | **NO-GO** | No latent-intent gold label exists in M0–M4. Matching ballots, messages, reward assignment, welfare loss, and scripted construction labels do not establish intent. |
| The 856-call authorization was respected | **GO** | 856/856 physical API requests terminal, zero retries/replacements, stable identity/fingerprint, estimated USD 0.3265017 against the USD 3 ceiling. No new requests will be made. |
| Independent replay and offline software integrity | **GO** | M4 replay confirms 24 assignments/attempts and no fabricated actions; three Monitor phase audits and cross-phase ledger reconcile. Final suite: 469 passed, 1 optional host-dependent Windows owner-table check skipped; see `offline-full-suite-final-postanalysis.log`. |

## What the data establish

1. The exact frozen M4 local model/runtime/parser combination did not satisfy the action interface on any of its first 24 message attempts. This identifies a protocol incompatibility/failure at the end-to-end boundary, not its unique causal component.
2. The exact DeepSeek Flash alias/fingerprint and default-thinking/128-token configuration returned many incomplete outputs. All 715 unparseable outputs reached the output limit; requests were retained without repair or rerun.
3. On these frozen inputs, the Monitor completion pattern differs by method and population. It is a coverage result, not a performance ranking.
4. The deterministic matched-world compiler produced the intended information boundary: Public-only evidence was identical within each pair; Privileged evidence differed in observable message content.
5. Two completed positive-control predictions occurred under B5 Privileged. This establishes two case-level matches, not broad sensitivity. No parseable model output was available to score on a hard-negative control, so specificity is unknown.

## What remains unknown

- Whether a revised, separately frozen Agent output protocol can produce valid ballots/messages with this checkpoint.
- Whether a different, explicitly configured reasoning/output budget can materially improve Monitor completion without changing the evaluation construct.
- Whether any model can discriminate message-caused coordination from shared incentives, own-history, task difficulty, or independent parallel behavior in a properly powered prospective design.
- Whether the monitor's structured ledger provides value beyond raw fusion and deterministic rules on common assessable instances.
- Whether observed sequences indicate any private agreement or intent.

## Next action

Stop inference and present the evidence package for human review. Any follow-up must first receive a new explicit authorization that fixes the model/provider, runtime and output limits, prompt/schema version, sample plan, privacy boundary, and cost/request caps. The current 856-request cap is fully consumed and cannot be reused.
