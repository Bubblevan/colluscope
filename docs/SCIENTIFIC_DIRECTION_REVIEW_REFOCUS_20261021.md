# Scientific Direction Review — B5 Failure and Evidence-View Refocus

**Date:** 2026-10-21
**Repository baseline:** `codex/deepseek-first-m4-research-20261020` at `a4123b73523f7528fb1e06ccd6236159cadf98f4`
**Review type:** offline independent replay, literature review, and separate-context scientific critique
**New model/API calls:** 0
**Decision:** keep B as the strongest prospective paper question; make a bounded A diagnostic the next experiment only if a new campaign-wide approval is granted. Do not revive the synthetic sequence-classification plan as the main study.

## Executive decision

The B5 anomaly was not absent from the research record. It motivated the M4 context-sensitivity campaign, which used 232 approved DeepSeek requests and is now closed. That campaign confirmed response changes but did not explain them. The earlier decision to move toward M1 package replication had a reasonable paper-value basis—M1 concerns real agent actions, while public-welfare labels are computable by code—but it moved too quickly from “the current public-harm label needs no LLM” to “the B5 response instability is no longer worth diagnosing.” Those are different claims.

I therefore separate **paper direction** from **next diagnostic**:

- **Paper direction:** B, a prospective test of the private-reward × chat-stage package, currently has the strongest empirical potential. The existing 9/15 result is post-hoc, family-heterogeneous, and does not identify a message effect or collusion.
- **Next diagnostic:** A, a fixed-corpus study of whether the B5 permission-view difference exceeds same-input variation and whether prompt order or tool-enum order explains the balanced-fixture all-`present` collapse. A is a monitor-validity gate, not a standalone contribution claim.
- **Claim framework:** C, evidence sufficiency and non-identifiability, remains necessary for Track 2.3, but the existing finite scripted construction is supporting evidence, not a general theorem.

No inference was launched in this review. The approved M4 scope (`m4-b5-context-sensitivity-campaign-v1`) is consumed and cannot fund the proposed follow-up.

## Rechecked evidence

The independent replay was run again from the protected local M4 and B5 runs. Outputs contain aggregates only; raw model payloads and private message text remain in the Git-ignored local run tree.

| Observation | Rechecked result | What it establishes |
|---|---:|---|
| M4 public-harm cases | 24/24 complete; unique optimum and reference replay 24/24 | Public matrix, ballots, chair rule, and outcome determine this task-specific reference. This is not a collusion label. |
| Historical B5 Public-only → Privileged | Labels changed 20/24; independent references changed 0/24; exactness 4/24 → 17/24 | Finite response sensitivity. Fifteen changes were `insufficient_evidence → absent`, four `present → absent`, and one `insufficient_evidence → present`; this was not 20 binary flips. |
| Completed 232-request M4 A1 | Public→Neutral changed 12/24, Neutral→Original 20/24, and Public→Original 19/24; duplicate-profile sensitivity changed Public→Neutral to 11/22 stable unique profiles | Registered directional gates were not met. One Public/Neutral profile repeated with differing transitions. This campaign did address A, but did not compare repeated outputs within each exact view. |
| Bundled M4 input changes | Privileged projection added 48 private-message events over 24 cases, plus event provenance, visibility/completeness cues, serialization, and 291–561 B5 prompt tokens | The historical view contrast does not isolate message meaning or any single structural feature. |
| Exact-request repeatability | 19/48 historical/current raw labels differed despite identical request bytes and matching reported fingerprints; 17/24 Public-only and 2/24 Privileged-original differed | Stored output disagreement is real for those pairs, not introduced by the scorer. It does not identify randomness, provider state, or a cause. |
| B5 balanced synthetic public-canonical rows | 40/40 raw labels were `present`, over 20 `present` and 20 `absent` references; exact 20/40 | A one-sided output collapse and failed positive-control gate, not evidence of invariance. |
| Completed 232-request M4 A2 production B5 | 35 `present`, 5 `insufficient_evidence`, exact 20/40; six-welfare-total presentation was 39/40; simultaneous prompt+enum reversal changed 36/40 outputs and was 10/40 exact | The all-present result belongs to the earlier 120-call fixture; it did not reproduce identically in the later production-form campaign. The 39/40 arithmetic result and 36/40 reversal remain bundled interventions. |
| Deterministic rule baseline | Exact 24/24 real M4 and 40/40 synthetic references | Structured public welfare/regret should be calculated by code. It does not show that LLMs cannot handle other monitor tasks. |
| Arithmetic aid / order perturbation | Six welfare totals: 39/40 exact; simultaneous prompt-order + enum-order reversal changed 36/40 outputs and scored 10/40 | Both are bundled presentation interventions; neither identifies arithmetic reasoning, prompt-order, or schema-order effects alone. |
| M1-100 package result | Independently reran the ballot-level analysis to a new output directory: 75/75 completed; 9/15 target executions in private-reward + chat; 0/15 in each other 2×2 cell; interaction +1 in 9 groups, 0 in 6, never negative | A post-hoc fixed-corpus association from one temperature-zero Qwen checkpoint. The two agents already knew the same target, and chat added a decision stage. |

The latest no-call replays and exact commands are indexed in `docs/results/research-sprint-20261021/b5-direction-review/`. Existing failure logs and earlier campaign artifacts were left untouched.

## Why the previous direction was selected—and what needed correction

The prior post-campaign review selected B because it uses real agent actions and could test an observable intervention, while the public-harm label itself is exactly computed by deterministic rules. It also correctly noted that the M4 232-call campaign failed its registered directional gate and that same-request outputs were not stable. That was a defensible ranking of **paper potential**.

The gap was treating the B5 mechanism question as exhausted. The 232-call campaign varied view/content packages, and the historical/current audit exposed repeat disagreement, but no experiment estimated within-view variability using interleaved exact repeats or independently varied prompt order and tool-enum order. The all-`present` collapse also remains unresolved: useful arithmetic improved exactness, while reversing prompt and enum order together changed many outputs. The next investigation should test these alternatives directly before describing B5 as merely a finished caveat.

This correction does not restore B5 as the paper's central claim. Its current task has a perfect deterministic baseline, and Arike et al. already study monitor information access and extract-and-evaluate. The defensible incremental question is narrower: whether this specific structured audit's apparent access sensitivity exceeds its same-input response variability, and whether an independently isolated presentation factor accounts for its failed balanced control.

## Competing explanations for B5's all-`present` collapse

The current 120-call fixture does not distinguish these explanations:

1. **Prompt-order bias:** changing the order of evidence or answer instructions may change which label is salient. The existing reverse-order run bundled this with tool-enum reversal.
2. **Tool-enum/schema-order bias:** the order of `present`, `absent`, and abstention options may affect tool selection. It was never varied independently of prompt order.
3. **Task/label-mapping difficulty:** the model may not reliably map a welfare regret comparison to the requested `public_harm` label. A deterministic program computes it exactly; model performance must remain a separately scored prediction.
4. **Within-service output variation:** the 19/48 exact-request disagreements make repeated-call variability a concrete rival to view-specific sensitivity. Matching the returned fingerprint does not establish identical hidden serving state.
5. **Synthetic/production presentation mismatch:** the earlier fixtures differed from production request construction. V2-direct versus production B5 changed only 5/40 outputs with unchanged 20/40 exactness, weakening but not eliminating this explanation.

### Minimal discriminating campaign proposed

**Cycle A1 — isolate presentation order (320 requests).** Use all 40 frozen public-canonical rows (20 `present`, 20 `absent`, combining the 20 primary and 20 label-flip control rows). Cross prompt order (forward/reversed) with tool-enum order (forward/reversed); send two exact repetitions per row/cell, interleaved in a pre-randomized schedule. Hold task wording, evidence values, system prompt, schema fields, model settings, and compiler constant otherwise. Score every raw prediction against the independent rule and report class balance, correctness, invalid/abstaining outputs, per-row agreement, and both factorial contrasts. No response repair or row replacement.

**Cycle A2 — estimate within-view variability (144 requests).** On the 24 fixed real M4 cases, issue three byte-identical requests for each of Public-only and Privileged-original under the current production B5 compiler. Interleave both views within case. Report within-view disagreement across repetitions and the case-level difference between each view's three-call majority labels. Keep all 24 cases. This estimates repeatability for these fixed contexts; it does not identify why the view inputs differ.

Together these cycles separate prompt order from tool-enum order and directly compare same-view variation with the historical view contrast. They still cannot establish private-message semantics, provider-internal nondeterminism, generalization to other models, or monitor utility beyond this finite task.

## Direction comparison and research value

| Direction | New knowledge | Strong falsifier | Nearest-work overlap and incremental boundary | Judgment |
|---|---|---|---|---|
| **A. Evidence-view instability and label collapse** | Whether the 20/24 fixed-corpus view change exceeds same-view response variation; whether prompt order or tool schema order explains one-sided outputs | View-majority changes no greater than within-view disagreement; no isolated order factor changes label distribution or accuracy; or balanced controls remain one-sided | Broad “more context changes monitor behavior” overlaps Arike et al.'s less-is-more and Extract-and-Evaluate results. A possible increment is a narrow, evidence-permission-aware reliability result on multi-agent traces. Public welfare has no LLM-specific need in this structured task. | High immediate diagnostic value; low standalone paper value. Run only as a gate. |
| **B. Reward, communication opportunity, and agent choice** | Whether the assigned private-reward × chat-stage package reproduces across new matched scenarios | Non-positive interaction, a result confined to one payoff family/order position, or similar target execution in the controls | Colosseum studies communication/action divergence and regret; double-auction and long-horizon work already test communication and reward/history. Increment must be the preregistered package contrast and evidence boundary, not “communication causes collusion.” | Highest prospective paper potential, but current 9/15 is not confirmatory. Preserve as next Tier 1 candidate after the B5 gate. |
| **C. Minimum evidence and identifiability** | Which permitted records establish welfare, proposal, acceptance, action, or sequence claims | A complete public trace whose rule-replayed label cannot be recovered from the specified public fields; or a constructed matched pair whose authorized projections are not actually identical | Directly fits Track 2.3 and plus-factors reasoning. Current 12-pair scripted test (8/12 with a determinate sequence-element difference, 2/12 complete-sequence differences) is finite and partly rule-coded. | Essential claim discipline; existing result is not a standalone empirical paper contribution. No more model calls needed now. |

### Independent Scientific Critic and reconciliation

The separate-context critic's verdict on A as the **next primary paper direction** was **REFUTED**. It found the label rule-computable, noted 19/48 exact-request disagreements and 7/24 repeated historical/current Public→Privileged transitions, and rejected a causal or distinctive LLM claim. It did, however, recommend one 144-request interleaved repeatability screen if A is reopened, continuing only if view changes recur and exceed within-view variation.

That verdict is accepted. A is selected here only as a bounded diagnostic that resolves whether the existing B5 anomaly is stable enough to retain as a monitor-validity result. A is not a Tier 1 paper claim. Separate desk reviewers rank B highest for prospective real-agent evidence or C highest for immediate identifiability efficiency; those judgments are compatible with this two-level choice. None independently replayed the protected M1 raw data in this review. Their scope and limitations are preserved in the adjacent review artifacts.

Related desk reviews: [C-first review](results/research-sprint-20261021/direction-review-current/independent-scientific-critic-review.md) and [B-first post-campaign review](results/research-sprint-20261021/direction-review-postcampaign/independent-critic-review.md).

## Paper contribution and claim boundary

If A1/A2 replicate the patterns, the strongest new sentence would be narrow: “On this frozen B5 audit task, response variation within identical evidence views was [smaller/comparable/larger] than differences between Public-only and Privileged-original views, and [prompt order/tool-enum order] shifted predictions on a balanced fixture.” It would not establish an LLM advantage, semantic understanding, or collusion.

For a potential Track 2.3 paper, B remains more promising: prospectively test the assigned package effect across new matched scenario groups, then state that parallel action and welfare outcomes are insufficient to establish communication-induced agreement or intent. The Sprint website currently says the submission window is closed while listing a future October 25 deadline; ask the organizers to resolve this before relying on a sprint submission window.

The LLM's nontrivial role is limited to natural-language extraction or semantic matching (e.g., complete allocation proposal and later ballot concordance), which must use independent human references and fixed rule baselines. The LLM should not compute structured welfare or serve as a latent-collusion oracle. ColluScope has not tested steganographic communication.

## Proposed single campaign authorization — not registered, not authorized

| Item | Proposed bound |
|---|---:|
| Named Cycle A1 | `m4-b5-presentation-order-factorial-v1` — 320 DeepSeek Flash generations |
| Named Cycle A2 | `m4-b5-interleaved-view-repeatability-v1` — 144 DeepSeek Flash generations |
| Total logical generations / physical attempts | **464 / 464**, zero retries, zero replacements |
| External provider | Official DeepSeek API only, `deepseek-flash` (the official page currently maps this alias to DeepSeek-V4.1-Flash-1017); no fallback |
| Frozen generation settings | Temperature 0, thinking disabled, max output 512; exact system prompt, task, schema, and request compiler hashes frozen before registration |
| Identity gate | Freeze the official alias and listed version before registration; require a returned fingerprint on the first assigned request and identical fingerprints thereafter. Any missing identity or mid-run drift is a terminal stop; the first request remains counted. A matching fingerprint does not prove identical hidden serving state. |
| Price window | Off-peak only; official pricing page currently lists $0.15/M cache-miss input and $0.60/M output off-peak. Current peak periods are 01:00–04:00 and 06:00–10:00 UTC weekdays. Recheck before each cycle. |
| Conservative cost reserve | At max 12,500 input + 512 output tokens/request, $1.012448 total off-peak; **hard cap $1.10** |
| Expiry | `2026-10-26T12:00:00Z`; unused slots expire |
| Private-data transfer | A2 sends the same 48 historical private-message events (two per case) three times each: **144 event appearances** to DeepSeek. This is explicit in-scope external transfer and requires approval. Raw response files remain local and Git-ignored. |
| Project-level impact | At most 464 new model calls; current ledger has 352/1,200 calls and $0.039167058/$2.50. Full use would be 816/1,200 calls and at most $1.139167058 total recorded-plus-reserved cost. |

Register and close A1, then A2, one at a time. Do not change prompts, scenarios, output labels, exclusions, or budgets after observing responses. Stop on expiry, cap, price/model/fingerprint drift, privacy boundary failure, unauthorized endpoint, or integrity mismatch. Invalid outputs and HTTP failures remain in their assigned denominators. A1 failure does not authorize replacement rows; A2 still runs only if its frozen inputs and privacy scope remain valid. This proposal does not reuse the consumed 232-request approval.

## Official references checked

- Apart Research, [AI Collusion Research Sprint 2026](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25): defines Track 2.2/2.3; current page displays “submission window has closed” alongside the October 25, 2026 deadline.
- Arike et al., [How does information access affect LLM monitors’ ability to detect sabotage?](https://arxiv.org/abs/2601.21112): information access and Extract-and-Evaluate on sabotage-monitor tasks; broad context-access novelty is therefore limited.
- Nakamura et al., [Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems](https://arxiv.org/abs/2602.15198): DCOP regret and divergence between communication and actions.
- Agrawal et al., [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413): direct communication and market behavior.
- Shi et al., [Emergent Collusion in Long-Horizon LLM Agent Interaction](https://arxiv.org/abs/2609.24967): peer interventions, reward structure, and interaction history.
- DeepSeek, [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/): alias, current listed model version, rates, and peak schedule checked on 2026-10-21.

## Reproduction and evidence files

Run in the repository root, with the protected local run directories available:

```powershell
python scripts/audit_public_harm_invariance.py --monitor-run runs/deepseek-first-m4/monitor --output docs/results/research-sprint-20261021/b5-direction-review/branch-a-independent-recheck-final.json
python scripts/score_b5_invariance_run.py --run runs/sprint-monitor/b5-evidence-view-stability-v1 --out docs/results/research-sprint-20261021/b5-direction-review/b5-120-score-independent-recheck-final.json
python scripts/audit_b5_deterministic_rule_baseline.py --out docs/results/research-sprint-20261021/b5-direction-review/b5-rule-baseline-independent-recheck-final.json
python scripts/analyze_m1_100_factorial_interaction.py --out-dir docs/results/research-sprint-20261021/b5-direction-review/m1-100-independent-recheck
python scripts/researchctl.py audit
```

These five commands were executed in this review and all exited 0. They made no model/API calls. See `docs/results/research-sprint-20261021/b5-direction-review/` for stdout, environment, critic record, independent M1 result, and the SHA-256 manifest. Historical raw payloads and private message text were not copied into this directory.
