# Track 2.3 v2: related work and data admission

Read on 2026-10-21. Sources below were checked against primary papers, official benchmark pages, or the dataset host.

## What is already covered

- **Colosseum** studies collusion in cooperative multi-agent systems using DCOP tasks, coalition regret, persuasion tactics, and communication-channel interventions. It explicitly reports “collusion on paper”: agents can coordinate in text without following through in action. Therefore neither a communication ablation nor a text/action mismatch is novel by itself. The ColluScope increment is narrower: a sender-authored proposal is yoked across matched recipient branches with B's history and other agents' ballots sealed, and the identical text is also attributed to a non-peer aide.
- **Emergent Collusion in Long-Horizon LLM Agent Interaction** (Shi et al., arXiv:2609.24967) examines repeated verification episodes, shared rewards, persistent history, and controlled peer interventions. The authors report that peer behavior and history scope shape joint instruction violations. This is stronger evidence about long-horizon behavioral collusion than ColluScope's single-stage task. The current study can add a local, controlled recipient action contrast; it cannot compete on long-horizon or cross-model generality.
- **Cheap Talk Stabilizes Strategic Interaction in LLM Agents** (Lorè, Zhu, and Heydari, arXiv:2609.16270) already uses matched current-message interventions and studies policy persistence in repeated games. A generic claim that “messages change LLM actions” would overlap. ColluScope's potential contribution is the same-message peer-versus-aide attribution control, a no-message/neutral comparison, and the explicit distinction between action change and settlement/public-welfare consequences.
- **NARCBench** (Rose et al., arXiv:2604.01151) evaluates multi-agent collusion detection with activation probes under environment shift. It is a white-box detector benchmark, not a black-box audit of logged delivery, timing, recipient response, or counterfactual action dependence. The scopes are complementary.
- **Arike et al. (ICML 2026)** find that LLM monitors can perform better with filtered information and introduce extract-and-evaluate monitoring. This makes information-view comparisons important, but it also makes it unsafe to assume that more trajectory detail improves evidence assessment. ColluScope's monitor results therefore remain finite, same-model, and separate from behavior outcomes.
- **Kovacic, Marshall, Marx, and White (2011)** organize antitrust “plus factors” as evidence that can distinguish parallel conduct from independent decisions. That framework motivates an explicit checklist for communication delivery, temporal precedence, a recipient response, action dependence, and consequences. It does not turn an experimental behavior label into a legal conclusion.

## Incremental claim and falsification

The project should not claim the first causal test of agent communication, a general collusion detector, or a new long-horizon collusion environment. The testable contribution is whether a fixed A-authored proposal changes B's action beyond no-message and neutral-message responses, whether that effect survives an identical-content task-aide source control, and whether the changed action alters the ex post joint settlement. Positive results support only this finite, yoked intervention; negative or unstable results are informative about the limits of the earlier advice-following observation.

The two strongest rivals are (1) shared incentives/public scores plus independent convergence or generic recommendation following, and (2) serving variability or prompt/source-label sensitivity large enough to explain the apparent shift. The no-message repeats, neutral-message arm, and same-text aide arm target these rivals directly.

## External data admission

The SALT-NLP `agent-collusion` dataset is available from its public Hugging Face repository under MIT and includes 27,100 tabular episode rows, long-horizon sequence metadata, and `trace_file` paths. Its repository is listed as 8.12 GB, including 7.97 GB of traces. The repository source describes ten-episode runs, intervention conditions, communications, verdicts, rewards, and task correctness. This is enough to establish that a future selective sample is plausible; it is not enough to treat the dataset's `collusion` field as intent ground truth. The 2026-10-21 local admission pass found no local licensed raw trace bundle, and this v2 cycle does not fetch the multi-gigabyte repository or use its monitor labels.

Colosseum's public code and paper were reviewed, but no local complete matched trajectory bundle was admitted for this cycle. Any future external sample should freeze the dataset commit, retain run/sequence clusters as the unit, exclude Qwen model traces from any new Qwen inference, separate assigned experimental conditions from observed outcomes, and code unobserved intent as unknown.

## Sources

- Apart Research, [AI Collusion Research Sprint — Track 2.3 and resources](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25).
- Nakamura et al., [Colosseum: Auditing Collusion in Cooperative Multi-Agent Systems](https://arxiv.org/abs/2602.15198).
- Shi et al., [Emergent Collusion in Long-Horizon LLM Agent Interaction](https://arxiv.org/abs/2609.24967); [SALT-NLP code](https://github.com/SALT-NLP/agent-collusion); [MIT dataset](https://huggingface.co/datasets/SALT-NLP/agent-collusion).
- Lorè, Zhu, and Heydari, [Cheap Talk Stabilizes Strategic Interaction in LLM Agents](https://arxiv.org/abs/2609.16270).
- Rose et al., [Detecting Multi-Agent Collusion Through Multi-Agent Interpretability (NARCBench)](https://arxiv.org/abs/2604.01151).
- Arike et al., [How does information access affect LLM monitors' ability to detect sabotage?](https://proceedings.mlr.press/v306/arike26a.html).
- Kovacic, Marshall, Marx, and White, [Plus Factors and Agreement in Antitrust Law](https://repository.law.umich.edu/mlr/vol110/iss3/1/).
