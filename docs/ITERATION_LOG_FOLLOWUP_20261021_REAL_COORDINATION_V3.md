# Iteration follow-up — DeepSeek real coordination V3

## INSPECT

The previous V2 batch stopped on its first request: local name resolution failed before HTTP, and a separate runtime defect then rejected the terminal record because it omitted the request hash. V2 has no model response. The highest-value uncertainty is whether the official endpoint can now be reached and whether real agents' message delivery changes ballots beyond the shared-reward baseline.

## SPECIFY

- If a simulated transport terminal omits `request_sha256`, the runner must verify request bytes against the unique `attempt_started` hash, terminalize the request, and stop without a second call.
- Any control failure must leave 39 or more assigned rows explicitly unattempted and must issue no game request.
- A real dispatch may proceed only after push, with four delivery controls first; one failed control ends the batch.
- The competing explanation is that both agents independently target the shared +20 outcome without relying on peer communication.

## IMPLEMENT

Created a separate V3 experiment identity, unique request namespace, frozen schedule/config, wrapper runner, protocol, authorization and preregistration. V2 raw files, code, registration, and closure were left unchanged. V3 runner defaults to offline mode and requires `--execute` to send any request. It verifies transport-failure bytes against the immutable start-row hash.

## RUN

- TLS-only official-host check: TLS 1.3 succeeded, with no HTTP, credential, prompt, or inference.
- `python -m py_compile ...v3.py`: exit 0.
- `python -m pytest -q tests/test_deepseek_real_coordination_v3.py tests/test_deepseek_real_coordination_v2.py tests/test_deepseek_real_coordination_analysis_v2.py`: **22 passed**.
- `python scripts/freeze_deepseek_real_coordination_v3.py --check`: `PASS_FREEZE_CHECK`.
- `python scripts/run_deepseek_real_coordination_v3.py --check-only`: `PASS_OFFLINE_PREFLIGHT`, 0 calls, exit 0.
- `python scripts/researchctl.py audit`: PASS, no errors; V3 is the sole open preregistered experiment.
- V3 live requests at this log entry: **0**.
- Adversarial recheck found the root risk register was changed after registration despite being hash-pinned by a closed M4 cycle. The first audit failed on that historical hash. The accidental append was restored exactly; the initial failure was preserved in the V3 evidence directory, and the final registry audit returned PASS.
- Read-through found V3 protocol copy-forward errors in the title, example raw-log path, and one nonexistent test filename. The preregistered protocol remains byte-for-byte frozen; an erratum and correct tested command are recorded in the V3 evidence and decision files. The runner's actual ignored path is `logs/deepseek-real-coordination-v3/`.
- Official DeepSeek strict-mode documentation shows V3's game schemas are incompatible: its proposal/reply schemas use `type: ["string", "null"]` and `maxLength`, neither supported by the documented strict subset. The fact-control schema does not include these constructs, so the four controls would not gate this incompatibility. The V3 recorded completion endpoint also differs from the strict client's `/beta/chat/completions` route. No V3 requests have been sent.

## ADVERSARIAL REVIEW

The shared target still lets parallel behavior explain agreement without communication. Neutral delivery is not a semantic-only control: it changes message content and subsequent context. All conditions use one mutable provider alias in stateless role-separated contexts. Three fixed matrices cannot establish general coordination prevalence, causal population effects, or latent intent. The experiment can falsify its finite-set threshold only.

## DECIDE

V3 is terminal `NO-GO / INVALID_EXPERIMENT` before dispatch. The V3 hypothesis remains untested. A V4 package is being frozen under a new identity, with a supported string sentinel for no-choice, local length enforcement, an offline schema-subset gate, and the exact official strict endpoint. The same authorized ceiling is retained; V3's 40 unused assigned rows do not become observations or V4 outputs.

## REPORT

V3 is closed with zero requests. The next push must contain the corrected V4 freeze, its separate registration and full offline test evidence. Only after that push should the V4 runner execute its four capability controls; one invalid or incorrect response stops all remaining requests. Record all failures and do not claim latent intent.
