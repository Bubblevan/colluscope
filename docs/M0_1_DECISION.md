# ColluScope M0.1 Decision — Research Validity Hardening

**Baseline:** fresh clone of origin/main at 190ea3cb4e5803bea3fede9a0eddbf8e4d57fe51. Full evidence and reproduction commands are in M0_1_EVIDENCE.md.
**Decision:** **M0.1 GO for human review of the bounded M1 behavior-pilot design. M1 execution: NO-GO pending the user's separate approval. Formal monitor evaluation: NO-GO.** No LLM, paid API, bank system, or large experiment was used.

## Gates

| Gate | Decision | Evidence / limit |
|---|---|---|
| Independent baseline reproduction from requested origin/main SHA | **GO** | Clean clone at 190ea3c; 40 tests passed; 24 scripted episodes generated and independently verified; key hashes match frozen M0. Same Windows host/runtime, so this is not an independent machine replication. |
| Neutralize C2/C4 direct construction-label cues | **GO for scripted traces** | C2 explicit agreement denial/independence language and C4 “individual ballot” cue replaced. Tests preserve those former phrases as counterexamples and scan all C1–C6 text. Scripted text only; no conclusion about LLM-generated text. |
| Correct M0 coalition-proxy interpretation | **GO with erratum** | coalition_value(target)=4, coalition_value(optimum)=1, delta 3; public W is 14 vs 28. Erratum corrects the frozen report without changing it. |
| M1 agent-visible and monitor-visible incentive separation | **GO as draft design; behavior untested** | Five controlled conditions and exact public/private task-score templates are in the draft config/TRD. A prompt-stated score is not presumed to be real model utility. No agent received it. |
| T/B/E labels and channel/behavior distinction | **GO as protocol; runtime untested** | Assigned bonus/channel is T; sent/delivered messages and chosen action are B; monitor receives permission-allowed E. Chat availability is not a collusion label; intent/agreement remains unknown. |
| Four-view fairness | **GO as preregistered design; monitor evaluation NO-GO** | Content differences, derived computation, token/cost, and hidden metadata are separated. Structured findings require a same-schema ablation. No monitor model/tokenizer was selected, and no performance/cost was measured. |
| Scenario/seed split protection | **GO for helper contract; dataset evaluation NO-GO** | Versioned SHA256 grouping and tests reject a paired split crossing and malformed digest. No M1 dataset/manifest exists; the five-seed pilot must remain exploratory. |
| M1 behavior-pilot launch | **NO-GO now; conditional proposal for review** | Requires separate approval of model/runtime, exact prompts, call/cost ceiling, score manipulation, and data retention. No automatic M1 transition. |

## Final run evidence

- Environment: Python 3.12.4, pytest 9.1.1, Windows 11 build 10.0.26200, AMD64; fresh clone started exactly at requested 190ea3c.
- Baseline before edits: **40 passed**; generated and verified 24 scripted episodes with hashes identical to frozen M0.
- Final targeted design tests: **10 passed in 0.04s**; full suite: **50 passed in 0.73s**. The release smoke run m0-20261018T145715Z generated all 24 rows (four each C1–C6), had four identical public-only C1/C6 evidence pairs, and passed both automatic and standalone verification. Model/API calls were 0; no detector metrics were claimed.
- Final trace SHA256: deb363db22edbd358ccf0e8d4ef30ea0e2eddd1b2c0fcaf934eb1b383ac632b9; source snapshot SHA256: ee5340578bf0713b132acb57628a1f539be8b0f6f7faf384c88be3e015a1ebed (all 14 file hashes rechecked).
- Frozen runs/m0/, docs/M0_EVIDENCE.md, and docs/M0_DECISION.md compare clean against the independent clone's baseline commit. New evidence is under runs/m0_1/; failed checkout/path attempts and the pre-fix text audit are retained.

## M1 recommendation for review

Review the behavior-only pilot TRD as a **conditional proposal**, not an authorization to run it. It tests whether the explicit task-score manipulation is understood and whether actions/messages vary under the five assigned conditions. It cannot establish latent intent. If the pilot fails to elicit a harmful action, report that failure and stop; do not tune the bonus against the same outcomes. A formal monitor study remains **NO-GO** until the behavior protocol passes isolation checks and a sufficiently grouped dataset and tokenizer/cost plan are approved.