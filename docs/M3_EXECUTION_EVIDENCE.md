# M3 Execution and Independent Verification Evidence

**Protocol:** `colluscope-m3-mechanism-v1`
**Local run:** `runs/m3/mechanism-20261020` (Git-ignored; current-user ACL verified)
**Frozen source:** `2da217c2ea81d90a5783b5ea67c63d26a5803d86`
**Runtime source used for generation:** `f190c78ae995669be9772d67bf660448af44e452`
**Post-run auditor SHA-256:** `671658d146b752e67d3735058ad4930d7d2ba397c3a38e44563b37d0eab6b288`
**Independent replay output:** `docs/results/m3-mechanism-audit-final/`

## Execution totals

| Item | Independently verified value |
|---|---:|
| Groups assigned / terminal / completed / failed | 12 / 12 / 12 / 0 |
| Message-eligible groups | 8 |
| Complete baseline groups | 12 |
| Complete four-arm groups with valid anchors | 8 |
| Logical generations | 84 / 96 maximum |
| Message / baseline ballot / counterfactual ballot requests | 24 / 36 / 24 |
| Generation HTTP attempts | 84 |
| Identity probe HTTP attempts | 2 |
| Total HTTP attempts | 86 / 192 maximum |
| Transient retries / invalid model actions | 0 / 0 |
| External API / monitor / training / download calls | 0 / 0 / 0 / 0 |

Both identity probes are included in the total HTTP denominator. The actual effective generation-attempt ceiling was 190 after reserving the two identity probes; the backend safety ceiling remained 191. The local request budget rejected any attempt beyond the effective limit.

## Identity and frozen inputs

- Checkpoint: local Qwen3-8B Q4_K_M GGUF, SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- Audited llama.cpp server build SHA-256: `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`.
- Endpoint: authenticated loopback `127.0.0.1:8081`, local offline server, no remote fallback.
- Sampling: temperature 0, top-p 1, top-k 0, min-p 0; frozen sampler order `top_k;top_p;min_p;temperature`.
- GGUF tokenizer SHA-256 `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`; chat-template SHA-256 `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`.
- Tokenizer library `tokenizers==0.19.1`; Jinja2 `3.1.4`. The run manifest records embedded GGUF tokenizer metadata. It labels live server/tokenizer parity as unverified; however, the aggregate reported input-token count (45,075) equals the independent local tokenizer count (45,075). This aggregate equality does not prove token-by-token server parity.
- Frozen schedule SHA-256: `380e5556f1e822a2e7f5e5a4eef31c41fd0a15aaffb9f37adb53e48b31951d75`.
- Protocol SHA-256 at freeze: `0e4e489c8895c317bca5ffd97a885f7473741f7b68d71a821f516e67341d9f6f`.
- Model prompts, schemas, config, payoff matrices and schedule stayed byte-identical to the pre-generation freeze. The two source errata changed runtime metadata export/resume allowance and dynamic HTTP reservation only; independent audit verified their exact commit/hash chain and confirmed model-facing semantics were unchanged.

## Raw evidence integrity and privacy

The local run has separate T, B, Public-only E, agent observations, full request/response rows, attempt-start reservations, HTTP-attempt rows, resource telemetry, progress ledger and per-episode envelopes. Raw messages and requests remain under the ACL-restricted, Git-ignored run path. The ACL verification covered 65 objects at audit time. The append-only local `audit-failures.jsonl` preserves failed independent audit invocations; the sanitized public transcription is `docs/results/merge-m0-m2/m3-independent-audit-failure.log`. One manually entered placeholder timestamp was retained and followed by an explicit timestamp-correction record rather than rewritten.

The independent audit recomputed outcomes from raw ballots, scenario matrices and the frozen voting rule. It verified all 12 baseline settlements, all 24 fixed-peer settlements, message send/delivery, T confirmation IDs, Public-E permissions, observation/request linkage, source/model/runtime lineage, budget, token counts, historical M1 hashes, and per-group schedule identity. Its exact-text scan checked all 13 delivered messages against the public audit outputs and found zero copies.

A broader scan checked all 187 files under `docs/` against all 13 delivered message strings and found zero exact copies. All ten M3 artifact-manifest hashes and all three M1 figure-manifest hashes verified. The reproducible check summary is `docs/results/merge-m0-m2/m3-public-privacy-hash-check.log`.

The source secret-pattern scan found no production credential and no tracked `.env`; its three broad matches were dummy API-key strings in existing HTTP-security tests. Summary: `docs/results/merge-m0-m2/m3-source-secret-scan.log`.

## Audit repair history

The first replay exposed that the auditor assumed B/E projections had top-level episode IDs. Runtime records intentionally store these as id-less projections; the repair links each row by terminal progress order and exact canonical equality against the immutable per-episode envelope. Subsequent replays found independent audit-only defects: an uninitialized event variable, overinclusive T receipt IDs, a misclassified unassigned C incentive, overly strict optional tie diagnostics, and a missing JSON artifact writer. Each failure was preserved, repaired with a targeted test, and followed by a new output directory. No raw run file, prompt, task condition, reward, model response or historical artifact was modified. The final successful replay is `v7`; earlier partial directories remain unchanged for auditability.

See `docs/M3_POSTRUN_AUDIT_ERRATA.md` for exact auditor-source scope and hash. These post-run repairs affected analysis code only and were not used during model generation.

## Evidence files

- `docs/results/m3-mechanism-audit-final/m3_summary.json`
- `docs/results/m3-mechanism-audit-final/artifact_sha256.json`
- `docs/results/m3-mechanism-audit-final/m3_group_results.csv`
- `docs/results/m3-mechanism-audit-final/m3_arm_summary.csv`
- `docs/results/m3-mechanism-audit-final/m3_paired_contrasts.csv`
- `docs/results/m3-mechanism-audit-final/m3_family_summary.csv`
- `docs/results/m3-mechanism-audit-final/m3_token_matching_summary.csv`
- `docs/results/m3-mechanism-audit-final/m3_self_history_summary.csv`
- `docs/results/m3-mechanism-audit-final/privacy_scan.json`
- `docs/results/m3-mechanism-audit-final/figures/m3_focal_ballot_match.svg`

Reproduction commands are in `docs/M3_REPRODUCTION.md`. No real-model inference is required to replay the independent audit.

The focused post-run audit suite passed **26 tests**. The full repository suite passed **344 tests, 1 skipped** when allowed to bind only offline loopback test servers. Its initial sandbox-denied attempt (6 loopback permission failures, 338 passed, 1 skipped) is retained as a sanitized summary in `docs/results/merge-m0-m2/pytest-m3-postrun-audit.log`; the raw 59,671-byte output remains local at `runs/m3/mechanism-20261020/logs/pytest-m3-postrun-audit-sandbox-failure-raw.log`, SHA-256 `be07885249fe2d706425bdf6c55803bde474a269b25cc605cb753ff9fb282bdd`. Neither run made any model inference or external traffic.
