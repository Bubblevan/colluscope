# Adversarial self-review: shared-target message-source v1

This is an adversarial self-review of the frozen protocol, sanitized outputs, independent raw replay, and interpretation. It is not a separate-context or human Scientific Critic review.

## Strongest supported statement

In the 24 frozen contexts served by the observed DeepSeek Flash identity, recipient ballots tracked a supplied target-or-decoy recommendation mapping under both the peer and task-aide labels. The preregistered descriptive source-insensitive gate passed, while the peer-specific advantage gate was not met. This is controlled recipient behavior in scripted prompts.

## Attempts to falsify or narrow that statement

1. **Provider identity and version drift.** All calls reported one model alias and the same fingerprint, but the serving alias and fingerprint are not immutable weight identifiers. The result is conditional on one observed provider-served identity and date.
2. **Context selection and scope.** The study used all 24 contexts in the frozen matrix package, not a newly sampled task population. Each context has four exact-prompt repeats per arm. The context is the comparison unit; the 576 calls must not be treated as 576 independent model instances.
3. **Source-label construct validity.** “Peer B” versus “Task aide” changes only the source label in matched prompts, with tokenizer parity verified. That isolates the label in the prompt; it does not instantiate peer social influence versus an actual independent advice service.
4. **Welfare interpretation.** The decoy is the nearest-welfare legal non-target in each context, but only 6/24 contexts have a welfare gap at most 1. Decoy mapping adherence is not uniformly welfare-neutral.
5. **Stability.** Eight of the 144 context-by-arm cells show at least one disagreement across four identical repeats. The high pooled adherence is not perfectly deterministic. Report all disagreements and do not infer stable individual-level policy.
6. **Baseline interpretation.** Hidden/no-message shadow mapping matched 14/96 ballots. This is an analyst-only randomized mapping benchmark in a fixed design, not an inferential null model or population calibration.
7. **Mechanism limits.** The requests are stateless and scripted. They do not observe sender intent, natural message generation, negotiation, recipient acknowledgement, agreement, collusion, or harm.
8. **Similarity gate.** The ±0.10 gate defines a preregistered finite descriptive pattern. Passing it does not demonstrate statistical equivalence or rule out source effects in other contexts or models.
9. **Raw-data accessibility.** Independent replay used the local protected raw responses and verified the sanitized artifacts. Git contains the sanitized ledger and context data, not the complete provider responses; external byte-for-byte replay therefore requires approved access to the protected raw run.

## Decision

Keep the scientific outcome `REFUTED` for the preregistered peer-source advantage hypothesis and report the source-insensitive recommendation pattern as a finite descriptive result. The result improves the evidence that controlled recommendation mappings can shift ballot choice in these tasks, while leaving generic instruction following and prompt-level pragmatic effects as compatible explanations. Do not call the outcome proof of collusion, social influence, equivalence, or model-population behavior.

Operational disposition: `PIVOT` to offline manuscript integration. This self-review does not satisfy the registry's independent-review condition for credited material progress.
