# ColluScope Scientific Direction Review — Current Synthesis

**Date:** 2026-10-21 local / 2026-10-20 UTC\
**Repository baseline:** `codex/deepseek-first-m4-research-20261020` at `b63ab29249b56909e27e279a7269199b2e24b019`\
**Activity:** independent no-call replay synthesis, deterministic scenario candidate generation, literature comparison, and a separate-context desk critique\
**New model/API inference requests:** 0; one read-only lookup of the official pricing page\
**Decision:** choose the private-reward × chat-stage package as the next primary empirical question; use evidence sufficiency as the Track 2.3 claim framework and test natural-language evidence extraction as the Track 2.2 component. Do not run more public-harm Monitor calls for a task already solved exactly by a rule baseline.

## 1. What changed in this review

Earlier direction notes prioritized explaining B5's public/privileged response difference. The approved 232-request campaign has now run and closed as `AMBIGUOUS / INCONCLUSIVE`. It generated useful facts, but it did not isolate message meaning, event packaging, prompt length, provider variation, or model-state effects. The balanced synthetic public-harm task also has a perfect deterministic rule baseline. Continuing to call a Monitor on that same structured label has low information value.

The existing M1-100 analysis supplies a more consequential real-Agent question: the post-hoc private-reward-plus-chat cell selected the rewarded target in 9/15 matched groups, versus 0/15 in each of three other cells. This remains a finite post-hoc pattern, varies across payoff families, and bundles a shared rewarded target with an extra message stage. The next useful test is a new matched replication of that *assigned package*, with message-content claims reserved for a separate monitor audit against human-coded observable references.

The latest separate-context Scientific Critic instead recommends a narrow C-first route because public welfare is mechanically computable and the scripted evidence boundary is cheap to audit. That is a useful caution about call efficiency, not a reason to claim the finite scripted construction is a standalone paper contribution. The final choice below combines B as the primary empirical question with C as the standard that limits what the resulting data can claim.

## 2. Independent evidence synthesis

The new synthesis script reads the sanitized score CSV and hash-checked audit summaries, not private message text or raw API payloads. It verifies all 40 matched A2 units (group hash × trajectory hash) and all four assigned arms before summarizing them. The explicit pairing key matters: grouping by trajectory alone collapses the 40 units to two trajectory classes and was rejected during review.

| Source | Independently checked result | Interpretation limit |
|---|---:|---|
| Real M4 public-harm references | 24/24 complete cases; unique optimum 24/24; independent replay matches 24/24; reference labels unchanged across permission views | Welfare regret is a public outcome label, not a collusion label |
| M4 B5 Public-only → Privileged | 20/24 prediction labels changed; references changed 0/24; exactness 4/24 → 17/24 | 15 changes are abstention → absent, so this is not 20 binary flips or a message-semantic effect |
| Earlier 120-call balanced synthetic B5 public controls | 40/40 valid binary tool outputs were `present`; balanced references; only 20/40 exact | Positive-control gate failed; zero pair changes are not evidence of invariance |
| 40-row production B5 A2 | 35 `present`, 5 `insufficient_evidence`; 20/40 exact | Same finite fixture, not a general ability estimate |
| B5 plus six-assignment welfare arithmetic | 39/40 exact; 19 paired predictions changed versus production B5 | The explicit arithmetic aid changes both content and prompt length; it is not independent model reasoning |
| Reversed label-order A2 | 36/40 predictions changed; exactness 20/40 → 10/40 | Prompt order and tool-enum order were reversed together; their effects are not separated |
| V2-direct versus production B5 A2 | 5/40 predictions changed; exactness remains 20/40 | Request builders differ in multiple fields; this does not identify a compiler cause |
| Scripted matched-world audit | Public projections equal in 24/24 worlds; 8/12 pairs differ on at least one determinate sequence element; complete-sequence difference in 2/12 pairs | Finite construction only, not natural behavior or a general impossibility result |

The output is `docs/results/research-sprint-20261021/direction-review-current/evidence-synthesis.json`; its source hashes and the exact denominators are embedded there. The independent public-harm replayer uses the matrix, complete ballots, voting rule, and chair identity. Recorded decision/outcome and the completeness flag are additional fields for checking that the stored settlement is consistent with the ballot replay. Private messages, incentive assignments, condition IDs, seeds, group identity, and latent-intent labels are unnecessary for computing the reference.

### Competing explanations for the one-sided synthetic B5 result

1. **Label/presentation prior.** B5's canonical form yielded all `present`; the bundled reversal changed 36/40 predictions and lowered exactness. A factorial prompt-order × tool-enum-order comparison would separate the two order effects. Because the existing arm reversed both, no such causal attribution is supported.
2. **Arithmetic or label-mapping burden.** The label is deterministically recoverable, baseline exactness is 40/40, and adding welfare arithmetic produced 39/40 Monitor labels. This is consistent with an arithmetic/prompt-mapping bottleneck, but the added table also changes length and salience. A length-matched irrelevant-number control would be required to attribute the gain to useful arithmetic.
3. **Synthetic/production request mismatch and distribution shift.** The old synthetic projector lacks production B5 ledger fields and some prompt text; its matrix scale and regret distribution differ from real M4. On a matched 40-row comparison, V2-direct and production B5 differ on only 5 predictions, with unchanged accuracy. This weakens but does not rule out request-construction effects; a remaining difference could reflect matrix scale or task semantics.
4. **Finite provider response variation.** Historical/current exact-request comparisons found 19 raw label disagreements among 48 pairs with matching reported fingerprints. This is direct evidence that stored label disagreement is not merely introduced by the scorer, but does not identify hidden serving state, nondeterminism, or the cause of cross-view changes.
5. **Task-instruction interaction.** The system prompt warns against inferring collusion from harm, while `public_harm` asks a separate welfare-regret question. Confusion between these concepts is plausible but unproven; only a frozen wording contrast with the same structured inputs could test it. Given the exact rule baseline, this is not a good reason to spend another campaign on the same label.

### What job remains for an LLM?

For structured public welfare, the deterministic program should calculate the optimum, settlement consistency, welfare, and regret. Those are not Monitor predictions. A potentially nontrivial LLM task remains when evidence is natural language: identify whether a message states a complete allocation proposal, whether it clearly accepts a proposal, or whether a later vote is semantically concordant with a proposal despite paraphrase, omission, or ambiguity. Those predictions require separately adjudicated human references and must be scored field by field. If the LLM does not outperform a literal/rule baseline on that narrow task, no distinctive LLM-monitor contribution has been shown.

## 3. Direction comparison and paper-worthiness

| Direction | New knowledge and strongest falsifier | Closest-work overlap / incremental contribution | Current decision |
|---|---|---|---|
| **A — B5 evidence-view response** | Determine whether content, evidence packaging, or response variation explains the finite 20/24 change. A repeated, interleaved identical-input design showing changes at least as large within an exact view as between views would falsify a view-specific interpretation. | Arike et al. already study Monitor information access and extract/evaluate designs; Colosseum studies communication/action divergence. The incremental result would have to be narrow: natural multi-Agent traces, evidence-permission accounting, and repeatability. The finished campaign is inconclusive and public harm is computable by rules. | Retain as a Track 2.2 validity caveat; stop further calls on this public-harm label. |
| **B — private reward × chat-stage behavior** | Re-test whether the matched package produces a positive target-execution interaction across new payoff families. A null/negative interaction or an effect confined to one family falsifies a general package-replication claim. | Communication effects already appear in auction-agent studies, and Colosseum includes welfare/regret and communication/action divergence. A possible increment is a prospective matched intervention with shared-target, stage, message, action, and evidence limits kept distinct. The current 9/15 result is post-hoc and not paper-ready by itself. | **Primary next empirical question**, with no claim about message semantics, collusion, or intent. |
| **C — minimum evidence / identifiability** | State which public fields suffice for welfare/action claims and which sequence claims require permitted private events. A natural-trace case where the proposed minimum public fields fail to reproduce the public label would falsify the task-specific rule claim. | Complements evidence-aware monitoring and Track 2.3's plus-factors framing, but the current 12 scripted matched pairs are not a general theorem or standalone empirical contribution. | Use to constrain the claims and define Monitor tasks; do not spend another call batch just to reproduce the scripted parser. |

**Paper-worthiness judgment:** the current B5 and C results do not independently support a full paper contribution: B5's main numeric label is rule-computable, and C is a finite scripted construction. B has the strongest empirical potential because it concerns actual Agent actions, but the 9/15 pattern needs prospective replication and is not yet an identified message effect. A credible submission would combine the replicated package result, a narrowly evaluated natural-language evidence task with human-coded references, and the evidence ladder that prevents overclaiming. Novelty remains uncertain and requires a final comparison against current literature before submission.

## 4. Separate-context Scientific Critic

The reviewer received a no-prior-chat task, read the sanitized evidence and repository candidate registry, and did not inspect raw private messages, call models, run tests, or edit files. It did see `research/hypotheses.json`, where B was already selected, so this was a separate-context **non-blind desk review**, not a blind independent evaluation. Do not count it as a registry-qualified independent confirmation.

The reviewer ranked C as the cheapest near-term action because public-harm is deterministic and the scripted sequence test is finite; it warned that C may be a construction rule rather than a paper-level contribution. It ranked B as a high-burden, potentially valuable causal direction but emphasized that shared-target knowledge, the additional chat stage, payoff-family heterogeneity, and no human message coding prevent a semantic or collusion claim. It found A's 232-call result inconclusive and noted that broad context-access claims overlap existing monitor work. The reviewer explicitly concluded that the public-harm task should use a deterministic baseline when structured inputs are present.

This disagreement is retained: the reviewer optimizes immediate cost/identifiability (C), while this synthesis selects B for the strongest prospective empirical contribution and keeps C as the evidence standard. A second reviewer blind to the selected hypothesis and seeing a frozen packet should assess paper-worthiness before final submission.

## 5. Draft unified execution scope — not registered or authorized

The current 232-request authorization names only `m4-b5-context-sensitivity-campaign-v1`; it is fully consumed and never reusable. It does not authorize new Agent generations or Monitor inference. The following two-cycle package uses the remaining project budget efficiently and must be registered, source-hash checked, and separately approved before any request.

### Cycle 1 — prospective M1 package replication

- 24 new scenario/seed groups, eight groups per each of three new matrix families; seeds 200–223; all five original M1 conditions remain together in each group.
- 120 assigned Agent episodes: 360 sealed ballots plus 96 peer-message slots from the two chat-enabled conditions; no comprehension probes.
- Primary outcome: groupwise target-execution interaction\
  `Δg = (private reward + chat − private reward/no chat) − (chat/no side bonus − normal cooperation)`.
- Public regret is secondary and recomputed from ballots; it is not an independent confirmation. The public-incentive parallel condition is retained and reported as a separate negative control.
- No replacements or retries. Each assigned logical request receives at most one transport attempt; failed/invalid actions remain in the denominator.
- Model/runtime: exact local `Qwen3-8B-Q4_K_M.gguf` hash and llama.cpp `b10068-571d0d540` hash already frozen in `M1_100_PROTOCOL.md`; verify identities and listener before registration/dispatch. Total: **456 requests** (360 ballots + 96 message decisions).

Three new matrices were generated without reading model outputs by continuing the frozen SHA-256 candidate stream and excluding all F0–F3 row/column permutation orbits. Candidate indices are 88, 71, and 27 for target regrets 6, 12, and 18. The draft JSON independently enumerates all six permutations and verifies a unique public optimum and the `target_welfare < optimum < target_welfare + 20` conflict for each family. These candidates are design inputs, not evidence of model behavior.

### Cycle 2 — Monitor semantic audit on the same corpus

- All 96 assigned chat-message slots, including `no_message`, are retained.
- Two tasks per slot: (a) whether the message contains a complete allocation proposal; (b) whether the recipient's later sealed ballot agrees with that proposal. This is **192 requests**.
- Add 12 frozen capability-control inputs (six clear full-allocation proposals, three ambiguous texts, three no-proposal texts), each paired with a known recipient ballot for the action-concordance task: **24 requests**. Controls are reported separately from natural traces.
- Total: **216 DeepSeek Flash requests**, one attempt each, no retries. DeepSeek receives only these monitor inputs; raw text/response bodies stay in the local restricted run directory and are not committed.
- Two independent human coders label the 96 natural message slots before any Monitor output is seen; adjudication and codebook are frozen. If labels cannot be independently adjudicated or controls are invalid, do not dispatch Cycle 2. This is not a latent-collusion label.
- Report proposal and concordance separately with abstention and citation validity; parser/citation errors do not erase otherwise scoreable fields. Compare against human consensus, a literal deterministic baseline, and a majority/always-negative baseline. Public welfare remains a deterministic rule output.

### One approval for both named cycles

| Resource | Proposed hard limit |
|---|---:|
| Cycle 1 local Qwen generation | 456 requests |
| Cycle 2 DeepSeek Monitor | 216 requests |
| Combined model/HTTP attempts | **672**, zero retry, zero replacement |
| DeepSeek external cost | **$0.45** hard cap, off-peak only |
| Model identities | Qwen3 GGUF + llama.cpp hashes from M1-100; official `deepseek-flash` endpoint only for Cycle 2 |
| Expiry | 2026-10-26 12:00 UTC (approval suggestion; pre-dispatch price/identity recheck still mandatory) |

At the official pricing page checked for this review, DeepSeek Flash off-peak cache-miss input was $0.15/M tokens and output $0.60/M; a conservative 10,000 input-token and 512 output-token cap for all 216 requests gives **$0.3903552**. The $0.45 ceiling is the hard stop, not a spend target. Peak pricing would exceed that ceiling, so dispatch only in a currently verified off-peak interval. Prices and serving aliases can change; recheck before any run. The new project call reserve is 672 against 848 remaining calls; if fully used, the new-campaign total would be 1,024/1,200. This approval proposal is not itself authorization or preregistration.

## 6. Exact next decision

The previous 232-call campaign is closed. No live experiment is registered or open. The next single action is to freeze the two-cycle preregistration and human codebook against the candidate matrix JSON, then request one approval covering both experiment IDs and the combined 672/$0.45 ceilings. If that approval is declined or the human-reference/runtime preflight fails, continue offline paper and evidence work; do not reuse the consumed M4 approval.

## Reproduction

```powershell
python scripts/audit_public_harm_invariance.py --monitor-run runs/deepseek-first-m4/monitor --output docs/results/research-sprint-20261021/scientific-direction-review/branch-a-invariance-rerun.json
python scripts/audit_b5_deterministic_rule_baseline.py --out docs/results/research-sprint-20261021/scientific-direction-review/b5-rule-baseline-rerun.json
python scripts/summarize_scientific_direction_review.py --out docs/results/research-sprint-20261021/direction-review-current/evidence-synthesis.json
python scripts/freeze_m1_replication_candidates.py --check
python scripts/researchctl.py audit
```

The first two commands read existing ignored raw runs and emit sanitized audit summaries. The synthesis script reads only sanitized rows/JSON. The candidate generator reads only the frozen M1 scenario definitions. None of these commands makes model/API requests.
