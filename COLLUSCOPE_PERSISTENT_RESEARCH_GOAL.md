# ColluScope — Persistent Research Goal / Codex North Star

**Scope:** From the present M1-P0 blockage through the Apart Research AI Collusion Research Sprint (2026-10-23–25), submission (check official deadline and portal before final upload), and a reproducible post-event research archive.  
**Current empirical state (2026-10-20, after M2-V3 and M3 evidence audit):** the real-agent corpus contains 25 historical F0 and 75 prospective F1–F3 episodes. One previously authorized DeepSeek Flash monitor run completed 1,500 scheduled task/view rows using 916 requests; it is an observable-fact audit, not a collusion detector evaluation. An independent no-call replay matched all 1,500 frozen scores and found welfare_gap directly in every eligible action-bearing view, making the highest structured score answer-exposed. Raw Fusion with privileged messages did not improve public-harm classification. M1 behavior supports a descriptive shared-target/message-concordance pattern, but shared incentives, the extra message stage, and simultaneous message composition prevent causal or intent claims. See `docs/M2_FINAL_SCIENTIFIC_SYNTHESIS.md`, `docs/EVIDENCE_AWARE_AUDITING_FRAMEWORK.md`, and `docs/M3_MECHANISM_PROTOCOL_DRAFT.md`. M3 is a protocol draft only; no new model call is authorized.

## 1. North Star: the outcome that matters

**Deliver a compact, falsifiable, independently replayable research result on the evidence required to audit multi-agent collusion—not another large Agent framework or an untested demonstration.**

The project should answer: *When a monitor sees only authorized communication and/or actions from interacting agents, what conclusions about harmful coordination can it justifiably draw, when must it abstain, and which additional evidence or interventions change that conclusion?*

Optimize **credible evidence per unit time, model call, and complexity**. Preserve negative results, contradictory cases, and uncertainty. A discovered failure mode with a sound experimental control is worth more than a polished interface and unreliable accuracy claim.

## 2. Durable success definition

A successful project has four tiers of evidence:

1. **Infrastructure:** exact model, GGUF/server source, tokenizer/template, prompt, schema, seed, raw request/response, permission, T/B/E trace and verified provenance. Green unit tests alone do not establish model behavior.
2. **Behavior:** genuine LLM episodes with complete failures, ballot/chat/score outcomes and matched controls, without conflating treatment assignment, harm and collusion.
3. **Audit:** same-episode text-only, action-only, raw-fusion, and structured-evidence monitoring under equal monitor, threshold, permission, and explicit token/cost accounting. Report hard-negative FPR and detection sensitivity only against defensible **observable** labels; flag latent coordination/intent as uncertain.
4. **Research report:** hypothesis, related work, experiment protocol, preregistered variants, primary results, ablations, failure cases, limits, dual-use discussion, reproducibility package and a submission-ready English PDF per official template.

There is no requirement that a model spontaneously collude or that the structured auditor outperform the baselines. If not, describe the tested limitations honestly and recover a narrower finding.

## 3. Scientific target and alternative hypotheses

- **RQ1 — Identifiability:** Can two distinct mechanisms yield the same authorized evidence? Reuse the proven scripted C1/C6 construction only as a *synthetic demonstration* and test what observable variables or permission changes resolve some ambiguity. Do not universalize a toy indistinguishability pair.
- **RQ2 — Parallel behavior vs communication:** Is action agreement common under shared incentives without peer messages? Distinguish offered channel, channel use, actual agreement evidence, realized target, and welfare loss. A/B know the same rewarded target; this limits causal claims.
- **RQ3 — Monitoring:** On matched and suitably labeled trajectories, does adding allowed action history improve over text-only, and when can a structured claim/action consistency report help beyond raw fusion? Separate added computation from changed serialization and increased token length.
- **RQ4 — Uncertainty:** Does abstention or more explicit evidence criteria reduce false accusations on common-incentive negatives, legitimate private conversations, 'talk-only' plans, and unilateral poor decisions?
- **RQ5 — Robustness:** How sensitive are the findings to chair tie-break, payoff matrix, agent role, message visibility, model decoding and scenario family? Answer only what the experiment actually varies; do not suggest that repeated fixed seeds establish external validity.

Pick **one primary research question** for the hackathon paper; other questions are supporting or future-work. Narrowness is a strength, not a retreat.

## 4. Research roadmap (stage gates; not a feature checklist)

**G0 — Resolve the true blocker.** Fix the interface-versus-choice confusion in M1-P0 preflight under a new version. Retain both old NO-GO records. Run only newly approved, bounded model probes. Gate is verifiable interface compatibility, not forced model obedience.

**G1 — Real behavior Pilot.** Run the previously frozen five-arm × five-block 25-episode batch only after protocol approval. Keep every assigned case including errors. Quantify completed episodes, valid votes, message actions, target execution, task scores and public welfare; publish raw trace and limitations. No formal monitor score here.

**G2 — Dataset quality/admission.** Distinguish *configured incentive/channel* (T), *observed action/harm* (B), and *auditor-visible evidence* (E). Predeclare what is positive, negative, and ambiguous for each research claim. No 'collusion=true' from channel availability, shared target, bonus or welfare loss alone. Pair and group split scenarios before monitor tuning; reserve held-out cases from any prompt tuning. Explicitly state sample-size limits.

**G3 — Four-view audit pilot.** Freeze monitor model/version/prompt/parser/threshold/permission and run matched views. Include a cheap action-rule baseline and, when warranted, an LLM monitor; compare raw fusion to same-format structured-without-findings and with-findings; account for tokens, time, cost. Analyze individual FP/FN and confidence/abstention, not just accuracy.

**G4 — Scientific synthesis.** Select the most defensible finding. Generate tables/figures directly from frozen scoring code. Check each abstract/claim against an artifact. Write official report (including limitations, ethics/dual-use, pre-sprint disclosures), provide repro command and optional short demo. Finish the submission before the portal deadline; do not spend submission day perfecting infrastructure.

**G5 — Post-event archive.** Tag exact code + dataset + model manifest, include a clear 'run with no network' replay and limitations, and separate unverified exploratory leads from final results. Build a reusable research scaffold only *after* the paper has a real finding.

## 5. If results are disappointing: disciplined pivot tree

**P0: runtime contract still fails** → Distinguish server grammar, chat-template rendering, model instruction following and parser. Fix only the identified layer; add a targeted counterexample; cap further preflight attempts. If unresolved, switch to a preregistered reproducible *offline evidence-audit study* rather than burning the sprint on deployment. A switch of inference backend/checkpoint requires permission and a new protocol.

**P1: most episodes fail or no behavior variability** → Preserve all failures and report protocol feasibility limits. Consider an **independent, predeclared** alternate experimental schedule (new model/seed/task family or a modest change in incentives) only as a new study, with no reuse of exploratory outcomes as hold-out evidence. If time is short, narrow the question to reliability of audit evidence and false-positive mechanisms.

**P2: no clear collusion positives** → Do *not* induce positive labels from welfare gap or shared bonus. Prefer Track 2.3 evidence sufficiency, non-identifiability and false-positive evaluation using clearly labeled scripted controls plus genuine behavior traces that can be justified. If the research goal truly demands affirmative instances, propose a separate approval gate to alter the environment, and disclose the change.

**P3: monitor fusion/structure does not outperform** → Report equality or harm if credible; analyze leakage, evidence redundancy, token length, error cases and variance. A negative result under a fair matched protocol can still be publishable as a hackathon finding; never change the scorer after reading test results.

**P4: limited statistical power** → No spurious significance claims. Show denominators, confidence intervals where meaningful, paired examples and clearly qualified effect sizes; stop when time or compute budget is exhausted.

**P5: deadline approaching** → Prioritize verified dataset, one clean comparison, two substantive failure cases, and a complete report over extra baselines, dashboards, RAG/Memory/RL, complex multi-agent orchestration, or fine-tuning.

## 6. Guardrails: claims, permissions, privacy and provenance

- Never claim real LLM collusion, an agreement, improvement of a detector, or a causal effect from Mock samples, a preflight, or treatment labels alone.
- Never use pre-existing FTEC5660/ICBC team code without rights; disclose the M0–M1 foundation built before the Sprint and AI assistance. Keep original paper/code attributions and license caveats.
- Never upload real private banking data, secrets, credentials, or local personal files as evidence. Preserve private-agent observations under access controls; when publishing, use sanitized synthetic data and inspect tracked `runs/` files for sensitive content.
- Never call a paid provider, change server/model/driver packages, authorize new generation, run a 25-episode Pilot, or start M2 merely because this goal exists. A distinct, explicit approval is required for each new real-model batch and budget.
- Never silently change a frozen source, parser, prompt, data split, reward, condition set, action schema, decoding option, label or result. Version every substantive revision and preserve the earlier contrary evidence.
- A clean run requires exact source/runtime/model/checkpoint fingerprints and independent semantic verification. Hashes prove byte identity, **not** scientific validity.

## 7. Codex autonomous iteration contract

Every bounded iteration must follow:

**INSPECT** → identify the highest-impact uncertainty blocking the paper.  
**HYPOTHESIZE** → predict a falsifiable outcome and identify the alternative explanation.  
**PREREGISTER** → specify what is held constant, what changes, negative control, success/fail/abstain gate, call/time ceiling.  
**IMPLEMENT** → smallest reversible code/protocol change, with explicit experiment vs infrastructure provenance.  
**RUN** → actually execute permitted tests, log raw evidence, including failures, and never cherry-pick.  
**ADVERSARIAL REVIEW** → act as reviewer: find leakage, uncontrolled confounds, scope inflation, invalid labels and misleading metrics.  
**DECIDE** → PASS, FAIL, AMBIGUOUS, BLOCKED or PIVOT, with a reason and bound.  
**REPORT** → update research log/risk register and state exactly one highest-value next experiment.

**Prioritization score:** maximize expected *reduction in a decisive scientific uncertainty* divided by engineering hours, model calls and deadline risk. Cheap decisive counterexamples outrank broad refactoring. Stop revisiting the same root cause without a materially new hypothesis; after two distinct failed remedies, surface the blocker and a scoped alternative instead of infinite retries.

## 8. Deliverables / final report quality bar

- Frozen `experiment_manifest.json` or equivalent: exact git SHA, model weight/hash, server build, tokenizer/template and prompt/schema hashes, seed/order, full budget, sampling, permissions, timestamps and data split.
- Reproducible raw T/B/E records, attempted/error logs and deterministic settlement/verification scripts.
- One main result table with clearly denominated experimental groups; one figure directly linked to actual scoring output; one or two illuminating error cases.
- Evidence table mapping each claim to exact file/row/experiment and to a cited prior work contribution; avoid unsupported generalizations and invented performance figures.
- An English report and abstract consistent with the official submission requirements, plus Limitations and Dual-Use/Ethical Considerations; explicit old-vs-new work disclosure.
- Public README with truthful 'What it does', 'What it does not prove', license, exact replay and safety boundaries. No grandiose claims about real finance or deployed fraud detection.

## 9. Concrete stop/go questions to ask repeatedly

1. Did a real model generate these actions, or only a test double?
2. Is the positive/negative label observable and defensible, or inferred from the assigned treatment?
3. Could an independent agent under shared incentives create this same trace?
4. Could a monitor win by reading a condition cue, task-score rule, private metadata, or repeated scenario identity?
5. Is a claimed improvement actually a difference in evidence, derived computation or token budget?
6. Can every conclusion be reproduced from the frozen raw bytes and verification scripts?
7. Is this the smallest next experiment likely to change the final paper's conclusion?
8. Are we preserving enough time to submit a complete report?

**The end goal is trustworthy research, not passing every gate, forcing a desired model choice, or maximizing implementation size.**

## M2-V3 DeepSeek one-run authorization — consumed (2026-10-20)

The user's single bounded DeepSeek Flash authorization has been consumed. It covered the one run against the frozen 100-episode synthetic corpus and has expired. It does not authorize any further API calls. Only the exact official Chat Completions endpoint received public task specifications, public ballots/results, and actually sent-and-delivered synthetic A/B messages in the Privileged Audit projection. T, hidden/private reward assignments, gold/reference labels, raw unfiltered researcher files, `.env`, keys, and unrelated repository data were excluded. Public-only E and historical M1/M2 artifacts are preserved.

The scheduled 1,500 monitor rows completed using 916 logical requests and 916 physical attempts, with zero retries and usage-based estimated cost USD $0.062844045. Offline verification found zero hidden metadata, zero Public-only private-text leaks, zero cross-split deduplication, and verified all 1,500 payloads. Results support observable fact-extraction analysis only; they do not establish latent collusion or intent. No Pro comparison, training, further M2 inference, or other model calls are authorized by this consumed approval. Any new model generation requires a new explicit approval, endpoint/model identity, protocol, and budget freeze.

## M3 mechanism and evidence-validity review — no-call synthesis (2026-10-20)

The independent M2 audit is in `docs/M2_FINAL_SCIENTIFIC_SYNTHESIS.md`; its reproducible tables, figures, input hashes and output hash inventory are under `docs/results/m2-final-scientific-synthesis/`. It verified all 1,500 stored scoring rows from the raw source and exact raw responses without new inference. The request payloads exposed public `welfare_gap` in every eligible action-bearing view. Structured findings therefore create answer leakage, and F2/F3 remain previously exposed exploratory groups.

`docs/EVIDENCE_AWARE_AUDITING_FRAMEWORK.md` separates assigned mechanisms, actual behavior, deterministic public consequences, message interpretation, cross-event consistency, permissioned evidence, monitor claims, and latent intent. `docs/M3_MECHANISM_PROTOCOL_DRAFT.md` proposes a matched message-content counterfactual with a maximum of 96 local generations, but is explicitly not frozen and authorizes zero calls. Raw source replay confirms the attached 12 development cases: three historical F0 episodes (five messages) and nine prospective episodes (14 messages), for 12 episodes and 19 delivered messages total. All existing cases remain development/descriptive evidence only.

Do not call an agent or monitor, train a model, or start the proposed M3 experiment without a separate approval that freezes sample IDs, checkpoint/runtime, arm order, token matching, and a hard request budget.

## Sprint-ready baselines / M4 preparation — pre-sprint offline work (2026-10-20)

Branch `codex/sprint-ready-baselines-evidence-auditor-20261020` contains offline Sprint baseline and evidence-auditor preparation. It adds B0–B5 definitions, a blind allowlist compiler, scripted synthetic evidence controls, independent source replay, fieldwise scoring, a 280-row Monitor request plan, and M4's six SHA-selected payoff families and 24 group split. No Monitor or Agent call was made; the scripted B0/B1 table is software sanity evidence, not model performance. The prepared LLM cells remain `NOT_RUN`. The 280 Monitor and 264 M4 ceilings are plans only; this branch has no dispatcher or authorization. Historical ignored M1-100, M1-P0 and M2-V3 raw run directories are absent on this host and were not replayed.

An adversarial test found that the acceptance phrase matcher treated “I do not explicitly accept …” as acceptance. Both the independent reference and deterministic baseline now reject direct negation; the retained failed assertion confirms the fixed rule abstains as `uncertain` where a reply exists without explicit acceptance. This is a narrow keyword-level safeguard, not robust semantic understanding. A read-only artifact verifier reconstructs the control/reference corpus, 280 payload hashes, historical source hashes, and M4 scenario/split manifests. Targeted tests and the full repository suite are logged under `docs/results/sprint-baseline-v1/logs/`.

Current decision: GO for offline artifact integrity and code review; NO-GO for new Monitor calls, M4 Agent calls, M2 comparison, and latent-collusion claims. The highest-value next action is independent review of the source/data contracts and acceptance codebook. Do not begin inference from this preparation; require new explicit approval and a runtime-enforced budget first.
