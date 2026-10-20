# DeepSeek-First M4 / Monitor — Final Decision

**Run:** completed once on 2026-10-20 under the user's bounded authorization.
**Freeze commit:** `550bf1361609e405dc50aa60d5d77b9c502e5bf0`.
**Provider identity:** `deepseek-flash`, system fingerprint `e72d3c7f663d3e1383b00b3884cb4501`.
**Final state:** `COMPLETE_INTEGRITY_PASS_SCIENTIFIC_CLAIMS_LIMITED`.

## Gate decisions

| Claim / gate | Decision | Evidence and boundary |
|---|---|---|
| Official-provider identity, privacy, request accounting | **GO / PASS for this run** | 628/628 official DeepSeek requests were HTTP 200, terminalized once, with 0 retries, 0 missing responses, 0 replacements, and no cap breach. Run root stayed local, ignored and ACL-restricted. The alias/fingerprint is not a pinned checkpoint hash. |
| Strict Function Calling compatibility | **GO / PASS** | The bounded pilot passed all 8 Agent and all 12 Monitor probes using Strict Function Calling. No JSON fallback was used. |
| M4 Agent episode validity | **GO / PASS for descriptive replay** | All 24 assigned groups completed and independently replayed from raw requests/responses; 72 ballots, contexts, delivery barriers, settlements, welfare/regret and Public-only evidence checks passed. This validates the recorded episode construction, not causal interpretation. |
| Monitor output/interface validity | **GO / PASS for schema/permission replay** | 376/376 outputs parsed and passed citation-membership validation. This is not semantic citation support or factual correctness. |
| Observable fact performance | **Descriptive only** | 145/376 request outputs matched every attached observable reference; 145/400 reference rows were exact. B4/B5 had 126 assessable pairs (65 both, 10 B4-only, 4 B5-only, 47 neither). No superiority claim is warranted. |
| Communication caused coordinated voting | **NO-GO / not identified** | No randomized natural episode-level message intervention was run in this DeepSeek extension. Proposal/ballot matches and focal prompt counterfactuals do not identify negotiated agreement or communication-caused behavior. Proposal/neutral prompts differed by 32–85 provider tokens. |
| Latent collusion, intent, or real-world detector accuracy | **NO-GO / unsupported** | No latent-intent gold labels exist. Shared reward, parallel action, welfare regret, message availability, proposal matching, and Monitor predictions are not collusion labels. |
| Further inference or M2 comparison | **STOPPED / not authorized** | The one-run authorization is consumed. No new model call, detector comparison, training, or extension is authorized by this result. |

## Summary of observations

The full assigned population is 24 Agent groups. All 24 completed. There were 48 sent and delivered messages, 20 complete allocation proposals, 72 valid baseline ballots, and the common rewarded target was executed in 2/24 groups. Mean public regret was 1.9583 (median 0; per-family reporting is required because welfare scales vary). The information positive control was followed 24/24 times. These are descriptive outputs of one provider alias/version and frozen task.

The Monitor produced 45/376 frozen-label abstentions (12.0%). On the observable explicit-sequence task, 3/190 references not labeled supported received a supported prediction. This is an observable-reference disagreement count; it is not a latent-collusion error rate.

For the Monitor, all 376 scheduled rows completed. The aggregate B4/B5 paired correctness tally is close and sparse in its discordant pairs: B4-only exact 10 versus B5-only exact 4, with 112 ties on all-reference exactness (65 both-correct, 47 neither-correct). This is not a preregistered superiority test; repeated tasks and cases are clustered, and the alias does not pin weights. Citation membership passed 376/376 but must not be read as semantic support.

## Cost and resource reconciliation

628 requests (20 pilot + 232 Agent + 376 Monitor), 655,032 input tokens and 43,645 output tokens. At the pre-dispatch official peak prices the usage estimate was USD 0.2488836; the conservative reserved amount was USD 1.7744040. The authorized ceilings were 900 physical requests and USD 5.00. No retries or replacements occurred.

## Reproduction

With the local ignored raw run root available and ACL-restricted:

```powershell
python scripts/audit_deepseek_first_research.py
python scripts/analyze_deepseek_first_research.py
python -m pytest -q
```

The sanitized outputs and hash inventory are in `docs/results/deepseek-first-m4/audit/`. A later exact-text scan checked 48 locally retained sent messages against 623 non-ignored repository files, found no matches, and emitted only aggregate counts (result SHA-256 `c205a2648089b8e55be47d8f0b69f3c1d79c21c1f833be8624faae7bf8fef45c`); regression tests cover both leak detection and non-leaking output behavior. The latest suite passed 556 tests with 1 opt-in Windows check skipped in 217.79s (stdout SHA-256 `2924095a8320abd1173c0f1f3811ac310b4ea41fe32eeb1672b96109cf2b2834`). The raw run root and private provider traffic are not committed. The latest complete suite result is in `docs/results/deepseek-first-m4/logs/pytest-full-final-with-monitor-claims.log`.

## Decision

**Close this authorized execution.** It supplies real, independently replayable DeepSeek Agent and Monitor observations. It does not establish a causal communication effect, monitor superiority, generalization, or latent collusion. Preserve the full assigned denominators and failures, publish only sanitized aggregates, and wait for a new user decision before any additional inference.
