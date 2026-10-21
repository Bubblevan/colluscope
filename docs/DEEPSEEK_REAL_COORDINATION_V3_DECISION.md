# DeepSeek Real Coordination Pilot V3 — Decision

**Terminal decision: NO-GO / INVALID_EXPERIMENT before dispatch.** No V3 request was sent. This is an interface/schema validity failure, not evidence for or against the behavioral hypothesis.

## Gate evidence

- V3 preregistration and immutable authorization are registered for `deepseek-real-coordination-40-v3`; no experiment is dispatched by registry tooling.
- V3 freeze check passes for 40 assigned requests, 40 physical attempts maximum, and USD 0.50 peak reservation.
- Targeted offline suite passes 22 tests, including a regression that injects a transport terminal missing its request hash. It verifies request bytes against the append-only start hash, records one failure, marks the remaining 39 assigned rows unattempted, and issues no second request.
- Runner `--check-only` passes with 0 model calls and exits 0. Real execution requires explicit `--execute`.
- Local credential presence/configuration is checked without revealing the secret. Official host DNS and a TLS 1.3 handshake succeeded in a separate no-HTTP, no-prompt preflight.
- Registry audit passes with 1,157 prior attempts and USD 0.133568658 used. The V3 ceiling of 40 remains under the project limits and leaves 3 attempt slots unused.
- Official DeepSeek strict-mode docs list the supported type set without `null` and mark `maxLength` unsupported. V3 game schemas used both constructs; its fact-control schema did not. Thus the four control responses could not verify the game-stage schema.
- V3 records `/chat/completions`, while the frozen strict-function client actually resolves to `/beta/chat/completions`. No request was sent to either path.
- Pre-dispatch review found copy-forward errors in the immutable V3 protocol's title, raw-log example path, and one nonexistent reproduction-test filename. The actual runner is pinned to the V3 ignored log directory; the evidence report records the erratum and exact tested command. No model request has been sent, and no frozen protocol input was edited after registration.

## Execution command and stop rule

V3 is closed and must not be dispatched. The corrected prospective V4 package has its own command and preregistration; it uses string sentinel `UNDECIDED`, local post-response length validation, a schema compatibility gate, and the exact strict endpoint. The old V3 live command is intentionally withdrawn.

For V4, the runner executes four fact controls first. Any incorrect, invalid, truncated, transport-failed, HTTP-failed, identity-mismatched, hash-mismatched, privacy-failed, or over-budget control stops the batch. No retries, replacement rows, or continuation of descendants follow a failed gate. All 40 assigned rows remain visible in the report.

For the V3 offline reproduction command, use the tested file set recorded in the evidence report: `tests/test_deepseek_real_coordination_v3.py`, `tests/test_deepseek_real_coordination_v2.py`, and `tests/test_deepseek_real_coordination_analysis_v2.py`. The copy-forward filename in the frozen protocol is not present in this checkout.

## Claims that remain out of scope

The shared +20 target is known to both agents; no-delivery agreement remains compatible with independent parallel behavior. This same-model, three-matrix finite pilot has no population-level causal identification. Even an accepted proposal followed by matching ballots and low-welfare settlement is observable behavior, not proof of internal intent or latent collusion. No Monitor inference or M2 comparison is authorized by this record.
