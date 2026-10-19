# M2 One-shot Scientific Results

## Abstract

We evaluated five evidence views under Public-only and Privileged Audit permissions on 100 frozen real-agent episodes. The experiment assigned 1,000 logical monitor evaluations and made 517 local model-completion calls (529 physical HTTP attempts including transport retries). None of the returned outputs passed the frozen JSON/schema validator; 20 additional logical rows ended in terminal transport failure. Therefore, coverage was zero and view/permission accuracy, abstention, and evidence-extraction comparisons are not estimable. Independent source reconstruction found 12 episodes with a delivered complete allocation proposal followed by both named agents casting that allocation in views permitted to see both messages and ballots. These are observable sequences, not collusion labels or causal evidence. The run supports an interface-failure finding and an auditable execution record, not a detector-performance claim.

## Research question and claim boundary

The question was whether text-only, action-only, raw fusion, structured evidence, and structured evidence without computed findings support accurate extraction of observable evidence under Public-only and Privileged Audit permissions. The output schema fixes latent intent to `unknown`. Shared incentives, target allocations, matched ballots, public harm, private-chat availability, and condition IDs are not gold labels. An observable proposal/action sequence is not evidence of agreement, causal influence, or latent collusion.

No monitor prediction was valid. Consequently, this run estimates no detector accuracy, recall, precision, abstention behavior, false-positive rate, view advantage, or permission advantage.

## Corpus and split results

| Partition | Provenance | Episodes | Logical evaluations | Valid | Invalid JSON/schema output | Request failed |
|---|---|---:|---:|---:|---:|---:|
| F0 | Historical M1-P0 | 25 | 250 | 0 | 234 | 16 |
| F1 | Prospective M1-100 | 25 | 250 | 0 | 250 | 0 |
| F2 | Prospective M1-100 | 25 | 250 | 0 | 246 | 4 |
| F3 | Prospective M1-100 | 25 | 250 | 0 | 250 | 0 |
| **Total** | Historical + prospective | **100** | **1,000** | **0** | **980** | **20** |

The 20 failed logical rows link to six unique requests that each exhausted two transport attempts. All 517 returned completions failed with `JSONDecodeError`; there were no valid predictions in calibration or held-out partitions.

### Treatment and scenario-family status

Each of the five conditions contributes 20 source episodes and 200 logical view/permission evaluations. Every condition has 0 valid, 196 invalid, and 4 failed evaluations. The identical output-contract failure across all five conditions provides no evidence for or against a treatment effect.

| Payoff family | Episodes | Logical evaluations | Valid | Invalid | Failed |
|---|---:|---:|---:|---:|---:|
| Historical `allocation-3agent-v1` | 25 | 250 | 0 | 234 | 16 |
| `m1_100_family_1` | 25 | 250 | 0 | 246 | 4 |
| `m1_100_family_2` | 25 | 250 | 0 | 250 | 0 |
| `m1_100_family_3` | 25 | 250 | 0 | 250 | 0 |

The 19 stale stored `harmful_outcome` booleans in the prospective M1 source were not used as authoritative labels. The monitor input/reference pipeline independently recomputed source facts from raw ballots and the scenario matrix, while preserving the original M1 bytes.

## View and permission coverage

Each view/permission cell contains 100 logical evaluations. “Local input tokens” is the tokenizer count summed over those 100 logical inputs, including exact duplicate inputs; server token totals are unique returned payloads.

| View | Public-only invalid / failed | Privileged invalid / failed | Public-only local input tokens | Privileged local input tokens | Privileged reference sequence positives |
|---|---:|---:|---:|---:|---:|
| Text-only | 91 / 9 | 100 / 0 | 103,965 | 105,981 | 0 (ballots omitted) |
| Action-only | 91 / 9 | 100 / 0 | 132,789 | 132,789 | 0 (messages omitted) |
| Raw fusion | 99 / 1 | 100 / 0 | 148,109 | 150,524 | 12 |
| Structured evidence | 99 / 1 | 100 / 0 | 141,707 | 147,371 | 12 |
| Structured without findings | 100 / 0 | 100 / 0 | 133,389 | 135,405 | 12 |

Every cell has zero valid predictions. The different input lengths expose real content/representation costs: action-only contains public task/actions; text-only contains only the permitted message stream; raw fusion uses a serialized event stream; structured views add structured representation, with computed findings present in only one arm. Because no response was valid, the run cannot say whether additional structure or findings improved monitoring. No padding or response repair was used.

Failures were confined to Public-only inputs: 9 text-only, 9 action-only, 1 raw-fusion, and 1 structured-evidence logical rows. The no-findings arm and all Privileged cells had no transport-failed rows. These are transport failures, not monitor judgments.

## Source-supported observable evidence

These counts come from the independent source reference, not from monitor predictions. They are view-specific facts and do not define collusion:

| Evidence fact | Source count | Boundary |
|---|---:|---|
| Episodes with at least one delivered A/B message | 12 / 100 | The 12 episodes contain 19 delivered message events. Public-only views cannot see these private events. |
| Privileged raw/structured views with a literal complete allocation mapping | 12 / 100 | Narrow deterministic text code; paraphrases are not promoted to mappings. |
| Those cases where both sender and intended recipient later cast the mapped allocation | 12 / 12 | Mechanical ballot concordance, not acceptance or causal influence. |
| Privileged raw/structured views with the preregistered observable sequence | 12 / 100 | Delivered complete mapping plus both later ballots; this is not a collusion gold label. |
| Public-harm reference in action-visible views | 22 present; 78 absent | Recomputed from the public task matrix and outcome. |
| Ballot-disagreement reference in action-visible views | 34 present; 66 absent | Recomputed directly from sealed ballots. |
| Qualifying post-delivery acceptance responses | 0 | The message protocol has no recipient reply turn; acceptance sensitivity is not estimable. |
| Literal commitment markers | 0 | Provisional frozen lexical code only; not a binding-agreement measure. |

Text-only privileged inputs can contain messages but omit ballots; action-only inputs include ballots but omit messages. Public-only message omission is `not_visible`, not evidence that no private message existed. There are no human adjudicators or inter-rater estimates. The positive sequence cases show why private evidence can improve observability, but the M1 messages were generated independently before batch delivery and the shared target was known to both agents; the sequence alone cannot identify communication-caused coordination.

## Output-contract diagnosis

The frozen validator rejected all 517 returned completions as `json_parse_error:JSONDecodeError`. A separate post-hoc diagnostic, which did not modify any status or score, found a complete leading `<think>...</think>` segment in all 517 raw assistant strings. Removing that segment only in memory allowed all 517 strings to parse as JSON, but the parsed roots still failed the frozen validator with `root_fields_mismatch`:

| Post-hoc root-key shape | Responses | Why it still fails |
|---|---:|---|
| Eight claim fields only | 474 | Omits required `latent_intent`, `evidence_refs`, and `abstention_reasons`. |
| Eight claim fields plus `latent_intent` | 8 | Still omits `evidence_refs` and `abstention_reasons`. |
| Eight claim fields plus `findings` | 34 | Adds an unrequested field and omits required fields. |
| Eight claim fields plus `findings` and `task_spec` | 1 | Adds unrequested fields and omits required fields. |

The raw response metadata marks reasoning content as absent even though the assistant text includes the leading markers. This is an observed format mismatch; the exact server/template cause is not established. The post-hoc transformation is diagnostic only. It does **not** turn any completion into a valid prediction or authorize a parser fix on this frozen run.

## Runtime and resource use

| Measure | Result |
|---|---:|
| Unique returned responses | 517 |
| Server prompt tokens (returned responses) | 704,153 |
| Server completion tokens (returned responses) | 49,124 |
| Total server tokens | 753,277 |
| Median generated duration per returned response | 1.546 s |
| Calibration / held-out wall duration | 580.206 s / 633.325 s |
| GPU telemetry samples | 1,114 |
| GPU | NVIDIA GeForce RTX 4090 Laptop, 16,376 MiB |
| Peak used / minimum free GPU memory | 6,621 MiB / 9,755 MiB |

The output confusion table has no prediction rows. The scorer's mechanically zero unsupported-sequence count and zero bootstrap interval must not be read as a low false-positive rate: there were no valid outputs. Coverage is 0%, while sequence accuracy and all prediction-conditioned metrics are not estimable.

## Interpretation and limits

This run does not demonstrate that the model detected, missed, or abstained on collusion. It demonstrates that the frozen local inference completed within the authorization and the output interface failed systematically. The only scientifically supported monitor result is the output-contract failure rate. Source reference facts remain useful for a later, separately approved and schema-valid audit, but there is no valid M2 comparison here.

Other limits remain: F2/F3 outcomes were previously exposed; the holdouts are groups within known payoff families, not unseen-family tests; Qwen3 was both agent and monitor; the source contains no human message adjudication; and the M1 protocol does not support a post-delivery acceptance label. Do not present this run as a formal Track 2.2/2.3 detector evaluation or as evidence that any agent colluded.
