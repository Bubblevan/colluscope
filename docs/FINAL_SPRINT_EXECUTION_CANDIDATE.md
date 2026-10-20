# Final Sprint Execution Candidate

**Candidate branch:** `codex/final-sprint-execution-candidate-20261020`

**Base reviewed commit:** `95cd6b5c5c0cc05ebf14a1be04052501b0602ad1`
**Status:** offline engineering candidate; no new model or provider inference in this task. The final pushed commit SHA is the branch tip reported with delivery.

## Readiness snapshot

| Area | Status | Evidence boundary |
|---|---|---|
| Portable offline suite | **446 passed, 1 skipped in 216.22s** | No live inference; the optional Windows listener canary is excluded and reported as skipped |
| Full-history integration | **447 passed in 227.19s** on restored local historical data | Raw ignored M1/M2/M3 data remains local; host-specific integration is not portable evidence |
| M4 real local backend | **Implementation GO after separate approval** | Fake local HTTP integration only; 24 groups / 264 physical attempts maximum |
| Monitor real provider backend | **Implementation GO after separate approved config and current pricing check** | Existing B2–B5 dispatcher; 280 requests / 280 attempts, USD 1 ceiling; no dispatch here |
| Behavioral inference / detector comparison | **NO-GO / not run** | Requires separate authorization and post-run scientific review |

The latest frozen local asset receipt is `docs/results/final-sprint-candidate/runtime-identities.json`. The exact M4 and Monitor artifact hashes are in `docs/M4_LIVE_RUNTIME_EVIDENCE.md`, the receipt, and the source/input inventory `docs/results/final-sprint-candidate/candidate-artifact-sha256.json`. M4 identity includes Qwen3-8B Q4_K_M SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`, llama.cpp b10068 binary SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`, GGUF tokenizer SHA-256 `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`, and chat-template SHA-256 `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`.

## Entry points and budgets

M4 uses the frozen 24-group scenario/split schedule and existing incentives. At most 11 generations per group yield 264 physical attempts. There are no retries or replacements. Full schedule includes two message actions, three baseline ballots, up to four eligible focal ballots, and two capability-control calls. Errors consume slots; all 24 assigned groups stay in the denominator. Exact launch and independent audit commands are in `M4_LIVE_RUNTIME_DECISION.md`.

Monitor preserves the existing B2–B5 280-row protocol: `8 controls × 5 tasks × (B2 2 permissions + B3 1 permission-invariant + B4 2 + B5 2) = 280`. One attempt per row, zero retry/replacement. The current frozen config is disabled; a separate approved config and explicit authorization ID are mandatory. Its verified plan reserves USD 0.4086309 under the USD 1 hard ceiling. Any missing provider usage is charged at the conservative request reservation. The CLI and independent audit commands are in `M4_LIVE_RUNTIME_DECISION.md`.

## Evidence and storage boundaries

- M4 raw requests, responses, private messages, episode traces and generated local key remain under Git-ignored, current-user ACL-restricted `runs/m4/`. Authentication headers are never serialized; the local API key is removed in cleanup.
- Monitor raw requests/responses and restricted privileged synthetic messages stay in ignored `runs/sprint-monitor/` under current-user ACL. Provider credentials are read only from `DEEPSEEK_API_KEY` after the approved live gates and never written to artifacts.
- Public-only and privileged Monitor projections are distinct. Hidden reference answers, incentive/treatment fields and construction labels are blocked from monitor payloads. Raw and gated predictions remain separate.
- No raw private-message or historical M1/M2/M3 content is staged. Existing unrelated Colosseum files under the workspace remain untouched and uncommitted.
- The reproducibility evidence includes hashes and source/runtime inventory. Hashes detect ordinary corruption but are not a signed external timestamp.

## Reproduction commands

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q tests/test_m4_live_runtime.py tests/test_sprint_monitor_runtime.py
python scripts/run_m4_live.py --help
python scripts/audit_m4_live.py --help
python scripts/run_sprint_monitor.py --help
python scripts/audit_sprint_monitor_live.py --help
```

See `M4_LIVE_RUNTIME_EVIDENCE.md` for portable and restored full-history suite commands. The M4 launch command requires explicit separate approval; the checked-in Monitor config refuses live dispatch.

## Scientific limitations and interpretation

The M4 pair shares a known rewarded target, so agreement can be independent parallel response to the common incentive. Real model-authored proposals may differ in token length; v3 measures full rendered proposal-minus-neutral prompt-token deltas for each eligible comparison and reports preregistered sensitivity bins without changing message text. Conditional proposal-eligible contrasts must be reported beside all-assigned-group outcomes. `NONE`, no-message, and no-delivery are distinct.

The already completed M4 v2 fixed-stimulus tokenizer/server parity is preserved and not repeated. It does not establish natural proposal length balance. Fake runtime responses are not behavioral evidence. Monitor scripted controls are software/scorer checks and cannot establish generalization or collusion-detection accuracy. No latent-collusion gold label is created.

## Contribution chronology

M0–M3, M4 scenario/protocol work, the frozen baselines, and this implementation candidate were completed before the Apart Research sprint starts on 2026-10-23. This branch is pre-sprint engineering/protocol preparation dated 2026-10-20, not sprint-period experimental work. No timestamps are altered and no earlier experiment is renamed as new sprint work. Any retained use in a submission must disclose pre-sprint work and AI assistance according to the official rules.

## Final gate

The engineering entry points are independently testable and enforce their sample/request/cost ceilings. M4 is capable of running locally after a separate approval. Monitor requires a separately approved versioned config and fresh price verification; it remains disabled in the checked-in config. **Neither real experiment was authorized or started by this task.** Passing offline tests does not convert either scientific experiment to GO, demonstrate a treatment effect, or establish detector performance.
