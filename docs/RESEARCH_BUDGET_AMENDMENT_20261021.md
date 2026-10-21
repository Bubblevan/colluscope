# Research budget amendment — 2026-10-21

The user raised ColluScope's **lifetime project ceiling** from 2,400 to **4,800 model/API attempts**. This change is recorded in `research/budget.json`; the project-wide external-cost ceiling remains **$2.50**. The change does not retroactively authorize or replenish any closed experiment.

At amendment time, the research ledger showed 1,772 cumulative attempts and $0.288371658 recorded cost. The raised ceiling therefore leaves 3,028 cumulative project attempts before the project call limit. The new, separate Track 2.3 grant is capped at 900 attempts and $1.80. Its frozen schedule assigns at most 840 attempts; the unassigned grant remainder will not be dispatched. If the local SALT-NLP admission check fails or eligible data are absent, its 120-request stress-test allocation is skipped.

The experiment cap uses the official DeepSeek weekday peak prices checked on 2026-10-21: $1.32 per million uncached input tokens and $3.96 per million output tokens. At 1,200 input tokens and 64 output tokens per request, the 840-attempt schedule reserves at most $1.7563392, below its $1.80 ceiling. The runner must enforce the frozen per-request bounds and cumulative reserve before dispatch; the older shared runtime's embedded pricing constants are not the cost authority for this cycle.

The grant is limited to `track23-counterfactual-delivery-v1`, uses only the official DeepSeek Flash endpoint, and expires 2026-10-23 00:00 UTC. No Qwen calls, provider fallback, custom transport, retries, replacements, resumption, or resampling are authorized.

The project cap and current grant are separate controls: raising the former to 4,800 does not authorize consuming all remaining calls. Each later experiment still needs its own exact-scope approval and immutable authorization record.
