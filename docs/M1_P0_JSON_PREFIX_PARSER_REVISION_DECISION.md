# M1-P0 parser revision decision

**Decision: NO-GO for the 25-episode Pilot under parser V2.** The JSON-prefix parser defect was narrowly repaired and passed against the retained real response. The fresh local compatibility preflight then stopped on the next expected-action check, before episode 1.

## Gate results

| Gate | Result | Evidence |
|---|---|---|
| Local model/runtime identity and process ownership | PASS | Exact GGUF/runtime hashes and listener PID; see run package |
| Loopback health on 8081 | PASS on the controlled retry | `server-health.json` |
| Properties, template and tested-prompt tokenizer parity | PASS | First three preflight records |
| Exact empty `<think>` prefix parsing | PASS for observed ballot and `no_message` outputs | `preflight/requests.jsonl`; offline actual-response regression |
| Required positive `send_message` compatibility probe | **FAIL** | Expected `send_message`; actual action was valid `no_message` |
| Full preflight | **NO-GO** | 5 logical / 5 HTTP / 2 completion requests; third probe not sent |
| Assigned behavior Pilot | **NOT RUN** | 0 episodes, 0 Pilot calls, no T/B/E episode rows |
| External/paid API use | PASS | 0 / 0 |

## Why no further retry was made

The parser problem is no longer the blocker. Sending the same probe repeatedly until the model chooses `send_message` would condition the result on a favorable action and obscure the observed refusal/no-message choice. It would also depart from the frozen stop-on-first-expected-action-mismatch rule. This preflight is a compatibility gate, not a behavioral sample from an assigned episode; the mismatch still means the positive communication path was not validated. No parser, prompt, label, or acceptance rule was broadened after this result, and no failed episode was removed because no episode was started.

The user's request to repair and retry has been executed within the bounded run. The first parser-V2 attempt failed before HTTP because of process sandbox loopback permissions and is preserved separately. One verified, byte-identical configuration retry passed the local endpoint gate and reached the model, then stopped at the expected-action mismatch. There is no automatic further run or M2 work.

## Evidence and reproduction

See [`M1_P0_JSON_PREFIX_PARSER_REVISION_EVIDENCE.md`](M1_P0_JSON_PREFIX_PARSER_REVISION_EVIDENCE.md), the raw run at `runs/m1_p0_local/25ep-pilot-json-prefix-v2-retry1-20261019/run/`, and `docs/ITERATION_LOG.md`. The independent command is:

```powershell
python scripts/verify_m1_p0_preflight_action_mismatch.py --run runs/m1_p0_local/25ep-pilot-json-prefix-v2-retry1-20261019/run
```

It returns `PASS_PACKAGE_INTEGRITY__NO_GO_ACTION_MISMATCH`, not a behavioral or compatibility PASS.
