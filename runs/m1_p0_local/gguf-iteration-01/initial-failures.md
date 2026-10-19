# Retained offline test failures

These are failures observed during development of the GGUF adapter. The excerpts below were captured from actual pytest tool output; they are transcribed here because the first exploratory commands were not initially tee'd to disk. No episode/sample was removed, and all affected assertions remain represented in the final tests.

## Run 1

Command: `python -m pytest -q tests/test_gguf_metadata.py tests/test_gguf_tokenizer.py tests/test_openai_compat_llamacpp.py`

Observed summary: `4 failed, 16 passed in 0.38s`.

- `test_default_config_is_denied_and_launch_command_is_only_a_candidate`: helper changed the fake counter's template hash but the test retained the old immutable backend settings; constructor raised `ValueError: GGUF token counter chat_template_sha256 differs from frozen local backend config`.
- `test_malformed_assistant_action_fails_explicitly_and_is_never_repaired`: the adapter correctly returned raw assistant text; strict action parsing occurs in `run_episode`, so the test incorrectly expected `ActionOutputFailure` directly from `RequestAdapter.invoke` and got `Failed: DID NOT RAISE`.
- `test_remote_endpoint_and_mismatched_tokenizer_identity_are_rejected`: implementation returned `base_url must be plain HTTP loopback ending exactly in /v1`; test expected a different error substring (`127.0.0.1`).
- `test_fake_preflight_runs_exact_six_request_sequence_and_parses_all_actions`: preflight reached tokenization then raised `AttributeError: 'LocalLlamaCppBackend' object has no attribute 'tokenizer_metadata'`.

Changes: keep the helper's updated config, test malformed actions at the episode/parser boundary, assert the stable loopback error, and store the tokenizer metadata on the backend. The failure was also useful: the preflight's tokenizer request path really was incomplete.

## Run 2

Observed summary: `1 failed, 19 passed in 0.32s`.

- The six-request fake preflight returned `PASS`, but the test compared only the final URL segment (`completions`) against `chat/completions`. The assertion was fixed to compare the full path; implementation behavior did not change.

## Run 3

Observed summary: `2 failed, 19 passed in 0.36s`.

- Both new preflight tests called the `fake_server_bundle` helper without requesting pytest's `tmp_path` fixture: `NameError: name 'tmp_path' is not defined`. The tests now declare the fixture.

## Run 4

Observed summary: `1 failed, 18 passed in 0.36s`.

- `test_transport_rejects_remote_redirect_targets_and_remote_url_before_dispatch` injected a `FakeOpener` and then tried to inspect default urllib handler objects on it: `AttributeError: 'FakeOpener' object has no attribute 'handlers'`. The test now uses a second backend with the default opener for handler inspection; it still makes no network request.

## Resolution evidence

Final focused suite: `26 passed`; final full repository suite: `128 passed`. See `pytest-gguf-focused-final.log` and `pytest-full-delivery-final.log`. The complete fake preflight stops on a template mismatch, appends a failure record preserving the raw response, and does not send subsequent requests. A tampered runtime DLL is rejected before any fake HTTP call.
