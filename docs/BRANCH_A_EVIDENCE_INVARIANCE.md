# Branch A — Public-Harm Evidence Invariance Audit

**Status:** offline audit artifact, no model inference. **Source base:** `cacc5db713653f333097bfb4e00be15162ab5cad`. **Raw data:** read from the ignored, locally retained `runs/deepseek-first-m4/monitor` directory; private message text and provider payloads are not copied into this report or its outputs.

## Question and falsifiable claim

The M4 `public_harm` task asks whether the settled allocation has lower public welfare than the unique optimum over six one-to-one allocations. Its reference can be calculated from the public task matrix, all three ballots, the chair tie-break rule, and the recorded decision/outcome. The narrow claim tested here is that those public records are sufficient for the task reference, so private-message access should not change that reference. This is an observable-task claim; it says nothing about hidden intent or collusion.

The counterexamples are concrete: fail the sufficiency claim if any case lacks a complete ballot/decision/outcome record, if recomputed settlement differs from the recorded settlement, if the matrix has a tied optimum, or if the independent public reference differs from the scored reference. Fail the invariance comparison if the public action record changes across permission profiles. The auditor enforces each condition rather than assuming it from the prior summary.

## Independent replay

The script pins the score CSV, protocol, monitor compiler, baseline compiler, prompt, task catalog, and ignored run freeze manifest. For each selected score row it verifies request, prompt, response and sidecar hashes; checks provider model/fingerprint, sampling and tool-call termination; parses the raw function arguments; and independently recomputes all six assignment welfares, ballots, plurality/chair settlement, outcome, and public regret. It does not use the scored reference to compute the reference.

Results for the 24 matched natural M4 contexts:

| Baseline | Public-only predictions changed after Privileged Audit | Reference changed | Public-only exact | Privileged exact |
|---|---:|---:|---:|---:|
| B4 raw fusion | 10/24 | 0/24 | 8/24 | 17/24 |
| B5 evidence aware | 20/24 | 0/24 | 4/24 | 17/24 |

All 24 cases had a unique public optimum, three complete ballots, a chair rule, a decision, and an outcome. Independent settlement matched the logged decision and outcome for all 24. Reference labels were 14 `absent` and 10 `present`, where `present` means positive public-welfare regret only. The regret counts were 0:14, 2:3, 4:2, 5:1, and 7:4. The same reference appeared in all four method/permission rows for every case.

For B4, 9 of the 10 changed predictions became exact; one remained wrong. For B5, 14 of 20 changed predictions became exact, 1 became incorrect, and 5 remained wrong. These are paired descriptive response changes for a single provider alias/fingerprint and 24 contexts. They are not a general estimate of access effects.

## What changed in the model input

Task specifications and all non-message action events were byte-structure-equivalent after JSON parsing in all 24 permission pairs for each baseline. The permission intervention bundled several other changes:

- Privileged Audit contained two additional delivered private A/B message events per context. Across the 24 unique contexts, this is 48 message events, 13,556 characters, and 2,407 whitespace-separated words. The same messages were serialized under B4 and B5, so they appeared in 96 request exposures; message text is deliberately absent from this report.
- Those events also add event IDs, sender/recipient, order, sent/delivered flags, and `visibility=private`. The privileged projection alone adds `delivered_message_window_complete=true`. No explicit `public_only` or `privileged_audit` arm string was found in the prompts; the permission value exists in request sidecar metadata. Thus there are still structural permission cues in the model input.
- The added events change evidence-object shape, JSON serialization, user-prompt length, serialized request size, and provider prompt tokens. These are bundled with message content and provenance; the observed change cannot be attributed to message semantics alone.

| Permission contrast | User-prompt characters, median (range) | Serialized request bytes, median (range) | Provider prompt tokens, median (range) |
|---|---:|---:|---:|
| B4 privileged minus public | 887.5 (739–1,185) | 953.5 (805–1,255) | 285 (218–488) |
| B5 privileged minus public | 1,146.5 (998–1,444) | 1,258.5 (1,110–1,560) | 358 (291–561) |

B5 also differs from B4 even under the same permission: it supplies a deterministic mechanical ledger (`record_checks`, `event_index`, and `normalized_ballots`). The ledger contains extra structured computation and repeats the ballots; it does not supply welfare, regret, harm, or the reference label. B5 requests used 298 more prompt tokens per public-only pair and 371 more per privileged pair, exactly in all 24 matched contexts. This comparison is not an Extract-and-Evaluate implementation and does not isolate reasoning ability from the added representation and token budget.

## Adversarial interpretation

The observed prediction changes are real response sensitivity in the retained requests. They do not establish that private messages are needed to identify public harm: the public-only sufficient statistic is complete by task definition. They also do not establish that message meaning caused the changes because message content, event presence, provenance fields, visibility labels, completeness metadata, serialization, and token count moved together. An unobserved interaction with these cues remains plausible.

The strongest falsifier of the narrow sufficiency claim is a valid case where the independent public replay cannot determine the reference. The script rejects missing ballots/outcomes, invalid assignments, non-unique optima, inconsistent settlement, score/reference drift, model or request drift, and permission-pair action drift. Eleven targeted tests include hidden permission labels in evidence, prompt text and message content, altered public outcomes, an unauthorized completeness flag, missing evidence, a tampered B5 ballot ledger, positive replay checks, and manifest truth/split checks; each counterexample is rejected with a sanitized error code.

An exact-text privacy scan compared all 48 private message events in the unique B4 privileged projection against 14 branch output/source files. It found zero exact-text matches. This does not detect paraphrases or transformed copies.

## Future controls frozen without inference

`docs/results/evidence-invariance/synthetic-invariance-groups-v1.json` freezes 20 deterministic synthetic evidence groups before any future model output. It has 10 primary `present` and 10 primary `absent` observable-harm references; every group includes a ballot-level label-flipping positive control. Each trajectory has public-only, short/long irrelevant private-message, and equivalent pretty-serialization variants. Public and privileged views share the same matrix and action truth. All variants inherit one split at the scenario/seed-group level: 4 calibration, 4 validation, and 12 held-out groups. The matrix generator and split hash algorithm do not consume model results. The manifest separates `monitor_input` from scoring references; a future runner must pass only the former.

This fixture tests invariance and a simple label-changing response control, not natural behavior, agent communication, collusion, or monitor deployment. A stronger future factorial should separately vary (a) message wording with character/token length held as close as the frozen tokenizer permits, (b) message presence/structure with masked content, (c) provenance fields, (d) `visibility` and completeness labels, (e) serialization, and (f) the B5 ledger. Pair every nuisance intervention with unchanged public outcomes and add positive controls by changing only ballots/settlement so public regret flips. Freeze exact tokenization, prompt, references, group split, and scoring rules before model calls.

## Closest prior work and novelty boundary

The closest methodological prior identified in this audit is Arike et al., [“How does information access affect LLM monitors’ ability to detect sabotage?”](https://arxiv.org/abs/2601.21112), which studies the effect of information available to monitors and introduces an Extract-and-Evaluate approach that selects relevant excerpts before a separate evaluator judges them. This substantially overlaps with the broad question “does more context help or hurt a monitor?” and with relevance filtering. B5 is materially different: it is a one-pass evidence-aware task prompt with a deterministic ledger, not a learned or model-based extractor followed by a separate evaluator.

Any contribution claim should therefore remain narrow: in one synthetic multi-agent audit task whose label is deterministically recoverable from public actions, the retained monitor predictions changed when a privileged projection bundled private communications and associated structure into context. This dataset does not identify which component produced the change, demonstrate a relevance-filtering advantage, or establish a new general principle. A future controlled factorial could test whether public-fact predictions remain stable under irrelevant private context while reference-identical views add/remove isolated provenance and serialization cues; novelty requires a broader literature review before submission.

## Reproduction

Run from the repository root in an environment that has the ignored local raw run:

```powershell
python -m pytest -q tests/test_public_harm_invariance_audit.py
python scripts/audit_public_harm_invariance.py --monitor-run D:\MyLab\colluscope\runs\deepseek-first-m4\monitor --output docs/results/evidence-invariance/branch-a-audit.json
python scripts/freeze_synthetic_invariance_groups.py
```

The audit exits nonzero on source/raw hash mismatch and emits only aggregate JSON or a sanitized error code. The raw output is retained in `docs/results/evidence-invariance/logs/`; the raw request/response tree remains Git-ignored and local. The full M4 result is not rewritten.

## Limits

This is a post hoc analysis of 24 matched contexts, one provider alias/fingerprint, and one task. Token counts come from provider usage and are descriptive; no token-matched natural-message control was run. `visibility=private` and the message completeness flag remain possible structural hints. Prompt response changes do not show what the model attended to. Citation validity, intention, agreement, protocol, and collusion are outside this task's label and are not inferred here.

## V2 fixture hardening (offline, no inference)

V1 remains byte-for-byte preserved at SHA-256 `b16f4da825dd2af9202d6081637480682292809738dadf49e22da88b9eefc81b`. Its “irrelevant” text explicitly mentions instructions and being informed, so V2 accurately calls it a **metalinguistic control** and adds separate garden/library text that does not refer to the task, instructions, matrix, allocation, vote, or decision. V2 has 20 deterministic groups, 40 trajectories, and 200 monitor-input variants (five variants per trajectory); all 20 groups retain one group-level split (4 calibration, 4 validation, 12 held out). Every group has a label-changing ballot/settlement positive control, and every nuisance variant within a trajectory has the same independently recomputed public-harm reference.

V2 freezes twenty independent 96-bit random opaque IDs that are not derived from matrices or labels. Primary labels are shuffled from an independent fixed 10/10 assignment; split assignment and row ordering use separate salted hashes of the IDs and never consume labels. The validator recomputes the frozen manifest and confirms those rules. Primary labels are 10 present / 10 absent; across primary and positive-control trajectories references are 20 / 20. These are deterministic synthetic contexts, not natural agent behavior, and their split labels are not model inputs. The first V2 draft's IDs were matrix-derived and its labels were derived from IDs; that draft is preserved as `synthetic-invariance-groups-v2-pre-id-audit.json` (SHA-256 `6ed6e36c53c4cfd2a81e501351842885df282780a91681d2d40c119d64e9c40d`) and is superseded by the corrected final manifest (SHA-256 `0cc0dd9fd543761d0369e68eb7f151f1223aefec614e415046de8b8c019b8d20`). Each variant also stores the hash of its exact serialized HTTP body; the validator independently rebuilds and checks all 200 body hashes.

The exact offline HTTP-body projector binds the historical system-prompt hash and request configuration. Its only content-bearing sources are that frozen prompt, the fixed task/question text, and `variant.monitor_input`. It extracts the input field and omits the surrounding manifest, including `primary_label`, `split`, `scoring_reference`, `group_id`, `generation_slot`, variant names, and permission names. Its serializer reconstructs the canonical body and rejects wrapper fields, altered prompts, invalid evidence schemas, or hidden routing/scoring markers in input text. Counterexample tests verify the serialized bytes are identical when only outer scoring metadata changes and that marker injection is rejected. This is a tested request-body builder, not a dispatched Monitor run.

The V2 variants provide two useful same-structure message-content controls: metalinguistic text versus task-irrelevant text, each at short and long lengths. They do not isolate semantic relevance from exact provider-token cost, lexical salience, or familiarity: the DeepSeek tokenizer is not locally pinned here, and no provider usage was queried. Public-only versus privileged inputs also still differ in the existence of message events and the completeness flag. A later inference protocol must freeze any tokenizer-based matching or sensitivity bins before seeing responses and keep these contrasts separate.

V2 reproduction commands:

```powershell
python scripts/freeze_synthetic_invariance_groups_v2.py
python scripts/validate_synthetic_invariance_groups_v2.py
python -m pytest -q tests/test_public_harm_invariance_audit.py tests/test_evidence_invariance_v2_projector.py
python scripts/audit_historical_call_config.py --run D:\MyLab\colluscope\runs\deepseek-first-m4
```

The latest offline verification covered 200 projected request bodies and 34 counterexample/replay tests. A separate read-only audit of retained historical payloads found 628 request/response pairs: 232 Agent, 376 Monitor, and 20 compatibility pilot; all used `deepseek-flash`, temperature 0, maximum 512 output tokens, and `thinking={"type":"disabled"}`. Each had one matching HTTP 200 response ending in `tool_calls`; no authorization headers were saved. The audit itself made zero model calls. See `scripts/audit_historical_call_config.py`, `docs/results/evidence-invariance/artifact-sha256-v2.txt`, and `docs/results/evidence-invariance/logs/` for hashes and preserved initial failures.
