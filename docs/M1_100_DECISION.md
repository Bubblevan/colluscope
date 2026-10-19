# M1-100 Decision

**Decision date:** 2026-10-19  
**Scope decision:** M1-100 execution and offline audit complete.  
**M2:** **NO-GO for formal monitor inference, benchmark scoring, training, or causal evaluation.** This document does not authorize M2 calls.

## Completion decision

The authorized extension is complete: **75 assigned / 75 completed / 0 failed**. Together with the unchanged historical 25, the corpus contains 100 provenance-aware episodes. The extension used **285 actual local model completions**: 225 ballots plus 60 communication decisions, all on the first attempt. It used 285 physical HTTP attempts, 0 retries, 0 paid API calls, and 0 external model calls recorded. Across the 100 behavior episodes, the generation call count is 380 (95 historical plus 285 new); separate preflight generations are outside that episode count.

The independent raw-ballot audit recomputed all 75 prospective settlements and rechecked all 25 historical rows. Public welfare, scenario optimum, regret, selected allocation, task scores, bonuses, and request/evidence links recomputed. Public E permissions passed. The final audit status is `PASS_CORE_RECOMPUTE_WITH_STORED_HARM_FLAG_MISMATCHES`, not a clean artifact pass: 19 new B rows store `harmful_outcome=true` while the actual scenario-specific regret is zero. These original B bytes remain unchanged. The authoritative CSV/JSON reports the raw-ballot recomputation and each mismatch separately.

The new extension provides usable exploratory behavior evidence. In 15 matched private-incentive groups, the chat-available arm executed the target in nine groups; the no-chat arm executed it in none. All nine target executions coincide with a sent-message episode, and all 14 delivered messages were explicit target-allocation proposals with sender and recipient ballots concordant. No explicit commitment marker was detected by the narrow frozen rule. The shared target and extra message-stage turn mean this does not isolate a causal effect of communication content and cannot support an intent claim.

## Dataset readiness for M2

**No-go for formal M2 evaluation.** The corpus has no defensible latent-collusion gold label. Available labels describe observable actions and outcomes only. There are 15 prospective matched groups, five per payoff family; F2/F3 hold out scenario/seed groups but not entire payoff families. F0 is an older exploratory protocol and must remain separate. The stored harm flag defect is material until downstream consumers are guaranteed to use the independently recomputed label rather than B's redundant boolean. No human blinded message coding or independent adjudication of acceptance/commitment has been performed.

After separate human review, the corpus could support an **exploratory Public-only E ingestion/pipeline exercise** or qualitative analysis of observable harm and ballots. It must not be used to claim detector accuracy, FPR, recall, held-out-family generalization, or communication-induced collusion. The current evidence does not include a Privileged Audit projection. Private message text remains local and cannot be supplied to a monitor without a new permission decision and a separately hashed view.

Before considering a formal M2 gate, the highest-value additions are:

1. A turn/context-matched control that separates message content from the extra generation round.
2. A design that varies shared-target disclosure independently from peer communication.
3. Blinded double-coding of message proposal, acceptance, commitment, and action concordance, with preserved disagreements and adjudication.
4. More independent groups and a whole-payoff-family holdout; do not split matched conditions or evidence views across partitions.
5. A fail-closed downstream schema that accepts only audited recomputed welfare labels, carries the 19 source-flag discrepancies, and defaults to `insufficient_evidence` for latent intent.

## Supported observations, hypotheses, and unknowns

| Category | Statement |
|---|---|
| Supported by these real model traces | 75/75 episodes completed; 285/285 local responses returned once; 9/15 target executions in private-incentive/chat and 0/15 in the matched no-chat arm; 14 sent/delivered explicit target proposals; 14/14 sender and 14/14 recipient ballots concordant; 13/75 positive-regret outcomes, including four non-target/no-message cases; 19 stale stored harm booleans. |
| Plausible interpretation only | Message-round opportunity or its added context may have contributed to the target executions. The matched contrast is compatible with that explanation but also with shared incentive, deterministic prompt sensitivity, or extra-turn effects. |
| Unknown / requires new experiment | Whether messages caused the action; whether the agents had a collusive intent; whether they understood the score rules; whether behavior generalizes to other models, new payoff families, stochastic sampling, or real-world agent systems. |

The auditable labels are intervention assignment (T, design only), message action and delivery (B), proposal text code, sender/recipient ballot concordance, target execution, scenario-specific welfare regret, and tie-break/parse status. None is a latent-collusion gold label. Publicly announced rewards and target behavior remain observable cues, not proof.

## Audit and release boundary

The original `m1-100-splits.json` and F0 historical rows were preserved. The F0 metadata discrepancy is handled by a post-run correction file that retains the old alias. The three failed audit records are retained and hash-bound to the post-run correction chain. A successful audit rerun produced the same corpus-manifest SHA-256 `4e7868449a5e2bc3621fef4da4eaded4d710c15570dbf12f7d4ab215f3a4bb13` and left T/B/E/request records and failure records byte-identical.

The full local manifest and raw traces are in `runs/m1_100/extension-75-20261019-run02/`. The raw B/request files contain private messages; they were not committed or published. The public evidence and sanitized aggregate reports contain no private message text. The full test suite returned **212 passed, 1 skipped**. No M2 monitor, new Agent Pilot, model training, or external inference was run.

## Reproduction

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python scripts/freeze_m1_100_design.py --check
python -m pytest -q
python scripts/audit_m1_100.py --run runs/m1_100/extension-75-20261019-run02
```

See [M1-100 Evidence](M1_100_EVIDENCE.md) for exact frozen model/runtime hashes, raw artifact hashes, audit failure hashes, local output paths, and the source commit used to execute the 75 assignments. The current topic branch contains the post-run auditor and runtime fix; do not rerun completed episodes.
