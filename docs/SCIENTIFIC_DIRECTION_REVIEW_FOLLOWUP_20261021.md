# Scientific Direction Review Follow-up — 2026-10-21

**Base:** `codex/deepseek-first-m4-research-20261020` at `d451c1068e34987c6b521f511c377546d89c4da0`
**Evidence class:** offline reanalysis and literature review
**New experimental model/API requests:** 0
**Scientific outcome:** `INCONCLUSIVE` on communication mechanism; the M3 subgroup arithmetic is reproduced from the frozen sanitized group table.

## What was independently checked

The new script `scripts/analyze_m3_self_history_strata.py` verifies the SHA-256 of the frozen `m3_group_results.csv` against its artifact manifest and recomputes the exploratory subgroup counts without reading private messages. The result is saved at `docs/results/research-sprint-20261021/direction-review-followup/m3-self-history-strata.json`.

| Eligible M3 context stratum | Groups | Neutral ballot changed | Masked ballot changed | No-delivery ballot changed |
|---|---:|---:|---:|---:|
| Recipient's own earlier message already contained the focal allocation | 5 | 0/5 | 0/5 | 0/5 |
| Recipient's own earlier message did not contain the focal allocation | 3 | 3/3 | 0/3 | 3/3 |

The exact same three groups changed under Neutral and No-delivery. No-delivery also removed a mean 45.125 prompt tokens. This is consistent with several explanations: incoming text may matter; the self-history may make it redundant; a message-stage/context cue may be enough; or these eight selected contexts may be idiosyncratic. The subgroup is **post hoc**, the self-history variable is endogenous, and all eight groups were selected by delivered-proposal eligibility. It is not a randomized moderator or a population estimate.

This is a reanalysis of an already hash-pinned sanitized table, **not** a raw-trace replay. The current checkout does not contain `runs/m3/mechanism-20261020`; the original audit's raw inputs could not be reopened here. The initial direct-file `--help` invocation also failed before argument parsing because `scripts/` was not on `sys.path`; module invocation succeeds. Both facts are preserved in `docs/results/research-sprint-20261021/direction-review-followup/analysis-first-failures.log`.

## Recent primary-work comparison

The broad claim that agent communication and actions can diverge is already central to [Colosseum](https://arxiv.org/abs/2602.15198), which measures objective-grounded action regret alongside communication and reports “collusion on paper.” The generic claim that peer behavior and interaction history influence later behavior is also directly studied in [Emergent Collusion in Long-Horizon LLM Agent Interaction](https://arxiv.org/abs/2609.24967), including scripted-peer interventions and history ablations. These papers do not reproduce ColluScope's fixed short-horizon allocation design, but they lower the novelty of another broad “chat changes action” result.

The defensible remaining distinction is narrower: ColluScope records researcher-only treatment, observed action and auditor-permitted evidence separately, and asks which observable events justify a protocol-level claim. Any new result must remain task-specific and must not label a shared incentive, matching proposal, target vote, regret, or message availability as collusion or intent.

## Direction choice

| Candidate | What it can decide | Main limitation | Disposition |
|---|---|---|---|
| M1 private-reward × chat-stage package replication | Whether the post-hoc target-execution interaction repeats across the three frozen new payoff matrices and 24 matched groups | Estimates the assigned package, not the semantic effect of a message; one local checkpoint | **Keep as the selected next primary empirical question**, but describe it only as a package replication |
| M3 own-history × received-message mechanism | Whether the M3 0/5 versus 3/3 pattern survives a crossed manipulation of own-history and peer-message content | Scripted history/messages would test controlled recipient responses, not spontaneous multi-agent coordination; recent work already studies history and peer effects | Keep as a competing mechanism and potential later experiment; do not promote the post-hoc split |
| Evidence-sufficiency / deterministic public-harm audit | Which public fields determine structured welfare labels and which sequence facts require privileged events | Current matched-world sample is finite and scripted; the deterministic rule is a framework contribution, not a new model capability | Retain as the claim boundary in the paper; no further calls on public-harm labels |

The selected B question remains the strongest use of the existing 100-episode behavioral corpus, but the planned 24-group extension needs a scope correction: it is one primary Agent experiment, not a bundled Monitor campaign. The separate 216-request natural-language Monitor audit should be deferred until the human annotation codebook, coder availability, and privacy review are real and frozen. This avoids spending requests before a defensible independent reference exists.

The M3 own-history observation should be retained as a **predeclared exploratory stratification** in the M1 replication, using a frozen literal mapping rule and preserving all assigned groups. It cannot be used as a causal moderator because message eligibility and own-history content are post-treatment. A later randomized history × message experiment should be considered only if the prospective package replication leaves that mechanism as the highest-value unresolved question.

## Candidate M1 replication scope

The existing draft already specifies 24 matched groups, eight per three output-independent payoff matrices, five original conditions per group, 120 episodes, 360 ballot calls, and 96 message decisions: 456 local Qwen generations, zero retries or replacements. The frozen interaction is:

```text
(private reward + chat − private reward + no chat)
− (no reward + chat − normal cooperation)
```

Before generation, compile and hash every semantic prompt with request/run IDs removed; retain duplicate profiles and report their sensitivity separately. Report all 24 assigned group slots, all three family means, assigned/completed/failed counts, public regret, target execution, and the public-incentive parallel-behavior control. The positive finite-replication pattern requires all 24 primary groups to have estimable four-cell outcomes, a positive overall mean, and positive means in at least two of three families. If any primary group is unestimable, report the complete-group mean and worst-case bounds for missing `Delta_g` values (`[-2,2]`) and classify the primary result as `INCONCLUSIVE`; do not impute or replace. No significance or collusion claim is authorized by that rule. Welfare/regret and target execution derive from the same ballots and are not independent confirmations.

**No new experiment is registered or authorized.** The consumed 232-request approval is only for the closed M4 campaign. The candidate approval request is one new scope: `m1-reward-chat-24group-replication-v1`, at most 456 local Qwen generations, zero external/API calls and external cost, zero retries/replacements, exact frozen checkpoint/runtime, and an expiry set by the user. The 216-request Monitor work is excluded from this request. Implementation and an offline request/identity preflight remain required before any generation.

## Adversarial limits

- The 9/15 versus 0/15 M1 pattern is post-hoc and concentrated by family (1/5, 5/5, 3/5); the prospective family gate must not hide that heterogeneity.
- Even a successful replication supports only the assigned incentive × chat-stage package in the fixed Qwen task. It does not identify message meaning, agreement, collusion, or latent intent.
- M3's neutral/no-delivery overlap and the 45.125-token No-delivery difference argue against describing those earlier changes as a semantic effect.
- The M3 source run is absent from the current checkout; only the frozen sanitized results are available for this follow-up.
- The reviewed recent papers reduce broad novelty claims. The paper must position its contribution around evidence permissions, independent recomputation, and claim boundaries, with the behavioral replication as task-specific evidence.
- This follow-up is not an independent critic review. Existing critic reviews disagree across B5 reliability, B behavior, and C evidence sufficiency; none reviewed this new literature/reanalysis packet blind.

## Reproduction

```powershell
python scripts/analyze_m3_self_history_strata.py --out docs/results/research-sprint-20261021/direction-review-followup/m3-self-history-strata.json
python scripts/researchctl.py audit
```

The first command verifies the source table hash and all counts. The second checks registry integrity only; neither authorizes inference.
