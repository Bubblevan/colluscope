# AutoResearch harness critique and design decisions

**Date:** 2026-10-21
**Scope:** revise the repository harness from the supplied critique. This is a
harness review, not execution of the proposed research work or any new
experiment.

## Criticism and disposition

| Criticism | Disposition | Change or reason |
|---|---|---|
| A terminal phase or ordinary `GO/NO-GO` can end a long-running Goal. | Adopted | Split typed scientific outcomes from operational review disposition. The Goal prompt explicitly continues after supported, refuted, inconclusive, invalid, and blocked outcomes; only research completion or a real hard boundary can finish it. |
| `researchctl.py` records cycles but does not continue them. | Partly adopted | Added `researchctl.py next` to expose the next required lifecycle step and made Codex `/goal` the reasoning/continuation driver. The CLI still does not launch registered commands or arbitrary shell. It is accurate to call this a Goal-driven coordinator, not a self-dispatching runner. |
| A future dispatcher needs approved entry points, recovery, and safe budget enforcement. | Deferred with a gate | No dispatcher was added. The current checkout has heterogeneous experiment entry points and no shared pre-request reservation service. A runner must first implement an immutable allowlist, atomic per-request reservations, expiry/identity/privacy checks, and crash-safe recovery. Until then no CLI can start an experiment. |
| Closed-cycle usage is compared against whichever approval is current, and expiry is not enforced. | Adopted in the record model | Added immutable per-approval records, exact approved experiment IDs and scope, an expiry timestamp, per-approval usage totals, project-wide cumulative caps, preregistration reservations, and a required hash-pinned ledger row for every physical request attempt. The evaluator checks attempt times against approval expiry. Since there is no dispatcher, this remains a post-run record check rather than pre-transport enforcement. |
| A self-authored `new_uncertainty_reduced` boolean can create fictional progress. | Adopted with a clear limit | Removed the boolean from schema v2. Closure now describes the changed claim, remaining alternatives, evidence references, and whether an independent critic confirmed the update. Only that structured record with a hash-pinned review receives progress credit. The program states that structure and provenance do not prove scientific truth or reviewer independence. |
| One open experiment blocks “養蠱” exploration. | Partly adopted | Added three evidence-anchored hypothesis slots for read-only comparison. A single formal cycle remains open at a time; isolated worktrees, separate branch ledgers, and shared paid-call scheduling are not implemented. This avoids parallel mutation of shared frozen inputs and an unprotected common budget. |
| There is no independent scientific critic or research memory. | Partly adopted | Added `scientific-critic`, `hypothesis-generation`, and `result-interpretation` skills, plus claim-level memory with exact artifact hashes. The skills require a separate review artifact and forbid calling self-review independent. This revision does not spawn a critic agent or claim its skills alone establish independence. |
| The Goal should remember what a result ruled out and feed that into its next choice. | Adopted | `research/memory.json` records four scoped findings from the 628-request and separate 856-row runs. `research/hypotheses.json` cites those records and states competing predictions. The 628 and 856 schedules remain separate. |
| The example “B5 changed its public-harm prediction in 20/24 cases” should drive an evidence-conditioned audit study. | Not adopted as a fact | That exact 20/24 result is absent from the currently available hash-pinned reports. The 856-row result instead reports only 2/72 parseable matched-world outputs and no common assessable B4/B5 pair. The number must not seed memory or a preregistration unless a source with that exact denominator is produced. |
| A zero-call lifecycle test should cover resume, failures, budgets, and pivot. | Deferred | This change does not add or run a test suite. The new coordinator is not described as end-to-end verified. The next infrastructure gate is a zero-provider-call fake-runner test of the record lifecycle before any dispatch capability is considered. |
| Use Luna for a critic, but do not substitute it for the evaluated Monitor. | Adopted as a role boundary | The critic skill separates research review from benchmark Monitor scoring. It names no fixed model dependency and forbids treating a Codex subagent as formal B4/B5 output or cross-model benchmark evidence. |

## Historical closeout reconciliation

The registry was waiting for a separate task even though the completed
DeepSeek-first closeout and independent artifacts were already in the checkout.
Created `research/handoffs/DEEPSEEK-FIRST-RESEARCH-01.json` from the frozen
protocol, sanitized post-run summary, independent raw replay, and terminal
decision, with exact SHA-256 references. Imported it through the existing
handoff command. The 628 historical calls are visible as consumed historical
usage and are excluded from new-cycle authorization.

The separate 856-row result is referenced only as distinct prior evidence. Its
0-pair B4/B5 estimability result is not combined with the 126 assessable pairs
from the 628-request run. No inference, new expensive phase, or experiment was
run as part of this revision.

## Current capability statement

The harness now maintains a continuing Goal, bounded hypothesis pool, typed
cycle outcomes, claim memory, and authorization-specific record checks. It
still relies on Codex `/goal` for reasoning and continuation. It has no
experiment dispatcher, no pre-transport request reservation, no actual
isolated branch runner, and no end-to-end lifecycle test in this revision.
Those are explicit limits rather than implied capabilities.

## Next action

Review the three memory-anchored candidates and preregister one zero-call
offline cycle. The evidence-boundary candidate is the only one with a clearly
available deterministic analysis path; this recommendation does not itself
start that analysis.
