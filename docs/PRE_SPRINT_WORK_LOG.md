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
