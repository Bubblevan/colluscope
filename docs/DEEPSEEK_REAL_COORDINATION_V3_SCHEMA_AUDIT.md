# V3 Pre-dispatch Interface Audit

## Finding

V3 was preregistered but had not sent any request. A source-level check against DeepSeek's current official strict-function schema subset found that the V3 proposal/reply schemas are incompatible with the interface they declare:

- `choice.type` is `[`"string"`, `"null"`]`. The documented strict type list does not include `null` or type unions.
- `text.maxLength` is 240. The official strict-mode guide explicitly lists `maxLength` as unsupported.
- The four planned fact-control calls use only a small string enum. Those calls therefore cannot validate the richer proposal/reply schemas. Passing the controls would not rule out a predictable HTTP 400 when the game schedule begins.
- V3's frozen config lists `https://api.deepseek.com/chat/completions`; the already-frozen client routes `strict_function_calling` to `https://api.deepseek.com/beta/chat/completions`. DeepSeek's official strict-mode instructions require the Beta base URL.

The official docs were inspected on 2026-10-21:

- [DeepSeek Tool Calls: Strict Mode](https://api-docs.deepseek.com/guides/tool_calls/) documents the Beta base URL, supported schema types, and unsupported `maxLength`.
- [DeepSeek Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) identifies `deepseek-flash` as DeepSeek-V4.1-Flash-1017 and lists peak cache-miss input/output rates of $0.30/$1.20 per million tokens. The V3 runtime's rates match those peak values, but its endpoint and action-schema metadata do not.

## Decision

Close V3 as `INVALID_EXPERIMENT` before dispatch. Keep all 40 assigned V3 rows unattempted. Do not edit the registered V3 protocol/source/config or retrofit V3 results. The coordination hypothesis remains untested.

V4 uses the same payoff task, common +20 reward, three routing arms, 40-request graph, temperature, and call ceiling. It changes the wire representation of no-choice from JSON null to `UNDECIDED`, removes server-unsupported length keywords while retaining a local post-response 240-character validator, and freezes the exact Beta endpoint. A new experiment identity and preregistration preserve that change prospectively.
