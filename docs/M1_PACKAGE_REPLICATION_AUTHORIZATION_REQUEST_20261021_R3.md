# M1 Package Replication v3 — Exact Scope Awaiting Approval (Revision 3)

**Status:** review snapshot only; not registered; no model generation authorized.  
**Candidate experiment:** `m1-reward-chat-24group-replication-v1`.  
**This request supersedes the unapproved R1 and R2 requests.** No M1-specific approval is recorded.

## Hash-pinned review package

- Candidate snapshot: `research/drafts/m1-package-replication-v3-review-manifest-r3-20261021.json`, SHA-256 `7f37e3a66ef54e4ace03a6f20bb4349bea1b2aff035b7f5dae2074c85bc44ee9`.
- Snapshot verifier receipt: `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-review-manifest-verification-r3-20261021.json`, SHA-256 `95b71fa45d8531b9b9def39d3f20b103b9e93005ac350e0ca283586df63ed037`. It matched all 23 current runtime input hashes and 36 supporting artifact hashes.
- Offline candidate receipt after the raw-response review: `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-check-only-after-raw-response-audit-v2.json`.
- Raw-response ballot audit: `docs/M1_PACKAGE_REPLICATION_V3_RAW_RESPONSE_AUDIT_20261021.md`; it reparsed all 225 ballots and independently matched all 75 settlements.
- Pre-registration analysis amendment: `docs/M1_PACKAGE_REPLICATION_V3_BALLOT_OUTCOME_AMENDMENT_20261021.md`.

These are review artifacts, not registration or authorization. The candidate check does not verify a live server/listener, tokenizer/template parity, or any new behavior.

## Requested execution scope

Authorize one prospective, local-only M1 v3 run across 24 frozen, output-independent payoff matrices, with all five original M1 conditions within each matched group. The treatment, model, prompts, action schema, reward amounts, seed schedule, run order, and request graph remain frozen.

- Denominator: 120 assigned episodes / 24 matched groups. Retain every failed or invalid assigned episode; no retry, replacement, or resampling.
- Local generation ceiling: 456 Qwen generations (360 ballots + 96 message decisions).
- Physical HTTP ceiling: 480 attempts, including at most 24 local identity requests.
- Local endpoint only: `http://127.0.0.1:8081/v1`; no proxy, external provider, or fallback.
- Model: `Qwen3-8B-Q4_K_M.gguf`, SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- Runtime: llama.cpp b10068, commit `571d0d540`, expected binary SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`.
- External requests: 0. External cost: USD $0. Proposed expiry: `2026-10-26T12:00:00Z`.

Raw requests, responses, private observations, and failures remain in a Git-ignored ACL-restricted local run directory. No private text or ballots are sent to DeepSeek or another provider.

## Outcomes and scientific boundary

The primary outcome remains environment selection of the target allocation and its frozen four-cell finite-set interaction. The preregistration amendment additionally requires raw-reparsed A/B/C target-ballot indicators, total target-vote count, chair identity, any one-vote chair-tie selection, and a secondary descriptive A/B joint-target-ballot interaction. Both environment settlement and A/B co-voting remain observable actions, not collusion, agreement, or intent labels. A and B share the same known target; the chat treatment also adds a message-decision stage. A positive result therefore supports only the assigned package on this finite matrix set and checkpoint, not message semantics or communication causality.

## Required gates and stop conditions

Before any live request, incorporate the amendment into a schema-v2 preregistration, create a fresh immutable approval batch for this exact experiment and ceilings, and rerun all current source/authorization/model/server/listener/tokenizer/template/storage gates. Stop immediately on any hash, identity, privacy, transport, budget, endpoint, or authorization failure. Invalid outputs and failed episodes remain assigned and are never repaired or replaced.

After approval, registration, and live preflight, the gated command is:

```powershell
python scripts/run_m1_package_replication_v3.py --live --approval-id <new-M1-approval-id> --out runs/m1_100/m1-package-replication-v3/run-<unique-id>
```

This approval request covers only the local Qwen experiment above. The prior DeepSeek approvals are closed, consumed, and unrelated.
