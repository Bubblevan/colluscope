# Track 2.3 counterfactual delivery v2 — pilot result

## Decision

The pilot is **technically valid but scientifically inconclusive**. Stop the cycle at the pilot gate. Do not run the 40-context main stage or monitor stage under this registration.

The preregistered opportunity condition failed: in all eight contexts, Agent A's generated proposal exactly matched Agent B's initial ballot. There were **0/8 contexts** where the proposed allocation could distinguish message following from the recipient's already stated choice. PEER-versus-control adoption contrasts therefore cannot answer the causal question. This is not evidence that delivery has no effect.

## Pilot results

| Check | Result |
|---|---:|
| Assigned / started / completed API requests | 64 / 64 / 64 |
| Complete contexts | 8/8 |
| A/B visible-target initial ballots selecting the disclosed target | 8/8 |
| Valid final ballots | 32/32 |
| Independent settlement replay and message delivery/withholding checks | Pass |
| Raw request and response hashes | 64/64 each |
| Frozen-prompt reconstruction and response reparse | 64/64 each |
| Stable returned model/system fingerprint | 1 identity |
| A proposals differing from B's initial ballot | 0/8 |
| Pilot expansion gate | **NO_GO** |

The raw-trace audit passed all 64 assigned requests. The 8/8 visible-target control is evidence that the control instructions were followed in this pilot; it does not rescue the absent treatment opportunities.

## Cost and budget

DeepSeek returned 42,824 prompt tokens and 3,496 completion tokens. Its cache counters sum to 18,688 hit tokens and 24,136 miss tokens. At the preregistered peak rates, the cache-adjusted usage estimate is **$0.011548128**; the uncached peak-rate estimate is **$0.0170424**. These are rate-based estimates from provider token usage, not a vendor invoice.

The user's requested spend floor of more than $1 was not reached. No calls were added to increase spend. Since the pilot cannot support a positive or negative causal conclusion, the cost-floor condition for issuing either conclusion is not met.

## Interpretation

This pilot shows that the endpoint and frozen evidence pipeline completed the assigned requests, and that these eight sender/recipient prompts yielded the same initial allocation proposal and recipient ballot in every context. The shared-incentive/common-choice explanation remains sufficient. The experiment did not estimate whether delivery would change an action when the proposal differed from the recipient's baseline, and it did not establish a message-mediated joint consequence or collusion.

The valid conclusion is `INCONCLUSIVE`, not `SUPPORTED`, `REFUTED`, or `INVALID_EXPERIMENT`. The preregistered behavior-feasibility gate stopped expansion. The next useful work is an offline audit of the frozen context set to determine whether a new authorized design can produce baseline-divergent proposals without changing the causal question or using researcher-authored proposals as if they were spontaneous communication.

## Reproduction and evidence

- `pilot-summary.json` contains the corrected, sanitized pilot summary.
- `pilot-summary-initial-classification.json` preserves the first analysis output, whose classification was inconsistent with the preregistered ambiguity rule.
- `pilot-analysis-amendment-v1.md` documents both analysis-entry defects and the hash-checked correction.
- `model-request-ledger.json` contains 64 privacy-preserving request identifiers, terminal statuses, timestamps, and rate-based costs.
- `pilot-cost-summary.json` separates provider token counters, the cache-adjusted rate estimate, and the uncached peak estimate.
- Raw requests and responses remain local in the ACL-restricted, Git-ignored run directory.
