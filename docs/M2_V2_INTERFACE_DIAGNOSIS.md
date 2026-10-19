# M2-V2 Interface Diagnosis

**Scope:** read-only diagnosis of the complete M2-V1 raw response set before any M2-V2 model request.
**Baseline:** `codex/m2-one-shot-audit`, HEAD `1478f0a21648170076adda1762a3d1c95862ea3a`.
**Frozen source:** `runs/m2/one-shot-20261019/`; its artifact inventory SHA-256 is `6d3f0d552aea565d80416a774d80e64710488318da274ef2053841f140d984b9`.

## Method and integrity

`scripts/diagnose_m2_v1_responses.py` independently opened every exact frozen request and each returned raw response. It verified the byte hash of every request body and response body/text, matched all 517 response files to their request, and recomputed the prior 1,450-file run inventory. The original inventory manifest still has SHA-256 `6d3f0d552aea565d80416a774d80e64710488318da274ef2053841f140d984b9`; all 1,450 entries match, with no missing or unexpected files. Six of 523 request payloads have no returned response; their 20 logical evaluation rows remain request failures.

The response diagnostic removes no arbitrary text. It inspects a leading literal `<think>...</think>` pair for measurement, records whether the enclosed content is blank, and parses the remainder only as a **non-authoritative diagnostic**. It does not modify any saved response, status, score, denominator, or manifest.

Reproduction from the repository root:

```powershell
python -m pytest -q tests/test_m2_v1_diagnosis.py
python scripts/diagnose_m2_v1_responses.py
```

Per-response records are in the Git-ignored local directory `runs/m2-v2/recovery-20261019/diagnosis/m2-v1-response-diagnosis.jsonl`; aggregate counts are in `m2-v1-response-diagnosis-summary.json`. The row records contain hashes, metadata, field names and counts, not private message or response text.

## Observed failures

| Check across returned responses | Result |
|---|---:|
| Raw assistant responses | 517 / 517 |
| Exact leading empty envelope `<think>\n\n</think>\n\n` | 517 / 517 |
| Envelope content non-empty | 0 / 517 |
| Frozen validator status | 517 invalid JSON; 0 valid |
| Remainder parses as JSON after diagnostic inspection of that exact envelope | 517 / 517 |
| Remainder passes frozen semantic/schema validator | 0 / 517 |
| `finish_reason="length"` or completion at/over output cap | 0 / 517 |
| Server prompt + completion tokens within 4,096-token context | 517 / 517 |

All 517 responses ended with `finish_reason="stop"`. The completion count was 49,124 tokens total (median 87, maximum 440 against a 512-token cap). Server prompt tokens totaled 704,153 (median 1,365, maximum 2,011). Neither output truncation nor context exhaustion explains the required-field failures.

The exact post-envelope JSON root-key shapes were:

| Root keys emitted | Responses |
|---|---:|
| Eight claim fields only | 474 |
| Eight claim fields plus `findings` | 34 |
| Eight claim fields plus `latent_intent` | 8 |
| Eight claim fields plus `findings` and `task_spec` | 1 |

`evidence_refs` and `abstention_reasons` are absent in all 517 outputs. `latent_intent` is absent in 509. The extra fields `findings` (35) and `task_spec` (1) are prohibited by the frozen closed-object schema. After exact envelope inspection and JSON parsing, every response still fails the original validator. These remain **invalid predictions**, not repaired outputs.

## What the model and server actually received

Every saved request body contains `response_format.type="json_schema"` and the exact frozen schema object. This is the direct schema shape documented by the pinned [llama.cpp server README at commit `571d0d540df04f25298d0e159e520d9fc62ed121`](https://github.com/ggml-org/llama.cpp/blob/571d0d540df04f25298d0e159e520d9fc62ed121/tools/server/README.md). The pinned [`server-schema.cpp`](https://raw.githubusercontent.com/ggml-org/llama.cpp/571d0d540df04f25298d0e159e520d9fc62ed121/tools/server/server-schema.cpp) source routes a supplied JSON schema through `json_schema_to_grammar` and installs the resulting output-format grammar.

The same complete output shape was **not** shown in the model-visible prompt. Nine of the eleven required root field names were mentioned; `evidence_refs` and `abstention_reasons` were not. No prompt contained a literal JSON object skeleton listing all required keys and the nested references shape. This is confirmed for all 517 exact frozen message payloads, not inferred from the prompt template alone.

Neither launch command records an explicit log-verbosity flag. At the pinned build's default verbosity, the saved launch logs contain no schema conversion, grammar compilation, rejection, or fallback diagnostic markers. Their absence cannot prove that the schema was or was not applied. The HTTP completion and request bytes establish neither runtime grammar enforcement nor model compliance. The observed schema-invalid outputs do establish that the end-to-end contract failed.

## Root-cause assessment

**Confirmed contributing failures:**

1. The model emitted the exact same empty reasoning envelope before its JSON in all 517 responses, while V1's authoritative validator required raw content to begin with JSON. This explains the initial `JSONDecodeError` status.
2. The model-facing V1 prompt omitted two entire required root fields and did not give the model the exact required object shape. After the envelope, outputs repeatedly omitted those fields and usually `latent_intent`; in 35 cases they added unrequested fields. This independently explains why simply permitting the historical empty prefix would not make the output valid.
3. The interface did not enforce the complete output contract in observed operation. The request carried the documented schema, but all returned outputs violate it.

**Not identified from the preserved V1 evidence:** whether the pinned running server ignored the schema, converted or applied it incorrectly, or whether another interaction among the chat template, reasoning output and constrained decoder defeated enforcement. The server logs do not contain the needed debug-level evidence, and no old response will be reinterpreted to guess the cause.

## V2 falsification plan

M2-V2 will (a) display a complete explicit model-visible shape and all field meanings, (b) accept only the single exact historically observed empty prefix or no prefix, rejecting non-empty reasoning and every other prefix, and (c) preserve raw bytes and validate the JSON, schema, enums, abstention/view compatibility and authorized event references independently. The bounded compatibility run will record schema-conversion diagnostics at an explicit local server log level and requires all ten fixed F1 cases across five views and both permission profiles to pass. A missing field, extra field, unsupported citation, non-empty reasoning prefix, truncation, or unauthorized event reference is a failed compatibility case; it is never repaired or resampled.
## Fault tree: separated causes and what the evidence can identify

| Layer | Observation in the frozen V1 artifacts | Diagnosis |
|---|---|---|
| Chat template / reasoning mode | Requests asked for thinking-disabled chat and used the recorded template hash. Every returned assistant string nevertheless begins with the same empty think envelope. | The envelope is directly observed. The saved HTTP data do not reveal whether the template/runtime surfaced an empty assistant reasoning segment or the model emitted it. Do not attribute the envelope to one layer without server-side rendering traces. |
| Reasoning-envelope parser | The authoritative V1 parser required JSON at byte zero; all 517 raw outputs begin with the envelope instead. | Confirmed immediate JSONDecodeError contribution. V2 accepts only the exact historically observed empty prefix or direct JSON; arbitrary reasoning/prose is rejected. |
| JSON Schema transmission | Every exact request includes response_format.type=json_schema and the schema object in the pinned llama.cpp request shape. | Transmission is confirmed. Pinned server README and source confirm documented support and a schema-to-grammar path. |
| Runtime schema enforcement | All 517 assistant strings omit required fields and 36 contain prohibited extra root fields. The old logs have default verbosity and no conversion/rejection diagnostics. | End-to-end format enforcement failed. Whether the active server ignored, misconverted, or applied the grammar inconsistently is unidentified from V1. V2 records verbosity-5 diagnostics and tests the exact running model/server path. |
| Model-visible instructions | The V1 prompt omitted evidence_refs and abstention_reasons and contained no complete object skeleton; the returned roots omit both fields in 517/517. | Confirmed prompt-contract defect. It is not evidence that the model cannot follow a fully specified schema. |
| Output/context limits | No completion hit the 512-token cap; maximum completion was 440. All 517 server prompt-plus-completion totals fit the 4,096-token context. | Truncation/context exhaustion is not a supported explanation for V1's root-field omissions. V2 independently tokenizes every exact candidate/formal prompt before requests. |
| Authoritative validation | V1 kept every raw response invalid even when a later diagnostic inspected the exact prefix and parsed the remainder. | Correctly preserves the original failed denominator. The post-envelope parse remains diagnostic only and never upgrades a V1 status. |
