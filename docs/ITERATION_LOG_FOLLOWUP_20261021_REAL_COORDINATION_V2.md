# Iteration follow-up — DeepSeek real coordination pilot V2

## INSPECT

V1 was registered with an experiment ID ending `-40-v1`, while its runner looked for a directory without `-40`. Exact check-only stopped before constructing the API client. V1 is preserved and closed as `EXECUTION_BLOCKED`, with zero calls. This V2 corrects the path and checks the runtime, preregistration, registration manifest, schedule and authorization experiment IDs agree.

## SPECIFY / FALSIFIERS

- Wrong answers at each of the four first-position fact controls must stop all later requests.
- Truncated or invalid message actions must block only their scheduled descendants; no fallback action or retry may appear.
- No-delivery and neutral arms must not receive the actual first proposal; actual delivery must route the proposal and reply only to the intended counterpart.
- Independent replay must detect any changed request bytes even when the attempt hashes are rewritten to match.
- The experiment, preregistration and registration IDs must match the exact filesystem path before dispatch.

## IMPLEMENT / RUN

V2 uses versioned module/scripts/tests/protocol, schedule/config and registration IDs. Raw traffic uses the pre-existing ignored `/logs/` directory. `python -m py_compile` passed; `python -m pytest -q tests/test_deepseek_real_coordination_v2.py tests/test_deepseek_real_coordination_analysis_v2.py` passed **17 tests**, including path alignment and all four stop positions. `freeze_deepseek_real_coordination_v2.py --check` passed. `run_deepseek_real_coordination_v2.py --check-only` printed `PASS_OFFLINE_PREFLIGHT` with 0 model calls, the frozen endpoint/alias, 40-request cap and $0.50 peak reservation, but its process returned exit code 2 because the CLI maps a missing `stop_status` to non-exhausted. This exit-status defect is retained and disclosed; the preflight payload and checks passed. `researchctl.py audit` passed with no errors; existing cumulative use remains 1,156 calls / $0.133568658 and the new V2 batch reserves no more than 40 calls / $0.50. No model request has been made for V2.

## ADVERSARIAL REVIEW

Same-call-count arms do not remove prompt-length, wording, salience, or call-order differences. The neutral arm has a possible genuine return reply. Shared +20 HH incentives can create parallel choices without communication. One deterministic same-model endpoint and three fixed matrices do not identify a population causal effect or latent intent. Reports will retain these limitations and all assigned rows.

## DECIDE

The exact freeze was pushed as `31b7ebf3aa82b7dd656b3b944183fa0a92a23fc3` before the authorized invocation. The first control could not reach the provider because local DNS resolution failed. The frozen zero-retry/no-replacement rule and first-control gate require stopping; no other request may be dispatched under this batch.

## REPORT — live attempt

One request was reserved and handed to transport; it failed before HTTP connection (`getaddrinfo failed`, Windows error 11001). The request bytes match the start-row hash. There is no HTTP response, model output, or billed cost. Thirty-nine assigned requests remain unattempted. The runner's follow-on validation error was caused by a missing `request_sha256` field on the transport terminal row; this is preserved as a distinct runtime defect rather than repaired in the frozen code. See the V2 evidence, decision, and `ATTEMPT_001_TRANSPORT_FAILURE.md`. No behavioral hypothesis update is warranted.
