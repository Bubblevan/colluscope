# Registered V1 preflight stop

- Registered experiment: `deepseek-real-coordination-40-v1`.
- Offline command: `python scripts/run_deepseek_real_coordination_v1.py --check-only`.
- Result: failed before client construction or any request. `verify_freeze()` looked for `research/experiments/deepseek-real-coordination-v1/preregistration.json`, while the immutable registered record is at `research/experiments/deepseek-real-coordination-40-v1/preregistration.json`.
- Physical model/API attempts: **0**. `runs/deepseek-real-coordination-v1` was absent.
- Registry audit initially exposed two historical hash mismatches after this task accidentally changed `.gitignore` and `docs/ITERATION_LOG.md`. Both files were restored to exact HEAD bytes; `python scripts/researchctl.py audit` then returned `integrity_check: PASS`, `errors: []`. The current iteration is recorded in a separate follow-up file so those historical hash-pinned artifacts stay unchanged.
- Disposition: close this registration as `EXECUTION_BLOCKED`; preserve its preregistration/manifest unchanged. Build and register a corrected versioned runtime with aligned experiment and registration paths before any model request.
