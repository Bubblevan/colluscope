# M4 DeepSeek Monitor V1 — Final Decision

**Status:** `COMPLETE_RAW_REPLAY_PASS`; all 376 frozen rows were dispatched and terminalized once.

## Results

All 376 responses passed syntax/label parsing and citation-membership checks. Exact matches on all attached observable references occurred in 145/376 requests and 145/400 individual reference rows. Membership-valid citations do not establish that a cited event semantically supports the prediction.

There were 126 assessable B4/B5 pairs. Both methods were exact on all references in 65; B4 alone was exact in 10; B5 alone in 4; neither in 47. Predictions had the same label in 101/126 pairs. This descriptive pattern does not establish method superiority, especially given only 14 discordant correctness pairs, repeated task/case instances, and one provider alias/fingerprint.

The populations remain separate: natural M4 traces B4 52/144 reference labels, B5 47/144; synthetic scripted controls both 5/8; matched synthetic worlds both 18/48. These counts are not independent samples across tasks/views and are not latent-collusion detection accuracy.

## Decision

**GO:** publish the sanitized task-level results as descriptive observations for this exact run and scorer.
**NO-GO:** B4/B5 superiority, broad detector capability, real-world generalization, or latent-collusion/intent claims.
**STOP:** the authorized inference scope is consumed; no additional Monitor or M2 calls follow from this decision.

Independent audit summary SHA-256: `49f3cf85cde5a4a6561b18c7dc6ed92e565a0a9e77e0bc48bbb477a5dd4d6ca7`. See `docs/M4_DEEPSEEK_MONITOR_V1_EVIDENCE.md` and sanitized CSVs under `docs/results/deepseek-first-m4/audit/`.
