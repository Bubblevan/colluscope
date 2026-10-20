# DeepSeek-First M4 / Monitor — Integrated Evidence

**Current status:** pre-inference freeze candidate. No real DeepSeek API request has been made in this task at the time of this commit.  
**Provider scope:** official DeepSeek API only; no local Qwen, third-party provider, external fallback, download, training or M2 detector comparison.  
**Protocol versions:** `M4-DEEPSEEK-AGENT-V1` and `M4-DEEPSEEK-MONITOR-V1`.

## Frozen design and budget

| Stage | Assigned requests/groups | Maximum physical attempts | Gate |
|---|---:|---:|---|
| Compatibility pilot | 8 Agent + 12 Monitor Strict; only on explicit Strict capability rejection, 4 Agent + 6 Monitor fallback | 30 | Agent output types and Monitor parse/pair/permission gate |
| M4 Agent | 24 frozen groups | 264 | First two preselected groups independently replay before remaining groups |
| M4 Monitor initial | First 6 groups × 3 tasks × 2 methods × 2 permissions | 72 | At least one assessable paired B4/B5 raw prediction |
| M4 Monitor remaining | Remaining 18 groups, same schedule | 216 | Only after initial pair gate passes |
| Scripted controls | Frozen synthetic positive/hard-negative set | 16 | After all 288 natural trace rows are terminal without fatal stop |
| Matched worlds | Frozen paired public/privileged set | 72 | After all 288 natural trace rows are terminal without fatal stop |
| **Total planned maximum** |  | **670** | Shared hard limit 900 attempts / USD 5 peak-rate reserve |

There are zero retries and zero replacement groups. Every assigned group and request remains in its denominator. The static 30-slot compatibility schedule and its input/source hashes are in `configs/m4-deepseek-pilot-plan-v1.json`. The Agent and Monitor protocols preserve the original M4 scenario, incentive, seed/split and task rules while explicitly versioning the provider/runtime interface.

## Pre-inference evidence

- Python 3.12.4, Windows 11. Temporary current-user-only ACL setup and verification passed.
- `.env` endpoint/model preflight passed; credential content was not printed or copied.
- Synthetic raw-response and injected fake-HTTP tests exercised both output interfaces, complete Agent group execution, context isolation, send/delivery distinction, settlement replay, monitor parsing, citation/input freeze, hard request cap, gate stopping, and error retention.
- Targeted suite: **35 passed** in the latest run, including byte-for-byte reproduction of the committed 30-slot plan. Final full repository suite on the freeze candidate: **547 passed, 1 skipped in 137.34s**; the skip is the opt-in host-dependent Windows listener-owner-table check. The complete output is `docs/results/deepseek-first-m4/logs/pytest-full-offline-final.log`.
- Historical M0–M4 raw artifacts and earlier failures remain unchanged. All M0–M3 research and current preparation date 2026-10-20, before the Apart Sprint starts on 2026-10-23; this work is pre-sprint work.
- Real model/API calls: 0 at freeze time.

## Required post-run append

After the bounded run, independently populate: assigned/completed/failed/unstarted Agent groups; message proposal/send/delivery and ballot-concordance counts; welfare/regret/target outcomes by scenario; focal token deltas; positive-control response; all Monitor parse/citation/factual/abstention rows and matched coverage; provider model/fingerprint; raw request counts, HTTP 200/non-200/ambiguous outcomes; provider-reported tokens, duration, usage cost and reserved cost; and hashes of the final audit tables. Do not place raw private message text or credentials here.

## Reproduction

Pre-inference and frozen-run commands are specified in `docs/DEEPSEEK_FIRST_RESEARCH_RELEASE.md`. The no-inference independent scoring/replay entry point is:

```powershell
python scripts/audit_deepseek_first_research.py
```

No pre-run PASS should be represented as behavioral model evidence.
