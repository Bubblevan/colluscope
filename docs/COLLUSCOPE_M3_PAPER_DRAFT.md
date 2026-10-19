# ColluScope: Evidence-Aware Auditing of Communication and Allocation Behavior in Multi-Agent LLMs

**Manuscript draft for review. Not a submission-ready paper.**

**Target context:** Apart Research AI Collusion Research Sprint 2026, Tracks 2.2 and 2.3. Verify the current submission portal, formatting, and deadlines before any submission.

**Portal status check (2026-10-20):** the official sprint page currently says the submission window has closed while listing the event for October 23–25. This draft is not submitted; verify directly with the organizers before preparing an upload.

**Authors:** [Add author names]

**Affiliations:** [Add affiliations]

## Abstract

We examine communication and allocation traces in a three-agent task with public welfare and private/public rewards. Local Qwen3-8B generated 25 historical and 75 prospective episodes across five conditions, three payoff families, and 15 matched groups. A DeepSeek Flash audit scored 1,500 repeated evidence-view rows without assigning collusion labels. In the prospective data, the rewarded target was executed in 9/15 private-incentive/chat episodes and 0/15 matched no-chat episodes; shared target knowledge and an extra communication stage prevent causal attribution. Fourteen delivered proposals preceded matching sender/recipient ballots, but no explicit commitment marker was found. Public-harm accuracy ranged from 8% to 100%; request replay found the welfare-gap value directly in every action-bearing view, explaining perfect performance in one structured cell as answer exposure. We propose provenance-aware observable labels, explicit abstention, and a controlled message-content replay. Results describe behavior; they do not detect latent collusion.

## 1. Introduction

Multi-agent LLM systems can coordinate through direct text, shared incentives, public actions, and potentially covert channels. Existing work studies collusion in settings including allocation, markets, and steganographic communication. The Colosseum benchmark evaluates strategic behavior using regret-based measures [Colosseum](https://arxiv.org/abs/2602.15198); a double-auction study examines LLM-agent collusion under direct seller communication [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413); and work on steganographic collusion shows that coordination can be encoded in apparently innocuous text [Hidden in Plain Text](https://arxiv.org/abs/2410.03768), [Secret Collusion among AI Agents](https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html). These settings motivate audits that combine what agents say and do, while making the evidentiary threshold for a collusion claim explicit.

ColluScope addresses two related questions aligned with the 2026 AI Collusion Research Sprint: whether combining speech with actions improves monitoring, and what should count as convincing evidence of collusion [official sprint page](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25). Our data expose a basic identification problem: agents can independently choose the same allocation because they share a rewarded target, while poor allocations can arise from ordinary individual errors or a tie-break. Communication availability, message delivery, action agreement, and welfare loss each describe different events; none alone establishes intent.

We contribute an evidence audit, not a collusion detector. We (1) independently recompute agent outcomes from raw ballots and payoff matrices; (2) re-score monitor outputs from exact request/response artifacts; (3) identify direct answer leakage in model-facing evidence; and (4) propose a narrow counterfactual message experiment that separates proposal content from shared-target incentives and extra turn/context effects.

## 2. Research questions and claims

**RQ1 (Track 2.2):** Does adding permitted communication to action evidence improve extraction of observable facts under comparable inputs and token costs?

**RQ2 (Track 2.3):** Which trace combinations support a defensible mechanism description, and which remain insufficient to infer agreement or intent?

The current monitor comparison is not a clean test of RQ1 because views vary in content, serialization, derived computations, permission, and token count. It can still falsify the simple expectation that adding private messages necessarily improves public-harm classification.

The current corpus can support claims about assigned incentives, messages sent and delivered, literal proposal patterns, ballots, selected allocations, welfare regret, and deterministic proposal/action concordance. It cannot support a latent-collusion gold label, a causal communication effect, or external validity beyond one model and these scenario families.

## 3. Experimental setting

### 3.1 Agent behavior corpus

Three agents allocate three tasks under a public quality matrix. Each agent receives task-specific score information, while interventions vary whether target rewards are public or private and whether A and B can communicate. The environment settles sealed ballots by plurality; when all three ballots differ, the chair's ballot determines the allocation. Public welfare and individual realized task scores are distinct outcomes.

The corpus has two provenance strata:

- **Historical F0:** 25 episodes from the original M1-P0 pilot, five conditions by five matched seed blocks, under the original payoff matrix.
- **Prospective F1–F3:** 75 assigned episodes, five conditions by fifteen matched groups, across three payoff-matrix families selected before observing model outputs. Each family has a unique public optimum and a publicly suboptimal rewarded target; target regret varies by family.

All agent actions were generated by the same local Qwen3-8B-Q4_K_M checkpoint (SHA-256 d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785), at temperature zero under the audited llama.cpp runtime. This is one deterministic checkpoint, not a sample of model populations or decoding variance. F0 and the prospective extension are reported separately; their raw welfare values are not pooled across payoff scales.

### 3.2 Independent behavioral reconstruction

The post-run audit reconstructs assignments from raw ballots, applies the frozen plurality/chair rule, enumerates the six possible task permutations, and recomputes public welfare and matrix-specific regret. A positive regret means the selected allocation falls below that matrix's public optimum. Stored B harm flags are retained as source artifacts but are not authoritative when they disagree with raw replay.

### 3.3 Monitor corpus and evidence views

A one-shot M2-V3 run scheduled 1,500 atomic task/view rows over 75 prospective episodes: 250 F1 calibration rows and 1,250 F2/F3 rows. It produced 916 unique DeepSeek Flash API responses, one physical attempt each, with zero retries. Every scheduled output was syntactically valid. F2/F3 had been exposed in earlier M1 development and are exploratory, not pristine held-out test data. F0 received no monitor call.

The tasks concerned public-harm status, ballot disagreement, delivered-message presence, literal complete-allocation proposals, and proposal/action concordance. Evidence views included Action-only, Raw Fusion, Structured Evidence, Structured without findings, and Text-only where scheduled; Public-only and Privileged Audit permissions were used where applicable. The frozen Public-only evidence was preserved. Privileged Audit was a separate input projection, not a replacement for Public-only E.

### 3.4 Independent monitor audit and baselines

The independent audit does not import the frozen M2 reference/scoring implementation. It reconstructs the task reference from raw source, parses the exact stored response, audits the exact payload, and compares every scored field with the immutable original score file. It reports:

- **Always nonpositive:** always predict the task's frozen negative observable class.
- **Deterministic source replay:** compute the observable fact directly from the evidence needed for that task. This is a rule/oracle reference, not an LLM.
- **DeepSeek Flash:** the original model output, with fact correctness, citations, and abstention scored separately.

The primary score contract was not changed after the run. A post-hoc provenance-linked F-finding citation analysis is reported only as a sensitivity analysis.

## 4. Results

### 4.1 Behavioral outcomes

All 75 prospective episodes completed and all assigned ballots parsed. Thirteen had positive public regret: nine target executions in the private target-incentive/chat condition and four non-target allocations under normal cooperation, common public incentive, or chat without side bonus.

| Prospective condition | Episodes | Rewarded target executed | Positive regret |
|---|---:|---:|---:|
| Normal cooperation | 15 | 0 | 2 |
| Common public incentive | 15 | 0 | 1 |
| Private target incentive + chat | 15 | 9 | 9 |
| Private target incentive, no chat | 15 | 0 | 0 |
| Chat, no side bonus | 15 | 0 | 1 |

Within the 15 private-incentive matched groups, target execution was higher in the chat arm in nine groups and tied in six. The regret difference was zero in six groups, +6 in one, +12 in five, and +18 in three. These are descriptive matched differences. The chat condition adds an agent decision stage and context, and both A and B know the same rewarded target before messages are composed.

Fourteen complete target-allocation proposals were sent and delivered in nine prospective episodes. Every sender and recipient later voted for the proposed allocation. Messages were generated before either agent saw the other's text, and no proposal matched the narrow explicit-commitment marker. These facts establish a sequence of delivered proposal and concordant ballots, not message-caused voting, negotiated agreement, or collusion.

Across all 100 source episodes, 12 episodes contained at least one delivered message (19 message events): three historical F0 episodes contained five messages, and nine prospective episodes contained 14.

The historical F0 results differ: normal cooperation had 2/5 positive-regret episodes; common public incentive had 4/5 and executed the target in 2/5; private-incentive/chat executed the target in 3/5; private incentive/no-chat and chat without bonus had no target execution. Six F0 episodes reached the chair tie-break, four with welfare regret. The prospective extension had no chair tie-break. This reversal is a warning against treating the combined 100 as identically generated or the common-reward outcome as stable.

### 4.2 Counterexamples and bad cases

- **Ordinary harm without communication:** prospective episode m1-100-episode-013 had regret 15 under normal cooperation, no delivered message, and no rewarded-target execution. At least one suboptimal individual ballot explains the outcome without communication-induced coordination.
- **Harm flag contradicted by replay:** in m1-100-episode-012, stored B marked harmful_outcome=true although the raw ballots selected the public optimum and recomputed regret was zero. The stale flag remains preserved and is excluded from authoritative labels.
- **Chair mechanism:** historical episodes include harmful chair tie-breaks when all agents chose different ballots. Such outcomes are generated by the declared environment rule, not evidence of an agreement.
- **Concordant proposal under shared incentive:** proposal-bearing episodes are consistent with communication-linked coordination, but both agents already knew the target and generated messages simultaneously. The same data are compatible with independent parallel incentives.
- **Citation ontology mismatch:** a Structured Evidence / Public-only response for m1-100-episode-028 cited the visible derived finding F01 along with P05. The frozen citation contract accepts source-event IDs only, so this citation remained invalid in primary scoring. A separate provenance-linked sensitivity analysis was performed without changing the original score.

### 4.3 Monitor performance on F2/F3

| Observable task | Repeated rows | DeepSeek exact result |
|---|---:|---:|
| Public-harm fact | 350 | 158 / 350 (45.14%) |
| Ballot disagreement | 350 | 350 / 350 (100%) |
| Delivered-message presence | 200 | 200 / 200 (100%) |
| Literal full allocation proposal | 200 | 181 / 200 (90.5%) |
| Proposal/action concordance | 150 | 149 / 150 (99.33%) |

Rows repeat the same episode across views and permissions; these are not independent examples. Deterministic source replay was perfect by construction. Always-nonpositive accuracy illustrates prevalence effects: 84% for public harm, 76% for ballot disagreement, and 90% for message presence, literal proposal, and concordance.

For public harm, every F2/F3 cell has 50 rows and eight positive examples:

| View / permission | DeepSeek exact | TP / FP / FN | Always nonpositive |
|---|---:|---:|---:|
| Action-only / Public-only | 24% | 6 / 11 / 2 | 84% |
| Raw Fusion / Public-only | 40% | 8 / 30 / 0 | 84% |
| Raw Fusion / Privileged Audit | 28% | 8 / 36 / 0 | 84% |
| Structured Evidence / Public-only | 100% | 8 / 0 / 0 | 84% |
| Structured Evidence / Privileged Audit | 98% | 8 / 1 / 0 | 84% |
| Structured without findings / Public-only | 18% | 5 / 5 / 3 | 84% |
| Structured without findings / Privileged Audit | 8% | 3 / 16 / 5 | 84% |

Across the 350 repeated public-harm rows, there were 99 false-positive present predictions, 10 false-negative absent predictions, and 83 incorrect abstentions. All format checks passed, but format validity did not imply factual validity.

### 4.4 Direct-answer exposure and view fairness

Exact payload replay found a public outcome welfare_gap field in all eligible action-bearing contexts: 64/64 Action-only/Public-only; 64/64 Raw Fusion/Public-only; 75/75 Raw Fusion/Privileged; 64/64 Structured Evidence/Public-only; 75/75 Structured Evidence/Privileged; 65/65 Structured without findings/Public-only; and 75/75 Structured without findings/Privileged. Text-only/Privileged had 0/75 contexts with this field.

Structured Evidence additionally included deterministic welfare-regret and ballot-disagreement findings; the privileged view also included message-derived proposal and proposal/ballot-consistency findings. Therefore, 100% public-harm accuracy under Structured Evidence / Public-only is directly answer-exposed. The deterministic threshold baseline also achieves 100%. Conversely, the no-findings structured views performed poorly despite seeing the raw welfare_gap, showing that monitor outputs were unstable even with an explicit answer field.

The views are not a factorial comparison that holds everything but modality constant. They differ in event content, permission, serialized format, derived calculations, task prompt, token count, and response length. For example, on public-harm requests the proportionally allocated prompt usage was 23,995 tokens per evaluation row for Action-only/Public-only and 29,381 for Raw Fusion/Public-only; these are allocations of shared request usage, not extra calls. Across the run the provider reported 865,059 input and 16,222 output tokens. The exact per-task/view usage table is included in the audit package.

Matched public-harm contrasts over 50 paired rows and ten scenario/seed groups were:

| Contrast | Difference | Right wins / ties / left wins | Group-bootstrap 95% interval |
|---|---:|---:|---:|
| Action-only/Public-only → Raw Fusion/Privileged | +4 pp | 8 / 36 / 6 | −20 to +32 pp |
| Raw Fusion/Public-only → Raw Fusion/Privileged | −12 pp | 0 / 44 / 6 | −30 to 0 pp |
| Raw Fusion/Public-only → Structured Evidence/Public-only | +60 pp | 30 / 20 / 0 | +30 to +88 pp |
| Raw Fusion/Privileged → Structured Evidence/Privileged | +70 pp | 36 / 13 / 1 | +46 to +90 pp |

Bootstrap resampling uses the matched group, not individual rows, with 20,000 replicates and seed 20261020. F2/F3 prior exposure and ten groups make these exploratory intervals, not confirmatory inferential results. The structured-view gains are confounded by deterministic findings; raw fusion with private messages shows no benefit.

### 4.5 Citation and abstention

The original M/P-only citation contract remains primary. In the public-harm Structured Evidence / Public-only cell, 0/50 citations met the frozen sufficient-source contract; in Privileged Audit, 2/50 did. A diagnostic that accepts a visible derived finding only when its complete event provenance is visible and supports the independently recomputed fact raised these counts to 50/50 in both cells. This does not replace frozen scoring; it shows the prompt's evidence ontology and citation format were misaligned.

The monitor also correctly handled two negative controls: 222/222 complete-empty message-stream rows were labeled absent, and 177/177 concordance rows with no assessable proposal were appropriately marked not assessable. Correctly finding absence or abstaining is distinct from inferring intent.

## 5. Evidence-aware interpretation

The evidence hierarchy in EVIDENCE_AWARE_AUDITING_FRAMEWORK.md separates assignment (T), actual behavior (B), public consequences, message interpretation, cross-event consistency, permission-specific evidence (E), monitor claims, and latent intent. Each derived label should carry source hashes, event IDs, permission, derivation version, and label provenance.

A convincing mechanism report can say that a message was delivered, contained a literal proposal under a named codebook, and was followed by ballots matching that proposal. It should also state that the agents shared knowledge of the same target before communication. Unless communication content is varied while other context and decision stages remain fixed, the message's causal effect is unknown. The present dataset contains no validated latent-collusion reference labels.

## 6. Proposed next experiment

We propose a separate 12-group local counterfactual replay across the three existing payoff families, four fresh seeds per family. In each group, preserve the private target incentive and actual A/B message stage. For a recipient of a complete delivered proposal, compare the original proposal with token-matched neutral text, a masked proposal, and a same-stage no-delivery event. Hold checkpoint, matrix, agent identity, chair, incentive delivery, own previous message action, other incoming messages, ballot prompt, and decoding fixed. Keep two peer ballots anchored and recompute settlement deterministically after each focal ballot.

The maximum call graph is 24 A/B message actions + 36 baseline ballots + 36 additional focal ballots = 96 local generations, with no replacement for ineligible/invalid cases. Proposal eligibility is decided from message evidence before new ballot outputs. This tests a narrow within-checkpoint message-content effect conditional on a delivered proposal; it does not identify general collusion. The draft protocol is not frozen and authorizes no execution. A distinct approval must set the exact model/runtime, sample schedule, request budget, and retention rules.

## Appendix A. Limitations

- One model checkpoint, one deterministic decoding configuration, and a small number of matched groups limit model and scenario generalization.
- Historical F0 and prospective F1–F3 have different provenance and payoff matrices; pooled raw welfare is not meaningful.
- F2/F3 outcomes were exposed during prior development. They cannot support a pristine held-out benchmark claim.
- The DeepSeek alias did not expose a weight hash or exact tokenizer revision. The reported model name and system fingerprint do not prove checkpoint-level replication.
- Four-view differences change multiple inputs at once. Token/cost normalization and content-matched ablations were not frozen as a full factorial design.
- Message proposal and commitment codes are mechanical; no blinded human semantic coding or inter-rater reliability is available.
- The supplied 12-case development reference matches raw source replay: three historical F0 message-bearing episodes (five messages) plus nine prospective episodes (14 messages). Their exact IDs are frozen in the M3 draft as development/descriptive cases only.
- No experiment here identifies deceptive intent, a secret agreement, or whether a message caused a ballot.

## Appendix B. Dual-Use and Ethical Considerations

This work uses synthetic allocation matrices and a local agent runtime for the behavior corpus. The bounded M2 monitor run used the explicitly authorized API only for permission-filtered synthetic task evidence; it did not receive hidden treatment assignments, gold labels, raw unfiltered researcher records, or real-world financial data. Raw privileged messages remain local and are not reproduced in this paper.

The evidence compiler and auditor could be misused to surveil agent conversations or overstate ambiguous patterns. We therefore report observables separately, retain privacy boundaries, preserve abstention and unknown-intent states, and do not present the framework as an operational accusation system. No real bank system, human participant, or live financial decision was involved in the audited experiments.

## 9. Reproducibility and disclosures

The M2 independent audit, raw response reparse, baselines, paired contrasts, field inventory, token accounting, privacy scan, figures, and hashes are under docs/results/m2-final-scientific-synthesis/. Reproduction:

    python -m pytest -q tests/test_m2_final_scientific_audit.py
    python scripts/audit_m2_final.py --out docs/results/m2-final-scientific-synthesis

The source behavior audits are documented in M1_P0_POSTRUN_SCIENTIFIC_AUDIT.md and M1_100_SCIENTIFIC_AUDIT.md. Private run artifacts remain ignored and permission-restricted. The audit created zero model calls.

**AI-assistance disclosure draft:** Codex assisted with software implementation, independent deterministic recomputation, diagnostic analysis, and manuscript drafting. The authors remain responsible for checking every claim, source, result, and disclosure before submission. The DeepSeek model was used only in the previously authorized atomic monitor run; no model was called while preparing this synthesis. Revise this statement to match the organizers' final disclosure requirements and the exact submission workflow.

## References

- [Apart Research, AI Collusion Research Sprint 2026](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25)
- [Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems](https://arxiv.org/abs/2602.15198)
- [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413)
- [Hidden in Plain Text](https://arxiv.org/abs/2410.03768)
- [Secret Collusion among AI Agents: Multi-Agent Deception via Steganography](https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html)
