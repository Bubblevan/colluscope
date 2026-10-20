# DeepSeek-First M4 / Monitor — Local Release and Reproduction

## Scope and authorization

This release implements the single bounded run authorized by the attached **“ColluScope — DeepSeek-First Recovery and Full Research Execution”** task. It permits only the official DeepSeek API at `https://api.deepseek.com`, using the configured `deepseek-flash` alias. It does not authorize another provider, local Qwen generations, downloads, training, M2 comparisons, or a later rerun.

The pre-inference freeze must be committed and pushed before dispatch. The full run is one command and stops automatically at the first failed gate:

```powershell
python scripts/run_deepseek_first_research.py
```

The exact schedule is at most 670 planned calls: compatibility pilot ≤30; M4 Agent ≤264; natural-trace Monitor ≤288; scripted controls 16; matched worlds 72. Runtime hard ceilings are 900 physical attempts and USD 5 peak-rate reserve across phases. Retries and replacement rows are disabled. The Agent gate is included in its 264 cap. Monitor scaling depends on the frozen assessable-pair gate. A failure does not authorize a retry or replacement.

## Pre-dispatch verification

Run the entire offline suite and frozen plan check before dispatch:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest -q
python -m pytest -q tests/test_deepseek_research_audit.py
```

The committed `configs/m4-deepseek-pilot-plan-v1.json` must reproduce byte-for-byte from the source. Confirm `.env` credentials are available without printing them and verify only the official host is configured. Refresh official pricing immediately before the first request. Raw request/response bodies, private messages, credentials, and identity records are local-only in Git-ignored, ACL-restricted `runs/deepseek-first-m4/`.

## Independent post-run audit

After any terminal run or stop, execute:

```powershell
python scripts/audit_deepseek_first_research.py
```

The audit replays Agent actions and settlements from raw request/response bytes, checks the request ledgers and source hashes, and separately scores Monitor parseability, citations, task facts, abstention, and matched coverage. Sanitized tables are written under `docs/results/deepseek-first-m4/audit/`; raw private artifacts stay under ignored `runs/`.

Use `python scripts/run_deepseek_first_research.py` only once. It is resumable solely from already persisted, hash-verified terminal responses and never resends a started request. Inspect `runs/deepseek-first-m4/final-run-summary.json` and the independent audit summary for the stop/status and denominators. Do not manually run later phases around the orchestrator's gates.

## Data and claim boundaries

Pre-sprint work (M0–M4 and preparation through 2026-10-20) must be disclosed as such; the Apart Sprint begins 2026-10-23. The prospective DeepSeek interface run is a versioned extension and does not rewrite or re-date earlier experiments. A provider alias/fingerprint is not a pinned weight hash. A/B share the same rewarded target, so matching votes without a communication intervention do not identify communication-induced coordination. Observable messages, delivery, proposals, ballots, settlement, welfare, and task scores must be reported separately. No latent-collusion gold label is created, and neither a model response nor a software PASS proves collusion or detector superiority.

## Frozen artifacts

The pilot plan binds the 30 compatibility slots to the frozen Agent/Monitor source, prompt, protocol, config, schedule, control, runtime and tests. Its SHA256 is recorded in `docs/M4_DEEPSEEK_FIRST_RESEARCH_EVIDENCE.md` and the run manifest. M4 and Monitor source manifests are verified before dispatch and on replay. A candidate change after this release requires re-freezing and re-running offline validation before any request; it is not silently folded into this run.

## Completed-run state

The single authorized execution completed on 2026-10-20: 628/628 requests, 24/24 Agent groups, and 376/376 Monitor rows. The authorization is consumed; the launch command above is a reproduction record, not permission to run again. Independent scoring and final decision are in `M4_DEEPSEEK_FIRST_RESEARCH_RESULTS.md` and `M4_DEEPSEEK_FIRST_RESEARCH_DECISION.md`. The corrected pre-inference freeze commit was `550bf1361609e405dc50aa60d5d77b9c502e5bf0`; the final analysis commit is recorded in Git after review.
