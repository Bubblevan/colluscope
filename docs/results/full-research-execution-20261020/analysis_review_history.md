# Post-run analysis review history

This file preserves analysis/reporting defects discovered during the independent post-run work. None changed the frozen schedule, raw request/response bytes, model outputs, scorer references, or experiment denominators.

## Coverage denominator draft — rejected before publication

The first uncommitted completion chart counted only records in the completed-score projection as if they were the assigned denominator. It consequently displayed values such as `9/9` for a method actually assigned 80 requests, `24/24` for a method assigned 144 requests, and some unscheduled matched-world cells as `0/0` with a plotted `0%`. The chart was not committed or used for a decision. Visual review exposed the denominator error.

Correction: the final analyzer joins parseable raw prediction scores by request ID to all frozen `progress.jsonl` rows, requires phase-level denominator conservation, and renders a method/population cell with zero assigned rows as “not scheduled.” It keeps a true observed `0/N` distinct from an unassigned `0/0`. Regression tests cover both cases.

## Row-level score projection — failed strict join retained in task history

The public `per_request_scores` member of the independent phase audit is a compact status-and-label projection; it does not contain baseline/task fields or row score objects. Treating it as the source of per-row scores is invalid. The final analyzer reads the local `raw_predictions.jsonl` score record, checks it against the complete frozen progress row and compact audit status/label, and reconciles key score counts against the independent task/view aggregates. An orphan, duplicate, mismatched baseline/task/permission, or tampered aggregate raises an error. No raw text is exported.

The first strict-join attempt also expected an `identity_probes.jsonl` file in the pre-generation M4 directory, where no identity probe had occurred. The absent file is correctly treated as an empty ledger; the two probe attempts in the later preserved directories must each have a unique terminal record. This absence is consistent with the M4 logs and does not change generation counts.

## Preserved scientific failures

- M4: 24 assigned first-message generations, 24 strict parser failures; no valid message/ballot/settlement.
- Monitor: 856 assigned physical requests, 715 `finish_reason=length` failures, zero retries/replacements.
- No parseable model result occurred on a frozen hard-negative control row, so model hard-negative specificity remains unestimated.

The files above are public aggregate/sanitized reports. Raw agent messages, monitor request/response bodies, exact privileged payloads, and append-only attempt records remain local and ACL-restricted under ignored `runs/` directories.
