# M1-P0 local Qwen Pilot — evidence and stop record

> **Historical run record.** This NO-GO applies to the original JSON-only parser and its consumed approval. A later user request initiated the separately frozen parser revision in [`M1_P0_JSON_PREFIX_PARSER_REVISION.md`](M1_P0_JSON_PREFIX_PARSER_REVISION.md); any resulting run has its own authorization, call ledger, and evidence package. No result from the revision may overwrite or reinterpret this record.

**Result: NO-GO before research episodes.** The requested 25-episode dataset was not produced. The exact local model and server connect successfully on the approved loopback port, and tokenizer parity was corrected, but the first frozen-schema action probe returned non-JSON wrapper text. The frozen strict parser rejected it, so the runtime stopped at preflight as specified. No prompt, schema, parser, label, reward, condition, or acceptance threshold was changed to obtain a pass.

## What the two live attempts established

The frozen port 8080 was already owned by unrelated `ApplicationWebServer.exe` PID 12152. It was left untouched. The user-selected port 8081 was used throughout.

The first Pilot entry launched the exact llama.cpp process and model. Listener ownership was attested as the launched `llama-server.exe` PID 53632; `/health` returned HTTP 200. `/props` matched the frozen checkpoint path, server build, context, slot count and sampler configuration. `/apply-template` matched the GGUF template byte for byte. The tokenizer check exposed a genuine implementation mismatch: generic GPT-2 ByteLevel produced 478 token IDs while llama.cpp's Qwen2 tokenizer produced 447. The first differing boundary was `pre-vote`. The run stopped before any completion: 3 setup HTTP requests, 0 generated responses, and 0 episodes. The original records remain at `runs/m1_p0_local/25ep-pilot-20261019/run/`.

The tokenizer was corrected to apply Qwen2's punctuation/word pre-tokenization before byte mapping. A regression replays the saved server response and asserts all 447 IDs match; the prior generic GPT-2 implementation is asserted to fail on the same input. The original failed run was preserved and copied into the continuation package.

The one permitted continuation reused the three successful setup responses after validating the copied parent manifest, source commit, exact request bodies/responses, prompt evidence, model/server hashes, exact server command and listener identity. It revalidated all 447 token IDs and dispatched one ballot-shaped **engineering preflight probe**. Qwen3 returned assistant content beginning with:

```text
<think>

</think>

{
  "type": "ballot",
  ...
}
```

The response had `finish_reason=stop`, `prompt_tokens=447`, and `completion_tokens=42`. The request explicitly used `enable_thinking=false` and `reasoning_format=none`; the server properties reported `reasoning_in_content=false`. Even though the wrapper is empty, it is text outside the frozen JSON object. The strict parser rejected it at byte 0 and preserved the raw response. It was not stripped, repaired, or retried. Preflight stopped immediately; the other two action probes were not sent.

## Scope and counts

- Model: Qwen3-8B Q4_K_M GGUF, local file SHA256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- Runtime: llama.cpp 10068, commit `571d0d540`, server SHA256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`, 53-file runtime bundle SHA256 `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`.
- Environment: Windows 11 build 10.0.26200; Python 3.12.4; pytest 9.1.1; tokenizers 0.19.1; Jinja2 3.1.4.
- Sampling/config: temperature 0, top-p 1, top-k 0, min-p 0; context 4096; frozen sampler order `top_k;top_p;min_p;temperature`; zero external API ceiling. Run-scoped config SHA256 `74942946c2b9aadf6fab5723aeb00be364366af9e5ffdfd2eb47df1466e01c9b`.
- Cumulative bounded preflight: 4 logical requests, 4 counted HTTP attempts, 1 completion attempt out of the frozen 6/12/4 maximum. The two readiness `/health` requests are logged separately. The full Pilot budget remained unused: 0/25 episodes, 0/95 logical Pilot requests, 0/190 Pilot HTTP attempts, 0 paid calls and 0 external calls.
- No condition was assigned to a research episode. No researcher T/B/E episode rows or monitor evidence were created. The preflight ballot is an engineering compatibility probe, not a behavioral sample.
- No agreement, coordination, collusion, detector performance, treatment effect, or model capability claim is supported.

## Artifact identities and verification

The source freeze used for the tokenizer fix and continuation was commit `cd81b8cebc1ccb7107a0ecb16ed1e0414ab09198` on `codex/m1-p0-local-qwen-integration`. Its pre-run full suite returned 151 passed and 1 opt-in live listener test skipped. The final repository suite after adding the blocker verifier returned **152 passed, 1 skipped**; raw output is `runs/m1_p0_local/pilot-iteration-00/pytest-final-no-go.log`. A closeout rerun transiently encountered six Windows `WinError 10013` loopback mock-test failures; with no source change, the identical suite then returned **152 passed, 1 skipped in 15.41s**, retained at `runs/m1_p0_local/pilot-iteration-00/pytest-restricted-loopback.log`. This was test-host socket behavior, not a model call or a change to the research gate.

- First failed preflight manifest: `runs/m1_p0_local/25ep-pilot-20261019/run/manifest.json`, SHA256 `9b5d0ec05ea8171b4c4d4dfc06295905b0c0a06bae65da35f8fac05b51050b15`.
- Continuation manifest: `runs/m1_p0_local/25ep-pilot-20261019/run-resume-01/manifest.json`, SHA256 `008c58a770248fad6d22aae926bbcd8aaadc73caeccb3954bac76cbed13abbd2`.
- Continuation raw preflight ledger: `runs/m1_p0_local/25ep-pilot-20261019/run-resume-01/preflight/requests.jsonl`, SHA256 `49713fd4bda82bc75bb9ffab0e99f8992975b888d5e83f40b1222abad00224d5`.
- The built-in complete-Pilot verifier records `FAIL` because no 25-row T/B/E dataset exists. This is the expected research stop, not an artifact-hash finding. The separate package verifier returns `PASS_PACKAGE_INTEGRITY__NO_GO_PREFLIGHT` after checking **50 current-run manifest entries and 24 copied-parent entries**. Its output is `runs/m1_p0_local/25ep-pilot-20261019/preflight-blocker-verification.log`.

Reproduce offline verification from this checkout:

```powershell
python -m pytest -q
python scripts/verify_m1_p0_preflight_blocker.py --run runs/m1_p0_local/25ep-pilot-20261019/run-resume-01
```

The original live invocation is retained in `pilot-console.log`; the bounded continuation invocation is retained in `pilot-continuation-console.log`. The approval and one continuation are single-use and consumed. Do not rerun either command as a way to obtain different output.

## Frozen gate disposition

| Gate | Evidence | Disposition |
|---|---|---|
| Loopback endpoint and exact listener | 8081 owner PID matched launched binary; `/health` 200 | PASS |
| Model/runtime identity and loading | GGUF, server and bundle hashes match; server log says model loaded | PASS |
| Frozen model properties | `/props` matched checkpoint/build/context/samplers | PASS |
| Chat-template parity | `/apply-template` exact match | PASS |
| Tokenizer parity | corrected Qwen2 path matches all 447 saved server IDs | PASS for the tested prompt |
| Strict JSON action contract | first action response contains text outside JSON; parser rejects and retains it | **FAIL** |
| 25 assigned research episodes | gate stopped before episode 1 | **NOT RUN / NO-GO** |
| External or paid calls | 0 | PASS |

The connection problem is resolved on port 8081. The exact frozen model/runtime/prompt/parser combination is not compatible with the strict JSON-only action contract on the one tested action. The observed wrapper could be model-emitted empty reasoning syntax; one probe cannot establish how often it occurs. It is still a concrete counterexample to this preflight contract.
