# Pre-Sprint Work Log

**As of:** 2026-10-18 (Asia/Shanghai)

**Sprint:** Apart Research AI Collusion Research Sprint, 2026-10-23–25

**Track focus:** 2.2 and 2.3

## Work completed before the sprint

- Read the project's M0 TRD and continuous-goal instructions.
- Audited the official sprint page and the paper/repository sources identified in the TRD. Recorded exact local repository commits and license status in `M0_RESEARCH_NOTES.md`.
- Ran only upstream `--help` entry points. All three exited before a usable run because required dependencies or API credentials were absent. No package installation, model call, paid API call, or LLM evaluation occurred.
- No ColluScope experiment, model result, detection score, or claim about real LLM collusion has been produced as of this entry.

## M0 completion update

- Completed the M0-A source/dependency audit and M0-B/C/D offline scaffold by 2026-10-18. The final evidence and gate decision are in `M0_EVIDENCE.md` and `M0_DECISION.md`.
- Implemented an independent, CPU-only scripted allocation task with 24 episodes across six cases, four monitor views, separate oracle files, and integrity tests. These are synthetic scripts, not LLM observations.
- Final paired runs passed verification with matching source/configuration and core artifact hashes. The worktree is still uncommitted; the source snapshot hash is recorded in both manifests and the reports.
- No real LLM pilot, paid API call, detector comparison, or M1 work has occurred. M1 requires a later explicit user decision.

## Provenance and disclosure

The work is an independent ColluScope project. The local `reference/` clones were inspected read-only for research and dependency preflight. No upstream source code or data is being reused in M0; no ICBC/FTEC5660 group code is used. The M0 environment and scripted cases are original work for this project and must be disclosed as pre-sprint engineering if retained for the competition. AI assistance was used to inspect sources, formulate adversarial criteria, and implement/check the M0 artifacts; any final report must be rewritten and verified by the author in their own words, consistent with the official sprint guidance.

This file will be updated after M0 execution to distinguish this pre-sprint groundwork from any later sprint-period work. M1 has not been authorized or started.

## Chronology correction and pre-sprint status (2026-10-20)

The preceding sections are dated historical snapshots. Their statements that M1 had not started and that the worktree was uncommitted were true only at those earlier timestamps and must not be read as the current project state. The Apart sprint is scheduled for 2026-10-23–25; as of 2026-10-20 all recorded ColluScope work through M0–M3, M4 protocol and token-parity preparation, Sprint baseline preparation, and the final execution-candidate implementation predates the sprint start.

Historical M1 local Agent runs and the M2/M3 analyses are prior work, not new sprint-period experiments. M4 v1/v2 fixed-stimulus/tokenizer diagnostics and the current M4 v3 fake-server runtime validation are also pre-sprint engineering; this task performed no new Agent generation, Monitor inference, model training or external API call. Preserve the original timestamps and branch history. Any submission must disclose this chronology and distinguish historical real-model observations, scripted controls, deterministic calculations, and the present fake-transport tests.

No result in this work log establishes latent collusion or detector accuracy. AI assistance was used in the project engineering and must be disclosed as required by the official sprint rules. Participant authorship, institution and other personal details must be supplied by the participant and are not inferred here.
