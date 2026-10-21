# M1 Package Replication Candidate — Offline Refresh (2026-10-21)

**Evidence class:** offline design/runtime preparation  
**Model or API generations:** 0  
**Live server started:** no  
**Live endpoint contacted:** no  
**Decision:** candidate passes offline gates; remains unregistered and unauthorized.

## Freshly verified

- The 24-matrix design generator reports 120 assigned episodes and 456 generations; `model_outputs_consulted=false`.
- The separate matrix auditor checks all 144 payoff permutations and passes.
- The prompt-profile auditor recomputes the message and C-ballot profiles and passes.
- The runner's `--check-only` reports 120 assigned episodes, 360 ballots, 96 message decisions, 456 generation ceiling, 24 identity-request ceiling, and 480 physical HTTP ceiling. It confirms external calls are disabled by default and `monitor_can_see_private_messages=false`.
- `researchctl.py audit` passes registry integrity, reports four closed cycles, no open experiments, 352 new-cycle model calls / USD $0.039167058, and zero audit errors. These project balances do not authorize another experiment.
- The local checkpoint exists at the configured path, has the frozen 5,027,783,488-byte size, and recomputed SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- The local llama.cpp server binary exists and its recomputed SHA-256 is `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`.

The exact outputs are preserved under `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/`: `matrix-generator.json`, `matrix-auditor.json`, `prompt-profiles.json`, `runtime-check-only.json`, `registry-audit.json`, and `file-identity.json`.

## Not verified

This offline refresh did not start a server, inspect port ownership, issue `/props`, `/apply-template`, or `/tokenize`, verify live tokenizer/template parity, or generate an agent action. Those are runtime gates for the gated live command and require a new exact-scope user approval first.

## Reproduction commands

```powershell
python scripts/freeze_m1_package_24_matrix_design.py --check
python scripts/audit_m1_package_24_matrix_design.py --check
python scripts/audit_m1_replication_prompt_profiles.py --check
python scripts/run_m1_package_replication_v3.py --check-only
python scripts/researchctl.py audit
```

## Decision boundary

The candidate is ready for scope-specific authorization and formal registration review. It does not yet have a `research/experiments/<id>/preregistration.json`, a new immutable authorization batch, or live endpoint/tokenizer evidence. No part of the expired/consumed DeepSeek campaigns applies to this local Qwen experiment.
