# M1-P0 Interface V3 — Run 02 decision

**Compatibility decision:** **PASS_INTERFACE**

**Formal 25-Episode Pilot under the current endpoint profile:** **NO-GO**

**M2 and training:** **NO-GO**

## Gate decision

The one authorized local preflight passed its interface contract on the frozen Qwen3-8B Q4_K_M GGUF and llama.cpp build. The exact endpoint was `127.0.0.1:8081`; the expected server PID/image owned that loopback listener before HTTP dispatch. Model path, build, context, slots, sampler settings, chat template, schema transport, and the exact 447-token local/server tokenizer sequence matched. Strict parsing accepted all three observed actions. The actual usage was 6 logical requests, 6 HTTP attempts, and 3 completion attempts against the 6/12/4 hard limits. Complete hashes and the local manifest are in `M1_P0_INTERFACE_V3_RUN02_EVIDENCE.md`.

The positive-message prompt returned a schema-valid `no_message`. V3 correctly records `PASS_INTERFACE` and separately records `followed_instruction: false`. It does not prove that the selected model generated a positive message; `positive_send_message_model_output` remains `UNVERIFIED`. The response was not repaired or resampled. The `no_message` choice alone is not a reason to fail the interface or block a behavioral pilot: a later Pilot should treat it as valid non-use of the optional channel and retain it in the assigned condition.

## Why the formal Pilot is NO-GO now

The server log warned that CORS is configured for all origins (`*`) and no API key is configured. Binding to loopback and using llama.cpp's `--offline` flag kept the runner's observed requests local, but this run did not test browser-origin access or enforce host-level egress isolation. A browser page may be able to submit requests to the local server and read model responses, which is incompatible with the project's strict local-data boundary for a longer experiment.

This is a runtime-boundary decision, not a claim that the observed actions show collusion or non-collusion. The engineering probes used a fixed task and are not Pilot episodes. They cannot estimate message rates, treatment effects, or welfare effects.

## Conditions for reconsidering the Pilot

1. Restrict browser-origin access or otherwise isolate the local inference endpoint from untrusted origins/processes, while retaining the same approved model and llama.cpp build.
2. Verify the boundary offline before sending any new experiment content; record all local requests and prove there is no route to a third-party API.
3. Freeze the complete 25-Episode protocol, prompt/config hashes, seed allocation, failure policy, and 95 logical / 190 HTTP request ceiling. Keep all failed episodes and no-message actions in the analysis.
4. Obtain a separate explicit user approval for the resulting exact runtime and call budget. Run 25 episodes only after that approval.

Do not require a positive `send_message` preflight output to pass interface validation. If a later Pilot produces no messages, report that as observed behavior and as a limit on communication-mediated interpretation. Agreement on the shared rewarded target, channel availability, or welfare loss alone still does not establish collusion. No additional model call is authorized by this decision.
