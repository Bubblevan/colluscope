# Autoresearch Current State — M1 v3 Raw-Response Audit (2026-10-21)

This addendum supersedes prior M1 v3 approval-request snapshots. Historical M0–M4 runs, the M1-100 T/B source records, the base M1 v3 candidate protocol/draft, and earlier review receipts remain preserved.

## What changed

A v1 action decomposition computed plurality from stored `parsed_assignment` fields. The limitation was found during adversarial review and preserved. Version 2 reparses all 225 raw ballot texts under the frozen ballot schema, confirms 225/225 assignments match the stored parser field, and independently recomputes all 75/75 settlements. The action-level counts are unchanged: 9/15 private-reward-plus-chat target settlements had both A/B target ballots, the other factorial cells had 0/15 joint ballots or target settlements, C was ballot-identical across four cells in 15/15 groups, and no target result came from a one-vote chair tie-break. These facts apply only to the fixed historical corpus.

The M1 v3 candidate still uses target settlement as the primary package outcome. The pre-registration amendment adds separate actor ballots and chair-tie decomposition, plus a descriptive A/B joint-ballot interaction. The treatment, matrix schedule, model, prompts, 120-episode denominator, and 456-generation / 480-HTTP ceilings are unchanged.

## Current authorization boundary

The current review snapshot is revision 3 at `research/drafts/m1-package-replication-v3-review-manifest-r3-20261021.json`, with verification receipt `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-review-manifest-verification-r3-20261021.json`. Both remain non-authorizing. The current exact request is `docs/M1_PACKAGE_REPLICATION_AUTHORIZATION_REQUEST_20261021_R3.md`.

No M1-specific approval or formal registration exists. No M1 identity request, Agent generation, or Monitor inference occurred. Prior DeepSeek approvals remain consumed by separate closed cycles.

## Next action

Await explicit approval of the exact R3 local-Qwen scope. Then create a new immutable authorization batch and schema-v2 preregistration incorporating the ballot-outcome amendment. The gated runtime must recheck live model, server, endpoint, listener, tokenizer/template, and storage identity before it generates any Agent action.
