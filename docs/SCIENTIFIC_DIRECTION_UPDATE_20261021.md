# Scientific Direction Update — M4 B5 Raw-Response Audit

**Purpose:** continue the evidence-led review of the B5 public-to-privileged response anomaly.  
**Activity this update:** offline-only; zero model/API requests.  
**Frozen baseline:** registered M4 B5 context-sensitivity campaign, closed `AMBIGUOUS / INCONCLUSIVE`; its 232-request authorization is consumed.

## What changed in our understanding

The prior 232-request campaign did not show the preregistered directional A1 pattern, and exact historical/current Public-only requests frequently returned different labels. This update preregistered a zero-call test of the most immediate alternative: whether those label differences were created downstream of the model response.

Across all 48 selected historical/current exact-request pairs, raw tool-call labels differed in 19 pairs, while every raw label and evidence-reference list matched its stored prediction under an independent strict parser. This supports finite response-level variation in the retained observations and weakens the parser/scorer-mismatch explanation for those rows. It does not show why a response varied or why the Public and Privileged views differed.

The response changes were concentrated in the Public-only repeats: 17/24 label differences, 15 of which were `insufficient_evidence→present`; the Privileged repeats had 2/24 differences. Public-only evidence references were identical in all 24 pairs even when labels changed. This is a descriptive field pattern, not evidence that the label changes were correct or that the model ignored the evidence.

## Research direction decision

Keep the main scientific question on whether monitor conclusions are justified by the permitted evidence and how those conclusions respond to controlled evidence-view changes. Treat the deterministic public-welfare rule as the reference baseline. The current public-harm target can be computed from matrix, ballots, settlement, and welfare; a language model's output is not an independent gold standard.

Do not switch back to the paused synthetic 108-call sequence task as the headline. The B5 exact-request audit addresses measurement integrity for the central 20/24 historical view-change observation, but it is not itself a monitor-capability result. A causal statement about private-message content remains unidentified because the earlier view comparison jointly changed text, event records, permission/completeness cues, and token length. The provider alias also lacks an immutable weights identity.

## Highest-value next question

If further inference is authorized, ask whether the original-message versus neutral-message response contrast exceeds within-identical-input response variability. Repeat a one-factor evidence-view design with interleaved calls and a fixed schedule. A possible bounded screen is 24 M4 contexts × 3 views (Public-only, privileged with frozen neutral text, privileged with original text) × 3 randomized repeats = 216 physical requests. This is a new proposal, not a continuation of the closed approval.

Keep every assigned request in the denominator; do not replace failures or choose a favorable response. Stop on serving identity drift, raw-input hash mismatch, permission leakage, any nonterminal request without a durable record, or budget/price boundary. Interpret as inconclusive if unchanged-input variation is comparable to the view contrast. Even a positive response contrast would establish only response sensitivity for these fixed cases, not semantic understanding, agent coordination, collusion, or intent.

## Independent challenge and remaining uncertainty

The independent scientific critic reviewed sanitized outputs and analysis code without opening raw runs. The critic confirmed that v3 counts support the narrow finite label-variation statement, then flagged missing independent schedule-hash enforcement, exact permission denominators, and duplicate-ID rejection. These were added with counterexample tests; the public API now requires the frozen schedule path; v5 reproduces the same substantive counts. The final review found no remaining material flaw in the public audit path. The critic did not rerun the tests or inspect raw runs.

The auditor's source snapshot matches, the exact schedule hash matches the preregistration, all 48 outputs strictly parse, and the registry audit passes. One earlier test failure and one amendment timestamp error are retained with append-only explanations. No raw request, response, or private-message text was added to tracked outputs.

## Reproduction

See [M4 B5 raw-response evidence](M4_B5_RAW_RESPONSE_REPEATABILITY_EVIDENCE.md) and [decision](M4_B5_RAW_RESPONSE_REPEATABILITY_DECISION.md). Reproduction uses the frozen schedule builder, the versioned v4 replay command, the nine focused tests, and `researchctl audit`; it performs no inference.
