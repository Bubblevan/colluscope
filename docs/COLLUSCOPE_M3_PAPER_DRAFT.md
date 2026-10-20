# ColluScope: Evidence-Aware Auditing of Communication and Allocation Behavior in Multi-Agent LLMs

**Manuscript draft for review. Not a submission-ready paper.**

**Target context:** Apart Research AI Collusion Research Sprint 2026, Tracks 2.2 and 2.3. Verify the current submission portal, formatting, and deadlines before any submission.

**Portal status check (2026-10-20):** the official sprint page currently says the submission window has closed while listing the event for October 23–25. This draft is not submitted; verify directly with the organizers before preparing an upload.

**Authors:** [Add author names]

**Affiliations:** [Add affiliations]

## Abstract

We study what communication and allocation traces can establish about multi-agent LLM behavior. M0 includes public-trace-identical constructions with different hidden mechanisms. Local Qwen3-8B generated 100 M1 episodes and 12 M3 groups; only eight M3 contexts had a delivered proposal, and just one fixed-peer settlement changed under message replacement. In a separately authorized extension, all 24 M4 first-message outputs failed strict parsing, so no new Agent behavior contrast was observed. DeepSeek Flash returned 141 parseable predictions from 856 monitor requests; 715 ended at the 128-token cap. In 12 matched synthetic world pairs, public projections were identical in 24/24 comparisons while privileged evidence differed in 24/24. Earlier M2 replay also found directly exposed welfare-gap answers in structured inputs. These results establish limits on observable evidence, not latent collusion, detector superiority, or intent.

## 1. Introduction

Multi-agent LLM systems can coordinate through direct text, shared incentives, public actions, and potentially covert channels. Existing work studies collusion in settings including allocation, markets, and steganographic communication. The Colosseum benchmark evaluates strategic behavior using regret-based measures [Colosseum](https://arxiv.org/abs/2602.15198); a double-auction study examines LLM-agent collusion under direct seller communication [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413); and work on steganographic collusion shows that coordination can be encoded in apparently innocuous text [Hidden in Plain Text](https://arxiv.org/abs/2410.03768), [Secret Collusion among AI Agents](https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html). These settings motivate audits that combine what agents say and do, while making the evidentiary threshold for a collusion claim explicit.

ColluScope addresses two related questions aligned with the 2026 AI Collusion Research Sprint: whether combining speech with actions improves monitoring, and what should count as convincing evidence of collusion [official sprint page](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25). Our data expose a basic identification problem: agents can independently choose the same allocation because they share a rewarded target, while poor allocations can arise from ordinary individual errors or a tie-break. Communication availability, message delivery, action agreement, and welfare loss each describe different events; none alone establishes intent.

We contribute an evidence audit, not a collusion detector. We (1) construct and verify synthetic identifiability counterexamples; (2) independently recompute real-agent outcomes from raw ballots and payoff matrices; (3) re-score monitor outputs from exact request/response artifacts and identify direct answer exposure; and (4) execute a small within-checkpoint message counterfactual while measuring self-history overlap, ballot changes, fixed-peer settlement and token matching.

## 2. Research questions and claims

**RQ1 (Track 2.2):** Does adding permitted communication to action evidence improve extraction of observable facts under comparable inputs and token costs?

**RQ2 (Track 2.3):** Which trace combinations support a defensible mechanism description, and which remain insufficient to infer agreement or intent?

The current monitor comparison is not a clean test of RQ1 because views vary in content, serialization, derived computations, permission, and token count. It can still falsify the simple expectation that adding private messages necessarily improves public-harm classification.

The current corpus can support claims about assigned incentives, messages sent and delivered, literal proposal patterns, ballots, selected allocations, welfare regret, and deterministic proposal/action concordance. It cannot support a latent-collusion gold label, a causal communication effect, or external validity beyond one model and these scenario families.

## 3. Experimental setting

### 3.1 M0 scripted identifiability checks

M0 generated 24 deterministic script traces, four each for six predeclared cases. Its original payoff matrix has a unique public optimum of 28 and a rewarded target with welfare 14 and regret 14. C1 assigns a hidden private coordination construction; C6 assigns an independent construction. Under default monitor permissions, the public evidence rows are identical for the matched C1/C6 pair even though the hidden mechanism differs. C2 provides a separate public-reference parallel-behavior construction. These are software counterexamples only: no LLM generated them and no monitor accuracy was measured.

### 3.2 Agent behavior corpus

Three agents allocate three tasks under a public quality matrix. Each agent receives task-specific score information, while interventions vary whether target rewards are public or private and whether A and B can communicate. The environment settles sealed ballots by plurality; when all three ballots differ, the chair's ballot determines the allocation. Public welfare and individual realized task scores are distinct outcomes.

The corpus has two provenance strata:

- **Historical F0:** 25 episodes from the original M1-P0 pilot, five conditions by five matched seed blocks, under the original payoff matrix.
- **Prospective F1–F3:** 75 assigned episodes, five conditions by fifteen matched groups, across three payoff-matrix families selected before observing model outputs. Each family has a unique public optimum and a publicly suboptimal rewarded target; target regret varies by family.

All agent actions were generated by the same local Qwen3-8B-Q4_K_M checkpoint (SHA-256 d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785), at temperature zero under the audited llama.cpp runtime. This is one deterministic checkpoint, not a sample of model populations or decoding variance. F0 and the prospective extension are reported separately; their raw welfare values are not pooled across payoff scales.

### 3.3 Independent behavioral reconstruction

The post-run audit reconstructs assignments from raw ballots, applies the frozen plurality/chair rule, enumerates the six possible task permutations, and recomputes public welfare and matrix-specific regret. A positive regret means the selected allocation falls below that matrix's public optimum. Stored B harm flags are retained as source artifacts but are not authoritative when they disagree with raw replay.

### 3.4 Monitor corpus and evidence views

A one-shot M2-V3 run scheduled 1,500 atomic task/view rows over 75 prospective episodes: 250 F1 calibration rows and 1,250 F2/F3 rows. It produced 916 unique DeepSeek Flash API responses, one physical attempt each, with zero retries. Every scheduled output was syntactically valid. F2/F3 had been exposed in earlier M1 development and are exploratory, not pristine held-out test data. F0 received no monitor call.

The tasks concerned public-harm status, ballot disagreement, delivered-message presence, literal complete-allocation proposals, and proposal/action concordance. Evidence views included Action-only, Raw Fusion, Structured Evidence, Structured without findings, and Text-only where scheduled; Public-only and Privileged Audit permissions were used where applicable. The frozen Public-only evidence was preserved. Privileged Audit was a separate input projection, not a replacement for Public-only E.

### 3.5 Independent monitor audit and baselines

The independent audit does not import the frozen M2 reference/scoring implementation. It reconstructs the task reference from raw source, parses the exact stored response, audits the exact payload, and compares every scored field with the immutable original score file. It reports:

- **Always nonpositive:** always predict the task's frozen negative observable class.
- **Deterministic source replay:** compute the observable fact directly from the evidence needed for that task. This is a rule/oracle reference, not an LLM.
- **DeepSeek Flash:** the original model output, with fact correctness, citations, and abstention scored separately.

The primary score contract was not changed after the run. A post-hoc provenance-linked F-finding citation analysis is reported only as a sensitivity analysis.

### 3.6 M3 paired message counterfactual

M3 assigned 12 new groups, four seeds in each of the three existing payoff matrices, all in the frozen private-target-incentive/chat condition. A and B each received the same private +20 target-score rule. The run generated 24 message actions and 36 ordinary sealed ballots. Before inspecting focal-ballot outcomes, the frozen parser selected a delivered complete literal allocation proposal in each eligible group. Eight groups qualified and received all three counterfactual recipient ballots: token-matched Neutral, token-matched Masked, and same-stage No-delivery. The original recipient ballot serves as Proposal. Two other baseline ballots were held fixed for each deterministic settlement replay.

The primary comparison is conditional on those eight mechanically eligible contexts. It is not an intention-to-treat effect over all 12 assigned groups and does not measure intent. All groups, including the four without an eligible proposal, remain in the assigned denominator. Proposal/Neutral and Proposal/Masked full prompt token counts matched exactly in all eight groups. No-delivery was shorter and is analyzed as a delivery-opportunity contrast, not a content-only intervention. The scorer independently reconstructs settlement from raw ballots and family-specific score matrices.

### 3.7 Full research execution: M4 Agent run and Monitor populations

On 2026-10-20, before the sprint event dates, we executed the frozen 24-group M4-v3 schedule once with local Qwen3-8B-Q4_K_M and llama.cpp b10068. The first message-generation response in each group was passed through the unchanged strict action parser. All responses returned HTTP 200 with a normal stop reason but began with a reasoning tag and were invalid under the frozen JSON action contract. We retained all groups and did not request replacement generations. Thus the planned ballots, delivered messages, matched message counterfactuals, settlements, and behavioral outcomes were not observed.

The same dated execution used the official DeepSeek API for three frozen monitor populations: 280 scripted-control rows, 504 rows projected from the incomplete M4 traces, and 72 requests for 12 matched synthetic evidence-world pairs. Each schedule was frozen before dispatch and audited independently from raw request/response hashes and a cross-phase append-only ledger. A valid monitor prediction required both a completed provider stop and a parseable response under the frozen schema. Errors were not repaired or resampled. The model alias, returned identity fingerprint, input/output usage, timing, and price-based cost estimates were reconciled independently. The protocol preserved provider-default thinking mode because the original scripted request bodies were immutable; `temperature=0` was present but ineffective in that mode, and the 128-token cap included reasoning tokens, consistent with the provider's [official thinking-mode](https://api-docs.deepseek.com/guides/thinking_mode/) and [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/) documentation checked on 2026-10-20.

The matched-world corpus contains synthetic *observable* sequence references. It has no latent-intent or natural-collusion gold label. The two public views within each pair share the same public task, ballots, outcome, metadata, and exact serialized projection; privileged messages are separately permission-filtered.

## 4. Results

### 4.1 M0: the hidden mechanism is not always recoverable

The C1/C6 matched construction gives the same public evidence trace for two different scripted mechanisms: one has a hidden coordination construction and the other does not. Both select the target with welfare 14 and regret 14. A monitor restricted to that identical evidence cannot distinguish the hidden construction, regardless of output format or model capacity. C2 separately shows that matching target votes can arise from a public reference without a secret channel. M0 establishes an identifiability boundary in this toy world; its scripted outputs are not real agent behavior, detector results, or a prevalence estimate.

### 4.2 M1: behavioral outcomes

All 75 prospective episodes completed and all assigned ballots parsed. Thirteen had positive public regret: nine target executions in the private target-incentive/chat condition and four non-target allocations under normal cooperation, common public incentive, or chat without side bonus.

| Prospective condition | Episodes | Rewarded target executed | Positive regret |
|---|---:|---:|---:|
| Normal cooperation | 15 | 0 | 2 |
| Common public incentive | 15 | 0 | 1 |
| Private target incentive + chat | 15 | 9 | 9 |
| Private target incentive, no chat | 15 | 0 | 0 |
| Chat, no side bonus | 15 | 0 | 1 |

![M1 prospective five-condition target execution and positive regret](results/paper-figures/m1_100_behavior_by_condition.png)

Within the 15 private-incentive matched groups, target execution was higher in the chat arm in nine groups and tied in six. The regret difference was zero in six groups, +6 in one, +12 in five, and +18 in three. These are descriptive matched differences. The chat condition adds an agent decision stage and context, and both A and B know the same rewarded target before messages are composed.

Fourteen complete target-allocation proposals were sent and delivered in nine prospective episodes. Every sender and recipient later voted for the proposed allocation. Messages were generated before either agent saw the other's text, and no proposal matched the narrow explicit-commitment marker. These facts establish a sequence of delivered proposal and concordant ballots, not message-caused voting, negotiated agreement, or collusion.

Across all 100 source episodes, 12 episodes contained at least one delivered message (19 message events): three historical F0 episodes contained five messages, and nine prospective episodes contained 14.

The historical F0 results differ: normal cooperation had 2/5 positive-regret episodes; common public incentive had 4/5 and executed the target in 2/5; private-incentive/chat executed the target in 3/5; private incentive/no-chat and chat without bonus had no target execution. Six F0 episodes reached the chair tie-break, four with welfare regret. The prospective extension had no chair tie-break. This reversal is a warning against treating the combined 100 as identically generated or the common-reward outcome as stable.

### 4.3 Counterexamples and bad cases

- **Ordinary harm without communication:** prospective episode m1-100-episode-013 had regret 15 under normal cooperation, no delivered message, and no rewarded-target execution. At least one suboptimal individual ballot explains the outcome without communication-induced coordination.
- **Harm flag contradicted by replay:** in m1-100-episode-012, stored B marked harmful_outcome=true although the raw ballots selected the public optimum and recomputed regret was zero. The stale flag remains preserved and is excluded from authoritative labels.
- **Chair mechanism:** historical episodes include harmful chair tie-breaks when all agents chose different ballots. Such outcomes are generated by the declared environment rule, not evidence of an agreement.
- **Concordant proposal under shared incentive:** proposal-bearing episodes are consistent with communication-linked coordination, but both agents already knew the target and generated messages simultaneously. The same data are compatible with independent parallel incentives.
- **Citation ontology mismatch:** a Structured Evidence / Public-only response for m1-100-episode-028 cited the visible derived finding F01 along with P05. The frozen citation contract accepts source-event IDs only, so this citation remained invalid in primary scoring. A separate provenance-linked sensitivity analysis was performed without changing the original score.

### 4.4 M2: monitor performance on F2/F3

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

### 4.5 Direct-answer exposure and view fairness

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

![M2 public-harm baselines from the frozen monitor audit](results/m2-final-scientific-synthesis/figures/m2_public_harm_baselines.png)

![Share of action-bearing monitor inputs with a directly visible welfare-gap field](results/m2-final-scientific-synthesis/figures/m2_welfare_gap_visibility.png)

### 4.6 Citation and abstention

The original M/P-only citation contract remains primary. In the public-harm Structured Evidence / Public-only cell, 0/50 citations met the frozen sufficient-source contract; in Privileged Audit, 2/50 did. A diagnostic that accepts a visible derived finding only when its complete event provenance is visible and supports the independently recomputed fact raised these counts to 50/50 in both cells. This does not replace frozen scoring; it shows the prompt's evidence ontology and citation format were misaligned.

The monitor also correctly handled two negative controls: 222/222 complete-empty message-stream rows were labeled absent, and 177/177 concordance rows with no assessable proposal were appropriately marked not assessable. Correctly finding absence or abstaining is distinct from inferring intent.

### 4.7 M3: message counterfactual results

All 12 assigned groups completed. The two A/B message actions were valid in every group; 13 of 24 actions sent a message and all 13 were delivered. Each delivered message contained a complete literal allocation for the rewarded target under the frozen parser, and the recipient's baseline ballot matched it in all 13 cases. Eight groups supplied at least one eligible delivered proposal and completed the full paired comparison. Five of the eight focal recipients had already produced an own mapping-bearing message matching the incoming proposal.

| Focal arm | Eligible groups | Ballot matches Proposal | Target votes | Ballots changed | Mean fixed-peer regret |
|---|---:|---:|---:|---:|---:|
| Proposal | 8 | 8/8 | 8/8 | 0/8 | 12.00 |
| Neutral | 8 | 5/8 | 5/8 | 3/8 | 9.75 |
| Masked | 8 | 8/8 | 8/8 | 0/8 | 12.00 |
| No delivery | 8 | 5/8 | 5/8 | 3/8 | 9.75 |

Proposal versus Neutral produced three Proposal-only matches, zero Neutral-only matches, and five shared matches. Proposal versus No-delivery had the same paired counts and the same three changed contexts. Proposal versus Masked had eight shared matches and no changes. Only one group changed its fixed-peer allocation under Neutral/No-delivery; in the other two, the other two ballots kept the target selected. In the single outcome-changing group, the family-3 seed-125 settlement moved from the target (regret 18) to that matrix's public optimum (regret 0). These counterfactual settlements are deterministic replays, not additional observed episodes.

The token-matching check found exact full-prompt token equality for Proposal–Neutral and Proposal–Masked in 8/8 groups. No-delivery was shorter by a mean of 45.125 tokens. The identical Neutral and No-delivery changed-ballot pattern leaves attention, turn/context, and semantic message content as competing explanations. Masking task identifiers did not change any observed ballot in this sample. The results therefore do not show a unique semantic proposal effect. They also cannot separate the incoming proposal from independent shared-target behavior: five focal recipients already had matching target information in their own message history.

M3 used 84 logical generations and 84 generation HTTP attempts, plus two authenticated local identity probes (86 HTTP attempts total), with zero retries and zero external or monitor calls. The local tokenizer counted 45,075 input tokens, equal to the response-reported aggregate; 3,346 output tokens were reported. Median generation latency was 0.908 seconds and peak sampled GPU memory was 6,397 MiB. The run manifest still marks live server/tokenizer parity as unverified.

### 4.8 Full research execution: parser failure, monitor coverage, and identifiability

M4 retained all 24 assigned groups. It made 24 local generation attempts (plus two local authenticated identity probes across the preserved pre-generation and final run directories); all 24 generation responses were HTTP 200/`stop`, but all 24 failed strict JSON action parsing. The run recorded zero valid messages, ballots, proposal-eligible groups, or settlements. It consumed 10,764 prompt and 1,098 completion tokens. This is an observed protocol/action-generation failure; it is **not** a zero-effect estimate and supplies no Agent behavior contrast.

The three Monitor phases completed 856/856 assigned requests with zero retries and zero external fallback. Across them, 141 outputs were parseable and 715/856 (83.53%) terminated at `finish_reason=length`, the frozen 128-token limit. The returned identity was stable (`deepseek-flash`, fingerprint `e72d3c7f663d3e1383b00b3884cb4501`). Requests used 667,687 input tokens and 105,163 output tokens. The estimated cost at the frozen official peak rates was USD 0.3265017; the per-schedule conservative reserve totaled USD 1.0224735 under the USD 3 hard ceiling. No response was retried or replaced.

| Frozen population | Requests | Parseable | Invalid at length cap | Input / output tokens | Estimated cost (USD) |
|---|---:|---:|---:|---:|---:|
| Scripted controls | 280 | 16 | 264 | 285,127 / 35,583 | 0.1282377 |
| Incomplete M4 traces | 504 | 123 | 381 | 291,672 / 60,379 | 0.1599564 |
| Matched evidence worlds | 72 | 2 | 70 | 90,888 / 9,201 | 0.0383076 |
| **Total** | **856** | **141** | **715** | **667,687 / 105,163** | **0.3265017** |

Per-method completion varied across populations and is not accuracy. Scripted controls produced parseable outputs for B2 9/80, B3 0/40, B4 4/80, and B5 3/80 scheduled rows. The M4-trace phase produced B2 24/144, B3 19/72, B4 39/144, and B5 41/144. The matched-world phase produced B4 0/36 and B5 2/36; B2 and B3 were not scheduled there. The B4/B5 pair had **zero common assessable completed instances in each phase**, so the predeclared head-to-head fact-accuracy contrast is not estimable. The full denominators and parseable counts are in `results/full-research-execution-20261020/monitor_method_coverage.csv`.

![M4 assigned groups and first-message attempts; no behavioral endpoint was reached](results/full-research-execution-20261020/figures/m4_attempt_disposition.png)

![Parseable completion coverage by method and population; gray cells were not scheduled](results/full-research-execution-20261020/figures/monitor_method_coverage.png)

For a same-cell deterministic reference in the scripted controls, the B1 public-harm rule replay was correct on 7/7 assessable Public-only/Action-only rows, including all five positive references. B0 always-negative was correct on 2/7 and had zero recall on those five positives. This is a narrow scripted check of deterministic source computation, not evidence of model superiority or generalization. In the new scripted Monitor responses, B4 had four assessable exact matches and B5 had two of three; however, these were not the same completed-and-assessable requests, and B4/B5 comparison remains unestimable. B5 provenance gating is an offline transformation of the saved raw response, not another model prediction or an extra API call.

On the same completed B5 rows, provenance gating left the aggregate exact counts unchanged: 2/3 assessable in scripted controls, 33/41 task-appropriate abstentions and zero fact-assessable outputs on incomplete M4 traces, and 2/2 matched positive controls. This describes only the selected parseable rows and provides no evidence of a general gating benefit.

Among the selected parseable scripted positives, B2 recognized 3/3 positive references, B4 4/4 and B5 2/2. These counts are conditional on rare parseable rows; most requests failed at the token cap. No model output was parseable on a row flagged as a frozen hard-negative control (n=0), so the unsupported-sequence rate on hard negatives is not estimable. No unsupported sequence assertion occurred among the parseable outputs, but the empty hard-negative denominator prevents a specificity claim.

The M4-trace phase yielded 123 parseable predictions, mostly abstention-like labels on incomplete evidence (107 `insufficient_evidence`, 11 `not_assessable`, 5 `not_visible`). These cannot be called correct across all rows without task-specific assessability. No positive sequence prediction was emitted in this phase. Because the source episodes contain no accepted Agent action after the failed first message, the monitor task does not test detection of a completed natural proposal/acceptance/action sequence.

In the 12 matched synthetic pairs, the independently compiled Public-only projections and observable references were identical in all 24 method-by-pair comparisons; the Privileged evidence projections differed in all 24. The 24 Public-only reference rows were `not_visible`; the 48 Privileged references comprised 4 `supported`, 32 `not_supported`, 8 `uncertain`, and 4 `insufficient_evidence`. Only two of 72 Monitor requests were parseable: both were B5 Privileged predictions on explicit scripted proposal/acceptance positive-control worlds, and both matched the observable reference with sufficient citations. This small selected subset is not a sensitivity estimate and does not identify latent intent.

![Observable-reference classes by evidence permission in the matched synthetic worlds](results/full-research-execution-20261020/figures/matched_evidence_sufficiency.png)

![Matched-world public indistinguishability and privileged observability controls](results/full-research-execution-20261020/figures/matched_world_identifiability.png)

These results do not show whether a competent monitor could discriminate latent mechanisms from natural traces. They show that the frozen API output cap made most requested predictions unscorable, that completed B4/B5 predictions did not overlap on assessable instances, and that the software-level matched-world construction exposed private observable evidence only under Privileged permission. The table and CSV exports preserve the complete assigned denominators; no failed rows or incomplete M4 groups were removed.

| Component | Observed result | Calls / added computation | Interpretation |
|---|---|---|---|
| Deterministic task computation (B1) | 7/7 assessable scripted `public_harm`, Public-only/Action-only rows correct | No model calls; fixed source replay | Narrow rule reference, not independent model reasoning or generalization |
| Language interpretation (B2–B5 raw) | 141/856 outputs parseable; zero common assessable B4/B5 instances | 856 official API requests across all methods and populations | No fair B4-versus-B5 accuracy comparison is estimable |
| Source validation (B5 provenance gate) | Applied to saved B5 outputs; the two matched-world parseable B5 positive controls remained supported with sufficient citations | Deterministic offline post-processing; zero additional model calls | Two case-level observations, not a broad validation benefit |
| Total remote inference | 856/856 requests; estimated USD 0.3265017, schedule reserve USD 1.0224735, hard cap USD 3 | 667,687 input and 105,163 output tokens | This one frozen run's cost; it does not imply useful prediction coverage |

| Monitor method | Scheduled rows | Parseable | Input tokens | Output tokens | Estimated peak-rate cost (USD) |
|---|---:|---:|---:|---:|---:|
| B2 text-only | 224 | 33 | 128,661 | 27,752 | 0.0719007 |
| B3 action-only | 112 | 19 | 76,560 | 13,721 | 0.0394332 |
| B4 raw fusion | 260 | 43 | 195,315 | 32,048 | 0.0970521 |
| B5 evidence-aware raw | 260 | 46 | 267,151 | 31,642 | 0.1181157 |

B5 used 71,836 more input tokens than B4 over their same 260 scheduled rows and cost USD 0.0210636 more at frozen peak rates; its output was 406 tokens shorter. This compares complete frozen payloads and does not isolate the ledger's causal cost. B5 gating added no API calls or provider tokens; local processing time was not instrumented.

![M3 focal ballot concordance across the four preregistered arms](results/m3-mechanism-audit-final/figures/m3_focal_ballot_match.svg)

## 5. Evidence-aware interpretation

The evidence hierarchy in EVIDENCE_AWARE_AUDITING_FRAMEWORK.md separates assignment (T), actual behavior (B), public consequences, message interpretation, cross-event consistency, permission-specific evidence (E), monitor claims, and latent intent. Each derived label should carry source hashes, event IDs, permission, derivation version, and label provenance.

A convincing mechanism report can say that a message was delivered, contained a literal proposal under a named codebook, and was followed by ballots matching that proposal. It should also state that the agents shared knowledge of the same target before communication. Unless communication content is varied while other context and decision stages remain fixed, the message's causal effect is unknown. The present dataset contains no validated latent-collusion reference labels.

| Case | Directly observed | Supported interpretation | Not established |
|---|---|---|---|
| `m3-3-seed-125` | A complete target proposal was delivered; the recipient's baseline ballot matched. The task-masked proposal preserved that ballot, while Neutral and No-delivery changed it. With the same two peer ballots, only Neutral/No-delivery moved the selected allocation from the target to the public optimum. | A within-context ballot response depended on which prompt variant was supplied; plurality settlement mediated whether it changed the allocation. | The trace does not establish a promise, acceptance, negotiated agreement, intent, or a general semantic proposal effect. Proposal, mask, neutral text and no-delivery still differ in content and context; this is one of eight eligible cases. |

## 6. Discussion and next research step

M3 was the narrow message-content replay proposed in earlier drafts, and its finite-sample results are reported above. It reduced the M1 shared-target/channel confound by varying what the focal recipient received after both message actions were composed, while retaining the recipient's own prior action. The pattern was not a clean monotonic response to message meaning: Masked was identical to Proposal, while Neutral and No-delivery changed the same three ballots. Only one counterfactual settlement changed. This points to the need for a larger, preregistered design with independent model/checkpoint or decoding replicates and a separately varied message-presence control, if such a study is later approved.

The completed M3 authorization is consumed. The present paper requires no further inference to report the approved results. Any new agent or monitor call requires separate approval, fresh preregistration and a new budget. A future study should also freeze a human or rule-based codebook for commitment and acceptance before collection, or retain these as unmeasured variables.

The 2026-10-20 full execution sharpens this conclusion but does not add an M4 behavior estimate: every Agent response failed the frozen parser before any message or vote could be observed. The Monitor run is likewise not a fair model ranking: 715 outputs ended at the token limit, and B4/B5 have no common assessable cases. The limited positive observations are separable: deterministic replay matched its assessable scripted rows, and two Privileged B5 outputs matched two explicitly scripted observable-sequence controls. Neither result supports claims about natural collusion. A revised Agent output contract or monitor reasoning budget would change the protocol and therefore requires a new prospective freeze; it cannot repair these completed outcomes.

## Appendix A. Limitations and Threats to Validity

- One model checkpoint, one deterministic decoding configuration, and a small number of matched groups limit model and scenario generalization.
- Historical F0 and prospective F1–F3 have different provenance and payoff matrices; pooled raw welfare is not meaningful.
- F2/F3 outcomes were exposed during prior development. They cannot support a pristine held-out benchmark claim.
- The DeepSeek alias did not expose a weight hash or exact tokenizer revision. The reported model name and system fingerprint do not prove checkpoint-level replication.
- Four-view differences change multiple inputs at once. Token/cost normalization and content-matched ablations were not frozen as a full factorial design.
- Message proposal and commitment codes are mechanical; no blinded human semantic coding or inter-rater reliability is available.
- M3 conditions its primary estimate on eight eligible delivered proposals from 12 assigned groups; this conditional estimand does not estimate the proposal availability rate in a broad population.
- M3 uses one fixed Qwen3 checkpoint at deterministic decoding. Its eight paired contexts are not independent model replications; no population uncertainty or formal significance claim is made.
- Five of eight M3 focal recipients had already expressed a mapping matching the incoming proposal. The incoming message may therefore be redundant with self-history.
- The masked arm preserves message structure while obscuring task identifiers; its null ballot difference does not establish that proposal semantics never matter.
- No-delivery is shorter by 45.125 full-prompt tokens on average, so Proposal–No-delivery changes more than message semantics.
- Private M3 raw traces are ACL-restricted and Git-ignored. Public commits include sanitized outputs and hashes but not the raw messages and prompts needed to regenerate every row-level result. Full reviewer replay requires controlled access to those local artifacts.
- Aggregate local and response-reported input token totals match, but the run records live server/tokenizer parity as unverified.
- The pre-M3 development reference matches raw source replay: three historical F0 message-bearing episodes (five messages) plus nine prospective F1–F3 episodes (14 messages). They are separate from the 12 new M3 scenario/seed groups and remain development/descriptive cases only.
- No experiment here identifies deceptive intent, a secret agreement, or whether a message caused a ballot.
- In the 2026-10-20 full execution, every one of 24 M4 agent message responses failed the frozen strict parser. No new Agent behavioral contrast, settlement, or welfare result can be estimated from those groups.
- In the three subsequent Monitor phases, 715/856 responses hit the 128-token limit; the returned output coverage is low, and the B4/B5 common assessable denominator is zero. No method superiority claim is supported by this run.
- DeepSeek's provider-default thinking mode remained enabled because the original request payloads were frozen. The run therefore measures this exact alias/default-mode/128-token protocol, not a deterministically decoded model capability or another output budget.
- The matched-world experiment uses explicitly scripted observable-evidence references. It tests permission-dependent identifiability, not natural prevalence or latent collusion detection. Only two model outputs were parseable in that phase.
- All new M4 and Monitor work described in Section 4.8 occurred on 2026-10-20, before the 2026-10-23 sprint start. It is pre-sprint work and must be disclosed as such.

## Appendix B. Dual-Use and Ethical Considerations

This work uses synthetic allocation matrices and a local agent runtime for the behavior corpus. The M2 and 2026-10-20 Monitor runs used the explicitly authorized DeepSeek API only for permission-filtered synthetic task evidence; requests omitted hidden treatment assignments, gold labels, raw unfiltered researcher records, credentials and real-world financial data. M1/M3/M4 agent generations used local Qwen3 inference. Raw privileged messages and raw provider traffic remain local in ACL-restricted, Git-ignored directories and are not reproduced in this paper.

The evidence compiler and auditor could be misused to surveil agent conversations or overstate ambiguous patterns. We therefore report observables separately, retain privacy boundaries, preserve abstention and unknown-intent states, and do not present the framework as an operational accusation system. No real bank system, human participant, or live financial decision was involved in the audited experiments.

## 9. Reproducibility and disclosures

The M2 independent audit, raw response reparse, baselines, paired contrasts, field inventory, token accounting, privacy scan, figures, and hashes are under `docs/results/m2-final-scientific-synthesis/`. M3 tables, results, privacy scan, figure and hashes are under `docs/results/m3-mechanism-audit-final/`. The full-execution summary, per-method denominators, deterministic baselines, figures, independent audit commands, and hashes are under `docs/results/full-research-execution-20261020/`; raw M4 and Monitor evidence remains local and ACL restricted. Reproduction requires the private ignored run roots described in `FULL_RESEARCH_EXECUTION_EVIDENCE.md`:

    python -m pytest -q tests/test_m2_final_scientific_audit.py
    python scripts/audit_m2_final.py --out docs/results/m2-final-scientific-synthesis
    python -m pytest -q tests/test_m3_independent_audit.py
    python -m scripts.audit_m3_mechanism --run runs/m3/mechanism-20261020 --out docs/results/m3-mechanism-reproduction
    python scripts/plot_paper_figures.py

    python scripts/analyze_full_research_execution.py
    python -m pytest -q tests/test_full_research_execution_analysis.py

The M1 summary figure is derived from the complete 75-row audited extension case table and has its own input/output hash manifest under `docs/results/paper-figures/`. The M3 audit and plotting commands make zero model calls. The source behavior audits are documented in `M1_P0_POSTRUN_SCIENTIFIC_AUDIT.md`, `M1_100_SCIENTIFIC_AUDIT.md`, and `M3_SCIENTIFIC_RESULTS.md`. Private run artifacts remain ignored and permission-restricted.

**AI-assistance disclosure draft:** Codex assisted with software implementation, independent deterministic recomputation, diagnostic analysis, figure generation, and manuscript drafting. The authors remain responsible for checking every claim, source, result, and disclosure before submission. DeepSeek Flash was used for the earlier M2 atomic monitor run and the separately authorized 2026-10-20 monitor phases; local Qwen3 generated the M1, M3 and M4 agent actions. The M4 actions in the latest run were malformed and excluded from behavior scoring. No model was called during the associated post-run audit or manuscript update. Revise this statement to match the organizers' final disclosure requirements and exact submission workflow.

## References

- [Apart Research, AI Collusion Research Sprint 2026](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25)
- [Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems](https://arxiv.org/abs/2602.15198)
- [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413)
- [Hidden in Plain Text](https://arxiv.org/abs/2410.03768)
- [Secret Collusion among AI Agents: Multi-Agent Deception via Steganography](https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html)
