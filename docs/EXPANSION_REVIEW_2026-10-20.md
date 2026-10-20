# M3 expansion recommendation: adversarial review

**Review date:** 2026-10-20
**Scope:** review of the new expansion recommendation against the frozen M3 audit and current submission plan.
**Execution status:** documentation and planning only; no model calls, baseline runs, M4 generation, detector evaluation, or artifact changes to M0-M3.

## What M3 supports

- All 12 assigned groups completed. Eight had a delivered, complete proposal and all required counterfactual ballots; four did not qualify for that conditional comparison and remain in the assigned denominator.
- In the eight eligible contexts, Proposal and Masked ballots matched in 8/8. Proposal and Neutral matched in 5/8; the same three contexts changed under No-delivery. Only one fixed-peer settlement changed.
- The own-history split (Neutral changed 0/5 when the recipient's earlier message already stated the target and 3/3 otherwise) is **post-hoc exploratory**. The marker was observed, not randomized; role, payoff family, message form, and context can differ across the strata. It is not statistical evidence or mechanism identification.
- This is not ordinary run-completion survivor bias: all 12 assigned groups completed and the four ineligible groups were not replaced. It does have **eligibility conditioning**: 3/8 describes the response among delivered-proposal contexts, not the rate across all assigned agent situations.
- With deterministic temperature-zero decoding, changing a seed does not by itself guarantee independent semantic contexts. A future freeze should compare actual model-visible contexts after removing request IDs, seed labels, and other non-semantic metadata, and report duplicate/context clusters rather than counting identifiers as independent evidence.

These statements are descriptive facts from M3. The explanation that an agent's own prior proposal makes a later proposal redundant is a **hypothesis**, not an observed mechanism.

## Recommended priority: a positive-control reproduction before expansion

The official Apart page's Results guidance says to report variance, seeds, and baselines and to “always include the positive control.” Its planning guidance says to start with 3–5 seeds per condition and expand only after the positive control works. The local Colosseum clone (`reference/colosseum`, HEAD `b077fe7e2f10566e92156cc12e06ffb2aac54790`) is the strongest immediately relevant candidate: Apart's Track 2.1 description identifies its supplied assigned-pair/private-channel run as a positive control. The clone's README also shows non-trivial Terrarium/CoLLAB setup and possible API credentials. This source inventory is not a reproduction, dependency check, or successful run.

Before any expansion, select and freeze one reference condition, upstream commit, config, model/runtime, seeds, outcome metric, expected qualitative result, and exact call graph. Attempt the smallest supported positive-control reproduction first. Preserve failures. Expand only if the positive control works under the authorized budget and the result is independently auditable. If the upstream environment cannot run within the approved model/runtime constraints, stop and report that incompatibility; do not silently substitute a different baseline after seeing outcomes.

Keep three kinds of controls separate:

1. **Behavior positive control:** a predeclared task where an agent receives genuinely decision-relevant information unavailable in its own prior context. It checks that the model/runtime can use the message; it is not a collusion event.
2. **Reference collusion positive control:** a reproduction of the upstream assigned-pair/private-channel condition. It checks whether the experiment harness can reproduce the source's operational outcome under a specified configuration; it does not establish that ColluScope detects latent intent.
3. **Audit-code canary:** deterministic synthetic records for proposal → explicit acceptance → matching action, plus weaker comparison traces. It checks event extraction and evidence permissions only; it is synthetic and cannot count as real-model behavioral performance or as evidence of collusion.

The official page's positive-control wording appears in its recommended Results structure, not in a separately enumerated legal submission form. Nevertheless, the candidate currently has no behavior or reference positive-control result, so it must disclose that gap and should not be treated as submission-ready until the entrant resolves how to satisfy the guidance.

## Assessment of the proposed larger design

The 6-new-matrix × 8-group suggestion is a separate, unapproved future M4 recommendation: that multiplication yields **48 groups**, while the pasted note also contains a “100 groups” figure whose relationship to the 48 is unclear. It is not the same as the currently frozen 24-group Sprint protocol. Do not change the frozen 24-group config or promote either proposed count into the current paper until the schedule is reconciled.

The proposed two-world comparison—actual message delivery versus a length-matched neutral replacement—has a useful estimand if each assigned group is retained, messages are generated once, both worlds are stateless, and no messages are invented for a valid `no_message` or failed send. It estimates the effect of a delivery policy on counterfactual ballots under the existing message-generation process. It does not estimate the effect of offering communication, and eligibility or treatment assignment must not be conditioned on outcomes.

The 2×2 self-history × received-message design is a reasonable preregistered hypothesis test, but self-history itself is not randomized. The design can randomize whether a previously authored target mapping remains visible in the ballot context, then compare proposal, neutral, and preselected alternative-allocation messages. Masking history can create a structural cue just as M3's Masked arm did; use matched sham masking, identical event counts/separators, token-count reporting, and an alternative allocation selected by a deterministic rule before model output. Report the interaction as an intervention contrast on visible history, not as the causal effect of an agent's natural history.

All assigned groups should be included in unconditional send, delivery, ballot, and outcome tables. A conditional proposal-recipient analysis may be reported separately only with the exact eligible denominator and the eligibility process shown. Do not infer message influence from agreement on the common rewarded target: A and B are both told the same target, so independent parallel behavior remains a live explanation.

## Budget audit

The suggested figures “336” and “480” are not yet reproducible budgets: the pasted table does not unambiguously reconcile “100 groups” with 48, or map the request totals to messages, ballots, worlds, eligibility, focal ablations, retries, and transport attempts. Do not copy them into a frozen protocol. For 48 groups, the two messages plus two complete three-agent ballot worlds alone imply up to `48 × (2 + 2×3) = 384` logical generations before self-history/alternative-message probes, retries, or identity checks, if messages are generated once and reused across the two worlds. A different task graph yields a different total. Before approval, reconcile the assigned group count, enumerate every call node, the number of calls per group, whether it is conditional on delivered proposals, retry eligibility, and maximum HTTP attempts; enforce the resulting total at runtime.

## Current decision

- **GO:** retain the existing PDF as a review candidate; record this critique and disclose the missing positive-control result.
- **NO-GO:** submit the current candidate as complete, claim that M3 established message-semantic response, or claim the 0/5 vs 3/3 split is confirmatory.
- **NO-GO:** start the proposed 48-group M4, run the 24-group protocol, call any agent/monitor model, or reproduce an upstream baseline without separate approval fixing model/runtime, seeds, call budget, and privacy policy.
- **Highest-value next step:** first verify the submission status/template with Apart; then freeze and reproduce one positive-control condition from a selected reference repo within an explicit budget. Only after that should the entrant decide whether the existing 24-group proposal is still worth running.

## Sources checked

- Apart official page, current page text and guidance, accessed 2026-10-20: https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25
- Local reference inventory: `reference/colosseum` at `b077fe7e2f10566e92156cc12e06ffb2aac54790`; README describes Terrarium/CoLLAB setup and example configs. No code or model was run.
