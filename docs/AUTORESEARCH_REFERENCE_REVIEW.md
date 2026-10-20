# Autoresearch harness reference review

Reviewed the local snapshots under `reference/` on 2026-10-21. No source code,
prompts, data, or assets were copied into the harness. Repository revisions
below identify the exact local snapshots inspected; they are not claims that
the local snapshot is the latest upstream version.

## Research-workflow references

| Snapshot | Local revision | Useful mechanism | ColluScope adaptation | License observation in local snapshot |
|---|---|---|---|---|
| [karpathy/autoresearch](https://github.com/karpathy/autoresearch) | `228791fb499a` | Small editable experiment surface, fixed evaluation path, bounded run, keep/revert decision, and results ledger (`program.md`, `prepare.py`, `train.py`). | Keep the research program, frozen-input hashes, finite registration, and append-only cycle records. Do not optimize ColluScope's open-ended research with a single accuracy score or discard negative results. | No top-level LICENSE file found in this snapshot; no code reused. |
| [Anikethh/ResearchGym](https://github.com/Anikethh/ResearchGym) | `0adc08e93754` | Budgeted research tasks, runtime separation, and a distinct InspectionAgent for completed runs. | Keep bounded resource records and a separate audit role. Do not import its long-running provider-backed runner or objective-score assumption. | No top-level LICENSE file found in this snapshot; no code reused. |
| [SakanaAI/AI-Scientist-v2](https://github.com/SakanaAI/AI-Scientist-v2) | `96bd51617cfd` | Experiment Manager and research-tree exploration over competing ideas. | Use competing explanations and a pivot rule, but keep one primary experiment per cycle and avoid unrestricted tree expansion or generated-code execution. | Includes `The AI Scientist Source Code License v1.0`, which has conditions beyond the permissive MIT/Apache pattern. No code reused; review its full terms before any future reuse. |
| [JoeyJin-NJU/research-engineering-suite](https://github.com/JoeyJin-NJU/research-engineering-suite) | `670d0be50c52` | Trace claims to files, commands, citations, or measurements; separate scientific validity from code correctness and reproducibility. | Use two narrow repository skills for discovery and audit rather than importing a general-purpose skill bundle. | MIT license present; no code reused. |

The local `reference/` directory is Git-ignored by this project. These sources
remain local and untracked; the harness uses only the workflow ideas summarized
above.

## Other local snapshots

These are primarily domain, benchmark, or ColluScope-history references rather
than autoresearch orchestration frameworks. Their source was not copied into
the new harness.

| Snapshot | Local revision | Local origin |
|---|---|---|
| `colosseum` | `b077fe7e2f10` | `https://github.com/umass-ai-safety/colosseum` |
| `llm-agent-collusion` | `2bb2a7e22860` | `https://github.com/andyjliu/llm-agent-collusion` |
| `LLM-Trust-Breaking` | `fd11aca351e5` | `https://github.com/Jerick-1380/LLM-Trust-Breaking` |
| `m01-independent` | `d30ecfd2da01` | `https://github.com/Bubblevan/colluscope.git` |
| `m1-p0-local-qwen-integration` | `e9d8b57c6798` | `https://github.com/Bubblevan/colluscope.git` |
| `Steganographic_Collusion` | `48e6713d3e26` | `https://github.com/Ostailor/Steganographic_Collusion` |
| `TraceGuard` | `0e2e8226d7ca` | `https://github.com/linhkid/TraceGuard` |

The two Bubblevan snapshots are project history, not independent upstream
baselines. The license inventory for these seven is not a blanket grant to
reuse code; consult each exact snapshot before any reuse. `Steganographic_Collusion`
and `TraceGuard` include MIT license files in the inspected snapshots.

## Decision

Use Codex `/goal` as the research director, repository instructions and skills
as the method, and the local CLI as a record/hash/budget consistency gate.
Do not add a background scheduler, autonomous shell runner, multi-branch
search tree, or model API adapter. Those systems would add risk without
resolving the current scientific uncertainty.
