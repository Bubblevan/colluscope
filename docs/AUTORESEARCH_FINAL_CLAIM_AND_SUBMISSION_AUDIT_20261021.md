# Autoresearch Follow-up — Claim Boundary, Literature, and Submission Audit

- **Date checked:** 2026-10-21 UTC
- **Evidence class:** offline synthesis and primary-source review
- **Model/API calls:** 0
- **Status:** working evidence audit; not the final sprint paper and not a submission

## 1. What the evidence currently establishes

This project has evidence at several distinct levels. They must not be collapsed into a single collusion label.

| Record | Directly supported observation | What it does not establish |
|---|---|---|
| M0 and the matched-world sequence audit | In 12 scripted pairs, the paired Public-only projections were identical in 24/24 method-by-pair comparisons; the permitted Privileged projections differed in 24/24. A source-event replay found at least one determinate sequence-element difference in 8/12 pairs and a complete proposal/acceptance/both-actions sequence difference in 2/12 pairs. | A universal impossibility theorem, natural LLM behavior, or a collusion detector's accuracy. These are finite synthetic witnesses. |
| M1-100 behavior corpus | In the 75-episode prospective extension, the private-reward-plus-chat cell selected the target in 9/15 groups, versus 0/15 in each other factorial cell. The v2 raw-response audit reparsed 225/225 ballots and independently reproduced 75/75 settlements. | A message-caused effect or collusion. Both rewarded agents know the same target; chat also adds a model turn. The old five-per-condition F0 stratum is a different provenance and matrix. |
| M2 monitor audit | Public welfare gap was present in the model payload for every eligible action-bearing public view, and a deterministic rule recomputed public harm exactly on the audited references. Some LLM score fields were therefore answer-exposed; structured scores are not independent LLM reasoning. | Detector superiority or evidence that an LLM is needed for mechanically computable welfare labels. |
| M3 paired message counterfactual | Eight of twelve assigned groups were proposal-eligible. Relative to Proposal, Neutral and No-delivery each changed 3/8 focal ballots, but only one fixed-peer settlement changed. Proposal–Neutral and Proposal–Masked prompt token counts matched; No-delivery averaged 45.125 fewer prompt tokens. Five of eight focal recipients had already expressed the same target mapping in their own message history. | A semantic proposal effect, population effect, or collusion. Eligibility is conditional, the no-delivery prompt is shorter, and the own-history signal is a competing source. |
| M4 B5 context campaign | The registered fixed corpus produced 12/24 Public-only→Neutral, 20/24 Neutral→Original, and 19/24 Public-only→Original label changes. Same-byte requests with the same reported provider fingerprint did not reliably reproduce labels across historical/current runs. | A general monitor response law, a causal content effect, or latent intent. B5 is a mutable provider alias and prompt length/wording/package differences remain. |

The current strongest synthesis is an **evidence-boundary result**: assignments, delivered communications, proposals, ballots, public consequences, evidence projections, and monitor predictions are separate observables. A shared target, matching votes, a delivered proposal, welfare regret, or a monitor label cannot independently establish agreement or intent. The synthetic matched-world audit is a finite construction showing that a specific authorized projection can omit sequence facts that differ in the corresponding permitted privileged view.

The project does not have a natural-trajectory gold label for latent collusion, a confirmed coordinated-harm positive, or an independently validated monitor classifier. It must not claim those results. The public-harm rule is a valid deterministic baseline for public outcome calculation, not a collusion oracle.

## 2. Primary-literature challenge to novelty

The novelty claim must remain narrower than “we combine what agents say and do” or “more monitor evidence may change predictions.” Those ideas have close predecessors:

- [Colosseum](https://arxiv.org/abs/2602.15198) evaluates communication and actions separately, measures regret/coalition advantage, and explicitly discusses “collusion on paper” where textual plans need not yield corresponding actions. ColluScope must not claim that this distinction or the phenomenon is new.
- [Evaluating LLM Agent Collusion in Double Auctions](https://arxiv.org/abs/2507.01413) studies controlled communication, model, and environmental-pressure factors in a market. ColluScope must not claim a first causal study of communication availability or generic incentive effects.
- [Arike et al.](https://arxiv.org/abs/2601.21112) study monitor information access and report cases where less information improves oversight. ColluScope must not claim that evidence-view sensitivity or information filtering is a new general monitor question.
- The [Apart Track 2.3 brief](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25) explicitly asks what counts as convincing evidence, references plus-factors, and proposes comparing coordinated harmful action, common-incentive parallel behavior, and collusive-sounding talk without behavioral effect.

The defensible contribution is therefore limited to a **provenance-aware, claim-specific evidence audit** over a set of finite synthetic and real-agent traces, with reproducible counterexamples for (i) harm without communication, (ii) shared-target action compatible with independent choice, (iii) talk/action concordance that does not isolate causal influence, (iv) public projection that omits privileged sequence details, and (v) same-input monitor non-repeatability. These examples can motivate and illustrate an evidence standard; they do not validate a decision threshold for accusing an agent of collusion.

## 3. Competing mechanisms and next discriminating evidence

1. **Shared-target parallel action:** A and B choose the rewarded mapping independently because both know the target. This predicts target votes can occur without private-channel use, and weakens any causal interpretation of their matching votes.
2. **Message-stage/context effect:** The extra chat-generation turn, target salience, or prompt context changes action even if the incoming text has no semantic effect. This predicts similar responses to a length- and stage-matched neutral input.
3. **Novel-information response:** A recipient changes a ballot only when incoming content supplies information not already present in that recipient's own history. M3's post-hoc 0/5 versus 3/3 split motivates this hypothesis, but it is confounded by role, matrix, wording, and small conditional samples.
4. **Monitor response variability:** Some apparent evidence-view changes arise from variation across repeated calls to identical input, rather than from the changed view. M4's historical/current exact-byte comparison supports this as a live alternative but does not identify its cause.

The selected prospective M1 candidate tests only the **private-reward × chat-stage package** across new matrices; it does not separate mechanisms 1–3. The 144-call M4 repeatability candidate targets mechanism 4. The M1 candidate remains the primary behavior direction because the current monitor public-harm target is mechanically computable and its evidence-view campaign was inconclusive. Neither candidate may run under the consumed M4 authorization.

## 4. Authoritative local sources and hashes

The following hashes were computed from the current worktree on 2026-10-21:

| Local source | SHA-256 |
|---|---|
| `docs/EVIDENCE_AWARE_AUDITING_FRAMEWORK.md` | `29ed5d818010d5a70587267e039d5e26b719bc8129761a0e1d96b3fefcd82535` |
| `docs/M2_FINAL_SCIENTIFIC_SYNTHESIS.md` | `01a62519dc2960288d480ae576f9d85a28ef48b8fe3853833698f51ed7d5cb08` |
| `docs/M3_SCIENTIFIC_RESULTS.md` | `dd194d2579366acd0d15c4bc63952b8fddd20bbe92ffc2bdd339efd50e7eaf41` |
| `docs/M1_100_SCIENTIFIC_AUDIT.md` | `0a20508d7048f1e573b4d158f348cfe647c8354199860ec1adf5b162a7ec9c1a` |
| `docs/M1_PACKAGE_REPLICATION_V3_RAW_RESPONSE_AUDIT_20261021.md` | `fe921424e3b86021c4ea3dd22db5175407a4ac95bc428355bd34c728f03f676d` |
| `docs/M4_B5_CONTEXT_SENSITIVITY_EVIDENCE.md` | `906891199731c2b9a0a9a0f6822dd7c572896c29b41620fbf53e85e42bf37402` |
| `docs/results/research-sprint-20261021/MATCHED_WORLD_SEQUENCE_VISIBILITY_AUDIT.md` | `f76ec46a585431d9e5d58d5583790587be6ec37242943ef1dc223b31ea87dada` |
| `docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-audit.json` | `6e5278737d9550d547ef4895ef9ed9bc6aa85fafdb1a26087fdbc4011a11041c` |

The last artifact is the restored hash-pinned audit output. Re-running its current audit script at the default path overwrites it; use the documented recovery caution before any future replay.

## 5. Sprint submission readiness and pre-sprint disclosure

The official page currently presents a contradiction: its upload form states “The submission window has closed,” while the event section states that submissions close October 25, 2026 at 11:59 PM AoE. This audit does not infer that the window will reopen or that the deadline has passed. The linked Google Docs template redirected to Google sign-in in the available fetch path, so the template file itself was not inspected.

The page lists a PDF report using the official template, a title and abstract of at most 150 words, authors and affiliations, and a required Limitations and Dual-Use / Ethical Considerations appendix. It recommends 4–8 pages, and says existing work is allowed only if the new Sprint-period work is clearly identified; undisclosed prior work may lead to disqualification.

All M0–M4 datasets, runs, audits, and this October 21 literature/claim audit precede the October 23 Sprint start. They must be described as pre-sprint work. Do not change timestamps or relabel prior runs. Author names, affiliations, and any team details remain unprovided and must remain placeholders until supplied.

Questions to resolve with organizers before upload:

1. Is the upload form intentionally closed now, and will it reopen before the stated October 25 AoE deadline?
2. Is there an accessible/exportable official template if the Google Docs copy link requires an account?
3. What upload route should participants use if the form remains closed while the stated deadline is still future?
4. What disclosure format do organizers prefer for a project whose M0–M4 evidence predates the Sprint and whose Sprint-period contribution will be a separately frozen extension?

No organizer has been contacted and no project has been submitted.

## 6. Decision

**Scientific outcome:** `INCONCLUSIVE` for any claim that the current corpus identifies latent collusion or validates a general detector. The narrower evidence-boundary observations are supported only at their stated finite scopes.

**Operational status:** current synthesis and hashes are reviewable; the M1 candidate is offline-ready but unregistered and without exact M1 authorization. The B5 232-request approval is consumed and unavailable for any new cycle.

**Single next action:** obtain the pending exact-scope decision for `m1-reward-chat-24group-replication-v1`. If approved, proceed with its immutable registration and all live identity/storage gates; if not, continue drafting and validating the no-call evidence-standard report without substituting another model run.
