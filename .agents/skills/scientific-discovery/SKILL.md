---
name: scientific-discovery
description: Select and preregister the next ColluScope research question from actual evidence and competing mechanisms.
---

# Scientific discovery for ColluScope

1. Read `RESEARCH_PROGRAM.md`, the active phase TRD, the persistent research
   goal, risk register, iteration log, and `research/state.json`.
2. Reconcile any active experiment before selecting work. Do not consume
   provisional results from another task.
3. Separate observed facts, interpretation, and proposed work. State the
   evidence class and identify the strongest competing explanation.
4. Prefer a decisive counterexample or offline reanalysis over a broad feature
   build. State one primary outcome, the denominator, negative controls, and
   explicit success/failure/ambiguous gates.
5. Freeze source/data/prompt/split hashes before implementation. Never promote
   treatment, harm, agreement, or monitor output to a collusion/intent label.
6. Register the proposed experiment with `python scripts/researchctl.py
   register <preregistration.json>`. Registration is not authorization or
   permission to execute.
7. Keep the next action singular. If three cycles add no distinct uncertainty
   reduction, recommend a documented pivot.

Use public literature search when novelty or a current citation claim matters;
prefer primary sources and record claim-to-source links. Never call an agent or
monitor model as part of discovery without separate explicit authorization.
