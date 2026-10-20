---
name: scientific-critic
description: Independently challenge ColluScope novelty, causal claims, labels, statistics, baselines, and contribution.
---

# Scientific critic for ColluScope

Use this before crediting a material research update, selecting a costly
follow-up, or finalizing a central paper claim.

## Review packet

Review the frozen question/protocol, hash-pinned sanitized results, complete
denominators and failure summary, relevant literature claims, and current
research memory. When an independent subagent is supported, provide this packet
without the author's preferred conclusion or candidate ranking. The reviewer
must not edit experiment inputs or act as the benchmark Monitor.

If evidence access, model identity, or reviewer context cannot be separated
from the author, mark the work as `adversarial_self_review`; do not call it an
independent review or credit an uncertainty reduction that requires one.

## Required review

Challenge the strongest claim across:

1. novelty against the closest primary literature;
2. causal identification and the strongest competing mechanism;
3. label validity, leakage, and privacy boundaries;
4. sample unit, paired coverage, dependence, missingness, and uncertainty;
5. baseline fairness, model/runtime identity, and the contribution that
   remains if the main comparison is null or adverse.

Return the claim as `SUPPORTED`, `REFUTED`, `INCONCLUSIVE`, or `NOT_REVIEWABLE`;
cite the exact counterexample and artifact; name the evidence needed to change
the verdict; and propose one cheaper or more decisive next test. Save the
review as a sanitized artifact and hash it. The registry checks the artifact
reference and shape, not reviewer independence or scientific truth.

## Example anchor

For the 628-request run, 126 B4/B5 pairs were assessable but there were only 14
discordant pairs (10 B4-only and 4 B5-only). A critic should challenge any broad
method-superiority claim and ask how repeated contexts, provider-managed model
identity, and the scoring reference affect the comparison. These limitations
do not erase the descriptive row outcomes.

Do not substitute a Codex subagent's opinion for formal benchmark Monitor
results or claim cross-model generalization from one provider alias.
