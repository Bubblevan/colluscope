# Iteration Log Follow-up — Final Offline Gate and Authorization Reconciliation

- **Date:** 2026-10-21
- **New model/API calls this iteration:** 0
- **Research cycle:** M1 v3 approval-readiness closeout, with B5 campaign authorization reconciliation

## INSPECT

The current checkout already contains a registered and closed `m4-b5-context-sensitivity-campaign-v1`. Its evidence records 232/232 attempts, an independent raw replay pass, and a scientific `INCONCLUSIVE` decision. The latest user reply approving that exact 232-request scope therefore cannot authorize another dispatch; the recorded grant is consumed.

The M1 v3 review package remains a separate, unregistered local-Qwen candidate. The preceding state correctly says no M1-specific authorization exists.

## SPECIFY

The falsifying counterexample for safe continuation would be any open B5 registration, unattempted row eligible for accidental replay, or new model request made under the consumed B5 grant. For M1, an offline candidate pass must not be misreported as live identity validation or experiment authorization.

## IMPLEMENT / RUN

Reran the frozen M1 candidate in check-only mode:

```powershell
python scripts/run_m1_package_replication_v3.py --check-only
```

It returned `PASS_OFFLINE_CANDIDATE` with exit code 0, 120 assigned episodes, ceilings of 456 logical generations and 480 physical HTTP attempts, and zero external calls/cost. The exact captured command output is saved at `docs/results/research-sprint-20261021/m1-package-replication-offline-refresh/m1v3-check-only-final-20261021.json` (SHA-256 `f2d57d1f906c112fff3acac5c346ad7395d49dca49e292f4043413924c6c2073`). The check includes the frozen matrix audit, prompt-profile audit, and research registry audit; it does not contact a model or validate a live listener.

The state record now points to this final receipt. No historical M0/M1 artifacts or protected raw records were rewritten.

## ADVERSARIAL REVIEW

The B5 campaign evidence remains scientifically inconclusive: identical Public-only and Privileged-original request bodies with the same reported provider fingerprint did not reproduce labels reliably across the historical/current runs. The differences therefore cannot be cleanly attributed to private-message semantics. Public harm remains an observable label, not a collusion or intent label.

The M1 raw-response audit remains the historical evidence source: 225/225 ballots reparse to the stored assignments and 75/75 settlements recompute. The 9/15 joint A/B target ballots in the private-reward-plus-chat cell are compatible with shared-target parallel action and do not identify communication, agreement, or intent.

## DECIDE

Offline M1 candidate readiness: **PASS**. M1 live execution: **NOT AUTHORIZED / NOT REGISTERED**. The consumed DeepSeek grants do not authorize local Qwen generation. No new B5 request is warranted under its consumed authorization. The next gate for M1 is an exact scope-specific approval, immutable authorization registration, schema-v2 preregistration, and live endpoint/model/tokenizer/template/storage checks.
