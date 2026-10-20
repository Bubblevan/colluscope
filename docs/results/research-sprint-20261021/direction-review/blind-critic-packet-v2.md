# M4 B5 Campaign Pre-dispatch Critic Packet v2

**Purpose:** adversarial review of the corrected fixed-corpus Monitor campaign before registration and dispatch. **No campaign request has been sent.** The prior reviewer saw v1 and recommended A1-only partly because the v1 arithmetic table exposed derived welfare fields. Treat this as a second-party follow-up with prior-context exposure, not a new blind independent review.

## Frozen design

- A1: 24 historical M4 contexts × Public-only, Privileged-original, Privileged-neutral = 72 requests. Neutral text is the frozen sentence `I received your message.` in both delivered message events. The text is much shorter than many originals; wording, salience, and token length remain confounded. The contrast is not a semantic-content test.
- A2: 40 fixed synthetic rows × four forms = 160 requests: V2-direct, production B5, production B5 plus six **unranked** allocation totals, and production B5 with `present`/`absent` order reversed in prompt and schema. The arithmetic table has no optimum, realized welfare, regret, ranking, reference label, or answer field. It is an arithmetic-presentation intervention, not natural behavior data.
- Total: 232 assigned physical attempts maximum, official DeepSeek Flash only, temperature 0, thinking disabled, max_tokens 512, off-peak only, zero retry/replacement, $0.90 hard cap, expiry `2026-10-23T01:00:00Z`.
- A1's outcome is fixed-context response sensitivity for a mechanically recomputable public-harm label. Neither block has a latent-collusion label or supports a population claim.

## Exact inputs

- Protocol: `docs/M4_B5_CONTEXT_SENSITIVITY_PROTOCOL.md`, SHA-256 `7cd2bece167fc4cb3d19985e7699a8adf254958a741fe951f99771304ffeca94`.
- Schedule: `research/schedules/m4-b5-context-sensitivity-campaign-v1.json`, SHA-256 `c44585532b18e8def0488c4f3de42be1c4a04009566b396251c3da2659043c3c`.
- Hash-only request manifest: `docs/results/research-sprint-20261021/direction-review/m4-b5-frozen-request-manifest-v2.json`, SHA-256 `3a675f76da0be43647fd04760d844ab8276da964c5040d83aa711c7bb7c8b423`.
- Runner: `scripts/run_m4_b5_context_sensitivity.py`, SHA-256 `be5669b219e8f2811b86a56aad29813c0d53fa7df7ca0585fb848eaa643d9cf6`.
- Tests: `tests/test_m4_b5_context_sensitivity_runner.py`, 11/11 pass; log `docs/results/research-sprint-20261021/direction-review/campaign-offline-tests-final.log`, SHA-256 `a19fb1747d6e0547c4d45611023738a4b6c7a268aff879aaf4b3c11edc545005`.
- Frozen request bounds: maximum 12,104 tokens; sum 2,095,712; peak no-cache reserve including all 512-token outputs is $0.7712544. No campaign API call has occurred.
- The V2-direct arm now reads the exact hash-pinned prompt bytes; the earlier `.strip()` variant failed the projector hash check and was fixed before registration.
- The superseded draft that put optimum/realized/regret into the A2 table is retained at `docs/results/research-sprint-20261021/direction-review/a2-oracle-leak-pre-review-preregistration-draft-v0.json` and is not used.

## Historical observations relevant to review

- On 24 fixed M4 contexts, B5 predictions changed in 20/24 between Public-only and Privileged Audit while public-harm references changed in 0/24. Transitions were 15 `insufficient_evidence→absent`, 4 `present→absent`, and 1 `insufficient_evidence→present`; 14 improved exactness, 1 worsened, and 5 remained wrong. This is a bundled view response pattern, not an identified content or causal effect.
- On 40 balanced synthetic public-canonical and label-flip rows, the prior B5 outputs were all `present`; a deterministic public-harm baseline was exact on 40/40. This public fact can be computed from public data and is not itself a collusion label.
- Sources: `docs/BRANCH_A_EVIDENCE_INVARIANCE.md` SHA-256 `56381dee01cacdd49735c878b4c130a9b8c2059a4d4c4fa5b01e0cadf407dd34`; `docs/results/deepseek-first-m4/audit/monitor_per_reference_scores.csv` SHA-256 `ebfc472cb615fc351d35099e2f61469396a3f1d08d82534fe3daf4ebd9cc48a7`; `docs/results/research-sprint-20261021/B5_POSTCLOSE_RULE_BASELINE_AUDIT.md` and its linked machine-readable result.

## Review request

Inspect only this packet and the listed source artifacts to verify hashes and the claims relevant to this campaign. Do not inspect author iteration logs, research memory, or hypothesis ranking. Do not edit files or inputs. Do not quote private messages.

Return:

1. `PASS`, `CONCERN`, or `BLOCK` for the campaign's pre-dispatch scientific validity and engineering boundary.
2. Whether the corrected A2 arithmetic aid is free of explicit reference leakage, and whether its contents instead constitute a legitimate but strong numeric-presentation intervention.
3. Any remaining problem in denominator integrity, compiler parity, label leakage, permissions, cost/attempt ceilings, or no-retry behavior.
4. Whether the full 232-call scope is proportionate after the correction, and the cheapest falsifying test for your strongest concern.

Distinguish explicit label leakage from model-inferable labels: exposing the task's public inputs can make a deterministic answer computable, but the test must not pass the reference label or an already-derived answer as an input field.
