# Autoresearch Follow-up — raw-response verification of ballot replay (2026-10-21)

## INSPECT

The first action-level replay independently recomputed settlement from `parsed_assignment`, but did not independently verify the stored parser fields against the original model responses. Calling that replay a raw-response audit would overstate its scope.

## SPECIFY

For every ballot, reparse the original response text with the frozen action schema, retain the observed empty reasoning wrapper only, fail explicitly on malformed/extra output, and compare the raw-text allocation with the parser field. Recompute plurality and chair tie-break from the reparsed raw-text allocation. A single mismatch must stop the replay and remain visible.

## IMPLEMENT / RUN

Preserved v1 source/results and added `scripts/analyze_m1_100_ballot_decomposition_v2.py` plus a separate output directory. The v2 analyzer reparsed **225/225** raw ballot responses, matched **225/225** stored parser fields, and independently reproduced **75/75** settlements. No new model/API requests occurred. Targeted matrix, prompt-profile, registry, and runtime offline gates remain documented separately; this v2 replay did not invoke them.

## ADVERSARIAL REVIEW

The v2 replay removes the parser-field dependency for the ballot assignment and settlement calculation. It still analyzes one deterministic fixed Qwen corpus, not independent stochastic draws. The 9/15 joint A/B target-ballot pattern remains compatible with parallel choice under the shared target; neither the raw message content nor the ballot match identifies intent.

## DECIDE / REPORT

Use v2, not v1, as the raw-response source for action-level claims. Keep the original candidate protocol and all v1 outputs unchanged. The M1 v3 amendment remains prospective and the live run remains unregistered and unauthorized. Next action: refresh the review snapshot and approval request to include the raw-response replay; no model call is authorized by this offline audit.
