# M1-P0 Interface Protocol V3

**Protocol ID:** `m1-p0-interface-v3`  
**Status:** frozen for review; offline implementation and counterexamples only  
**Source baseline:** `657eab90356ce9137c2988aacb4b5b10d0402c28`  
**Scope:** distinguish transport/schema validity from model action choice. This protocol is not authorization to start a server or issue model completions.

## Research question

Can the local llama.cpp request path accept and faithfully retain every schema-valid action for a message-stage request, while separately reporting whether the model followed an engineering probe's requested action?

This gate concerns engineering interface compatibility. It is not an agent episode, a behavioral sample, a measure of comprehension, or evidence of collusion. M1-P0/P1, M2, and real model calls remain unauthorized until separately approved against an immutable configuration and budget.

## Frozen request sequence and ceilings

The only permitted sequence for a future, separately approved V3 preflight is:

1. `GET /props` to attest model path, server build, context, and settings.
2. `POST /apply-template` on the frozen ballot observation.
3. `POST /tokenize` on that exact rendered prompt; token IDs must match the pinned local tokenizer.
4. One ballot completion.
5. One message completion whose prompt requests `send_message`.
6. One message completion whose prompt requests `no_message`.

The fixed ceiling remains **6 logical requests / 12 HTTP attempts / 4 completion attempts**, with at most two transport attempts per logical request. Transport retry behavior remains the already frozen policy. Invalid JSON, schema-invalid output, action parse errors, truncation, or context failure are terminal and cannot be repaired or retried. Stop after the first hard failure. Do not sample again to obtain a preferred action.

No completion, configuration, prompt, reward, sampling, condition, output cap, timeout, model, server, or approval ID is changed under this protocol. Any new user-approved run requires a new run-scoped authorization and a fresh evidence directory. The consumed 2026-10-19 approvals cannot be reused.

## Two independent gates

### Schema and transport gate — hard

- A ballot-stage request must parse as exactly one valid ballot action under the frozen parser and ballot schema.
- A message-stage request may return either `send_message` with valid nonempty text or `no_message` with its exact allowed fields. Both are valid actions under the message schema.
- Any malformed JSON, extra key, missing/wrong type, invalid message, invalid allocation, unexpected prefix/suffix, truncation, server/model mismatch, template mismatch, or tokenizer mismatch fails this gate.
- Raw request and response bytes, parse result, attempt count, and error remain in the preflight ledger. There is no format repair and no favorable-sample replacement.

The interface result is `PASS_INTERFACE`, with `schema_transport_status: PASS`. It means only that the checked local interface gates passed for the observed requests. It does **not** assert that the model obeyed every probe instruction or that a live `send_message` output was observed.

### Instruction-compliance diagnostic — descriptive

For each completion, record:

```json
{
  "requested_action": "send_message",
  "actual_action": "no_message",
  "followed_instruction": false
}
```

The diagnostic retains the prompt, raw response, request ID, requested action, actual action, and boolean comparison. A valid alternative message action is not converted into a parser, schema, or transport failure. It also is not reported as instruction success. No compliance diagnostic enters monitor evidence `E`.

The `requested_action` must be recoverable from the exact `preflight_probe_instruction` inside the serialized prompt observation. Before any HTTP request, the runner parses that observation and cross-checks the caller-supplied action metadata against the instruction. If they disagree, the preflight is rejected before dispatch. This prevents a mislabeled instruction-compliance diagnostic from being manufactured by changing only researcher metadata.

When no actual completion returns `send_message`, report `positive_send_message_model_output: UNVERIFIED`. When one does, report that it was observed in this particular engineering probe only. Do not generalize a single output to the model's general propensity or the research behavior conditions.

## Positive-branch evidence boundary

The offline fake-transport tests must exercise a valid `send_message` through parsing, A-to-B delivery, sender history, C exclusion, T/B/E handling, and independent verification. They must also exercise `no_message` and ensure that malformed message output still fails hard. This validates ColluScope's software path, not the model's choice and not the actual llama.cpp server's acceptance of every `oneOf` branch.

If the separately approved live probe returns only `no_message`, the record establishes that the observed response was a schema-valid alternative for the message request. It leaves live positive-branch generation **unverified**. Do not repeat the probe until a send appears. The earlier parser-V2 run remains the historical `NO-GO_ACTION_MISMATCH` artifact under its then-frozen criterion; this protocol does not rewrite its status, bytes, or counts.

## Non-goals and interpretation limits

- No assigned episode is generated by preflight; no T/B/E episode record or monitor input is produced.
- A preflight response does not prove reward comprehension, actual utility, agreement, coordination, harmful action, or collusion.
- A future 25-episode pilot remains a distinct approval gate with the exact frozen five conditions and 95 logical / 190 HTTP-attempt maximum. All assigned failures remain in the denominator.
- Shared A/B target rewards mean target agreement without private messages is compatible with independent parallel choice. A message-channel offer is not a collusion label.
- No M2 comparison or detector metric is authorized.

## Acceptance and stop criteria

| Item | Required evidence | Decision if absent |
|---|---|---|
| Source and runtime identity | Exact checkpoint, launcher/DLL bundle, tokenizer, template, settings and loopback owner records | `NO-GO_INTERFACE` before completion |
| Ballot schema | One valid parsed ballot; malformed counterexamples fail | `NO-GO_INTERFACE` |
| Message schema | Any valid message union branch accepted; malformed counterexamples fail | `NO-GO_INTERFACE` |
| Action compliance | Requested/actual/followed fields retained; mismatches are descriptive | Report as observed, not a schema gate |
| Positive message software path | Offline fake-transport A/B-only route independently verifies | `NO-GO_INTERFACE` if offline plumbing fails |
| Positive message model output | Live `send_message` actually observed | `UNVERIFIED` if not observed; never resample |
| Prior failure integrity | Historical parser failure and action-mismatch packages verify unchanged | Stop and repair provenance |
| Live permission | New explicit approval fixes protocol, model/runtime, sampling, budget and retention | No live call without it |

## Required counterexamples

1. Prompt requests `send_message`; valid `no_message` is `PASS_INTERFACE` with `followed_instruction: false` and complete raw response.
2. Prompt requests `no_message`; valid `send_message` is `PASS_INTERFACE` with `followed_instruction: false`; offline route still delivers A-to-B and excludes C.
3. Truncated JSON, extra keys, nonempty/altered `<think>` prefix, invalid message text, and invalid ballot remain hard failures with retained responses and no retry.
4. Historical parser-V2 action mismatch verifier still reports `PASS_PACKAGE_INTEGRITY__NO_GO_ACTION_MISMATCH`, not a success verdict.
5. Historical zero-HTTP startup blocker still reports `PASS_PACKAGE_INTEGRITY__NO_GO_NO_HTTP`.
6. The previously consumed 8081 approval ID is rejected before creating an output directory, launching a server, or issuing HTTP.
7. Requested-action metadata that contradicts the exact action instruction embedded in a probe prompt is rejected before any HTTP request.

## Frozen implementation inputs

The prompt/schema/config SHA256 values and source commit are recorded in `M1_P0_INTERFACE_EVIDENCE.md`. The preflight runner, protocol, and raw evidence are versioned together. No token-cost or compute-cost claim is made from offline tests.

The configured llama.cpp commit's README and JSON-schema converter were statically inspected. Its direct `response_format.schema` request form is documented; the converter maps `oneOf` alternatives to union grammar branches. In this frozen communication schema, each branch requires `type` with a different `const`, making the branches disjoint. This does not establish that the installed server accepts/applies the schema at runtime. The independent strict parser remains required, and live compatibility stays NO-GO until a separately approved preflight exercises the configured server.
