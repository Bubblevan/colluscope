# Risk Register Follow-up — Audit Output Side Effect

**Risk:** the M4-B5 independent audit command writes to the same fixed path as the hash-pinned registry artifact. Re-running it can replace a previously audited file with a regeneration, making the current checkout fail registry integrity even when the regenerated values look equivalent.

**Observed evidence:** a post-push re-run changed the audit output from the committed SHA-256 `6e5278737d9550d547ef4895ef9ed9bc6aa85fafdb1a26087fdbc4011a11041c` to `cec9057abfc78a6cb26cb9c338fd8c0ce93dd59cbc2a9d18fb5ede395ef9d818`. Restoring the committed copy returned `python scripts/researchctl.py audit` to `PASS`, with no accounting errors. No raw model record or scientific source was changed.

**Mitigation now in force:** do not rerun the audit into its default pinned path. The integrity correction is documented in `docs/ITERATION_LOG_FOLLOWUP_20261021_POSTPUSH_AUDIT_RESTORE.md`.

**Remaining action:** before any later replay, add a versioned output-path option or use a separate run directory, then compare the new report without replacing the registered artifact. This is an engineering reproducibility risk only; it does not alter the M4-B5 scientific conclusion (`INCONCLUSIVE`).
