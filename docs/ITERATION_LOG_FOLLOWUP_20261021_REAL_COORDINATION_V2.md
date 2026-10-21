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

The corrected V2 freeze is eligible for the already approved 40-request batch, subject to pushing this exact commit first. After push, execute the four fact controls first; any wrong, invalid, truncated, interrupted, non-200 or identity-mismatched control stops the remaining 36. No Qwen, retry, replacement, extra probe, or external fallback.

## REPORT

Current V2 status: frozen and registered, offline checks PASS, no real model calls yet. Next action: push the freeze, then run the bounded DeepSeek batch immediately and preserve raw provider evidence locally.
