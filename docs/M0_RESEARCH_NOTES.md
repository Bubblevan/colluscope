# M0 Research Notes

**Checked:** 2026-10-18 (Asia/Shanghai)

**Purpose:** M0-A source and dependency preflight. This is a record of source inspection, not an experiment report.

## Official sprint facts

The [official sprint page](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25) dates the event to 2026-10-23–25 and lists Track 2 as “Detection and Audit of Collusion.” It states questions 2.2 (“Does combining what agents say with what they do beat either alone?”) and 2.3 (“What should count as convincing evidence of collusion?”).

The Resources section for 2.2 explicitly recommends giving the same monitor four views (messages, actions, raw combination, structured claim/outcome report), freezing model/prompt/threshold, and reporting accuracy and false-positive rate. The 2.3 resource explicitly separates harmful coordinated action, similar behaviour from common incentives without agreement, and collusion-sounding talk that does not affect behaviour; it suggests testing a frozen decision rule on held-out cases. Thus these specific methods are supported by the current official page, not just by the TRD. The M0 extensions (scripted-only, six case families, oracle isolation, provenance, and byte-identical non-identifiability pair) are ColluScope design requirements, not claims made by the organizers.

The official page requires a research report PDF using its template, a <=150-word abstract, author/affiliation, and a limitations/dual-use/ethics appendix. It says prior work must be disclosed. No claim is made here that the current M0 artifacts satisfy the eventual submission requirements.

## Source and upstream audit

| Source | Exact local snapshot | What the source supports | License / reuse status | Preflight result |
|---|---|---|---|---|
| [Colosseum paper](https://arxiv.org/abs/2602.15198), v2 | arXiv:2602.15198v2 | Formalizes cooperative multi-agent tasks and compares communication-based evidence with action regret relative to the cooperative optimum; also reports “collusion on paper,” where text plans are not carried through in actions. These distinctions inform our separation of T/B/E; its LLM results are not M0 data. | The local code snapshot `reference/colosseum` is commit `b077fe7e2f10566e92156cc12e06ffb2aac54790`; its root tree has no `LICENSE` file and GitHub page shows no license. **No code reuse.** | `python experiments/collusion/run.py --help` exited 1: `ModuleNotFoundError: No module named 'terrarium'`. `external/CoLLAB` submodule is uninitialized (`-018c9e...`). High-level/API experiment **NOT RUN**. |
| [Colosseum repository](https://github.com/umass-ai-safety/colosseum/tree/b077fe7e2f10566e92156cc12e06ffb2aac54790) | commit `b077fe7e2f10566e92156cc12e06ffb2aac54790` (2026-10-09) | README requires Python >=3.11, `terrarium-agents[providers,science,plots]==0.1.1`, `uv`, and CoLLAB for some tasks; documented experiment commands use model-provider configuration. | No root license at this commit; treat as all-rights-reserved for code reuse unless clarified by maintainers. CoLLAB has a separate license and its local submodule was not initialized. | Static dependency inspection only; no install or API invocation. |
| [When Agents Lie paper](https://arxiv.org/abs/2607.05132), v2, linked by official 2.2 resources | arXiv:2607.05132v2 | Studies repeated n-player games and separates private plan, public announcement, and final action; it is a promise-breaking / strategic-deception source, not by itself a collusion label or proof of coordinated harm. | Paper citation only; no source code copied. | Read abstract/metadata and compared against repository README. Full reproduction **NOT RUN**. |
| [LLM-Trust-Breaking repository](https://github.com/Jerick-1380/LLM-Trust-Breaking/tree/fd11aca351e52c65c929e1a7d46d9f087f237adf) | commit `fd11aca351e52c65c929e1a7d46d9f087f237adf` (2026-06-29) | README describes strategic deception / promise-breaking across private plans, public announcements, and final actions, and lists model-performance figures. The README contains no paper citation or result data in this snapshot; those figures are not adopted as evidence here. | No root `LICENSE` file in this commit. **No code reuse.** | `python experiments/run_endogenous.py --help` exited 1 during import because the harness requires `OPENAI_API_KEY` or `OPENROUTER_API_KEY` even for help. No key was supplied and no API was called. Offline harness run **NOT RUN**. |
| [TraceGuard repository](https://github.com/linhkid/TraceGuard/tree/0e2e8226d7ca98e0375ed3aa54f9a870a3794714) | commit `0e2e8226d7ca98e0375ed3aa54f9a870a3794714` (2026-03-23) | Its README describes a single-agent control/BashArena monitor and includes an action-trace consistency dimension. This is a reusable *idea* for comparing claims with actions, not a ready-made multi-agent collusion detector. | MIT (`LICENSE` present). No source copied into M0. | README setup requires Docker, ControlArena, API keys; `python scripts/run_eval.py --help` exited 1: `ModuleNotFoundError: No module named 'inspect_ai'`. No install, Docker setup, or API call. |

### Source-version caveats

- The checked LLM-Trust-Breaking commit predates the officially linked “When Agents Lie” arXiv v1 submission by about a week. Its README and the later paper have related three-stage concepts, but an exact commit-to-paper/result correspondence has not been established. The README's reported rates are therefore third-party/unverified claims for this project.
- Colosseum's code and its `CoLLAB` dependency are separate repositories. A parent submodule pointer is not a license for either repository.
- TraceGuard's MIT license permits reuse subject to its notice requirements, but M0 only borrows the broad claim/action consistency idea. Its Python/Inspect AI/ControlArena/Docker/API stack is unnecessary for the independent toy environment.

## Existing findings, unverified questions, and minimum increment

### Existing findings from primary sources

1. The official Track 2.2 recipe calls for matched monitor inputs and four evidence views; Track 2.3 names the three most important contrasting case types.
2. Colosseum motivates measuring task harm via regret/welfare relative to an optimum and separates text planning from executed action.
3. The officially linked repeated-game work separates private intent, public announcement, and binding action. A promise-breaking/deception label is not equivalent to multi-agent collusion.
4. TraceGuard offers an action-trace consistency rubric but is for single-agent control monitoring.

### Not verified

- No upstream experiment was reproduced. The available local environment lacks required packages and no external model credential/API was used.
- No source-code license is present in the checked Colosseum or LLM-Trust-Breaking commit trees.
- No current LLM behavior, collusion frequency, detector accuracy, or generalization result has been measured by ColluScope.
- An observed welfare loss alone cannot identify coordination; the same action trace may be generated by a coalition mechanism or independent policies.

### Minimum ColluScope increment and falsification criteria

Implement the smallest independent Python allocation task that permits all six assignments to be enumerated. Define construction truth (T), observed actions/outcome (B), and permission-filtered evidence (E) separately. The key M0-B falsifier is whether the proposed C1 can produce a lower-welfare selected allocation through traceable votes, while C2/C4 can yield similar loss or behavior without a coalition. The key M0-C falsifier is whether a no-private-message audit view can be made byte-identical for two different construction mechanisms, and whether every structured-evidence field is derivable from raw-fusion events with event provenance. If either fails, do not claim that the toy labels are identifiable.

No code or data from upstream repositories or the prior ICBC/FTEC5660 group project has been copied.
