# Blind Scientific Critic Packet v1

**Prepared:** 2026-10-20 UTC  
**Purpose:** independent assessment of three candidate scientific directions and the proposed next monitor campaign.  
**Evidence scope:** retained real-LLM Monitor outputs from one historical DeepSeek Flash alias/fingerprint run, offline recomputation, and a fixed synthetic diagnostic. No new model calls are represented here.

## Candidate directions

Review all three directions without assuming a preferred ranking.

- **Route North — Evidence-view response:** explain why a monitor's public-welfare label changes when it receives a different evidence projection, and test whether a representation change can reduce errors.
- **Route East — Communication and choice:** identify whether message content or shared information changes an agent's subsequent action when incentives and public task structure are controlled.
- **Route South — Evidence boundary:** identify which permitted observations are sufficient to support an observable proposal/acceptance/action sequence, and which latent interpretations remain unidentified.

The review question is which route, if any, could support a paper-level contribution beyond existing work. Consider scientific value, causal identification, rule baselines, sample units, model calls, failure risks, nearest literature, and the result that would falsify each route.

## Hash-pinned observations

### Historical M4 B5 public-harm task

- Scored CSV: `docs/results/deepseek-first-m4/audit/monitor_per_reference_scores.csv`, SHA-256 `ebfc472cb615fc351d35099e2f61469396a3f1d08d82534fe3daf4ebd9cc48a7`.
- Independent replay: `docs/results/evidence-invariance/branch-a-audit-independent-recheck.json`, SHA-256 `348d0bc8d8bb4604c2bcf0a9ebf8b1efd2324659eb9190e152fae46b99b3b8fb`.
- Protocol/compiler boundary: `docs/BRANCH_A_EVIDENCE_INVARIANCE.md`, SHA-256 `56381dee01cacdd49735c878b4c130a9b8c2059a4d4c4fa5b01e0cadf407dd34`.
- There are 24 matched natural-trace contexts. Public references are 14 `absent`, 10 `present`; all 24 have complete public matrix, three ballots, chair rule, settlement/outcome, and a unique public optimum. Public-harm reference labels are mechanically recomputable and do not encode collusion or intent.
- For B5, Public-only versus Privileged Audit predictions differ in 20/24 contexts, references differ in 0/24, and exactness is 4/24 versus 17/24. Transitions: 15 `insufficient_evidence→absent`, 4 `present→absent`, 1 `insufficient_evidence→present`; among changed predictions, 14 improve exactness, 1 worsens, 5 remain wrong. Do not call these 20 binary flips.
- The historical view change bundles actual private-message text, added message rows and provenance fields, `visibility=private`, `delivered_message_window_complete=true`, longer serialization, and additional provider tokens. In B5 the median token delta was +358 (range +291 to +561). Public task and action records and the mechanical ledger were otherwise paired. Historical provider alias has no immutable weight hash.
- The public-harm system task is mechanically solvable from matrix, ballots, chair settlement, and public outcome. No LLM is required to compute this label.

### Prior 120-request synthetic B5 diagnostic

- Frozen report: `docs/results/research-sprint-20261021/B5_EVIDENCE_VIEW_STABILITY_EVIDENCE.md`, SHA-256 `9a281c7052269f961167edbeeeaf871d882dc6898696907a01386a5dc620b507`.
- Independent deterministic replay: `docs/results/research-sprint-20261021/b5-deterministic-rule-baseline.json`, SHA-256 `e2538cfb2b8711de054964151993a6340a40c55804d569d8455c8cdfb7e53ce6`.
- Across 120 successful API responses, labels were 116 `present`, 0 `absent`, and 4 `insufficient_evidence`; parsing/tool calling succeeded. On the 40 balanced public-canonical rows (20 primary + 20 label-flip controls), model outputs were 40/40 `present`, exact on 20/40. Deterministic public-harm replay was 40/40 exact.
- The historical synthetic request projector omitted the production B5 mechanical ledger and differed in task/label/completeness prompt construction and request fields. Synthetic payoff entries ranged 0–100; M4 task entries ranged 1–20. These are plausible distribution/compiler differences, not proven causes.
- One possible model role beyond deterministic scoring is natural-language interpretation of proposals/acceptance or ambiguous event records. The public-harm score task itself does not establish a need for an LLM.

### Existing communication and evidence-boundary observations

- M3: among 8 proposal-eligible contexts, Neutral changed the focal vote in 3/8, Masked 0/8, No-delivery 3/8; settlement changed in 1/8. Five recipients had previously expressed the same target. This is post-hoc small-sample evidence and does not identify communication causality.
- Synthetic matched-world audit: `docs/results/research-sprint-20261021/MATCHED_WORLD_SEQUENCE_VISIBILITY_AUDIT.md`, SHA-256 `f76ec46a585431d9e5d58d5583790587be6ec37242943ef1dc223b31ea87dada` (verify against file; if mismatched, report it). It reports 12 scripted pairs: Public-only request projections identical within 12/12 pairs; at least one determinate privileged sequence-element difference in 8/12; complete proposal–acceptance–both-actions sequence present in only 2/24 worlds. This is a finite synthetic construction; its sequence parser is deterministic.

## Candidate next campaign, not yet registered or run

The proposed `m4-b5-context-sensitivity-campaign-v1` uses at most 232 physical attempts and USD 0.90, official DeepSeek Flash only, off-peak only, one attempt per request, no replacement rows; expiry 2026-10-23 01:00 UTC. User approved this resource envelope. No new request has yet been sent for this campaign.

- **A1, 72 requests:** 24 fixed M4 contexts × (Public-only, Privileged-original, Privileged-neutral). Neutral message text is frozen to `I received your message.` for both messages, with event metadata, completeness, ledger, and public evidence held constant against original privileged view. The neutral is shorter, so text semantics remain confounded with wording, salience, and token length. All 24 contexts stay in the denominator.
- **A2, 160 requests:** 40 synthetic public-canonical rows (20 balanced groups × primary and label-flip trajectory) × four request forms: historical V2-direct projection; production B5 compiler; production B5 plus six-allocation welfare/optimum/actual/regret table without reference label; production B5 with present/absent order reversed in prompt and schema.
- A1 primary comparison is descriptive, fixed-context response sensitivity. A2 is a fixed-fixture diagnostic. Both score only the public welfare label; neither creates a collusion gold label.

## Closest primary literature to assess

Use primary sources and distinguish covered ideas from any remaining contribution.

1. Arike et al., “How does information access affect LLM monitors' ability to detect sabotage?” ICLR 2026 submission / arXiv:2601.21112. Abstract reports information-access studies across three sabotage environments, a “less-is-more” effect, and Extract-and-Evaluate, which extracts relevant trajectory excerpts before a separate monitor judges them. Code: https://github.com/rajamoreno/info-access-mle-sabotage
2. Nakamura et al., “Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems,” arXiv:2602.15198 / NeurIPS 2026 E&D. Abstract describes DCOP-based cooperative tasks, regret-relative-to-optimum, secret communication, and “collusion on paper” where language plans may not affect actions. Code: https://github.com/umass-ai-safety/colosseum
3. “Evaluating LLM Agent Collusion in Double Auctions,” arXiv:2507.01413. Code: https://github.com/andyjliu/llm-agent-collusion
4. Motwani et al., “Secret Collusion among AI Agents: Multi-Agent Deception via Steganography,” NeurIPS 2024: https://proceedings.neurips.cc/paper_files/paper/2024/hash/861f7dad098aec1c3560fb7add468d41-Abstract-Conference.html

## Reviewer deliverable

Return a concise, independent report with:

1. One of `SUPPORTED`, `REFUTED`, `INCONCLUSIVE`, or `NOT_REVIEWABLE` for the strongest candidate scientific claim; cite the exact counterexample and artifact.
2. Rank the three directions on novelty, importance, identifiability, expected information gain per call, baseline adequacy, and feasibility. Explicitly assess whether a paper contribution remains after the rule baseline and Arike's Extract-and-Evaluate work are considered.
3. At least three competing causes of the all-`present` synthetic output, each paired with the smallest falsifiable test and the result that would weaken it.
4. Assess whether A1/A2 as frozen are worth the full 232-call/$0.90 envelope. Propose one more decisive or cheaper alternative if not. Do not recommend a model call merely because a test is easy to pass.
5. State precisely what evidence would be needed for a stronger claim, and one highest-value next action.

Do not treat the rule-generated reference as an LLM prediction, do not assign a latent-collusion label, and do not quote private message contents. This packet is the only author-prepared framing; source artifacts may be consulted only to verify listed observations and hashes. Do not inspect author-authored iteration logs, research memory, hypothesis rankings, or prior direction-review conclusions while producing the review.
