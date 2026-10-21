# M4 B5 Repeatability Scope Refocus

**Date:** 2026-10-21
**Mode:** offline design and schedule freeze only; no model or API calls
**Decision:** retain one narrow B5 validity diagnostic; defer the separate prompt/schema-order factorial.

## Authorization status

The user's reply approved `m4-b5-context-sensitivity-campaign-v1` for at most 232 physical attempts and USD 0.90. That exact campaign is already closed with 232/232 attempts, USD 0.027381738 actual cost, zero retries, and an `INCONCLUSIVE` scientific outcome. The approval is consumed and cannot fund another run. This document does not register or authorize a new experiment.

## Why the candidate was narrowed

The completed 232-call campaign found 12/24 Public-only→Neutral, 20/24 Neutral→Original, and 19/24 Public-only→Original label changes. The registered directional gate was not met, and one duplicate request profile had variable transitions. Separately, the exact-request audit found 19/48 historical/current label disagreements with matching request bytes and reported fingerprints. Those are finite output observations; they do not identify hidden provider state, randomness, or a semantic-message effect.

The prior 464-request proposal combined two different questions. The 320-call prompt-order × tool-enum factorial addresses a fixed synthetic presentation failure. The 144-call repeatability study directly addresses whether the M4 view-package contrast exceeds same-view response variation. Since the latter is the current interpretive blocker for the M4 result, the factorial is deferred. This reduces the next candidate from 464 to 144 attempts and avoids spending calls on a separate synthetic question before the real-trace contrast is interpretable.

## Candidate experiment

**ID:** `m4-b5-view-repeatability-v2`
**Question:** For the same 24 fixed M4 contexts, do Public-only versus Privileged-original majority-label differences exceed within-view label variation across identical repeated requests?

- Every one of the 24 fixed contexts receives three Public-only and three Privileged-original requests: 24 × 2 × 3 = **144 assigned attempts**.
- Each replicate within a context/view must use byte-identical request bodies. The six requests for each context are interleaved in a deterministic randomized schedule (seed `20261022`).
- Use the existing B5 task, compiler, system prompt, tool schema, temperature 0, thinking disabled, maximum output 512, and forced `report_evidence` contract. Exact identity and token metadata must be rechecked before registration.
- The schedule contains only hashes, view IDs, repeat indices, and assignment hashes. It contains no raw case IDs, prompt payloads, references, or private-message text.
- The Privileged-original arm sends two historical private-message events per request. Across 72 privileged requests this is **144 private-message event appearances** sent to the provider. Any new approval must explicitly cover this transfer.
- Hard ceiling: 144 physical attempts, zero retries, zero replacements. Every failed, malformed, timed-out, or unstarted assignment remains accounted for.
- Offline preparation compiled 48 exact context/view bodies and confirmed all three repeats per body are byte-identical. Maximum conservative input bound is 12,104 tokens; at the presently documented off-peak rates and 512 output tokens, the exact full-schedule reserve is USD 0.26585640. Candidate hard cost ceiling remains **USD 0.35**, subject to a fresh official price/window check and pre-dispatch token-size verification.

## Frozen schedule and scoring plan

The hash-only schedule is generated from the completed campaign's frozen A1 Public-only and Privileged-original context assignments. It has 24 paired context hashes, 144 unique assignment hashes, and no model-visible metadata. Schedule SHA-256: `37cce3e98a0493cb26e6610cdc823aa5cc7a1303086f7943ed269b895441e099`; serialized schedule file SHA-256: `08e9b6d72862629f1e3e2fa3f02f3dcaee41a6356ad874cdd7cecc6d9ac93f3e`. The builder is `scripts/freeze_m4_b5_view_repeatability_v2.py`; source schedule SHA-256 is `c44585532b18e8def0488c4f3de42be1c4a04009566b396251c3da2659043c3c`. The offline compiled request manifest is SHA-256 `6d26f48244bd06d93b29d58d02d69f03fe49d6db967b74cae0618ccfdfaf760a`; it contains no raw payload.

Primary reporting uses all 24 contexts. For each view report the three raw outcomes, the number of canonical labels, whether all three agree, whether there is a unique canonical mode, and within-view pairwise disagreements. Invalid or failed outputs remain explicit outcomes; a view/context has a unique mode only if at least two canonical labels agree. For each context with a unique mode in both views, report the Public-only/Privileged-original mode transition. Also report all invalid, failed, and unstarted requests by assigned slot. Do not treat the three pairwise comparisons within one context as independent samples; no significance test or population estimate is planned.

Descriptive interpretation gates:

- **Stable package difference observed:** at least 18/24 contexts have a unique mode in both views, and the number of cross-view mode changes is at least 6 and exceeds the number of contexts with any within-view disagreement.
- **Historical contrast not reproduced:** at least 18/24 contexts have a unique mode in both views, at most 1/24 cross-view mode changes, and at most 6/24 contexts have any within-view disagreement.
- **Inconclusive:** every other outcome pattern, including fewer than 18 contexts with unique modes in both views or cross-view changes that do not exceed within-view instability.
- **Invalid repeatability comparison / stop:** any endpoint or returned-model identity change, reported serving-fingerprint drift, or non-identical request bytes within a context/view. Preserve all prior and affected rows; do not retry or replace them.

These are fixed-corpus descriptive gates. Even a stable difference concerns the bundled Public-only versus Privileged-original evidence package; it does not isolate message semantics, prove comprehension, or identify collusion/intent. Public welfare remains independently computable by deterministic rules.

## Stop conditions and implementation gate

No registration or dispatch occurs from this candidate. Before any future registration, implement and offline-audit an append-only runner that enforces the exact schedule, local-only raw payload storage, pre-attempt ledger rows, endpoint/model/approval checks, per-request budget reservation, identical request bytes across repeats, hard ceilings, and no-resampling resume behavior. Recheck official model alias, price, and off-peak hours. Stop before an attempt if the requested target is not the official DeepSeek endpoint, the alias/price/window differs, request size exceeds the cap, private-data permission is unresolved, or source/schedule/prompt hashes drift. After dispatch begins, any returned-model or fingerprint drift terminalizes the run; retain all completed and failed attempts.

The current authorization reply does not cover this new ID. A future approval would need to name `m4-b5-view-repeatability-v2`, 144 physical attempts, USD 0.35, official DeepSeek Flash only, off-peak only, zero retries/replacements, and an expiry. It would also need to explicitly authorize transmission of the 144 private-message event appearances. Remaining project budget is not an approval.

## Reproduction

Offline schedule and request preparation (zero model/API calls; request bodies containing historical private messages are stored only in the restricted Git-ignored run directory):

```powershell
python scripts/freeze_m4_b5_view_repeatability_v2.py
python scripts/run_m4_b5_view_repeatability_v2.py --prepare
```

The schedule builder refuses a different overwrite and prints only aggregate counts and hashes. The live runner is implemented with a hard registration/approval gate and was exercised only through an offline loopback fake server. This candidate is not registered or authorized for provider requests.
