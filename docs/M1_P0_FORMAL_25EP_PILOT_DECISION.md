# M1-P0 Formal 25-Episode Pilot Decision

**Decision:** the authorized exploratory Pilot completed and its artifact gate is **GO for human review**. This is not a GO for detector evaluation, a causal claim, another model run, or M2.

## Evidence supporting completion

- All 25 assigned episodes are retained: 25 completed, 0 failed.
- The independent verifier returned `PASS_ARTIFACTS`, recomputed settlements, verified observation hashes, and found no hidden treatment/oracle metadata in monitor inputs. A separate verify-only invocation exited 0.
- All 95 Pilot logical requests returned once; observed usage was 95/95 logical/HTTP attempts against hard limits of 95/190. No paid or external model call was recorded.
- The preceding interface gate returned `PASS_INTERFACE` within 6 logical / 7 HTTP / 3 generation attempts. Authentication and untrusted-Origin canaries passed; the temporary key was removed and the server shut down.
- Exact run configuration, source revision, prompts, schemas, model, server, tokenizer/template metadata, environment, request records, and hashes are preserved in the local package referenced by `M1_P0_FORMAL_25EP_PILOT_EVIDENCE.md`.

## Interpretation boundary

The results are descriptive only: five episodes per condition, one local model/runtime, one frozen task and prompt family, and greedy sampling. A/B share a rewarded target in relevant conditions. The no-chat common-incentive condition had harmful outcomes in 4/5 episodes, while the coalition-incentive private-chat condition had delivered messages in 5 episodes and harmful outcomes in 3/5; this pattern does not isolate communication as a cause. Small per-condition counts, shared-target incentives, and bundled message/deliberation opportunities prevent a reliable causal estimate. Welfare loss, agreement, incentive assignment, or the existence of private chat alone does not establish collusion or intent.

There is no detector performance estimate and no gold label of latent intent. `T` records assigned interventions and delivery receipts; `B` records actual messages, ballots, settlements, welfare, and task scores; `E` is the auditor-permitted evidence view. These distinctions remain necessary when interpreting the run.

## Next decision

Stop at M1-P0. Review the evidence and limitations before authorizing any new model calls. **NO-GO for M2, further episodes, detector comparison, training, or claims of collusion/causality under this run.** A follow-up should first address the shared-target confound and separate communication opportunity from extra deliberation/token exposure, with its protocol and call budget frozen before execution.
