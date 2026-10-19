# M1-P0 Interface V3 — decision

**Decision:** **GO for human review of the offline V3 protocol and implementation. NO-GO for any real-model preflight, M1-P0/P1 behavior episode, or M2 work.**  
**Baseline:** `657eab90356ce9137c2988aacb4b5b10d0402c28`  
**Real model calls in this cycle:** 0

## Gate-by-gate decision

| Gate | Decision | Evidence and limit |
|---|---|---|
| Baseline and historical failures | **PASS** | Clean target checkout began at the specified remote topic SHA. Strict-parser, zero-HTTP, and action-mismatch NO-GO packages reverified after the source changes; their original counts and labels remain intact. |
| Schema vs action-choice separation | **PASS offline** | The valid `no_message` response to a `send_message` request now yields `PASS_INTERFACE` plus `followed_instruction: false`. The requested action is extracted from the actual prompt and cross-checked with metadata before HTTP. This corrects the type of failure without changing the historical run's NO-GO verdict. |
| Strict invalid-output handling | **PASS offline** | Malformed message output remains terminal, retained, and unrepaired; the next completion is not dispatched. Existing ballot/prefix/parser counterexamples still pass. |
| Positive message software path | **PASS offline only** | Fake HTTP completion reaches runtime parsing, A-to-B delivery, sender self-history, C exclusion, and permission-controlled evidence export. It does not establish live model action choice or actual server `oneOf` behavior. |
| Stale approval and protocol isolation | **PASS** | The consumed standalone 8081 approval is rejected before output creation. Pre-V3 evidence cannot be continued as a V3 run. Pilot approval IDs in the retained ledger are consumed. |
| Full offline regression | **PASS** | Final rerun after the pinned-schema counterexample: 165 passed, 1 host-dependent skip. The prior 164-pass result is also retained. See raw logs and exact commands in `M1_P0_INTERFACE_EVIDENCE.md`. |
| Actual llama.cpp V3 interface compatibility | **UNKNOWN / NO-GO** | Pinned upstream docs and converter source statically document the direct schema request form and conversion of `oneOf` branches into a union grammar. The frozen message branches are disjoint by distinct required `type.const` values. No V3 server was started or contacted, so request acceptance and runtime enforcement are still unverified; V2 compatibility does not prove V3 positive-message output. |
| Positive `send_message` generation by the selected model | **UNVERIFIED** | The retained real completion returned valid `no_message`; no favorable resampling is permitted. The software branch is separately covered with fake transport. |
| M1-P0/P1 behavior study | **NO-GO pending separate approval** | No episode was generated. Requires a new immutable approval covering exact model/runtime, schema, prompt, sampling, call and compute ceiling, retention, and permissions. V3 review is not that approval. |
| M2 / detector comparison | **NO-GO** | No monitor evaluation or detector comparison is authorized or run. |

## Scientific interpretation

The observed V2 completion was a schema-valid `no_message` action to a message-stage prompt asking for `send_message`. It is evidence of an action-choice mismatch under V2's probe instruction, not a JSON/schema failure. The parser accepted the exact empty prefix and the action. The observation does **not** establish a positive send path in the selected live model, a refusal propensity beyond this single probe, message delivery, agent behavior, agreement, or collusion.

V3 treats the interface question and instruction-compliance question separately. This reduces an invalid inference from “model chose the other legal branch” to “schema incompatible.” It does not guarantee that any future detector or analysis will be free of condition leakage. The M1-R shared-target confound remains: A and B can independently choose their commonly rewarded target without communication, and chat arms consume an extra message-stage turn even when no message is sent.

## Remaining blocker and next action

The V3 package is **ready for human review only**. Do not reuse prior one-time approval IDs. The single highest-value next action is review of the frozen V3 gate and, if accepted, a separate user-approved run-scoped protocol fixing model/runtime/tokenizer/template, sampling, output/context limits, endpoint, 6/12/4 ceilings, local compute bound, retention, and auditor permission. That approval would authorize only the stated preflight; a 25-episode pilot requires its separate approval and immutable 95/190 ceiling. No call is initiated by this decision.

## 2026-10-19 Run 02 authorization addendum

The status above records the earlier V3 review decision. The user has since explicitly authorized **one** local Interface V3 compatibility preflight under `docs/M1_P0_INTERFACE_V3_RUN02_PROTOCOL.md`, using the frozen GGUF/runtime and `127.0.0.1:8081` with ceilings of 6 logical requests, 12 HTTP attempts, and 4 completion attempts. This authorization does not approve a Pilot episode, M2, or model training. The unique run approval is consumed at most once; the separate Run 02 evidence and decision will supersede the earlier `UNKNOWN / NO-GO` compatibility line after execution.
