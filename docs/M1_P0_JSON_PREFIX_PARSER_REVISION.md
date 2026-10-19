# M1-P0 JSON Prefix Parser Revision

## Status and scope

This is a new, explicit action-output contract revision prompted by the retained 2026-10-19 engineering preflight response. It supersedes the parser gate only for a newly authorized run; the original NO-GO report and raw failed parse are immutable historical evidence. It does not reinterpret the earlier response as a behavior observation.

The observed output began with the exact empty envelope `<think>\n\n</think>\n\n` followed by one JSON action object. The parser now accepts either (a) one JSON action object directly or (b) that exact empty envelope followed by one JSON action object. The envelope contributes no action fields and is not included in parsed text. Raw request and response bytes remain preserved in the request ledger.

## Strict rejection boundary

The parser still rejects non-empty `<think>` content, any other prefix or whitespace variant, Markdown fences, trailing text, multiple objects, malformed JSON, extra fields, invalid message text, and invalid allocations. It does not search for a `{`, strip arbitrary text, ask the model to repair output, or resend a format failure. An invalid Pilot action remains a failed assigned episode; it is retained and never replaced.

The source of the parser rule is the one retained live counterexample. This is a post-observation protocol revision and must be reported as such. It is not evidence that Qwen3 generally emits this wrapper or that accepting other wrappers is safe.

## New run limits and frozen variables

- New approval identifiers are bound to the user's direct request to repair the JSON-prefix parser and retry. The prior single-use approval and both prior run packages remain unchanged.
- The first execution of this revision loaded the exact server/model but Windows denied the loopback health request with `WinError 10013` before an HTTP request reached llama.cpp. That zero-request package was independently verified. One separately identified environment retry is permitted only from that exact verified zero-HTTP parent; no further infrastructure retry is predeclared.
- The revised run uses a fresh bounded preflight: maximum **6 logical requests / 12 HTTP attempts / 4 generation attempts**. It stops on the first non-retryable compatibility failure.
- If preflight passes, the previously requested Pilot remains bounded at **25 assigned episodes / 95 logical calls / 190 HTTP attempts**, with at most two transport attempts per logical call. There is no comprehension-probe budget and no M2 work.
- Transient transport/timeouts may use the frozen adapter retry policy. Parser/schema failures are non-retryable. No repeated preflight or episode sampling is allowed merely to obtain a syntactically successful response; doing so would condition inclusion on model formatting success.
- Model path and bytes, llama.cpp bytes, endpoint, prompts, schemas, sampling, reward amounts, conditions, seeds and communication order remain frozen. Only the output parser contract revision changes.

## Falsification tests

Offline tests use the exact retained live response and require it to parse to the same ballot as the plain JSON object. Adversarial counterexamples require rejection of non-empty reasoning, altered envelope whitespace, a leading newline, duplicated envelope, Markdown, explanatory prefixes, and trailing text. Both ballot and message actions are tested. The old run's blocker verifier must continue to identify the original parse failure and verify its exact retained bytes.

Reproduce parser tests and old-failure integrity from this checkout:

```powershell
python -m pytest -q tests/test_m1_runtime.py -k "action_parser or retained_live_empty_think"
python scripts/verify_m1_p0_preflight_blocker.py --run runs/m1_p0_local/25ep-pilot-20261019/run-resume-01
python scripts/verify_m1_p0_runtime_start_blocker.py --run runs/m1_p0_local/25ep-pilot-json-prefix-v2-20261019/run
```
