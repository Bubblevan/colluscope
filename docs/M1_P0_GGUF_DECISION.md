# M1-P0 GGUF Runtime Decision

> **Historical decision record.** This entry records the earlier owner-table blocker and is preserved as written for audit history. Later approved 8081 preflight runs resolved the connection/ownership gate and then stopped on a strict JSON action-format failure before episode 1. The latest evidence and disposition are in [`M1_P0_25EP_PILOT_EVIDENCE.md`](M1_P0_25EP_PILOT_EVIDENCE.md) and [`M1_P0_25EP_PILOT_DECISION.md`](M1_P0_25EP_PILOT_DECISION.md).

**Decision:** **GO for offline implementation review. NO-GO for claiming the bounded local preflight passed, for M1-P0/P1 research calls, and for M2.** The user authorized a single bounded preflight on 127.0.0.1:8081. llama.cpp loaded the selected GGUF and logged that it was listening, but the runner's process-owner gate timed out without sending an HTTP request. The independent listener observations and in-run gate disagreed; the gate has not been shown reliable enough to protect prompts.

## GO: offline integration package

Evidence supports review of a local llama.cpp adapter candidate:

- The user-provided GGUF checkpoint path, size, and SHA256 were verified. The model choice is fixed as Qwen3-8B Q4_K_M GGUF.
- Static tokenizer/template extraction and candidate rendering work locally without loading model weights.
- The adapter uses the pinned llama.cpp request shape, strict response checks, loopback-only transport, no proxy, no redirect, no model fallback, recorded request/response/error data, bounded retry, and independently enforced 95-logical/190-attempt caps.
- Fake HTTP adversarial tests cover schema rejection without fallback, timeouts, 5xx retry, invalid output, alias/usage/token drift, reasoning leakage, endpoint restrictions, runtime DLL drift, and hard call ceilings.
- The offline M0/M1-R artifacts independently verify. M1-R's scripted Mock behavior is explicitly not behavioral evidence.

Exact commands and retained output are in [`M1_P0_GGUF_COMPATIBILITY_EVIDENCE.md`](M1_P0_GGUF_COMPATIBILITY_EVIDENCE.md).

## NO-GO: live compatibility and research calls

The user's 2026-10-19 request authorized only the frozen six-logical-request compatibility preflight (at most 12 HTTP attempts and four generation attempts), with local retention and no paid API. The original 8080 listener remains untouched. A run-scoped config used 8081. The selected server process image and PID were recorded, and its raw stderr logged model load and `listening on http://127.0.0.1:8081`. However, the runner's startup owner poll returned no rows for 180 seconds and failed closed before `/props`; an independent read-only shell observation during the run showed PID 12636 listening on 127.0.0.1:8081. No HTTP request, completion, or research episode was created. This inconsistent owner attestation is a valid NO-GO counterexample. A fallback owner-table implementation also returned access denied; a `netstat` child-process canary failed once and passed once. Do not treat the later isolated pass as erasing the failures.

The server log proves that the frozen GGUF was loaded by the selected binary, not that its tokenizer, template, schema, sampling, reasoning, or action behavior is compatible. `nvidia-smi` recorded 15,855 MiB free before launch, 10,395 MiB in periodic samples while the server was alive, and 15,533 MiB after shutdown. These are host-wide observations; they do not attribute GPU memory to this process. The sampler incorrectly labeled its in-run samples `prelaunch`, so no per-phase GPU-fit claim is supported.

The preflight is specified as six logical requests, at most 12 HTTP attempts and four generation attempts. It must stop on the first mismatch. Approval of this preflight does not authorize the 25-episode pilot. Pilot authorization would separately need the exact model/runtime/tokenizer/sampling/context and a call/retention/auditor budget. No pilot or M2 work follows automatically.

The first port-conflict attempt remains under `runs/m1_p0_local/gguf-preflight-iteration-02/`. The authorized 8081 startup attempt and its hashed output package are under `runs/m1_p0_local/gguf-preflight-iteration-03/run/`; test and owner-query failures are retained in the sibling `logs/` directory. The new runner code has not itself completed a verified owner check against llama.cpp. A future attempt requires review of an instrumented, stable PID-owner gate and phase-correct telemetry. No further service start is authorized by this decision.

## Research validity limitations preserved

- A and B share the same rewarded target, so their independent agreement in the no-chat private-bonus arm is compatible with parallel independent choice.
- A/B chat conditions include an extra pre-ballot request even when the action is `no_message`; the contrast estimates a bundled communication-turn opportunity, not the effect of message content in isolation.
- A task-score rule or public bonus is visible evidence about the task. It does not reveal private treatment assignment and does not itself establish collusion.
- The runtime cannot infer intent, mental agreement, comprehension, or model utility from an action. Intervention labels and actual-action labels must remain separate.

## Stop condition

Stop at offline llama.cpp integration review. Await human review of the failed-preflight evidence and revised owner-attestation approach. Do not start another server, M1-P0 real-agent pilot, or M2 automatically. Full-pilot and M2 authorization remain false.
