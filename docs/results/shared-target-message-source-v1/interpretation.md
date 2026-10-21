# Shared-target message-source v1: interpretation

**Date:** 2026-10-21  
**Evidence class:** `real_llm_behavior` from controlled, scripted recipient prompts  
**Experiment:** `shared-target-message-source-v1`  
**Scientific outcome:** `REFUTED` for the preregistered peer-source advantage hypothesis  
**Operational disposition:** `PIVOT` to offline manuscript integration; the lifecycle disposition is separate from the scientific result.

## Result

All 576 assigned requests were attempted once and completed with assessable legal allocation ballots. There were no failed, invalid, or unattempted rows, no retries, replacements, or resumptions, and no integrity errors. The visible-target/no-message check selected the target in 96/96 ballots.

Under hidden-target prompts, ballots matched the recommendation mapping in 161/192 peer-attributed requests (83.85%) and 168/192 task-aide-attributed requests (87.50%). For the true-target recommendation, mapping hits were 82/96 for peer and 88/96 for aide. For the counterfactual decoy recommendation, they were 79/96 for peer and 80/96 for aide. The hidden/no-message analyst-only balanced shadow mapping matched 14/96 ballots (14.58%).

The equal-context mean peer-minus-aide mapping-adherence difference was -3.65 percentage points. Peer adherence exceeded aide adherence in 0/24 contexts; aide adherence exceeded peer adherence in 2/24, with 22 ties. Eight of 144 context-by-arm cells contained disagreement among four exact-prompt repeats. All context-arm cells retained four completed ballots.

The preregistered peer-source advantage gate was not met. The preregistered source-insensitive recommendation-pattern gate was met: both source rates were at least 0.70 and more than 0.20 above the shadow match rate; each source's target and decoy cells were at least 0.65; coverage and the visible-target check passed; and the absolute equal-context difference was within 0.10.

## What the evidence supports

For these 24 frozen contexts and this single provider-served model identity, changing the supplied target/decoy recommendation mapping was associated with strong ballot tracking under both source labels, compared with the hidden/no-message shadow mapping. This strengthens the finite controlled-message-response evidence beyond the earlier three-context, single-source result. The task-aide arm is a useful generic-advice framing control: the observed response does not require a peer label in this prompt design.

The result weakens the preregistered claim that peer attribution produces at least a 15-point equal-context advantage with peer-favoring differences in at least 18/24 contexts. It does not establish statistical equivalence. The ±10-point source-insensitive rule is a preregistered descriptive gate over a fixed set, not a population-level equivalence test.

## What remains unresolved

- A task-aide label is a prompt framing manipulation, not a genuine independent advice channel or a socially independent agent.
- The study used stateless recipient requests. There was no endogenous sender, negotiation, repeated interaction, acceptance, agreement, or shared plan.
- The 24 contexts are a fixed synthetic matrix set served by one mutable provider alias and one reported system fingerprint (`e72d3c7f663d3e1383b00b3884cb4501`). They are not a sample of models, deployments, or human-relevant settings.
- Decoys were the nearest-welfare legal non-target allocations, but only 6/24 contexts had a target-decoy welfare gap of at most 1. The decoy result therefore should not be described as uniformly near-equal-welfare choice.
- Eight context-arm cells had at least one disagreement across the four repeats. Repeated requests are within-cell stability observations, not independent model instances.
- The no-message shadow rate is a finite descriptive comparison. It is not a significance test or a calibrated estimate of an underlying choice probability.
- Neither the source contrast nor target/decoy choice establishes collusion, intent, agreement, harmfulness, or welfare impact.

## Audit and resources

The separate audit script reparsed the protected raw responses, reconstructed assigned counts and ballot hits, verified schedule/request/response hashes and the provider fingerprint, and reproduced the runner's aggregate rates and costs without a network call. It also independently matched all 576 sanitized ledger timestamps to raw attempt-start events using the hashed attempt ID. The ledger timestamp reconciliation receipt and audit result are in `ledger-timestamp-reconciliation.json` and `independent-audit.json`. The sanitized per-request ledger and context table are committed. Protected raw prompts and responses remain in the Git-ignored local run directory; the sanitized package is not a byte-for-byte public copy of those raw responses.

Peak-rate usage-derived cost was $0.1467360; the full scheduled peak-rate reserve was $0.6730992. These are usage-derived estimates, not a provider invoice. The run took about 9.54 minutes.

## Next action

Integrate this bounded source-framing result and its limitations into the sprint submission and reproducibility package. No additional model calls are proposed by this closure.
