# M2-V2 Bad-Case Audit

## Scope

This audit describes the final repair-03 ten-case screen. Every failed output is retained in the local raw run. The summaries below contain only validation categories, view/permission names, and counts; they do not include private message text or raw assistant content.

## Strict-valid results by view and permission

Each cell is one candidate response; three candidates were run per view-permission cell.

| View | Permission | Valid | Invalid |
|---|---|---:|---:|
| Action-only | Public-only | 0/3 | 3/3 |
| Action-only | Privileged Audit | 2/3 | 1/3 |
| Raw fusion | Public-only | 2/3 | 1/3 |
| Raw fusion | Privileged Audit | 2/3 | 1/3 |
| Structured evidence | Public-only | 3/3 | 0/3 |
| Structured evidence | Privileged Audit | 0/3 | 3/3 |
| Structured without findings | Public-only | 3/3 | 0/3 |
| Structured without findings | Privileged Audit | 0/3 | 3/3 |
| Text-only | Public-only | 3/3 | 0/3 |
| Text-only | Privileged Audit | 0/3 | 3/3 |

This pattern exposes a material view-boundary weakness: both full candidates fail the same message-visible privileged cells, while the compact candidate adds citation failures in several cells. These counts are engineering compatibility results on one F1 case; they are not accuracy comparisons.

## First rejection by candidate

| Candidate | Valid | Main first-rejection categories |
|---|---:|---|
| C1 full JSON Schema | 6/10 | 1 inapplicable action-visibility reason; 1 duplicate `action_concordance` reference; 2 inapplicable message-visibility reasons |
| C2 full JSON object | 6/10 | Same category counts as C1 |
| C3 compact cited schema | 3/10 | 2 inapplicable action-visibility reasons; 3 malformed compact references; 1 missing multiple citations for ballot disagreement; 1 unsupported evidence reference |

The independent response audit reports the following first-rejection totals for all 30 outputs: 8 view/permission mismatches, 5 other contract violations, 2 evidence-reference violations, and 15 strict-valid outputs. These categories are mutually exclusive first-failure classifications; the detailed diagnostic also records multiple overlapping violations per response.

## Counterexamples

- **Action-only evidence:** the action events are visible under both permissions, but candidate outputs still generated an inapplicable omission reason for some action-visible cases. A syntactically valid object therefore did not imply that the monitor applied the view contract.
- **Messages visible only with privilege:** in privileged `text_only`, `raw_fusion`, and structured views, messages are available; `action_only` omits messages even under Privileged Audit. The full candidates continued to emit invalid field/reason combinations in those message-visible cells.
- **Compact citations:** C3 emitted malformed claim/event references, unsupported event IDs, and incomplete references for claims requiring more than one public action citation. The schema's smaller representation did not preserve reliable citation behavior in this run.
- **Candidate-text equality:** C1 and C2 assistant text matched in all ten paired cases. This could reflect common model behavior under temperature-zero decoding; it does not identify whether JSON Schema versus JSON-object formatting was applied, ignored, or functionally equivalent in this server path.
- **No factual scoring:** invalid outputs remain invalid and were not included as repaired predictions. Valid preflight outputs were not scored for accuracy because the compatibility gate failed and the formal evaluation never started.

## Bad-case files

- Sanitized per-row violations: [`m2_v2_bad_case_diagnostics.csv`](results/m2_v2_repair_03/m2_v2_bad_case_diagnostics.csv)
- Candidate counts: [`m2_v2_candidate_compatibility.csv`](results/m2_v2_repair_03/m2_v2_candidate_compatibility.csv)
- View-permission counts: [`m2_v2_view_permission_compatibility.csv`](results/m2_v2_repair_03/m2_v2_view_permission_compatibility.csv)
- Full raw requests and responses: local only, under `runs/m2-v2/recovery-20261019/repair-03/`.
