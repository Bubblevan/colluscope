# M4 B5 Raw-Response Repeatability Audit — Decision

**Decision:** `SUPPORTED` for the narrow finite raw-output provenance claim; `INCONCLUSIVE` for the cause of response variation and for the earlier evidence-view effect.  
**Operational integrity:** `PASS`; registered researchctl audit passes.  
**Model/API calls this offline cycle:** 0.  
**Previous campaign authorization:** the separate 232-request M4 B5 campaign is already consumed and closed; it cannot be reused.

## Claim supported

Across the 48 preregistered historical/current pairs with byte-identical request bodies and matching reported system fingerprints, 19 pairs had different raw tool-call labels. Independent strict parsing reproduced every stored label and evidence-reference array; there were no source-integrity, parse, or downstream mapping failures. This establishes finite raw-response label variation in this retained comparison.

The 19 changes are not homogeneous: 17/24 Public-only pairs differed, including 15 `insufficient_evidence→present`; only 2/24 Privileged pairs differed. Evidence references stayed equal in 24/24 Public-only pairs and 21/24 Privileged pairs. This suggests output-field variation can occur while references remain fixed, but correctness and cause are not identified by this comparison.

## Claims not supported

- The comparison does not establish population-level stochasticity or prove sampling randomness caused the differences. A mutable model alias and equal reported fingerprints do not prove identical hidden serving state.
- It does not identify whether message meaning, event structure, completeness metadata, length, wording, or salience caused the 20/24 historical Public-to-Privileged B5 changes.
- It does not establish message comprehension, collusion, intent, or general monitor ability.
- It does not establish a need for an LLM to compute public-harm labels; those are deterministically reconstructible from public records.

## Integrity and review

The preregistered selector source hash and 48-pair schedule hash were verified. A first fixture-only test failure arose because the test data omitted the frozen source run's full 232 attempt-start entries. The selector was restored byte-for-byte to the preregistered version; synthetic fixtures now include inert, unselected entries, and all 12 focused tests pass. The earlier failure and correction are retained.

The independent critic found v3 aggregate reporting gaps, then found missing external-schedule-hash, exact denominator, and duplicate-request-ID checks. A later review found that the in-memory function path could bypass the CLI schedule-hash gate and duplicate-ID coverage was incomplete. The public API now accepts only a schedule path; tests cover all three ID indexes. The final independent v5 review found no remaining material flaw in the public audit path and confirmed the same substantive counts. The critic did not rerun tests or inspect raw runs. A separate amendment timestamp was accidentally set in the future; the line remains and an append-only correction explains that the exact write time was not retained. This administrative error does not affect request selection or the v5 replay but remains in the audit trail.

An initial preclosure registry audit also failed after this iteration appended text to two prior hash-pinned documents. The failure log is retained; those files were restored to their original committed bytes, the update moved to dated appendices, and the final preclosure audit passes.

## Next step

Do not spend more calls on the closed campaign. If the B5 mechanism remains a priority, the next useful experiment is a newly preregistered, interleaved repeatability study that varies one evidence-view component at a time while repeating unchanged inputs. A screening version could use all 24 cases × 3 views × 3 repeats (216 physical requests), randomize order within case, retain all invalid and failed rows, use a separately approved model/provider scope, and report actual token counts. A result is inconclusive if same-input label variation is comparable to the edited-view contrast, if the serving fingerprint drifts, or if the intended one-factor contrast changes multiple request fields.

This is a proposal only. No new experiment is registered or authorized here. The prior 232-request approval has been fully consumed; obtain scope-specific approval before any new inference.
