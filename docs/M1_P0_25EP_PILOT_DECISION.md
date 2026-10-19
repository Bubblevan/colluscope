# M1-P0 25-Episode Pilot decision

**Decision: NO-GO for this frozen real-LLM Pilot.** The user authorized a local 25-episode behavior Pilot, but its mandatory compatibility gate failed before episode 1. The full dataset therefore does not exist.

## GO findings

- The 8080 conflict was an unrelated process (`ApplicationWebServer.exe` PID 12152). It was left untouched; the approved 127.0.0.1:8081 listener was used.
- llama.cpp started the selected local GGUF. In the two recorded launches, listener ownership matched the exact launched `llama-server.exe` process and `/health` returned 200.
- `/props` matched the exact model path, server build, context, slots, sampler order and frozen sampling parameters.
- `/apply-template` matched the GGUF's chat template exactly.
- The initial tokenizer implementation was false: its generic GPT-2 ByteLevel boundaries gave 478 IDs while llama.cpp Qwen2 returned 447. A narrow Qwen2 pre-tokenizer correction now matches all 447 IDs in the retained live prompt. The failed original run remains unchanged; the correction is tested against the original raw server token response.
- Offline runtime regression: **152 passed, 1 opt-in host-dependent listener test skipped**. Package-integrity verifier independently checked 50 continuation-run entries and 24 copied-parent entries.
- Spend and privacy boundary: no external API or paid call; no real banking service, user data, or unauthorized reference-repository code used.

## NO-GO findings

- The first actual completion request was an engineering preflight probe, not a Pilot ballot. Its assistant content starts with `<think>\n\n</think>\n\n` before a JSON ballot. The frozen parser rejected the first byte as malformed JSON and preserved the complete raw response.
- Retrying or accepting a modified output format after observing this response would violate the frozen failure policy and make the preflight outcome post-hoc. No wrapper stripping, schema change, prompt rewrite, label change, sample deletion, or second continuation was performed.
- Because preflight stopped on the first strict-parser failure, the other action probes were not sent. Episode requests: **0**. Research episodes: **0/25**. Monitor-eligible episode evidence: none.
- Agreement, collaboration, harmful allocation, incentive comprehension, collusion, detection quality and causal effects are **not measured**. The single engineering probe carries no private treatment and is excluded from behavior data.

## Gate table

| Gate | Decision |
|---|---|
| Correct local model and server bytes | GO |
| 8081 connection and listener ownership | GO |
| Properties, template and tested-prompt tokenizer parity | GO |
| Frozen JSON-only ballot/message output contract | **NO-GO** |
| Start the 25 assigned episodes | **NO-GO** |
| Start M2 detector comparison | **NO-GO / not performed** |

## Research risk and next decision

The observed response proves that this exact frozen configuration can emit text outside the strict JSON action object even with the recorded no-thinking request settings. It does not establish whether that wrapper appears on all or only some requests. The remaining completion probes cannot be used to tune a parser after this failure.

The next useful decision is a protocol review: preserve the JSON-only contract and choose a reviewed runtime/model configuration that satisfies it, or explicitly preregister a new output contract that defines permitted wrapper syntax and its handling. Either option changes the current frozen interface and requires a new user-approved preflight budget before any further model request. This package does not launch that work automatically.

## Reproduction

From this checkout:

```powershell
python -m pytest -q
python scripts/verify_m1_p0_preflight_blocker.py --run runs/m1_p0_local/25ep-pilot-20261019/run-resume-01
```

The second command should return `PASS_PACKAGE_INTEGRITY__NO_GO_PREFLIGHT`. It means the failure evidence is intact and the research gate remains NO-GO. The consumed one-time approval and continuation are recorded under `runs/m1_p0_local/approval-ledger/`; rerunning the live Pilot command is not a valid reproduction.

Source commit at the live continuation: `cd81b8cebc1ccb7107a0ecb16ed1e0414ab09198`. Final evidence-package commit and push identity are recorded after delivery.
