# Sprint Execution Readiness and Baseline Integrity Protocol

**Version:** 1.0, 2026-10-20
**Status:** Offline-only validation complete; no live inference authorized or performed.

## Purpose

Validate that the frozen Sprint baseline and M4 runtime can be independently prepared, dispatched through a bounded offline mock, and replay-audited without reference-label leakage or hidden model calls. This protocol is not a monitor benchmark and does not evaluate real agent behavior.

## Frozen scope and boundaries

- Preserve M0–M3 historical artifacts and the previously frozen baseline source rows. The superseded B0 output is retained under `docs/results/sprint-execution-readiness/superseded-b0-before-v2/` with hashes.
- B0 must be determined only by permitted evidence completeness and its frozen negative decision rule. It may not inspect reference answers, construction sidecars, researcher-only truth, or scoring labels.
- The offline monitor dispatcher uses the frozen 280-row schedule, one attempt per row, zero retries, no external fallback, and a $1 estimated-cost ceiling. Current operation is disabled for live inference; credentials are not read from `.env`.
- M4 uses the six frozen scenario families and 24 assigned groups, with a 264 logical-generation ceiling, zero retries, and no replacements. Its offline CLI deliberately exposes only mock mode.
- Raw mock requests, responses, and traces are stored under ignored, ACL-restricted `runs/` paths. Public receipts contain hashes and counts, not private message text or credentials.
- V2 supplementary controls are synthetic software/scorer controls with construction-family-disjoint development/evaluation groups. They are not naturalistic data or model predictions.

## Iteration loop

1. **INSPECT:** identify label leakage, request-boundary failures, incorrect settlement replay, and evidence of false model-call claims.
2. **SPECIFY:** counterexamples include poisoning all gold/reference fields while holding visible evidence fixed; corrupting any request-response-attempt link; injecting an extra retry; altering a matrix or prompt artifact; and changing the target string without changing the no-chat channel.
3. **IMPLEMENT:** make only versioned, minimal changes to B0, bounded mock dispatch, audit scripts, and synthetic controls. Never rewrite M0–M3 source results or their historical timestamps.
4. **RUN:** execute generation, mock dispatch, environment identity/token checks, independent replay, and tests; save unedited output.
5. **ADVERSARIAL REVIEW:** check permissions, metadata leakage, token equality, retry/budget behavior, missing raw data, and whether success statements exceed the evidence.
6. **DECIDE:** offline software integrity can pass while live Agent/Monitor inference remains NO-GO.
7. **REPORT:** update `docs/ITERATION_LOG.md`, the risk register, evidence, and decision before any separately authorized inference.

## Required reproduction commands

```powershell
python -m pytest -q tests/test_sprint_baselines.py tests/test_sprint_controls.py tests/test_sprint_preparation.py tests/test_m4_scenarios.py tests/test_sprint_monitor_runtime.py tests/test_m4_runtime.py tests/test_sprint_controls_v2.py tests/test_m3_mechanism.py tests/test_m3_independent_audit.py tests/test_openai_compat_llamacpp.py
python scripts/prepare_sprint_baselines.py --output docs/results/sprint-baseline-v1
python scripts/verify_sprint_baselines.py
python scripts/audit_b0_recompute.py --output docs/results/sprint-execution-readiness/b0-score-delta.json
python scripts/run_sprint_monitor.py --config configs/sprint-monitor-runtime-v1.toml --mode mock --out runs/sprint-monitor/mock-e2e-v1
python scripts/audit_sprint_monitor_mock.py --run runs/sprint-monitor/mock-e2e-v1 --out docs/results/sprint-execution-readiness/sprint-monitor-mock-audit.json
python scripts/prepare_sprint_controls_v2.py
python scripts/prepare_sprint_controls_v2.py --verify
python scripts/run_m4_offline.py --mode mock --out runs/m4/offline-mock-v2
python scripts/audit_m4_mock.py --run runs/m4/offline-mock-v2 --out docs/results/sprint-execution-readiness/m4-mock-audit.json
python scripts/verify_m4_local_environment.py --out docs/results/sprint-execution-readiness/m4-local-environment.json --mock-run runs/m4/offline-mock-v2
```

The final command is expected to exit nonzero with a token-match NO-GO even though model/runtime identity hashes match. That failure is a substantive gate result and must not be normalized into PASS.

## Interpretation rules

- A mock dispatch/replay pass establishes only software and artifact integrity.
- B0 score reductions caused by removing reference access are retained and reported as errors, not excluded cases.
- No scripted V2 outcome is an LLM prediction or latent-collusion label.
- Matching votes, a shared rewarded target, a private channel, target execution, welfare loss, and a treatment ID are not collusion gold labels.
- The exact token mismatch is a design limitation and a live-inference stop condition for the frozen M4 design.
