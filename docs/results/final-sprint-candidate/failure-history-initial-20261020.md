# Final Sprint candidate offline failure history

These failures were retained rather than filtering tests or converting them to success. Later entries identify the fix and rerun.

## Initial source-identity check

Command: Python call to load the frozen M4 live config and run verify_frozen_assets.

Observed error before any server launch or generation:

    KeyError: 'tokenizer_sha256'

Cause: the v3 runtime config deliberately followed the base config field name sha256, while the verifier indexed tokenizer_sha256. Fixed by mapping the verified GGUF tokenizer digest to the frozen sha256 field. Added a success-and-mismatch unit test and then verified the actual local model/runtime assets.

## Focused suite collection attempt

Command: python -m pytest -q tests/test_m4_live_runtime.py tests/test_sprint_monitor_runtime.py

Observed: collection stopped on an unclosed parenthesis in the newly added resume-corruption fixture. No tests ran in this attempt. Fixed the fixture with an explicit retained-row list before writing the temporary test ledger.

## Monitor fake-live resume attempt

Command: python -m pytest -q tests/test_sprint_monitor_runtime.py

Observed: 22 passed. One resume test failed because the transport-error response was hashed as compact JSON but persisted using the pretty-print helper, so the append-only terminal hash did not match its response file. Fixed by persisting the exact compact bytes used for the response hash.

## Monitor fake-live identity/cost attempt

Command: python -m pytest -q tests/test_m4_live_runtime.py tests/test_sprint_monitor_runtime.py

Observed: 48 passed, 2 failed. One expected the frozen-off error but received the earlier injected-transport guard; reordered validation so the configured authorization gate is reported first. One fake-live resume expectation counted the persisted transport-error receipt as if it were a raw provider response; the byte-persistence defect above was the root cause.

## Latest focused attempt before final correction

Command: python -m pytest -q tests/test_m4_live_runtime.py tests/test_sprint_monitor_runtime.py

Observed: 51 passed, 1 failed. The incomplete-start fixture correctly had one reserved fake transport attempt slot, but the assertion incorrectly expected zero slots. The test also verified that the injected fake transport itself was never called. Corrected the assertion to distinguish a reserved attempt slot from an actual physical HTTP request.

## Initial tokenizer verification suite

The first focused M4 HTTP test run without elevated loopback socket permission was blocked by Windows WinError 10013. One additional hard-cap test fixture exposed an UnboundLocalError and was corrected. Elevated reruns bind only ephemeral 127.0.0.1 fake servers; they do not launch llama.cpp or access an external provider.

## Portable full-suite redirect fixture failure

Command: `python -m pytest -q` with restored ignored historical data and without the opt-in host listener test.

Observed: **445 passed, 1 failed, 1 skipped** in 205.83 seconds. The failure was `test_monitor_http_transport_does_not_forward_authentication_through_redirect`, which raised Windows `WinError 10053` while reading the local test server's 302 response. A focused rerun reproduced it. The fake handler did not consume the declared POST request body before replying; on this host that left unread bytes and caused the socket to be reset. The production redirect policy was not the failure.

Correction: both local fake handlers now consume `Content-Length` bytes before returning. The regression remains an actual HTTP transport check: it requires the 302 response, verifies the Authorization header reached only the configured origin, and verifies the redirect sink received no request. The failed full-suite log and focused failure remain preserved; rerun the focused test and entire suite after this fixture correction.

## Runtime identity receipt label correction

The first generated `runtime-identities.json` mislabeled M4's 24 assigned groups and 264 attempt cap with the prefix `m1_`. The original is preserved as `runtime-identities-initial-mislabeled.json`; the corrected receipt uses `m4_assigned_groups` and `m4_hard_generation_attempts`. Values, asset hashes, and configuration hashes did not change. This was a receipt-labeling error, not a runtime or experiment result.
