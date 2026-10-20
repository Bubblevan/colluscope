# Sprint Baselines Decision

**Decision date:** 2026-10-20 (Asia/Shanghai)

**Scope:** offline baseline and evidence-auditor preparation only.

## Decision

- **GO:** scripted evidence controls, blind evidence compiler, independent reference replay, B0/B1 offline sanity checks, scoring primitives, M4 scenario/split freeze, and reproducibility checks are ready for independent code review.
- **NO-GO:** B2–B5 real Monitor inference. There is no current authorization, and no inference dispatcher was implemented. The 280-request/280-attempt figure is a frozen planning ceiling, not an active runtime-enforced limit. The mutable provider alias, live pricing, exact returned model identity, token accounting, execution window, and data-egress approval must be fixed before any request.
- **NO-GO:** M4 real Agent inference. The exact Qwen checkpoint/runtime fingerprint and message/action tokenization must be reverified; the M4 behavioral positive-control token equality is explicitly unverified; 264 generations remain only a design ceiling. A separate approval must authorize the complete run.
- **NO-GO:** M2 detector superiority, latent-collusion detection, and any claim that control-case performance generalizes to real or unseen agent traces.

## Evidence for this decision

1. `python scripts/verify_sprint_baselines.py` reconstructs the eight controls, 280 observable references and 280 request payload hashes, checks the result table and zero-dispatch receipt, verifies M0–M3 source hashes, and independently checks the M4 scenario and group manifests.
2. Targeted offline tests (**24 passed**) exercise hidden-field poison, public/private message boundaries, voluntary disclosure retention in authorized evidence, action-only permission invariance, malformed output rejection, citation/fact separation, provenance gating, B1/reference parity, negated acceptance, heterogeneous CSV rows, cluster resampling determinism, scenario uniqueness and split integrity.
3. The generated B0/B1 table is marked `SCRIPTED_OFFLINE_SANITY_ONLY`; all seven LLM cells are `NOT_RUN`. The preparation receipt records zero model/API calls, zero external traffic, and zero historical raw-data access.
4. Ignored M1-100, M1-P0 and M2-V3 raw paths are absent on this host. The M2 synthesis is available but has known answer leakage and is not relabeled as an unbiased baseline.

The full repository test command was also run unchanged and returned **320 passed, 10 failed, 6 errors, 1 skipped**. All 16 failures/errors trace to missing ignored M1-P0 files under `runs/m1_p0_local/formal-25ep-pilot-20261019/run/` (`researcher/T.jsonl`, `runtime-config.toml`, or `full-pilot-config.toml`). These tests exercise historical M1/M2 corpus integration and cannot run without those local raw artifacts. They were not deleted, skipped, or replaced. The complete captured output, normalized to LF, is preserved in `docs/results/sprint-baseline-v1/logs/full-pytest-final.txt.gz`; the adjacent `.txt` is a readable copy with trailing spaces stripped. Missing-path inventory is recorded in `historical_data_access.json`.

## Remaining gates before a new inference request

- Independent review of this branch and a separately approved, fixed execution window.
- For Monitor calls: approved provider/data egress; rechecked price and token accounting; exact returned model/fingerprint requirement; a newly written dispatcher enforcing 280 logical/physical maxima and a hard spend cap; request/response retention and failure policy.
- For M4 calls: exact local checkpoint, llama.cpp build, tokenizer/chat template, prompt/schema/seed and sample freeze; verify exact neutral/information message token counts or preregister the mismatch; secure raw storage and independent endpoint/listener checks.
- Never combine either budget: the Monitor plan is at most 280 logical/280 physical requests; M4 is at most 264 logical/264 physical generations. Neither is authorized now.

## Reproduction

```powershell
python scripts/prepare_sprint_baselines.py --output docs/results/sprint-baseline-v1
python scripts/verify_sprint_baselines.py
python -m pytest -q tests/test_sprint_baselines.py tests/test_sprint_controls.py tests/test_sprint_preparation.py tests/test_m4_scenarios.py
python -m pytest -q
```
