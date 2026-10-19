# M1-P0 Interface V3 — decision

**Current decision:** **PASS_INTERFACE for the one authorized V3 Run 02 preflight. NO-GO for the formal 25-Episode Pilot under the current endpoint profile, M2, and training.**
**Preflight source commit:** `2f495ffd4aa7e7b4982587e00818b2d282da8b4c`
**Local model-completion attempts:** 3; paid/external API calls: 0

## Gate-by-gate decision

| Gate | Decision | Evidence and limit |
|---|---|---|
| Baseline and historical failures | **PASS** | Clean target checkout began at the specified remote topic SHA. Strict-parser, zero-HTTP, and action-mismatch NO-GO packages reverified after the source changes; their original counts and labels remain intact. |
| Schema vs action-choice separation | **PASS offline and live** | Run 02 returned valid `no_message` to the `send_message` probe and reported `PASS_INTERFACE` plus `followed_instruction: false`. The action was not called a JSON/schema failure and was not resampled. |
| Strict invalid-output handling | **PASS offline** | Malformed message output remains terminal, retained, and unrepaired; the next completion is not dispatched. Existing ballot/prefix/parser counterexamples still pass. |
| Positive message software path | **PASS offline only** | Fake HTTP completion reaches runtime parsing, A-to-B delivery, sender self-history, C exclusion, and permission-controlled evidence export. It does not establish live model action choice or actual server `oneOf` behavior. |
| Stale approval and protocol isolation | **PASS** | The consumed standalone 8081 approval is rejected before output creation. Pre-V3 evidence cannot be continued as a V3 run. Pilot approval IDs in the retained ledger are consumed. |
| Full offline regression | **PASS** | Final repository suite: 171 passed, 1 host-dependent skip; the 3 verifier tamper counterexamples and separate opt-in Windows owner-table test passed. The initial six local socket-canary failures remain recorded. |
| Actual llama.cpp V3 interface compatibility | **PASS_INTERFACE** | Run 02 verified `/props`, `/apply-template`, `/tokenize`, all 447 token IDs, and three strict completion parses under the actual frozen server. Six logical/HTTP requests were used, with three completion attempts. Full hashes are in `M1_P0_INTERFACE_V3_RUN02_EVIDENCE.md`. |
| Positive `send_message` generation by the selected model | **UNVERIFIED** | The retained real completion returned valid `no_message`; no favorable resampling is permitted. The software branch is separately covered with fake transport. |
| Formal 25-Episode Pilot | **NO-GO under current endpoint profile** | Run 02 logged llama.cpp's warning that CORS allows all origins and no API key is configured. Browser-origin access and host egress isolation were not tested. A separate Pilot approval is required after the local endpoint boundary is hardened and verified offline. |
| M2 / detector comparison | **NO-GO** | No monitor evaluation or detector comparison is authorized or run. |

## Scientific interpretation

The observed V2 completion was a schema-valid `no_message` action to a message-stage prompt asking for `send_message`. It is evidence of an action-choice mismatch under V2's probe instruction, not a JSON/schema failure. The parser accepted the exact empty prefix and the action. The observation does **not** establish a positive send path in the selected live model, a refusal propensity beyond this single probe, message delivery, agent behavior, agreement, or collusion.

V3 treats the interface question and instruction-compliance question separately. This reduces an invalid inference from “model chose the other legal branch” to “schema incompatible.” It does not guarantee that any future detector or analysis will be free of condition leakage. The M1-R shared-target confound remains: A and B can independently choose their commonly rewarded target without communication, and chat arms consume an extra message-stage turn even when no message is sent.

## Remaining blocker and next action

The compatibility gate is complete. Before a 25-Episode Pilot, restrict browser-origin access or otherwise enforce local endpoint isolation, verify that boundary offline, freeze the exact Pilot protocol and 95/190 ceiling, and obtain a separate explicit approval. The valid `no_message` outcome is not an interface blocker and must remain a valid action in any later analysis. No additional model call is authorized by this decision.

## 2026-10-19 Run 02 result addendum

The status above records the earlier V3 review decision. The user later authorized exactly one local Interface V3 compatibility preflight under `docs/M1_P0_INTERFACE_V3_RUN02_PROTOCOL.md`. It completed as **PASS_INTERFACE** on the frozen model/runtime at `127.0.0.1:8081`: 6 logical requests, 6 HTTP attempts, 3 completion attempts, and exact parity on all 447 tested tokenizer IDs. A valid `no_message` response to the engineering prompt asking for `send_message` passed the interface gate and was recorded separately as `followed_instruction: false`; no resampling occurred. Full hashes and raw local artifact paths are in `M1_P0_INTERFACE_V3_RUN02_EVIDENCE.md`.

**Formal 25-Episode Pilot recommendation: NO-GO under the current endpoint profile.** The server log warned that CORS allows all origins and no API key is configured. Although the run's requests were loopback-only and `--offline`, browser-origin access and host egress isolation were not tested. Before a separate Pilot approval, restrict or otherwise enforce the local endpoint boundary and verify that control offline. The `no_message` response is not itself a Pilot blocker; any later Pilot must count it as a valid behavioral choice. M2 and training remain NO-GO, and this addendum does not authorize starting any further run.
