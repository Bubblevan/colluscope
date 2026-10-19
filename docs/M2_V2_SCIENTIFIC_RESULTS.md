# M2-V2 Scientific Results and Manuscript Draft

## Methods

We investigated whether a local Qwen3-8B monitor could return a permission-bounded, source-cited audit record over the unchanged 100-episode M1 corpus. The five views were text-only, action-only, raw fusion, structured evidence, and structured evidence without derived findings. Each view was evaluated under Public-only and Privileged Audit permissions. The output contract retained eight observable claim categories, required exact citations to visible event IDs, required `latent_intent=unknown`, and rejected invalid view/permission combinations. No latent-collusion reference label was constructed.

Before any formal evaluation, the protocol required one candidate to pass all ten fixed F1 compatibility cells (five views × two permissions). The same preselected F1 episode was used for each cell; three candidates were run in fixed order per round. Following the initial failure, three separately versioned prompt/configuration repairs were authorized, each with an unchanged ten-of-ten gate and a maximum of 30 requests. Raw responses were never repaired, resampled, or reclassified. The checkpoint, llama.cpp runtime, tokenizer, chat template, endpoint, sampling, parser, view definitions, and evidence permissions were held fixed across the repairs.

Independently of the monitor, we replayed raw ballots under the frozen plurality/chair tie-break rule and recomputed welfare from each scenario payoff matrix. We then generated view-permission reference facts from T/B/Public E. This is a deterministic evidence-availability analysis, not a monitor prediction or a latent-collusion baseline. Private text remains local.

## Results

The four 30-request gates returned 120 model responses from 120 local HTTP attempts, with no retries or external calls. All 120 responses parsed as JSON, had the expected root shape and core enum values, and ended with `finish_reason=stop`. Strict validity was lower because the independent checker also enforced branch-specific view rules, abstentions, and evidence citations.

| Round | C1 | C2 | C3 | Valid across round |
|---|---:|---:|---:|---:|
| Initial | 1/10 | 1/10 | 0/10 | 2/30 |
| Repair 01 | 3/10 | 3/10 | 3/10 | 9/30 |
| Repair 02 | 6/10 | 6/10 | 5/10 | 17/30 |
| Repair 03 | 6/10 | 6/10 | 3/10 | 15/30 |

No candidate passed 10/10. Repair-03's first-rejection classes were view/permission mismatch (8/30), other contract violations (5/30), evidence-reference violations (2/30), and contract-valid output (15/30). In the two full candidates, all ten matched assistant-text pairs were identical; this is an observed property of the recorded outputs, but the effect of response-format and decoding interactions is unidentified.

The deterministic replay covered all 100 source episodes and all 1,000 view-permission rows. It found 22/100 public-harm outcomes and 34/100 episodes with ballot disagreement in views where actions are visible. Privileged message-bearing evidence includes at least one delivered message in 12/100 episodes; the frozen literal complete-mapping and ballot-concordance rule supports an observable sequence in 12/100 episodes when both actions and messages are visible. The 12 episodes are evidence sequences, not agreements or collusion labels. The literal commitment-marker rule found 0/100 episodes, and the environment has no post-delivery acceptance turn; this does not establish that no latent agreement existed.

| Evidence projection (100 episodes each) | Public harm available | Ballot disagreement available | Delivered-message episode visible | Literal mapping episode visible | Sequence predicate supported |
|---|---:|---:|---:|---:|---:|
| Action-only, either permission | 22 | 34 | 0 | 0 | 0 |
| Raw fusion, Public-only | 22 | 34 | 0 | 0 | 0 |
| Raw fusion, Privileged Audit | 22 | 34 | 12 | 12 | 12 |
| Structured evidence, Public-only | 22 | 34 | 0 | 0 | 0 |
| Structured evidence, Privileged Audit | 22 | 34 | 12 | 12 | 12 |
| Structured without findings, Public-only | 22 | 34 | 0 | 0 | 0 |
| Structured without findings, Privileged Audit | 22 | 34 | 12 | 12 | 12 |
| Text-only, Public-only | Not visible | Not visible | 0 | 0 | 0 |
| Text-only, Privileged Audit | Not visible | Not visible | 12 | 12 | 0 |

The source contains 19 stale stored `harmful_outcome` flags that disagree with independent replay. Those fields were not used as labels. The full view-by-partition counts and all eight claim-value counts are available in the CSV tables linked from the execution evidence.

## Interpretation

The experiment establishes a local interface-validity failure under the frozen candidate family and a bounded repair allowance. The key failure was not JSON syntax: it was correct application of the claim-to-view mapping, abstention semantics, and citation contract. The run therefore cannot estimate observable-claim accuracy, unsupported-sequence rate, abstention quality, false accusations, permission effects, or differences among evidence views. There were no valid formal monitor predictions because formal inference never began.

The deterministic source replay demonstrates that the corpus contains both observable positive facts and views where those facts are unavailable. It also provides auditable reference-label distributions for a future implementation. It cannot show that a monitor can extract those facts, and it cannot substitute for model scoring.

## Limitations

The compatibility screen uses only one F1 episode, selected by a frozen source rule, so it does not estimate robustness across episodes or scenario families. Even the count of 43 strict-valid responses across all rounds is not a performance rate because the prompt/configuration changed at each repair. The same Qwen3 family generated the original agent traces and the monitor probes, leaving potential style and self-evaluation bias for any future run. F2/F3 had prior exposure in the earlier research workflow and would remain exploratory. The fixed M1 environment has shared targets and incentives, simultaneous message generation, no post-delivery response turn, repeated seeds within matched groups, and nineteen source harm-flag discrepancies.

Observable message delivery, a literal proposal, ballot concordance, public harm, common incentives, and welfare loss do not identify intent. A future paper must label only the directly observable sequence facts and retain abstention where evidence is insufficient. It must not report latent-collusion accuracy or false-positive rates without an independently defensible gold standard.
