# Shared-target message content v1: replay and interpretation

**Date:** 2026-10-21  
**Evidence class:** real LLM behavior  
**Scientific outcome:** `SUPPORTED` for the preregistered finite message-response pattern

## Question and scope

With the target hidden and the same shared-target reward held fixed, does a recipient ballot follow the allocation mapping stated by a controlled peer message? This study tests a recipient response to scripted message content. It does not test spontaneous sender behavior, bargaining, collusion intent, or population behavior.

## Design and integrity

The frozen schedule assigned 24 physical requests: three fixed allocation contexts, four arms, and two exact-prompt repeats per arm. The arms were visible target/no message, hidden target/no message, hidden target/true-target message, and hidden target/counterfactual-decoy message. Each row was attempted once. The offline preflight recorded that the true and decoy prompts had equal token counts and differed only in the task mapping in the message. The target, payoff matrix, active role, and shared reward were held constant within each context.

The saved outputs were replayed with the frozen ballot contract. All 24 assigned requests were attempted, completed, and assessable; there were no failed, invalid, or unattempted rows, no repeat disagreements, and no replay integrity errors. The attempt-ID hashes in the sanitized ledger match the 24 unique started requests. The official `deepseek-flash` alias reported fingerprint `e72d3c7f663d3e1383b00b3884cb4501`. The recorded execution took 23.047 seconds and cost $0.0060696, within the fresh 24-call / $0.05 authorization. No retries or replacements occurred.

## Results

| Frozen arm | Target ballots | Decoy ballots | Mapping-following ballots |
| --- | ---: | ---: | ---: |
| Visible target, no message | 6/6 | 0/6 | Not applicable |
| Hidden target, no message | 0/6 | 0/6 | Not applicable |
| Hidden target, true-target message | 6/6 | 0/6 | 6/6 |
| Hidden target, counterfactual-decoy message | 0/6 | 6/6 | 6/6 |

Each of the three fixed contexts showed the same pattern: 2/2 target choices when the target was visible, 0/2 target or decoy choices with the target hidden and no message, 2/2 target choices under the true mapping, and 2/2 decoy choices under the permuted message. All repeated ballots within an arm agreed.

## Interpretation

This meets the preregistered positive criterion in all three contexts and passes the visible-target control. In these frozen prompts, changing only the mapping named in a scripted peer message changed the recipient's allocation ballot, including toward a legal decoy, while the actual hidden reward target remained fixed. Independent convergence under the shared incentive alone does not explain this message-arm pattern.

The supported claim is finite and task-specific: this provider-served model alias responded to the controlled mapping in the message. The repeats are response-stability observations, not independent model instances or population samples. Because a human-scripted message supplied the recommendation, the experiment does not distinguish peer-specific social influence from generic instruction or advice following. It provides no evidence that an autonomous sender would produce the message, that the agents formed an agreement, or that the behavior reflects collusion intent.

## Adversarial limits

- The intervention establishes sensitivity to the mapping stated in the message, but not to the social identity or status of its source.
- Only three preselected contexts and one provider-served alias were studied; repeats do not increase the number of distinct contexts.
- A reported alias and fingerprint identify this run, not immutable model weights or future serving behavior.
- A ballot matching a false mapping demonstrates content sensitivity, not a harmful outcome or deceptive intent.
- The monitor, spontaneous sender, and interactive multi-agent behavior were not evaluated.

## Highest-value next experiment

Test whether the response depends on the **peer source** or follows any matched recommendation. In a new, separately authorized study, use the same hidden-target task in three frozen contexts and cross the target versus near-equal-score decoy mapping with two source frames: a peer proposal and a non-social task-aide recommendation containing the same allocation. Include a hidden-target/no-message baseline and two exact-prompt repeats per cell (30 physical requests). Freeze exact wording, token parity, source framing, and assignment order before any call.

If peer and task-aide recommendations both move ballots to either mapping relative to no message, the current effect is better described as general recommendation following. If the peer-framed message produces a larger or more reliable mapping response than the content-matched task-aide cue across contexts, that would support a narrower peer-source effect. Neither result alone would establish spontaneous collusion. This proposal requires a fresh preregistration and authorization and has not been run.

## Reproduction

The sanitized context table, analysis, and request ledger are in this directory. To reparse the protected local responses without making model calls, use:

```powershell
$env:TEMP = (Resolve-Path tmp).Path
$env:TMP = $env:TEMP
python scripts/run_shared_target_message_content_v1.py --analyze
```

Raw requests and responses remain in the Git-ignored local run directory and are not included in the public sanitized results.
