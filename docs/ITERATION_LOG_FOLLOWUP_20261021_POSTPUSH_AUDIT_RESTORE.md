# Iteration Follow-up — Restore Hash-Pinned B5 Audit Output

- **Date:** 2026-10-21
- **New model/API calls:** 0
- **Evidence class:** offline audit-integrity maintenance

## OBSERVE

After commit `163c74aa840d47e061324d80d7a29438adf7c476` was pushed, a verification command reran `scripts/audit_m4_b5_context_sensitivity_run.py`. The script rewrites the existing fixed-path audit output, `docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-audit.json`, so the worktree copy no longer matched the hash referenced by the closed registry record. This was an audit-output overwrite, not a new model request or a change to raw request/response evidence.

The overwritten regeneration had SHA-256 `cec9057abfc78a6cb26cb9c338fd8c0ce93dd59cbc2a9d18fb5ede395ef9d818`; the previously committed frozen audit had SHA-256 `6e5278737d9550d547ef4895ef9ed9bc6aa85fafdb1a26087fdbc4011a11041c`.

## REPAIR / RUN

Restored the exact committed audit JSON with:

```powershell
git restore --source=HEAD -- docs/results/research-sprint-20261021/m4-b5-context-sensitivity-independent-audit.json
```

Then reran the read-only registry audit:

```powershell
python scripts/researchctl.py audit
```

It returned `integrity_check: PASS`, four closed registered cycles, zero open experiments, 352 accounted new-cycle calls, USD `0.039167058`, and no errors. The 232-call M4-B5 authorization remains consumed. No campaign audit script was rerun after restoration.

## ADVERSARIAL REVIEW / DECIDE

The raw campaign evidence and the committed independent replay remain unchanged. The incident shows that the audit command is not side-effect-free because its default output path is a registry-pinned artifact. Repeated verification must preserve that path or direct output to a new versioned location. The current experiment record is restored and integrity passes; no scientific result changed.

**Next action:** keep this integrity correction in the iteration record and avoid running the fixed-path audit command again unless a versioned output-path workflow is added. Continue the autoresearch Goal through evidence review and hypothesis selection; do not dispatch under the consumed approval.
