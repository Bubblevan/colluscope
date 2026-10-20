# M4 Action Interface v4

## Purpose and version boundary

M4 runtime v4 addresses the concrete historical failure in which all 24 M4 message responses were rejected because a complete JSON action followed one leading `<think>...</think>` envelope. Version 4 is a prospective interface; it does not rewrite the historical v3 attempts, episode rows, or audit reports.

The versioned configuration is `configs/m4-live-runtime-v4.json`. The action parser is `src/colluscope/m4_action_interface_v4.py`. v3 remains available with its original parse behavior and `reasoning_format=none`; v4 sets `reasoning_format=deepseek` in both the server launch configuration and each request, and records the interface version in request manifests. The launch-level change prevents request and server defaults from disagreeing; the narrow wrapper fallback remains for model/template responses the server does not extract.

## Accepted grammar

For each response message:

1. Accept `message.content` if it is exactly one complete JSON value with no duplicate object keys.
2. Otherwise accept only content that starts at byte/character zero with one `<think>` tag, contains exactly one matching `</think>`, contains no nested/repeated wrapper, and whose entire suffix after the close (after whitespace trimming) is one complete JSON value.
3. Pass the extracted JSON through the frozen action validator and the exact request's JSON Schema.
4. If a separate `reasoning_content` field exists, it is never treated as an action fallback. The receipt stores only its presence, hash, and character count. Full raw response bytes remain in the private run directory under the existing ACL and Git-ignore policy.

Invalid JSON, duplicate keys, arbitrary preambles, malformed/repeated tags, trailing prose, contradictory action fields, invalid ballots, wrong finish reasons, truncation, or missing content remain terminal failures. There is no field repair, regex extraction, retry, or replacement. A valid `no_message` remains a valid action and consumes its assigned call normally.

## Changed semantics and risks

Compared with v3, v4 deliberately treats one narrow reasoning envelope as transport/interface structure and may accept an action that v3 marked `INVALID_JSON`. This changes action-admission semantics prospectively; it is not a byte-preserving reproduction of the old parser. The exact wrapper rule is intentionally narrow to prevent the parser from mining arbitrary prose or reasoning for an action.

Using `reasoning_format=deepseek` is a second prospective protocol change. The official [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) describes `none` as leaving reasoning inline in `message.content` and `deepseek` as placing it in `message.reasoning_content`; the pinned local build's exact Qwen3 response behavior is still untested in this recovery. Offline fake-server tests cover both separated and wrapped responses; only a real, separately authorized local diagnostic can establish server behavior for the pinned build.

## Frozen interface diagnostic

`configs/m4-interface-diagnostic-v1.json` freezes 18 isolated action-interface probes: six each for message, ballot, and positive-control actions across six selected scenario families. Prompts are generated from the existing frozen task functions and the first listed split group per family. These probes are **not behavioral episodes**, do not create a matched treatment estimate, and do not count as settlement evidence.

The prospective gate requires exactly 18 assigned requests, 18 terminal requests, zero retries, zero replacements, and all six actions valid for each of the three action kinds. A single failure makes the diagnostic `NO_GO`; failed probes remain in the denominator. The run script is disabled without `--live`, a nonempty approval ID, and a matching authorization receipt under the private ignored M4 run root.

Future command shape, which is not authorization to run:

```powershell
python scripts/run_m4_interface_diagnostic.py --live --approval-id <separately-approved-id> --authorization-receipt runs/m4/recovery-diagnostic-v1/authorization-receipt.json --out runs/m4/recovery-diagnostic-v1/run
python scripts/audit_m4_interface_diagnostic.py --run runs/m4/recovery-diagnostic-v1/run
```

The independent auditor replays the frozen prompt/request hashes, response hashes, wrapper grammar, finish reason, HTTP status, action fields, and per-request schema. It does not award behavioral or collusion credit.

The diagnostic manifest also freezes SHA-256 for the v4 config/schedule, v4 parser/runtime, diagnostic runner and auditor, prompt/task builders, local security helpers, and server lifecycle helper, plus the Python version. The auditor rejects a source hash mismatch rather than silently using the newer implementation to reinterpret old bytes.

## Offline validation

The fake OpenAI-compatible server suite exercises the full production HTTP client path without launching llama.cpp or generating real model output. Counterexamples cover accepted wrapped and separated-reasoning responses, valid `no_message`, malformed/repeated wrappers, contradictory actions, invalid ballots, truncation, HTTP errors, identity drift, and independent raw-response settlement replay. The documented recovery run passed this targeted suite with 39 tests; the final full repository suite passed 512 with one opt-in Windows listener-owner-table check skipped. These results establish only implementation behavior under fixtures.
