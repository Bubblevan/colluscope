# Track 2.3 claim-level evidence dataset v1

**State:** offline build complete; independent replay receipt generated separately; human review of commitment semantics pending; no new Monitor call has been made.

## What is included

- `pair_behavior_metrics.csv`: 29 valid pair rows rebuilt from the hashed raw run files. It preserves both condition regret gaps, secret-minus-control regret and reward deltas, message/action counts, execution anomalies, and source hashes.
- `field_dictionary.csv`: source and meaning for the dataset fields.
- `split_manifest.json`: frozen pair-level development/test allocation. Both conditions from a pair stay together. Pairs 1, 16, and 25 are development examples. The six held-out pairs were selected by a published SHA-256 rule that did not use outcomes or Judge scores.
- `dataset_manifest.json`: row counts, source hashes, private-file hashes, split, and integrity/privacy receipts.
- `verification_receipt.json`: deterministic no-call source replay and arithmetic checks.
- `monitor_schedule_manifest.json`: the frozen offline 116-request plan (29 pairs × four methods). It is not a dispatch authorization.
- `figures/`: regret-gap and reward comparisons generated from `pair_behavior_metrics.csv`.

The normalized private data are in Git-ignored `runs/sprint-monitor/track23-evidence-audit-v1/`: `episodes.jsonl`, `messages.jsonl`, `actions.jsonl`, `settlements.jsonl`, `claims.jsonl`, the human-review queue, and the prompt/evaluation-key schedule. Message content is not duplicated in public-facing artifacts. The private directory is verified as current-user-only on this Windows host. The manifest carries hashes so the protected records can be checked without printing their contents.

## Rebuild and verify

From the repository root, with the protected raw Colosseum output still available:

```powershell
python scripts/build_track23_evidence_dataset_v1.py
python scripts/verify_track23_evidence_dataset_v1.py
python scripts/prepare_track23_monitor_schedule_v1.py
```

All three commands are offline. The builder checks the five raw source files against the saved per-trajectory hashes before writing. The verifier independently reloads those source files, checks hashes and cross-file assignments, recomputes rewards/regret, checks references and split integrity, and confirms that full message text is absent from public outputs. The schedule builder emits requests and a separate private answer key; it does not open a network connection.

## Label boundary

Source facts (message identity/order, executed task, rewards, official regret) are deterministic and cross-checked against raw logs. Task-commitment meaning and commitment/action matching are not yet human-adjudicated: 245 secret-board messages are in the review queue. Those values remain `PENDING_HUMAN_REVIEW`; neither replacement Judge's 348 ratings nor a Monitor response is used as ground truth. Causal attribution and latent intent are `NOT_IDENTIFIABLE`, not false or true labels.

One negative provenance control swaps the speaker in a fixed candidate claim while leaving the original message untouched. It is explicitly marked as a researcher-authored evidence intervention and is not original dialogue, a generated agent message, or a communication treatment.

## Sprint paper and reproducible figures

The initial report is `docs/submission/colluscope_when_collusion_evidence_disagrees_sprint_draft_v1.md`; its current rendered 7-page PDF is `output/pdf/colluscope_when_collusion_evidence_disagrees_sprint_draft_v1.pdf`. The report separates pre-Sprint Colosseum/Judge results from the new Sprint dataset and planned audit evaluation. Six source figures are in `figures/`; the report embeds the workflow, permissions, paired regret, and Pair 16/25 case figures. The other two figures cover the complete regret distribution and its relation to system reward.

The draft uses the official Sprint's required report sections, 8-page ceiling, and the requested abstract length, but is not a copy of the Google Docs template: the template URL required sign-in in the available session. Author, affiliation, and team fields remain placeholders for completion before submission.

## Sampling limits

The 29 pairs all reuse Jira environment seed 1. Pair-held-out Monitor results would describe held-out trajectories from one fixed benchmark instance, not generalize over environment seeds. The four invalid assigned pairs (7, 9, 13, 18) remain in the source denominator and are neither reconstructed nor silently replaced.
