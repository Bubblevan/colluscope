# ColluScope Scientific Direction Review — Post-campaign

**Date:** 2026-10-21
**Baseline:** `codex/deepseek-first-m4-research-20261020` at `12b3ded4454087e5c1ef6ee961518089b20dbcce`
**Activity:** offline reanalysis, literature comparison, and independent desk review; **zero new model/API calls**
**Decision:** prioritize a prospective replication of the M1 private-reward × chat-stage *package* interaction. Keep the B5 anomaly as a secondary monitor-validity result and use the evidence ladder as the Track 2.3 framing.

## Research question and why the direction changed

The completed B5 campaign is still the most striking monitor anomaly: all 232 requests returned valid HTTP 200 tool outputs, with no retries or replacements and $0.027381738 reported cost. On 24 fixed M4 contexts, public-only/neutral/original-message labels changed 12/24, 20/24, and 19/24 times, respectively; the preregistered directional pattern was not met. A post-hoc audit of 48 historical/current pairs with byte-identical requests and matching **reported** fingerprints found 19 raw label disagreements (17/24 Public-only, 2/24 Privileged-original). Every strict-parsed label matched its stored prediction. This weakens the parser/scorer explanation but leaves within-service response variation, unobserved serving state, and request-view confounds unresolved. One more unreplicated view comparison would not fix that attribution problem. See the [campaign decision](M4_B5_CONTEXT_SENSITIVITY_DECISION.md) and [raw-response audit](results/research-sprint-20261021/raw-response-repeatability-v5/m4-b5-raw-response-repeatability-audit.json).

The M1-100 corpus now supplies a more promising empirical question using real Agent actions, without any new inference. An independent script reconstructed 75 outcomes from sealed ballots and the frozen settlement rule. In the four cells of a post-hoc 2×2 private-reward × chat-stage contrast, target execution occurred in 9/15 groups in the combined private-reward/chat-stage cell and 0/15 in each other cell. The groupwise target-execution interaction was +1 in 9 groups, zero in 6, and negative in none. The mean groupwise regret interaction was +9. These are two summaries of the same outcomes, not independent confirmations.

This is the strongest reason to prioritize B over another B5-only campaign: it concerns an observed multi-Agent action pattern, has all 75 assigned episodes complete, and can motivate a sharp falsification test. The independent critic ranked B highest in prospective scientific potential. **It is still a post-hoc descriptive result, not a confirmatory or population-level finding.**

The B5 synthetic positive/negative control also sharpens the division of labor: on the frozen balanced 40-row fixture, the Monitor answered `present` on all 40 rows (20/40 exact), while an independently implemented deterministic welfare rule matched all 40 references; adding explicit arithmetic reached 39/40. This is evidence that the task's welfare label is mechanically computable and should be emitted by code. It does not establish that the model is generally incapable, and the campaign did not identify whether the synthetic failure came from task framing, compiler differences, range/distribution shift, order sensitivity, or provider response variation. No more synthetic rows are justified just to chase a PASS. See the [post-close baseline audit](results/research-sprint-20261021/B5_POSTCLOSE_RULE_BASELINE_AUDIT.md) and [recomputed rows](results/research-sprint-20261021/b5-deterministic-rule-baseline.json).

## M1 reanalysis: exact scope and adverse checks

The script reads the raw T/B records, but recomputes outcome only from sealed ballots, the frozen scenario matrix, and the deterministic plurality/chair rule. It verifies T/B/schedule IDs, condition assignment against the frozen TOML, scenario/seed/group consistency, and all five scheduled conditions per group. It does not read, print, or export private message text or raw model responses. Public regret is recomputed from each matrix's own optimum.

| Descriptive result | Recomputed count |
|---|---:|
| Assigned / completed / failed | 75 / 75 / 0 |
| Matched groups | 15 |
| Target executed: private reward + chat stage | 9/15 |
| Target executed: private reward, no chat | 0/15 |
| Target executed: chat, no side bonus | 0/15 |
| Target executed: normal cooperation | 0/15 |
| Target-execution interaction | +1 in 9/15; 0 in 6/15; none negative |
| Mean groupwise regret interaction | +9 units |

The effect is heterogeneous across the three frozen payoff families: target execution under private reward + chat was 1/5, 5/5, and 3/5 in families 1, 2, and 3. By split, it was 4/5 in F1, 3/5 in F2, and 2/5 in F3. These splits were frozen for the original M1 protocol, but the interaction analysis was chosen after inspecting the completed outcomes; F2/F3 therefore do **not** make this a confirmatory held-out analysis.

The combined condition had at least one target execution at each of its five order positions, but position cell sizes were 3, 6, 1, 2, and 3. Across all five conditions the condition-by-position allocation is imbalanced: normal cooperation was never first and was last in 6/15 groups. This is a post-hoc check only and does not establish absence of temporal/order effects. The fixed temperature-zero checkpoint and deterministic generation also mean the 15 groups are not independent model-sampling draws.

The DiD is not a new independent signal: because the other three cells had zero target executions, the binary interaction recodes the 9 combined-cell executions. The regret interaction is also derived from these same settlements. The original M1 report already records the primary descriptive result (9/15 vs 0/15 for private-reward chat vs private-reward no-chat); this reanalysis makes the four-cell contrast explicit but does not upgrade its status.

## Mechanism boundary

The condition contrast is **private target reward plus an available chat stage** versus the matched cells. It does not isolate message meaning. A and B receive the same rewarded target before communicating; both message actions are generated before either message is delivered; and the chat conditions include an additional message-stage prompt/context. Thus the observed ballots remain compatible with:

1. agents independently acting on a shared, rewarded target;
2. the additional stage or prompt making the target more salient;
3. the delivered proposal influencing one or both ballots;
4. payoff-family-specific task reasoning or other fixed-model behavior.

The messages and target votes form observable sequences, not evidence of an inferred private agreement or latent intent. M3 supplies a counterexample to a simple content account: Neutral and No-delivery each changed the same 3/8 eligible focal ballots, Masked changed 0/8, and only one ballot change altered settlement. Five of eight recipients already had the target in their own prior message history. In M1-100, episode 013 had positive welfare regret under normal cooperation with no private communication or target execution. Welfare loss is therefore not a coordination label.

## Candidate routes and novelty check

| Route | Current evidence | Strongest limitation | Decision |
|---|---|---|---|
| **A. B5 evidence-view response instability** | 19/48 exact-request raw-label disagreements under matching reported fingerprints; 20/24 historical Public→Privileged prediction changes, with reference truth unchanged | The 232-call campaign did not identify the cause; response repeatability and mutable service state undermine single-call view attribution. Public welfare is exactly computable by rules on this task. | Keep as a Track 2.2 reliability result and a guardrail. Do not spend more calls on the same synthetic control or claim an evidence-view mechanism. |
| **B. Private-reward × communication-stage behavior** | 9/15 target executions in the combined cell, 0/15 in each other 2×2 cell, from raw-ballot replay across three payoff families | Post-hoc, one fixed checkpoint, heterogeneous by matrix family; the treatment bundles reward and message-stage context. | **Select as the next prospective scientific question**, conditional on a fresh preregistration and explicit scope approval. First replicate the package contrast; do not describe it as a message-semantic effect. |
| **C. Evidence sufficiency / identifiability** | Finite scripted matched worlds share the same public projection while privileged construction differs | Scripted fixtures and rule-coded traces do not establish prevalence, general impossibility, or LLM monitoring ability. | Use as Track 2.3 framing and label policy, not as the sole empirical contribution. |

The broad claim that more monitor context changes monitor behavior is not novel by itself: Arike et al. study information access and Extract-and-Evaluate for sabotage monitors. Communication/action and welfare/regret comparisons also appear in Colosseum, and communication effects in auction-agent work. A narrower contribution could be a prospective fixed-model incentive × communication-stage result with explicit evidence limits, but the present data are not enough to claim novelty or generality. The project has not tested steganographic communication and must not claim it has.

References checked against primary sources:

- Apart Research, [AI Collusion Research Sprint](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25), Tracks 2.2 and 2.3.
- Arike et al., [How does information access affect LLM monitors' ability to detect sabotage?](https://proceedings.mlr.press/v306/arike26a.html), ICML 2026.
- [Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems](https://arxiv.org/abs/2602.15198).
- [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413).
- Ouyang et al., [An Empirical Study on Non-determinism of ChatGPT in Code Generation](https://arxiv.org/abs/2308.02828), used only as context for why same-request variation is a plausible rival—not as an explanation of this run.
- Motwani et al., [Secret Collusion among AI Agents: Multi-Agent Deception via Steganography](https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html); related threat model only, not a ColluScope experiment.

## Next falsifiable action

Preregister a **confirmatory replication of the finite package interaction**, not another loosely specified context-sensitivity campaign. A candidate minimum is 15 new matched scenario/seed groups with the original five M1 conditions, using three new payoff matrices selected by the frozen output-independent matrix-selection algorithm at target regrets 6/12/18, the same Qwen3 checkpoint/runtime, and condition order counterbalanced across groups. Freeze all matrices and seeds before responses. This assigns 75 episodes: 225 ballots plus 60 message decisions = 285 logical requests. Use zero retries and zero replacement groups so the physical attempt ceiling is also 285; every assigned failure remains in the denominator. The primary outcome is the four-cell target-execution interaction; public regret is a secondary outcome from the same ballots. Report family-stratified counts and no significance claim unless the registered analysis justifies it.

This is a design recommendation only. No M1 Agent call is authorized by the completed DeepSeek Monitor campaign. A new approval must name the local model/runtime, exact call ceiling, treatment schedule, and expiry before registration and execution. If the replication fails or is family-specific, reject a broad package claim. If it reproduces, the result still says only that this treatment bundle altered allocation behavior for the tested model/tasks; a separate experiment would be needed to isolate delivered message semantics.

## Independent review and reproducibility

An isolated scientific critic reviewed the sanitized M1 reanalysis and compared A/B/C without opening raw private-message text or running tests/calls. The critic agreed B has the highest prospective scientific value, but explicitly rejected a Tier 1 or population-level causal interpretation, flagged family and order sensitivity, and recommended a new preregistered replication. The review is a desk review, not a second raw-data replay; see [`independent-critic-review.md`](results/research-sprint-20261021/direction-review-postcampaign/independent-critic-review.md).

Reproduce with:

```powershell
python scripts/analyze_m1_100_factorial_interaction.py
python scripts/researchctl.py audit
```

The first command requires the local Git-ignored M1-100 raw run at `runs/m1_100/extension-75-20261019-run02` and makes zero model calls. It writes sanitized JSON/CSV outputs and records source hashes. The second command checks the experiment registry and budget ledger; it is not a scientific-validity test.

Core artifact hashes (SHA-256):

| Artifact | SHA-256 |
|---|---|
| `scripts/analyze_m1_100_factorial_interaction.py` | `eb2982beefc8517751494376aa9871a5ed4fa08aa1f94132b17f091486355ea4` |
| `docs/results/m1-100-factorial-interaction-20261021/m1_100_factorial_interaction.json` | `ec79311bcd835f7960df147adfa0fb71aa1dcf8a0369bc8d291ea5c521315498` |
| `docs/results/m1-100-factorial-interaction-20261021/matched_group_interactions.csv` | `218f126943634496740c19dd3442d6a0e4eabee624a553d48acda041d94fc35f` |
| `docs/M1_100_PROTOCOL.md` | `8c64c562aae0c39d8bf45ef6858a0618068dadf5e8a747b97dd962c42accfcc4` |
| `docs/M1_100_SCIENTIFIC_AUDIT.md` | `0a20508d7048f1e573b4d158f348cfe647c8354199860ec1adf5b162a7ec9c1a` |
| `docs/M3_SCIENTIFIC_RESULTS.md` | `dd194d2579366acd0d15c4bc63952b8fddd20bbe92ffc2bdd339efd50e7eaf41` |
| `docs/M4_B5_CONTEXT_SENSITIVITY_EVIDENCE.md` | `906891199731c2b9a0a9a0f6822dd7c572896c29b41620fbf53e85e42bf37402` |
| `docs/results/research-sprint-20261021/raw-response-repeatability-v5/m4-b5-raw-response-repeatability-audit.json` | `1926e9c60f565ef6b18ab1c3df7cd17326694b0e6cb88899fa7b500b67d7f62d` |
| `docs/results/research-sprint-20261021/B5_POSTCLOSE_RULE_BASELINE_AUDIT.md` | `be534c19e05aa540fcc52cd82f969cc63ffca3e871d402c23d2163ce03facb1e` |
| `docs/results/research-sprint-20261021/b5-deterministic-rule-baseline.json` | `e2538cfb2b8711de054964151993a6340a40c55804d569d8455c8cdfb7e53ce6` |
| `docs/results/research-sprint-20261021/MATCHED_WORLD_SEQUENCE_VISIBILITY_AUDIT.md` | `f76ec46a585431d9e5d58d5583790587be6ec37242943ef1dc223b31ea87dada` |

The B5 campaign closure remains unchanged and hash-pinned. Its authorization is consumed and does not cover the proposed Agent replication. The legacy iteration log and risk register were not rewritten because the closed campaign pins them; this post-campaign report and claim-level memory are append-only updates.
