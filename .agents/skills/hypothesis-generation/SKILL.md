---
name: hypothesis-generation
description: Generate competing, evidence-grounded ColluScope mechanisms and select a discriminating next question.
---

# Hypothesis generation for ColluScope

Use this after a completed result, a repeated anomaly, or a required pivot. Read
`research/memory.json`, `research/hypotheses.json`, the relevant frozen protocol,
and the cited result artifacts before proposing mechanisms.

## Required output

1. Separate directly observed facts, interpretations, and proposed work.
2. Produce two or three competing mechanisms. For each, state a prediction that
   differs from the others and the observation that would falsify it.
3. Identify the smallest decisive next analysis or experiment, its evidence
   class, denominator, failure handling, expected calls/cost, and whether new
   user approval is required.
4. Check whether existing evidence already answers the question. Preserve
   rejected and unresolved directions in `research/hypotheses.json` or the next
   preregistration; do not rewrite past records.
5. Mark every direction `candidate`, `selected`, or terminally `supported`,
   `refuted`, or `retired`. Candidate status never grants execution permission.

## Evidence rule

Every factual anchor needs a repository-relative, SHA-256-pinned source. Keep
different runs, evidence classes, denominators, and model identities separate.
Do not turn treatment, agreement, welfare, or monitor output into a
collusion/intent label.

## Example anchor

The DeepSeek-first Monitor report has 126 assessable B4/B5 pairs: 10 B4-only
exact, 4 B5-only exact, 65 both exact, and 47 neither exact. This supports
competing questions about method effects, repeated-case dependence, and
observable reference quality. It does not support a claim that B5 is superior
or an estimate of population performance.

Do not call a live model or launch a costly phase during discovery.
