# What Agent Traces Can Establish About LLM Collusion

## Evidence Boundaries in Multi-Agent Allocation Audits

**Authors:** [AUTHOR NAMES TO BE COMPLETED]
**Affiliations:** [AFFILIATIONS TO BE COMPLETED]
**Team:** [TEAM NAME TO BE COMPLETED]
**Submission track:** Apart AI Collusion Sprint Track 2.3 — Detection and Audit of Collusion
**Evidence cutoff:** 2026-10-21. The experiments reported here were completed before the Oct 23-25 sprint.

## Abstract

Multi-agent traces combine shared incentives, communication, actions, and monitoring, but these observables do not by themselves identify a collusion mechanism. Across scripted identifiability cases and finite LLM studies, M1 showed joint rewarded-target selection in 9/15 groups under a bundled private-reward-plus-chat condition and 0/15 in each other condition; M3 found proposal and masked-message ballots matched in 8/8 eligible groups, while neutral and no-delivery variants changed 3/8 ballots each. A preregistered 24-request message-content intervention found that recipients followed the mapping in a scripted message in all three fixed contexts: 6/6 true-target and 6/6 counterfactual-decoy ballots, versus 0/6 target or decoy ballots without a message when the target was hidden. In a separate 576-request source-framing study, adherence was similar for peer and task-aide recommendations (161/192 and 168/192), with no preregistered peer advantage. Monitor judgments were sensitive to evidence presentation, and matched-world construction yielded identical public projections despite different privileged sequences. A later delivery pilot was blocked before a provider response. The evidence supports a finite response to supplied message content in these prompts; it does not establish spontaneous coordination, peer-specific influence, collusion, intent, or detector accuracy.

## 1. Introduction

AI-agent collusion research asks both whether agents coordinate on harmful objectives and what an auditor can infer from an interaction trace. Those questions are related but distinct. A shared target can be selected independently under common incentives. A message can contain a proposal without the recipient accepting it. A later matching ballot can follow a proposal without having been caused by it. A monitor can cite an allowed event while still misclassifying the event or changing its answer when evidence is re-presented.

This paper reports ColluScope's audited evidence across allocation behavior, counterfactual message prompts, evidence projections, and language-model monitors. Its main claim is deliberately limited: **target agreement and proposal-action concordance alone do not identify communication-mediated collusion; a controlled message-content intervention shows that a recipient followed both the hidden rewarded mapping and a counterfactual decoy mapping when each was supplied in a scripted message, while a separate source-framing study found no peer advantage over matched task-aide advice.** This finite reversal is inconsistent with shared-incentive-only choice as a complete explanation of those prompt outputs. It remains compatible with generic instruction following and does not show that an autonomous sender would produce the message, that agents formed an agreement, or that they had collusive intent. We make no claim that LLM agents never collude.

The audit separates assigned mechanisms, observed messages and actions, deterministic outcomes, message interpretation, permission-filtered evidence, monitor predictions, and latent intent. The last remains unknown. This reporting ladder is motivated by a concrete problem in our data: behavior and monitoring results can each look decisive when their denominators, counterfactuals, or evidence permissions are omitted.

## 2. Related work

Recent work has introduced direct LLM collusion benchmarks and causal communication interventions. **Colosseum** measures action-based collusive behavior using regret relative to a cooperative optimum alongside communication-based behavior, and reports that textual plans can diverge from actions [1]. A 2026 cheap-talk study tests message interventions and matched history-by-message counterfactuals across repeated games, finding model- and context-dependent effects on policy persistence [2]. A long-horizon study examines protocol violations under repeated peer interaction, rewards, verification, and history ablations [3]. These works mean ColluScope should not claim to introduce either an LLM collusion benchmark or causal message intervention.

The independent-convergence alternative is also empirically live. A network-consensus study reports that one tested model reached consensus even without communication, while outcomes varied across model and network conditions [4]. For monitors, evidence access is itself an intervention: recent sabotage-monitor work reports a less-is-more effect and evaluates extract-and-evaluate architectures [5]. ColluScope complements this line with allocation-specific audits of evidence presentation and same-request repeatability. Our results do not compare monitor architectures or estimate sabotage-detection accuracy.

## 3. Evidence and methods

### 3.1 Evidence levels and analysis boundaries

We distinguish four levels: (1) scripted or constructed cases used to test identifiability and scoring; (2) real model-generated agent behavior; (3) monitor predictions against references for observable facts; and (4) deterministic offline replay of saved assignments, ballots, settlements, and request records. A successful parser, a completed HTTP response, or a reproducible hash is an operational or provenance fact, not a scientific behavior result.

Outcome reconstruction applies the frozen allocation rule to raw ballots and recomputes public welfare and matrix-specific regret. Target execution, public harm, sender messages, message delivery, recipient ballots, and fixed-peer settlements are reported separately. Literal proposal detection is a codebook operation, not a claim about commitment or intent. A monitor response is a prediction about a specified observable reference, not an independent witness to the event.

### 3.2 M0: matched-world identifiability construction

M0 contains 12 paired synthetic worlds. Within each pair, the public-only projection and observable reference are held equal, while privileged evidence can contain different proposal, acceptance, and action sequence information. Independent replay found identical public projections in all 12 pairs. A determinate privileged sequence element differed in 8/12 pairs; two pairs differed on a complete proposal-acceptance-both-actions sequence. This demonstrates a finite construction-level boundary: an observer cannot identify a hidden difference from an identical permitted input. It is not a general impossibility theorem, real-agent behavior, or a test of monitor accuracy.

### 3.3 M1: shared reward and communication conditions

M1's prospective extension assigned 75 groups across five conditions and three payoff-matrix families. The central descriptive pattern was 9/15 joint target selections in the private-target-reward-plus-chat condition and 0/15 in each of the four other conditions. Both agents had access to the same rewarded target before the chat decision stage. The chat condition also adds a decision stage and context. Thus the comparison bundles target knowledge, incentive, and communication opportunity; it is not a causal estimate of communication.

### 3.4 M3: within-context message counterfactuals

M3 assigned 12 groups, of which eight had a delivered, complete proposal eligible for the preregistered focal comparison. Proposal and Masked ballots both matched the proposal in 8/8 contexts. Token-matched Neutral and same-stage No-delivery ballots each changed in 3/8 contexts, and the changed contexts were the same. Five of eight recipient histories already contained target information. With the other two baseline ballots held fixed, only one context changed the selected allocation under the counterfactual settlement. The comparisons are finite prompt interventions on one checkpoint, not natural interaction repeats. Proposal, Neutral, Masked, and No-delivery do not isolate every semantic and context feature.

### 3.5 M4: monitor presentation sensitivity and repeatability

In the B5 evidence-view campaign, 12/24 labels changed from Public-only to Privileged-neutral, 20/24 from Privileged-neutral to Privileged-original, and 19/24 from Public-only to Privileged-original. The views differ in information and serialization; these are fixed-corpus response changes, not estimates of a general information-access effect. In a separate historical/current comparison, the request bodies were byte-identical and the returned fingerprint matched, yet labels agreed in only 7/24 Public-only pairs and 22/24 Privileged-original pairs. The fingerprint does not prove immutable provider weights or state. The repeat comparison establishes finite non-repeatability for those observations, not its cause.

### 3.6 DeepSeek agent and monitor extension

A separately frozen DeepSeek Flash extension completed 24 agent groups and 376 monitor requests. The rewarded target was executed in 2/24 groups. Across 400 individual observable-reference labels, 145 were exact; the common assessable B4/B5 paired set did not establish superiority. The model alias and fingerprint are provider-reported identifiers rather than immutable weight hashes. Synthetic monitor controls encode observable references, not latent collusion. All runs described in this paper occurred before the sprint dates.

### 3.7 New message-visibility attempt

On 2026-10-21, we separately preregistered a 36-request factorial design crossing target visibility with actual sender text versus neutral text and two exact recipient-prompt repeats. Shared target bonus and payoff contexts were frozen before dispatch. The run stopped under its schema hard-stop rule after 13 physical attempts: 12 valid completed outputs (two senders and ten recipient ballots), one HTTP 200 response rejected for an additional top-level field, and 23 assigned requests unattempted. No retry, replacement, or resumption occurred.

In the only complete context, all four recipient arms chose the target 2/2. The actual-minus-neutral contrast was zero both with target visibility (2 versus 2) and hidden (2 versus 2). In the second context, one visible-actual and one visible-neutral ballot both chose the target; hidden arms were incomplete. Both observed senders disclosed the full target mapping, below the preregistered three-disclosure eligibility threshold. Three of four designated visible-target/neutral positive-control ballots were observed, all choosing the target; the fourth was unattempted. The positive-control gate is therefore not assessable for the incomplete study.

The neutral text and full recipient prompt in the first context were 43 tokens shorter than the actual sender message and prompt under the pinned tokenizer; the corresponding residual in context two was 14 tokens. The preregistered protocol had not set a residual tolerance, so we report this as a material design limitation rather than imposing a post-hoc exclusion. The offline smoke test used a short fake sender message and did not detect the residual. The study is inconclusive and adds no positive or null causal result. Full denominators and the sanitized request ledger accompany the analysis.

### 3.8 Shared-target message-source study

The preregistered source-framing study assigned six stateless arms in each of 24 frozen payoff contexts, with four exact-prompt repeats per arm (576 physical requests). Under hidden-target prompts, mapping adherence was 161/192 for peer-attributed recommendations (83.85%) and 168/192 for task-aide-attributed recommendations (87.50%). The target recommendation was followed in 82/96 peer and 88/96 aide requests; the counterfactual decoy mapping was followed in 79/96 peer and 80/96 aide requests. The hidden/no-message analyst-only shadow mapping matched 14/96 ballots, while the target-visible/no-message control selected the target in 96/96.

The equal-context mean peer-minus-aide difference was -3.65 percentage points; peer adherence was higher in 0/24 contexts and aide adherence higher in 2/24, with 22 ties. All 576 rows were completed and assessable. Eight of 144 context-by-arm cells had disagreement among their four repeats. The preregistered peer-advantage gate (at least +15 points and peer-favoring in 18/24 contexts) was not met. The preregistered source-insensitive descriptive gate passed, including at least 70% adherence under both labels, at least 65% in every target/decoy source cell, and a context-mean difference within ±10 points. This is not a statistical equivalence test.

This controlled finite pattern supports response to a supplied recommendation mapping under a hidden shared-reward target, including a decoy mapping. It does not isolate peer-specific influence: the aide is only a prompt source label. One provider alias, one fingerprint, and 24 fixed contexts bound the result to this setting. Only 6/24 decoys are within one welfare point, and 8/144 context-arm cells show repeat disagreement. The companion materials include the interpretation, adversarial review, sanitized ledger, and independent raw replay.

### 3.9 Shared-target message-content intervention

A separately preregistered 24-request study tested whether recipient ballots followed the allocation mapping in a controlled peer message when the rewarded target was hidden. Three output-independent payoff contexts each received two exact-prompt repeats in four arms: visible-target/no-message, hidden-target/no-message, hidden-target/true-target message, and hidden-target/counterfactual-decoy message. The common target reward, payoff matrix, role, decision stage, and recipient history were fixed within context. True and decoy prompts had equal pinned-token counts and differed only in the mapping stated by the scripted message.

All 24 assigned requests were attempted once, completed, and assessable; there were no invalid or unattempted rows, repeat disagreements, or frozen-replay integrity errors. The visible-target/no-message control selected the target in 6/6 ballots. With the target hidden, no-message ballots selected neither target nor decoy (0/6 each); true-message ballots selected the target in 6/6, and counterfactual-message ballots selected the decoy in 6/6. The preregistered finite response criterion passed in all three contexts.

This within-prompt mapping reversal shows that the shared incentive alone does not account for the observed message-arm choices in these fixed prompts. Because the messages were scripted by researchers, the result does not distinguish peer-specific social influence from generic advice or instruction following. It does not test a live sender, spontaneous communication, agreement, harm, intent, or population behavior. The closure is an adversarial self-review, not an independent second-party raw-response audit; the provider alias and reported fingerprint do not identify immutable model weights.

### 3.10 Track 2.3 delivery pilot execution boundary

A later registered Track 2.3 pilot assigned 56 requests. One physical attempt began and failed in Python name resolution before an HTTP response; 55 assigned requests remained unstarted. There were zero model responses, valid actions, or assessable contexts. The cycle was closed as `EXECUTION_BLOCKED` under its no-retry rule. This is an operational failure, not a behavioral null, and contributes no evidence for or against a message-delivery effect.

## 4. Results in one view

| Evidence | Observed result | Supported interpretation | Not established |
|---|---|---|---|
| M0 construction | Public projection equal in 12/12 paired worlds; privileged sequence differs in 8/12 | A finite permission-specific identifiability boundary | General impossibility, natural behavior, monitor accuracy |
| M1 behavior | Joint target choice 9/15 with private target reward plus chat; 0/15 in each other condition | A finite condition association | Communication caused target selection |
| M3 counterfactual | Proposal/Masked match 8/8; Neutral/No-delivery change 3/8 each; one settlement changes | Ballot response depends on prompt variant in some saved contexts | A general semantic message effect, agreement, intent |
| M4 monitor | Labels change across views; exact-body historical/current labels agree 7/24 Public and 22/24 Privileged-original | Presentation sensitivity and finite request non-repeatability | Latent-collusion detection accuracy or provider-variability cause |
| DeepSeek extension | Target executed 2/24; exact observable labels 145/400 | Finite observable outcomes under one alias | B4/B5 superiority or generalization |
| Visibility V1 | Stopped at 13/36; only one complete context, with equal 2/2 arms | Inconclusive attempted contrast; material token mismatch | Positive effect, null effect, or equivalence |
| Source V1 | 161/192 peer and 168/192 aide mappings followed; peer-minus-aide equal-context difference -3.65 points | Finite recommendation-mapping response under both source labels; preregistered peer advantage not supported | Statistical equivalence, peer social influence, collusion, intent, population generalization |
| Content V1 | True-target message followed 6/6; counterfactual-decoy message followed 6/6; hidden/no-message chose neither 0/6; 24/24 assessable | Finite content-sensitive ballot response in all three fixed contexts; shared reward alone does not explain the mapping reversal | Autonomous sender behavior, peer-specific influence, agreement, collusion, intent, population effect |
| Track 2.3 delivery pilot | 1/56 attempt started; 0 provider responses; 55 unstarted | Execution boundary only | Any behavioral conclusion about message delivery |

## 5. Competing explanations and the missing evidence

For the historical co-selection and proposal-action observations, two explanations remain compatible:

1. **Independent convergence:** shared incentives, target knowledge, payoff salience, or prior context are enough to produce matching choices; messages may be redundant.

2. **Communication-mediated action change:** message content changes recipient behavior beyond the same incentives, target information, decision stage, and message presence.

M1 cannot separate these because its chat and shared-target-reward conditions move together. M3 does not resolve the issue because target information was already in five eligible histories, the masked and proposal arms matched, and Neutral and No-delivery changed the same ballots. Recipient's 804-request scripted-cue study is not a substitute: its delivered-fact positive control was 0/20, and some invalid stage outputs propagated to dependent ballots. The new source-framing study adds a different result: ballots tracked mappings under both source labels, weakening pure common-incentive-only convergence as an explanation of those mapped choices. It does not show that a peer source matters more than generic advice; the finite source difference favored aide by 3.65 points on average and the preregistered source-insensitive gate passed. Natural peer communication remains unresolved. The message-visibility V1 attempt stopped before enough complete contexts and exposed a ceiling pattern and neutral-message length residual.

The content intervention now shows a finite effect of the supplied mapping on recipient ballots in three fixed contexts. The remaining behavioral uncertainty is whether a genuine peer-originated recommendation affects action differently from content-matched non-social advice when the recipient has an interaction history. The source-framing study found no peer advantage in stateless prompts, but its source manipulation was a label and does not establish that peer identity is causally irrelevant in natural interaction. Any follow-up should use an independently sampled context set, retain the target/decoy mapping control, and predefine a meaningful source-effect margin and repeatability rule. It would still not establish collusion, agreement, intent, or welfare harm.

## 6. Next research step

An independent critic reviewed the content V1 protocol, sanitized results, and manuscript claim and supported only the narrow finite message-mapping response. The review could not inspect raw prompt/response bytes, so final claim-to-artifact checks and any privacy-approved raw-response audit remain the next paper tasks. No further model calls are proposed under the closed authorizations. The synthesis preserves the distinction between bundled-condition association (M1), finite message-prompt responses (M3 and content V1), source-insensitive recommendation mapping (source V1), and the execution-blocked delivery pilot.

If the synthesis leaves peer-specific causal influence as a paper-critical uncertainty, a later experiment should instantiate a genuine sender-recipient interaction and compare a peer-originated message with content-matched non-social advice and a no-message baseline. It should use independently selected contexts, prevent ceiling choices, preserve target/decoy mapping controls, and preregister the source-effect margin, repeatability rule, and failure interpretation before a separate authorization. Even a positive effect would not establish collusion, agreement, intent, or welfare harm.

## 7. Limitations and ethical scope

The experiments use a small collection of synthetic allocation tasks and a small number of model aliases/checkpoints. Repeated provider requests do not sample independent model populations. Provider fingerprints are not immutable model hashes. The positive content V1 result covers three fixed contexts and researcher-scripted messages. An independent critic reviewed the sanitized protocol/results and supported only the narrow mapping-response claim, but could not inspect raw prompt/response bytes; there has been no independent second-party raw-response audit. The study also lacks validated human-coded agreement or commitment labels. Monitor references are observable-task labels, not latent-intent ground truth. Raw prompts and responses for several paid runs are stored in ACL-restricted, Git-ignored directories, so the repository's sanitized artifacts support audit and deterministic reanalysis but do not alone permit an external byte-for-byte replay of every provider response. These limits are substantive and should accompany any replication claim.

All tasks used synthetic payoff matrices and allocation decisions. No human participants, real-world financial data, or deployed systems were involved. The analysis keeps private evidence permissioned, does not expose raw private messages in the public report, and does not label agents as collusive. A monitor or evidence compiler built from this work could be misused to make accusations from ambiguous traces; outputs must therefore preserve unknown and not-assessable states.

## 8. Reproducibility and materials

The project repository is [Bubblevan/colluscope](https://github.com/Bubblevan/colluscope). Sanitized artifacts and no-model-call analysis paths include:

- M1: `docs/M1_100_SCIENTIFIC_AUDIT.md`.
- M3: `docs/M3_SCIENTIFIC_RESULTS.md` and `docs/results/m3-mechanism-audit-final/`.
- M4 evidence-view campaign: `docs/M4_B5_CONTEXT_SENSITIVITY_EVIDENCE.md` and `docs/results/research-sprint-20261021/`.
- DeepSeek-first extension: `docs/M4_DEEPSEEK_FIRST_RESEARCH_RESULTS.md` and `docs/results/deepseek-first-m4/audit/`.
- New stopped message-visibility attempt: `docs/SHARED_TARGET_MESSAGE_VISIBILITY_V1_PROTOCOL.md`, `docs/results/shared-target-message-visibility-v1/`, and `research/experiments/shared-target-message-visibility-v1/`.
- Positive controlled message-content intervention: `docs/SHARED_TARGET_MESSAGE_CONTENT_V1_PROTOCOL.md`, `docs/results/shared-target-message-content-v1/`, and `research/experiments/shared-target-message-content-v1/`.
- Independent critic review of the content V1 claim: `docs/results/shared-target-message-content-v1/critical-review-v1.md`.
- Shared-target source-framing study: `docs/SHARED_TARGET_MESSAGE_SOURCE_V1_PROTOCOL.md`, `docs/results/shared-target-message-source-v1/`, and `research/experiments/shared-target-message-source-v1/`.
- Track 2.3 delivery pilot execution failure: `docs/TRACK_2_3_COUNTERFACTUAL_DELIVERY_V1_PROTOCOL.md`, `docs/results/track23-counterfactual-delivery-v1/`, and `research/experiments/track23-counterfactual-delivery-v1/`.
- Research claim synthesis and design boundary: `docs/SCIENCE_DIRECTION_HANDOFF_20261021_STMI.md`.

The content V1 frozen reanalysis is `python scripts/run_shared_target_message_content_v1.py --analyze`; it makes no model call and requires the protected local run directory. No reproduction command in this report dispatches a model. Raw response replay requires the protected local run roots identified in the corresponding evidence files. The public or reviewer-facing package should provide access to those artifacts only through an approved privacy and data-sharing procedure.

**AI assistance:** Codex assisted with analysis, independent deterministic recomputation, literature review, software, and manuscript drafting. The authors are responsible for verifying all source citations, results, disclosures, and final claims. DeepSeek Flash and local Qwen3 were used in the dated experiments identified above; no results from these pre-sprint experiments are represented as sprint-period work.

## References

1. Mason Nakamura et al. "Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems." arXiv:2602.15198, 2026. https://arxiv.org/abs/2602.15198

2. Nunzio Lorè, Hongan Zhu, and Babak Heydari. "Cheap Talk Stabilizes Strategic Interaction in LLM Agents." arXiv:2609.16270, 2026. https://arxiv.org/abs/2609.16270

3. Xinrui Shi, Yanzhe Zhang, and Diyi Yang. "Emergent Collusion in Long-Horizon LLM Agent Interaction." arXiv:2609.24967, 2026. https://arxiv.org/abs/2609.24967

4. Isabel Jones, Matthew Edwards, and Janina A. Hoffmann. "Drivers of LLM Consensus Formation Under Competing Incentives: A Simulation Study." arXiv:2610.20200, 2026. https://arxiv.org/abs/2610.20200

5. Rauno Arike et al. "How does information access affect LLM monitors' ability to detect sabotage?" Proceedings of the 43rd International Conference on Machine Learning, PMLR 306:3473-3526, 2026. https://proceedings.mlr.press/v306/arike26a.html

6. "Evaluating LLM Agent Collusion in Double Auctions." arXiv:2507.01413, 2025. https://arxiv.org/abs/2507.01413

7. "Hidden in Plain Text." arXiv:2410.03768, 2024. https://arxiv.org/abs/2410.03768

8. "Secret Collusion among AI Agents: Multi-Agent Deception via Steganography." NeurIPS 2024. https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html
