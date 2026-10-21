# DeepSeek Real Coordination Pilot V3 — Evidence

**Terminal V3 status:** `NO-GO / INVALID_EXPERIMENT` before dispatch. V3 remains preserved with zero HTTP attempts and zero model generations. Its four simple fact controls would not have checked the unsupported schemas used by the 36 game requests.

## Why V3 exists

V2 remains closed `EXECUTION_BLOCKED`. Its single first-control transport attempt failed before an HTTP connection and returned no model output. V3 is a separately registered batch with new request IDs; it does not resume V2 or replace any observed behavior row. V2's raw request, terminal record, reports, and closure remain unchanged.

After the V2 failure, a resolver-only lookup succeeded, followed by an official-host TLS 1.3 handshake. The latter sent no HTTP request, credential, experiment prompt, or model inference. These checks show that the hostname and TLS path were available at those later moments; they do not identify the earlier failure's cause or establish API-key validity.

## Frozen V3 design

- Experiment: `deepseek-real-coordination-40-v3`.
- Hypothesis: across three fixed two-agent payoff matrices, actual peer-message delivery produces joint HIGH in at least two matrices where matched no-delivery does not.
- Conditions: common +20 joint-HIGH reward in every arm; no peer delivery, fixed neutral delivery, and actual proposal/reply delivery. Every arm has two message-stage and two sealed-ballot requests.
- Call graph: 4 delivery/absence capability controls first, then 3 matrices × 3 arms × 4 requests = 36 game requests; **40 assigned requests total**.
- Runtime: official `deepseek-flash`, `https://api.deepseek.com/chat/completions`, temperature 0, thinking disabled, strict function calling, 256 output-token cap, 90-second timeout, zero retries and replacements.
- Limits: 40 physical attempts / USD 0.50 peak-safe reservation; project capacity at registration was 43 attempts, leaving 3 outside this batch. Authorization expires `2026-10-23T01:00:00Z`.
- V3 schedule SHA-256: `8543f5272bcbfcefadb85717d9fad91977a47754fb5e2f62a33f591a6c99f980`.
- V3 configuration SHA-256: `4f5987585255a8aef4fb6c19d8919dd53db59bafe43bb540f1191fa27df82a6d`.
- Tokenizer SHA-256: `81f64d1248a68ce3663e07ab3ee48b851e5df0e32d27cb98e4c9a268151e8d99`.

The V3 runner is offline by default; only `--execute` dispatches. Its terminal verifier accepts the shared client's transport-failure record only when raw request bytes match the corresponding `attempt_started` hash. A mismatch remains fatal. The regression test exercises the actual runner's control-failure path with an injected transport error and confirms one attempt, 39 unattempted rows, and no descendants dispatched.

## Offline evidence

| Check | Result | Record |
|---|---|---|
| Python compilation | Exit 0 | `docs/results/deepseek-real-coordination-v3/py_compile.log` |
| V3 regression + frozen V2 behavior/analysis tests | **22 passed** | `docs/results/deepseek-real-coordination-v3/targeted_pytest.log` |
| V3 schedule/config hash freeze | `PASS_FREEZE_CHECK` | `docs/results/deepseek-real-coordination-v3/freeze_check.log` |
| V3 runner check-only | `PASS_OFFLINE_PREFLIGHT`, 0 calls, exit 0 | `docs/results/deepseek-real-coordination-v3/runner_check_only.log` |
| Research registry audit | `PASS`, no errors after restoring the historical risk-register hash | `docs/results/deepseek-real-coordination-v3/registry_audit_final.log` |
| Endpoint DNS/TLS-only check | TLS 1.3 succeeded; no HTTP or inference | `docs/results/deepseek-real-coordination-v3/endpoint_tls_preflight.json` |

The prior 1,157 project attempts / USD 0.133568658 remain the accounting baseline. V3 has **0 live model requests so far**. Raw V3 traffic will be written only under ignored, ACL-restricted `logs/deepseek-real-coordination-v3/`; no `.env` value or authorization header is stored.

## Interpretation boundary

This pilot can test one finite, preregistered pattern in three fixed matrices. Both agents know the same rewarded target, so matching HIGH choices in the no-delivery arm can arise from independent responses to the shared reward. A same-model alias in two stateless role contexts is not two independently trained models. Positive observable message/ballot sequences could support communication-mediated behavior in these contexts, but cannot prove latent intent or a hidden agreement. A negative result falsifies only the frozen finite-set gate, not the general possibility of coordination.

The exact protocol, preregistration, authorization, frozen source hashes, and reproduction commands are recorded in the repository. V3 is terminal: retain all 40 assigned requests as unattempted, never dispatch them, and never overwrite the V2 failure. Any corrected execution uses the separate V4 identity.

## Pre-dispatch adversarial review corrections

- A first registry audit after preregistration failed because this task had appended V3 risks to the root `docs/RESEARCH_RISK_REGISTER.md`, which is hash-pinned by a closed M4 cycle. That edit was restored byte-for-byte from HEAD. The initial failure is preserved in `docs/results/deepseek-real-coordination-v3/registry_audit_initial_failure.json`; the final audit passes. New V3 risks remain in the separate follow-up file and do not alter historical frozen inputs.
- The registered V3 protocol contains copy-forward documentation errors: its heading says “V2”, its raw-log example points at `logs/deepseek-real-coordination-v2/`, and its reproduction command names a V3 analysis test file that does not exist. The actual V3 runner and analyzer target `logs/deepseek-real-coordination-v3/`; the tested command uses the V3 runner test plus the existing V2 behavior/analysis regression tests. Because the preregistered protocol hash is immutable, the frozen file was not edited. Treat this paragraph and the actual runner paths as the erratum; these documentation defects do not change prompts, schedule, action semantics, or request budget.
- The four fact controls were inspected in the frozen prompt builder: delivered records explicitly mark an authoritative teammate message and contain ALPHA/BETA; absent records explicitly state no message was delivered and disclose no code; expected answers live only in researcher-side metadata. The existing tests exercise those exact frozen prompt functions, and the V3 runner's control gate is covered by the V3 tests.

## V3 terminal decision

V3 was closed before any provider request because the frozen proposal/reply schemas contained a union including `null` and unsupported `maxLength`. The official strict-mode docs explicitly exclude these. The V3 fact-control schema did not contain them, so the planned 4/4 control gate could have passed while the first proposal request then failed schema validation. V3's strict endpoint was also recorded as `/chat/completions` while the client actually resolves strict mode to `/beta/chat/completions`. These are preserved as pre-dispatch interface-integrity failures; no outcome was generated or inferred. The corrected V4 is a separately frozen, prospective run with the same 40/$0.50 cap, same treatments, and schema-compatible string sentinel.
