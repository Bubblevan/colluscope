# M2-V3 Decision

**Decision date:** 2026-10-19

## Decisions

- **M2-V2 formal evaluation: NO-GO.** None of the three frozen candidates passed the 10/10 compatibility gate. Preserve all 120 responses and their original strict statuses.
- **M2-V3 offline validity revision: GO.** The raw responses can be parsed and independently rescored field by field. The reclassification reproduced all 120 raw-output hashes and all source-derived reference labels without model calls.
- **M2-V3 model pilot: NO-GO pending a frozen request plan and separate model-call approval.** No new local or external model request was made.

## Evidence

The offline reclassification found 120/120 JSON/root/enum-valid responses, 43/120 frozen V2 strict-valid responses, and 18 strict-valid responses with at least one visibility-label mismatch. A direct Action-only counterexample is accepted by the frozen V2 validator despite visible ballots and public outcome. This proves the strict-valid count is not a sufficient measure of evidence reasoning.

The response-level score table also shows that the available-label exact matches vary sharply by field. These are repeated responses to one F1 episode and four prompt rounds, so they cannot establish population performance or a general Qwen capability limit. Message proposal, commitment, concordance, and sequence labels remain mechanical-codebook outputs; explicit acceptance is not scoreable from this corpus.

## Conditions before any pilot call

1. Freeze the task-specific prompts, answer schemas, reference codebook, eligible-row rule, scorer, split/sample manifest, and failure policy.
2. Freeze the exact model identifier. If using a DeepSeek API, freeze its endpoint and cost cap, and authorize transmission of the selected synthetic privileged-message evidence off-device.
3. Freeze the maximum logical request and HTTP attempt counts. The proposed diagnostic schedule is at most 15 requests per model (five ballot facts, five message-stream facts, and up to five concordance tasks); a two-model comparison is at most 30 generation requests with no retries.
4. Treat the five-episode sample as a one-shot interface diagnostic only. Do not use it to claim detector accuracy or to tune a prompt that will later be scored on the same cases.

Until those conditions are reviewed, the next allowed work is offline design and deterministic scorer implementation. No M2 monitor comparison, fine-tuning, or model calls are authorized by this decision.

## Reproduction

```powershell
python scripts/reclassify_m2_v2_preflight.py --out runs/m2-v3/offline-reclassification-20261019-rerun-04
python -m pytest tests/test_m2_v3_offline_scoring.py -q
```
