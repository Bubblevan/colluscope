# Research Risk Register Follow-up — Repeatability Candidate

- **Date:** 2026-10-21
- **Scope:** candidate `m4-b5-view-repeatability-v2`; no live calls

| ID | Risk / falsifying counterexample | Current evidence | Required control and interpretation |
|---|---|---|---|
| RV-260 | Overstating the recent synthetic A2 pattern as 40/40 `present` | The 120-call public-canonical diagnostic and the 232-call V2-direct arm were 40/40 `present`; production B5 was 35 `present`, 5 abstentions. | State each form separately; report all 40 fixed rows and abstentions. Do not say the later campaign reproduced an all-present result. |
| RV-261 | Calling repeat variation “randomness” or “model nondeterminism” | 19/48 exact-request historical/current pairs differ despite matching request bytes and reported fingerprints. | The 144 repeats can measure short-window output variability only. They cannot separate sampling, serving cache/state, backend revisions, or hidden provider routing. |
| RV-262 | Calling a stable Public-only/Privileged difference a private-message semantic effect | The two requests differ in permissions, event inclusion/provenance, completeness cues, wording, salience, and token length. | A stable contrast supports only a bundled evidence-package difference. No message-comprehension or causal-content claim. |
| RV-263 | Treating 3 repeats as independent contexts | Each of 24 contexts contributes 6 correlated calls and 3 pairwise within-view comparisons. | Use context as the unit. Keep 24 contexts in the denominator; no population estimate or p-value. |
| RV-264 | Treating a conservative byte-derived input bound as provider tokenization | The preflight computes `2 × UTF-8 bytes + 256` and checks provider usage after any future authorized response. | Report 12,104 as a conservative bound, not an exact tokenizer count. Stop if returned usage exceeds the bound. |
| RV-265 | Implying local ACL prevents external disclosure | A future Privileged-original call sends two historical private events; 72 such calls mean 144 event appearances go to DeepSeek. | Obtain explicit approval for provider and data categories; keep raw payloads local and Git-ignored. Local ACL is not a transmission control. |
| RV-266 | Reusing an exhausted experiment grant or dispatching at peak price | The 232-call approval is consumed; no approval exists for the 144-call candidate. The no-call preflight ran at 01:23 UTC, a published weekday peak interval. | Require new immutable scope-specific authorization. Recheck price/alias/window immediately before dispatch; no current call authorization exists. |
| RV-267 | Calling the repeatability screen novel as a general finding | Primary work already studies repeated identical prompts and provider/serving variability; a recent serving paper directly studies Q4_K_M `llama.cpp`/Qwen cache behavior. | Limit any contribution to the task-specific evidence-view audit. Do not claim novelty, a mechanism, or transfer to hosted DeepSeek before a literature-complete review. |

This addendum does not alter the hash-pinned base risk register or any frozen experiment artifact.
