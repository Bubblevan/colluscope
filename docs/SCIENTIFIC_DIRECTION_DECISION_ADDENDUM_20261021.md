# Scientific Direction Decision Addendum — 2026-10-21

**Status:** offline research-direction review complete; no new model calls.  
**Decision:** A is retained as a verified monitor-validity finding but closed to further B5 public-harm inference; B remains the highest-value prospective empirical question; C constrains all claims.  
**This addendum supersedes the proposed 464-request B5 follow-up in `SCIENTIFIC_DIRECTION_REVIEW_REFOCUS_20261021.md` as the current next-action decision.** That proposal and its prior reasoning remain unchanged as history.

## What the evidence says

The concern that the M4 anomaly had not been checked was valid as a criticism of research prioritization, but not as a claim that the data were unavailable. A1 and A2 were rechecked offline from the local source summaries and the 232-request campaign artifacts. The 24 M4 public-harm labels are independently reconstructible from the public matrix, three ballots, chair tie-break, and settled outcome. All 24 references match independent replay and are unchanged between views.

| Finding | Verified result | Boundary |
|---|---:|---|
| Historical M4 B5 Public-only → Privileged | 20/24 predictions changed; 0/24 references changed; exactness 4/24 → 17/24 | Fifteen transitions were `insufficient_evidence → absent`, four `present → absent`, and one `insufficient_evidence → present`; not 20 binary flips and not a message-semantic effect. |
| M4 input change | +362.625 mean B5 prompt tokens; 48 private-message events plus event IDs/order/sender/recipient/sent/delivered/visibility, a completeness flag, serialization, and longer context | The treatment is bundled. |
| Exact-request historical/current comparison | 19/48 labels disagreed; Public-only 17/24 and Privileged-original 2/24 disagreed | Same bytes and reported fingerprint do not reveal why outputs varied. |
| Earlier balanced synthetic B5 public controls | 40/40 canonical predictions `present`; references 20/20 balanced; 20/40 exact; deterministic rule 40/40 exact | This is a clear discrimination failure for this structured label. |
| Later production-form A2 B5 | 35 `present`, 5 `insufficient_evidence`; 20/40 exact. Six-welfare-total arm 39/40 exact. Prompt+enum reversal changed 36/40 and was 10/40 exact. | The arithmetic arm changed length/content; reversal changed two factors together. Neither identifies its mechanism. |
| Matrix-scale comparison | Synthetic `present` mean regret 115.9 and mean cell range 79.95; M4 `present` mean regret 4.7 and mean cell range 16.1 | Different fixed corpora; scale may matter but was not isolated. |

Reproduction outputs are in `docs/results/research-sprint-20261021/b5-direction-review/` and `direction-review-refocus-20261021/b5-task-difficulty.json`. The task-difficulty audit made zero model calls and exported no private-message text.

## Why the next experiment should not be more B5 public-harm calls

The all-`present` result has several live explanations: answer-option/prompt-order bias; tool-enum order; a welfare-to-label mapping burden; input-compiler differences; a shift in matrix scale and regret; and within-service response variation. The existing evidence supports each as a possibility, not a root-cause finding.

The one result we can act on without another call is decisive for task choice: the deterministic program recovers the public-welfare label exactly from the public record, while B5 misses half the balanced fixture and has no demonstrated advantage. An LLM has no nontrivial role in calculating that label. The response instability is still worth reporting as a limitation on single-call monitoring, but another campaign to explain a label that should be computed by code would have low paper value. The latest independent critic also rejected the proposed 256-call A2 diagnostic in its current form because it did not include a compiler contrast, lacked a pinned provider-token matching rule, and still tested a rule-solvable target.

The previous synthetic proposal to classify proposal–acceptance–action sequences is **not** the next primary experiment. Its labels are mostly deterministic on a small scripted fixture, and it does not answer the B5 failure. Keep those 12 matched pairs as a supporting evidence-construction audit, not a reason to spend another model-call batch.

## Direction comparison

| Direction | New knowledge worth seeking | Strong falsifier | Research value and decision |
|---|---|---|---|
| **A — B5 view/presentation response** | Whether view changes exceed repeat variation, and which isolated interface factor changes predictions | Interleaved same-input disagreement equals or exceeds view differences; isolated factors do not shift behavior; a deterministic rule remains exact | Strong finite audit finding, but low standalone value. Broad information-access work overlaps Arike et al.; public welfare is rule-computable. Stop B5 inference for this label. |
| **B — private reward × chat-stage Agent choice** | Whether the post-hoc target-execution interaction recurs on 24 new distinct payoff matrices | Non-positive finite mean, incomplete primary groups, or positive mean confined to fewer than two predeclared regret strata | Highest prospective empirical value because the object is actual model behavior. The claim remains the assigned package, not message semantics, coordination, collusion, or intent. Keep as Tier 1 candidate. |
| **C — evidence sufficiency/identifiability** | Which source records support each observable welfare, proposal, acceptance, action, and sequence claim | A complete public record whose rule-replayed label cannot be derived from the specified fields, or a matched fixture whose authorized projections are not identical | Keep as Track 2.3 claim framework. Existing finite scripted evidence is supporting material, not a general impossibility result. No new model calls needed. |

The current M1 v3 protocol resolves the scenario-count ambiguity: it uses **24 distinct matrices** (eight each at target regrets 6/12/18), not the superseded three-matrix draft. The v3 schedule has 24 groups, five conditions per group, 120 assigned episodes, 456 local Qwen generations, and up to 24 local identity HTTP requests. It is an output-independent finite benchmark, not a population sample.

## Independent Scientific Critic

The fresh separate-context critic agrees that the M4 20/24 result should be prominent, but ranks B above A for the next experiment. It regards A as a narrow negative/reliability result, not a distinctive LLM method contribution. It identified five competitors for the all-present pattern and warned that the earlier 256-call diagnostic lacked an explicit compiler comparison. The critic verified counts only from sanitized summaries; it did not replay raw T/B, inspect private messages, call a model, or run tests.

This converges with earlier independent desk reviews: one ranked C highest for immediate identifiability and low cost but warned that C is not a standalone paper; the post-campaign critic ranked B highest for prospective action evidence while rejecting causal or population claims. These are separate-context critiques, not blind raw-data reviews. The fresh review is preserved at `docs/results/research-sprint-20261021/direction-review-final/fresh-independent-critic-review.md`.

## Paper contribution and prior-work boundary

The strongest existing sentence is descriptive: **in 24 fixed M4 contexts, B5’s public-to-privileged predictions changed in 20 cases while independently reconstructed public-welfare references changed in none; exactness rose from 4/24 to 17/24, but same-request history shows substantial response disagreement and the view treatment is bundled.** This is not a causal context effect or a collusion result.

The next prospective sentence, if the M1 v3 result meets its preregistered finite-set gate, can only describe a private-reward × chat-stage **package** interaction for the tested checkpoint, schedule, and payoff matrices. The shared target and extra chat-stage prompt remain part of the treatment. A non-positive or family-specific result is a substantive falsification, not a reason to retune.

Arike et al. already study monitor information access and Extract-and-Evaluate, limiting novelty for broad “more context helps/hurts” claims. Colosseum already separates communication text from regret/action outcomes; auction and long-horizon studies also test communication, incentives, and history. ColluScope’s plausible increment is a narrowly preregistered allocation-package contrast plus auditable evidence permissions and disciplined observable-claim boundaries—not a new general theory of collusion. The current M1 proposal is not yet enough for a paper by itself; results and a final literature comparison are still required.

Relevant primary references: [Arike et al. (ICML 2026)](https://proceedings.mlr.press/v306/arike26a.html), [Colosseum](https://arxiv.org/abs/2602.15198), [Agrawal et al.](https://arxiv.org/abs/2507.01413), [Shi et al.](https://arxiv.org/abs/2609.24967), and [Jones et al.](https://arxiv.org/abs/2610.20200).

## Execution decision and one approval scope

**GO for offline review:** M1 v3 Agent package replication candidate.  
**NO-GO now:** any new B5 inference, the previous 108-call synthetic-sequence plan, M1 live inference, or DeepSeek Monitor inference. There are no open experiments and neither past DeepSeek approval is reusable.

The most compact useful prospective package is already drafted in `research/drafts/m1-package-monitor-campaign-v2.md`:

| Cycle | Maximum generations | Physical attempts | Cost | Prerequisites |
|---|---:|---:|---:|---|
| `m1-reward-chat-24group-replication-v1` | 456 local Qwen | 480 local HTTP | $0 | New explicit local-run approval; exact v3 model/runtime/listener/template preflight. |
| `m1-natural-message-action-audit-v1` | 216 DeepSeek Flash | 216 external HTTP | $0.45 hard cap | Two independent blinded human coders and adjudication first; a live runner is not yet implemented; explicit approval to transmit eligible private message text and recipient ballots to DeepSeek. |
| **Combined ceiling** | **672** | **696** | **$0.45** | Register and close sequentially; Cycle 2 remains NO-GO until its gates pass. |

The two cycles share a single campaign approval ceiling so the user need not approve each small batch. Cycle 1 is the Tier 1 behavior test; Cycle 2 is a conditional Tier 2 natural-language audit, not a collusion detector. DeepSeek uses only the official `deepseek-flash` alias, off-peak, at no more than 10,000 input and 512 output tokens per request; price and model identity must be rechecked immediately before dispatch. The official pricing page currently lists off-peak cache-miss input at $0.15/M and output at $0.60/M. The `$0.45` cap is above the $0.3903552 worst-case envelope for 216 calls, but is a hard stop, not a target.

The proposed 672 generations fit the current ledger’s 848 remaining generation slots. They would raise usage from 352/1,200 to 1,024/1,200 and reserve no more than $0.45, raising recorded-plus-reserved project cost from $0.039167058 to $0.489167058/$2.50. The 24 identity checks are included in the separate 696 physical-attempt ceiling. Both prior DeepSeek approvals are experiment-specific and consumed; fresh approval is still required.

**What remains before any call:** Cycle 1 is not registered or authorized. Cycle 2 also lacks a live runtime, two completed human annotations, and explicit approval for external private-text transfer. If these conditions cannot be met, run Cycle 1 only under its own exact approved scope; do not silently substitute a B5 or synthetic run.

## Reproduction commands

```powershell
python scripts/audit_public_harm_invariance.py --monitor-run runs/deepseek-first-m4/monitor --output docs/results/research-sprint-20261021/b5-direction-review/branch-a-independent-recheck-final.json
python scripts/score_b5_invariance_run.py --run runs/sprint-monitor/b5-evidence-view-stability-v1 --out docs/results/research-sprint-20261021/b5-direction-review/b5-120-score-independent-recheck-final.json
python scripts/audit_b5_deterministic_rule_baseline.py --out docs/results/research-sprint-20261021/b5-direction-review/b5-rule-baseline-independent-recheck-final.json
python scripts/analyze_b5_task_difficulty.py --out docs/results/research-sprint-20261021/direction-review-refocus-20261021/b5-task-difficulty.json
python scripts/researchctl.py audit
```

These commands make no inference requests. They require the local ignored source runs for the raw replays.
