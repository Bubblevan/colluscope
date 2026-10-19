# M3 Reproduction Guide

## Offline re-audit

Work from the repository root `reference/m1-p0-local-qwen-integration`. The frozen raw run remains local at `runs/m3/mechanism-20261020/` and is Git-ignored because it contains private synthetic messages, full prompts and responses. The independent replay makes **no model calls**, but it needs the local run, the exact configured GGUF path for tokenizer verification, Python dependencies, Git history, and Windows ACL inspection support.

Run the focused tests and replay into a new, empty output directory:

```powershell
python -m pytest -q tests/test_m3_independent_audit.py
python -m scripts.audit_m3_mechanism --run runs/m3/mechanism-20261020 --out docs/results/m3-mechanism-reproduction
```

To rerun the entire offline repository suite:

```powershell
python -m pytest -q
```

The committed successful output is `docs/results/m3-mechanism-audit-final/`. The auditor refuses to overwrite a nonempty result directory; choose a new path for each replay. Earlier partial output remains locally archived under `runs/m3/mechanism-20261020/audit-attempt-outputs/`, and the sanitized error sequence is committed. The final suite result was **344 passed, 1 skipped**. Six localhost HTTP contract tests require permission to bind/connect loopback sockets on Windows; the default sandbox run's 6 failures are preserved, and the same suite passed once those loopback-only tests were allowed.

## Evidence dependencies and limits

The independent replay joins each T/B/E projection to the assignment schedule, progress ledger and immutable per-episode envelopes; verifies request and HTTP-attempt hashes, model/server/source lineage, settlements, token totals, privacy permissions and historical M1 file hashes; then exports CSVs, JSON summary, SVG figure, privacy scan, and artifact hashes. It does not trust the runner's stored welfare result as its scoring reference: settlement is recomputed from the three raw ballots, frozen matrix and chair rule.

The raw run is not in Git. Public outputs contain sanitized aggregates, group identifiers, ballots' derived classifications, run hashes and verification code, but omit raw private message text and full prompts. A reviewer without the local run cannot independently regenerate the full row-level replay from the pushed repository alone. Controlled access to the ACL-restricted source run would be required for that; this limitation is not hidden by the public hashes.

The tokenizer metadata is hashed from the GGUF and the independent local prompt count matches the aggregated response-reported input total. The run manifest still marks live tokenizer/server parity as unverified, so this aggregate equality must not be described as exact token-sequence verification.

## Privacy check

The final audit's `privacy_scan.json` records that 13 delivered messages were checked against 9 sanitized output files and no exact copies were found. Re-run the audit after changing any report or output. Never export private message text, prompts, or raw responses as a convenience for reproduction.
