# M1 Package Replication v3 — Exact Scope Awaiting Approval (Revision 2)

**Status:** review snapshot only; not registered; no model generation authorized.  
**Candidate experiment:** `m1-reward-chat-24group-replication-v1`.  
**This request supersedes the earlier unapproved request from 2026-10-21.** No M1 approval is recorded.

## Hash-pinned review package

- Candidate snapshot: `research/drafts/m1-package-replication-v3-review-manifest-r2-20261021.json`, SHA-256 `a0b401c06893fd4435ff4af72de36a5e023e8c51a02d0cf1de56376c7bfa1d91`.
- Snapshot verification receipt: `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-review-manifest-verification-r2-20261021.json`, SHA-256 `46b9a939ccf337668ddaf8970f73c20829c55435b59c6dd3b91a0e78a14a54b0`. The verifier matched all 23 runtime inputs and 24 supporting artifacts.
- Offline runner receipt: `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-check-only-after-ballot-review.json`, SHA-256 `4e0b80e7b643529b9937c7c3c666b7bdf72de6c756466f77dc00a001141f1f79`.
- Historical action-level review and proposed analysis amendment: `docs/M1_PACKAGE_REPLICATION_V3_BALLOT_DECOMPOSITION_REVIEW_20261021.md` and `docs/M1_PACKAGE_REPLICATION_V3_BALLOT_OUTCOME_AMENDMENT_20261021.md`.

The manifests remain review snapshots, not registration or authorization. No live listener, server identity, tokenizer parity, or new behavior was checked in this offline review.

## Requested execution scope

Authorize one prospective, local-only run of the private-target-reward × chat-stage package across 24 frozen distinct payoff matrices, with all five M1 conditions within each matched group. The original prompts, action schema, task, incentive amounts, model, sampling parameters, matrix schedule, seed mapping, and communication order remain frozen.

- Assigned denominator: 120 episodes / 24 matched groups. All failures and invalid outputs remain assigned; no retries, replacements, or resampling.
- Generation ceiling: 456 local Qwen generations (360 ballots + 96 message decisions).
- Physical request ceiling: 480 HTTP attempts, including at most 24 local identity requests.
- Endpoint: `http://127.0.0.1:8081/v1` only. No proxy, external provider, or fallback.
- Model: `Qwen3-8B-Q4_K_M.gguf`, SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- Runtime: llama.cpp b10068, commit `571d0d540`, expected binary SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`.
- External calls and external cost: 0 calls / USD $0.
- Proposed expiry: `2026-10-26T12:00:00Z`.

Raw requests, responses, private observations, and failures remain local in a Git-ignored ACL-restricted run directory. No private text or ballots are sent to DeepSeek or another provider.

## Outcomes and limits

The primary outcome remains independently recomputed environment selection of the target allocation and its frozen finite-set four-cell difference-in-differences. The attached pre-registration amendment additionally requires separate A/B/C target-ballot indicators, target-vote counts, chair identity, one-vote chair-tie selection, and an A/B joint-target-ballot interaction as a descriptive secondary measure. These keep agent actions distinct from settlement; neither result identifies message causality, collusion, agreement, or intent. A/B share advance knowledge of the same target, and chat adds a message-decision stage.

## Required gates and stop rules

No live command begins until the exact amendment is incorporated into a schema-v2 preregistration, a fresh immutable approval batch names this experiment and exact ceilings, and current gates revalidate all frozen hashes, model/server identity, loopback listener ownership, tokenizer/template parity, authorization, and restricted output storage. Stop immediately on any identity, privacy, hash, budget, listener, or authorization failure. Invalid output and transport failures remain in the assigned denominator and are never repaired or resampled.

After approval and registration, the already-gated entry point is:

```powershell
python scripts/run_m1_package_replication_v3.py --live --approval-id <new-M1-approval-id> --out runs/m1_100/m1-package-replication-v3/run-<unique-id>
```

Approval is requested for this exact local Qwen scope only. The earlier DeepSeek approvals cover closed, unrelated experiments and cannot be reused.
