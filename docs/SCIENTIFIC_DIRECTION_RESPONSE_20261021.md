# Scientific Direction Response — 2026-10-21

**Review type:** offline evidence reanalysis, adversarial direction comparison, and campaign design

**Model/API calls this review:** 0

**Scientific outcome:** the historical B5 effects are verified for the frozen requests; their mechanism and paper-level novelty remain `INCONCLUSIVE`.
**Next candidate:** a controlled B5 failure-mechanism campaign; not registered and not authorized.

## Why the real M4 anomaly was not the previous primary direction

The user is right that the evidence was already available. [`BRANCH_A_EVIDENCE_INVARIANCE.md`](BRANCH_A_EVIDENCE_INVARIANCE.md) and the hash-pinned `monitor_per_reference_scores.csv` independently reconstruct the 24 M4 cases. This review reran that audit and confirmed: 20/24 B5 Public-only/Privileged predictions changed, the reference changed 0/24 times, and exactness changed from 4/24 to 17/24. The underlying CSV hash is `ebfc472cb615fc351d35099e2f61469396a3f1d08d82534fe3daf4ebd9cc48a7`.

The previous direction treated the failure to identify a cause as a reason to demote the phenomenon. That was a research-selection error. “Not causal yet” means “design the discriminator,” not “the verified real-data anomaly is low value.” The separate 232-call campaign then tested A1 and balanced synthetic A2 forms, but bundled evidence-view changes and same-input variation remained; it did not close the mechanism question. Meanwhile, the synthetic matched-world audit was easier to validate but did not explain either the M4 view response or B5's all-`present` control failure. It should remain a supporting evidence-boundary control, not the main line.

The defensible next claim is still conditional: **B5's public-welfare labels are sensitive to request form and/or repeated identical requests on these fixed inputs; the available evidence does not yet identify which factor causes the changes.** This is a research question, not a claimed finding about collusion or intent.

## Independent reanalysis of the all-present failure

The no-call rule replay and matrix-distribution analysis add two useful constraints:

| Frozen corpus / arm | Reference | Monitor | Deterministic rule | Input/task profile |
|---|---:|---:|---:|---|
| 40 balanced synthetic Public-canonical rows | 20 present / 20 absent | 40 present; 20/40 exact | 40/40 exact | cell values 46–92; positive regret mean 115.9; mean relative regret 55.02% |
| 24 natural M4 Public-only contexts | 10 present / 14 absent | historical Branch A B5 exact 4/24; later campaign B5 exact 10/24 | 24/24 replayed | cell values 12–19; positive regret mean 4.7; mean relative regret 11.25% |
| Same 40 synthetic contexts, correct six-sum arithmetic aid | 20 present / 20 absent | 21 present, 19 absent; 39/40 exact | same 40/40 reference | arithmetic, length, and salience change together |
| Same 40 synthetic contexts, both prompt and enum order reversed | 20 present / 20 absent | 15 absent, 23 insufficient, 2 present; 10/40 exact | same 40/40 reference | prose order and tool-enum order are bundled |

This confirms that “all present” is not a parser failure, an invalid tool call, an unbalanced reference set, or an impossible public label. It is a finite model-output pattern on valid responses. The rule baseline is exact for the structured public-harm task, so the LLM has no demonstrated advantage on computing this label. The scale and relative-regret distributions differ greatly between M4 and synthetic A2; this is a plausible distribution confound, not proof that scale caused the failure. The 39/40 arithmetic result is promising but also changes prompt length and salience. The reversed arm cannot tell whether the prose order, enum order, or their interaction changed outputs.

The independent aggregate output is [`b5-task-difficulty-distribution-v2.json`](results/research-sprint-20261021/scientific-direction-review-followup-20261021/b5-task-difficulty-distribution-v2.json), SHA-256 `c36cf97644e5a4620383a1541573954d7ee1ee11c769a7fad0d24a931fa4bb5d`. Its analysis script is [`analyze_b5_task_difficulty.py`](../scripts/analyze_b5_task_difficulty.py), SHA-256 `a6b2fe87b1525527e8a2619b03d6de765ff1f851d29ca71094075e66645df9ad`.

### Competing explanations and minimum discriminators

| Explanation | Current support / counterexample | Smallest useful discriminator |
|---|---|---|
| **Prompt/schema label-order sensitivity** | The bundled reverse arm changed 36/40 predictions from production B5; isolated causes are unknown. | Cross prose label order (2) with tool-enum order (2) on every same frozen unit; hold everything else fixed. If neither isolated factor nor their interaction changes paired outputs, weaken this explanation. |
| **Arithmetic burden versus added-number/salience effect** | Correct six-sum table is 39/40 exact; no table is 20/40; but table content and prompt length changed together. | Compare no table, the six correct welfare totals, and an irrelevant numeric table with the same structure and tokenizer length. A gain unique to correct totals supports useful computation; equal gains from either table support added-number/salience effects. |
| **Numerical scale / matrix-distribution shift** | M4 values and regret are much smaller than the synthetic A2 values; this is a cross-corpus association only. | On the same 24 M4 public cases, multiply every payoff by five while retaining ballots and outcome. The truth is invariant. A systematic label change implicates magnitude; no change weakens magnitude alone but leaves relative-regret/task-distribution differences open. |
| **Task-definition ambiguity or welfare/collusion conflation** | The public-harm question is a clear welfare comparison, but the shared system prompt warns against inferring collusion from welfare loss. A model may conflate those instructions; that is unverified. | Add one frozen explicit definition that labels only `optimal public welfare − realized welfare > 0`, and explicitly says this is not a collusion label. Keep the evidence, schema, order, and other fields unchanged. |
| **Within-view response variation / mutable serving state** | 19/48 historical/current exact-request pairs disagreed despite byte-identical bodies and matching reported fingerprints. Provider identity is a mutable alias. | Three exact repeats per view, interleaved within each M4 case. Compare same-view disagreement with Public-only versus Privileged-original unique-majority changes. If within-view variation is as large or larger, do not attribute the historical single-call difference to view. |

The five contrasts are combined in a single 728-assignment campaign draft. No source row is filtered or replaced. The repeated Public-only/Privileged comparison remains a **bundle** (permission, messages, ledger structure, completeness, wording, and tokens); it cannot identify message semantics.

## A/B/C direction comparison and paper-worthiness

| Route | New knowledge if the next test succeeds | Falsifier | Closest-work overlap and plausible increment | Decision |
|---|---|---|---|---|
| **A. B5 evidence-view instability and all-present failure** | Whether presentation order, arithmetic support, task wording, numerical magnitude, or same-input variability explains specific parts of the frozen B5 behavior. | Isolated factors do not change paired predictions; correct arithmetic is no better than irrelevant numbers; or within-view variation matches/exceeds cross-view majority changes. | Arike et al. already study monitor information access, relevance filtering, and Extract-and-Evaluate. The possible increment is narrower: a permission-aware multi-Agent evidence setting with reproducible exact-input variation and a demonstrated separation of semantic evidence from interface presentation. | **Selected next diagnostic because it directly explains the verified real-data anomaly and the all-present failure.** It is not yet a paper-ready contribution; stop the line if deterministic rules remain sufficient and the LLM adds no validated value. |
| **B. Communication content, shared knowledge, and Agent choices** | Whether delivered message content contributes beyond shared target incentives and an added communication turn. | In a turn- and context-matched design, content has no effect beyond shared-target knowledge, or the package effect does not replicate across new payoff families. | Colosseum, double-auction agent work, long-horizon peer-intervention work, and recent competing-incentive consensus work already make generic “communication changes behavior” crowded. A distinct result needs clean separation of common knowledge, turn, content, and later action. | Keep as the strongest alternative for a later behavioral paper. The existing 9/15 M1 interaction is post-hoc and does not identify message semantics. Do not substitute it for the B5 mechanism question before the current anomaly is explained. |
| **C. Minimum sufficient evidence / identifiability** | Which exact claims can be supported from public projections and which require privileged events. | A source-verified reconstruction finds public projections differ in a content-bearing field, or removes the purported privileged sequence difference. | Partial observability and formal-monitoring work already provide the general principle. ColluScope's possible increment is a permission-specific claim ladder and missingness discipline. The 12 scripted pairs show public projections equal in 12/12, determinate element differences in 8/12, and complete-sequence differences in only 2/12. | Supporting Track 2.3 framework and control suite only. A constructed 12-pair pass is not the primary discovery and is not a standalone paper result. |

The “abstract sentence” that could be earned by A is conditional, not current: *“On a fixed balanced audit benchmark, isolated prompt/schema and calculation-support interventions explain which parts of a monitor's one-sided welfare judgments are presentation-sensitive, while repeated evidence views distinguish stable package response from same-input variation.”* If the planned factors fail, this sentence must be rejected; if they pass, it still needs cautious scope and should not imply general monitor capability.

## Independent Scientific Critic and disagreement

The separate-context, ranking-blind reviewer assessed A/B/C for paper-worthiness and did not read raw messages or make calls. Its review is archived at [`independent-scientific-critic-review.md`](results/research-sprint-20261021/scientific-direction-review-followup-20261021/independent-scientific-critic-review.md). This was a desk review of sanitized reports, not a second raw-data replay.

The reviewer ranked **C > B > A** for near-term effort and judged C supported only for the frozen synthetic fixture. It emphasized that C may merely restate a construction rule, does not prove a general impossibility theorem, and is not a strong standalone contribution. It judged A inconclusive because view factors remain bundled and a deterministic rule solves structured public welfare; it judged B inconclusive due to shared-target knowledge and the extra chat turn. Its strongest counterexample to C as a paper is that only 2/12 pairs differ on a complete sequence.

I do **not** adopt C as the primary route because low-cost deterministic confirmation is exactly the drift risk the user identified. A is selected as the next question because it explains a verified real-data anomaly and failure mode; the reviewer’s novelty concern is retained as a hard paper-worthiness gate. Another non-blind critic also cautioned against A as a main contribution; that view is recorded in the reviewer artifact and is not counted as blind confirmation. The evidence does not yet resolve this disagreement.

## Literature positioning

- Arike et al., [How does information access affect LLM monitors' ability to detect sabotage?](https://proceedings.mlr.press/v306/arike26a.html), ICML 2026: directly overlaps broad context-access and extract/evaluate monitor claims. We should not claim “more context changes a monitor” as novelty.
- Nakamura et al., [Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems](https://arxiv.org/abs/2602.15198): already connects communication judgments, action, and objective-grounded regret; it also documents communication/action divergence.
- Agrawal et al., [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413), and Shi et al., [Emergent Collusion in Long-Horizon LLM Agent Interaction](https://arxiv.org/abs/2609.24967): make generic communication/peer-intervention effects a crowded claim.
- Jones et al., [Drivers of LLM Consensus Formation Under Competing Incentives](https://arxiv.org/abs/2610.20200): a very recent competing-incentive result that further raises the bar for B.
- Wei et al., [Unveiling Selection Biases: Exploring Order and Token Sensitivity in Large Language Models](https://arxiv.org/abs/2406.03009), ACL Findings 2024, and Arraf et al., [Learning Rewrite-Invariant Reasoning with Targeted Alternation Training](https://proceedings.mlr.press/v306/arraf26a.html), ICML 2026: both make generic order/rewrite sensitivity an established topic. The proposed factorial must identify the particular effect in this audit task rather than claim generic position bias.
- Motwani et al., [Secret Collusion among AI Agents: Multi-Agent Deception via Steganography](https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html): threat-model context only. ColluScope has not run a steganography experiment.

The contribution is not established by these comparisons. A final paper still needs a verified novelty search and should be framed around permission-aware evidence, repeatability, and failure mechanisms only if the proposed campaign produces discriminating results.

## Campaign and authorization boundary

The candidate is [`m4-b5-mechanism-campaign-v1.md`](../research/drafts/m4-b5-mechanism-campaign-v1.md) with an output-independent sanitized assignment schedule generated by `scripts/freeze_m4_b5_mechanism_campaign.py`. It assigns 728 calls; the schedule's internal SHA-256 is `9329234b8afde015cddcff99c2ab606f130ffbf8f3101d837f36aaac8620b046`. The official off-peak price was checked on 2026-10-21 at $0.15/M uncached input and $0.60/M output; a 15,000-input/512-output cap per request implies $1.8616416 worst-case usage estimate, with a proposed $1.95 hard cap. The budget registry currently has 848 calls and $2.460832942 remaining. Campaign expiry proposed: 2026-10-25 23:59 UTC; only official DeepSeek Flash, off-peak, zero retries/replacements. The model version and off-peak windows are subject to immediate preflight confirmation on the [official pricing page](https://api-docs.deepseek.com/quick_start/pricing/).

The 72 Privileged-original repeats carry two private-message event appearances each (144 appearances sent to the provider). Raw messages/responses stay in the restricted, Git-ignored run. The assignment schedule contains no labels, payloads, raw IDs, or private text.

The existing 232-call grant is consumed and cannot fund this design. No request may be dispatched until the user approves this new named campaign, exact prompt/request bytes are frozen offline, all 728 requests pass privacy/token/cost checks, and a new authorization is registered. The official DeepSeek price page currently lists `deepseek-flash` as DeepSeek-V4.1-Flash-1017, with off-peak uncached input $0.15/M and output $0.60/M; peak rates are double and are prohibited here. Recheck the official page before dispatch because the provider can change prices and aliases. No M1, M2, or synthetic-sequence inference is included in this scope.

## Reproduction and current boundary

```powershell
python scripts/audit_public_harm_invariance.py --monitor-run runs/deepseek-first-m4/monitor --output docs/results/research-sprint-20261021/scientific-direction-review-followup-20261021/branch-a-final-rerun.json
python scripts/audit_b5_deterministic_rule_baseline.py --out docs/results/research-sprint-20261021/scientific-direction-review-followup-20261021/b5-rule-baseline-rerun.json
python scripts/analyze_b5_task_difficulty.py --out docs/results/research-sprint-20261021/scientific-direction-review-followup-20261021/b5-task-difficulty-distribution-v2.json
python scripts/freeze_m4_b5_mechanism_campaign.py
python scripts/freeze_m4_b5_mechanism_campaign.py --check
python scripts/researchctl.py audit
```

These commands perform offline analysis/schedule construction only. The rerun stdout is preserved in `branch-a-final-rerun.log`, `b5-rule-baseline-rerun.log`, and `b5-task-difficulty-analysis-v2.log`; the deterministic schedule check is in `m4-b5-mechanism-schedule-check.log`; and the final registry audit is in `researchctl-audit-final.log`. The analyzer's initial source-selection, JSON extraction, and sorted-permutation mistakes are preserved in three failure logs and the invalid intermediate output beside the final distribution file. They are analysis-script failures, not historical experiment failures. The new schedule generator reports zero model calls and explicitly labels itself unregistered and unauthorized. `researchctl audit` reports 4 registered closed cycles, 0 open experiments, 352 past requests, and no integrity errors; scientific validity is not something that registry check can establish.
