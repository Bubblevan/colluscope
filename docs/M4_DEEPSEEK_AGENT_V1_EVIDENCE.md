# M4 DeepSeek Agent V1 — Evidence Record

**State:** pre-inference freeze candidate; no DeepSeek API request has been made by this task yet.  
**Protocol:** `M4-DEEPSEEK-AGENT-V1`  
**Pilot plan:** `configs/m4-deepseek-pilot-plan-v1.json`  
**Pilot plan SHA-256:** `63a04a7874132bfa91fa758f9a864f2516f8fc3bff8fa4e59099049248380bba` (regenerate after any frozen source change).

## Frozen inputs

- Scenario IDs, matrices, 24 split groups, target, +20 A/B private task-score rule, positive-control task, and M4 focal schedule come from the existing frozen M4 configs. Historical Qwen M4 artifacts are not read or rewritten by the new Agent runner.
- The compatibility plan has 30 possible slots: 20 Strict Function Calling slots (8 Agent, 12 Monitor) and 10 predefined JSON fallback slots (4 Agent, 6 Monitor). Fallback is unlocked only by a raw HTTP 400 explicitly stating a tool/function/strict capability is unsupported.
- Formal Agent ceiling: 24 assigned groups, 264 physical requests maximum, zero retries, zero replacement groups. Each group has 7 baseline/positive-control requests, plus 4 focal ballot requests only when an eligible proposal is delivered.
- The shared budget ceiling is 900 physical HTTP attempts and USD 5.00 at the frozen peak rates. The planned maximum across pilot, Agent, and Monitor schedules is 670 requests.
- Raw prompt and response bytes, private messages, T/B/E, API diagnostics, and ledgers are written only below Git-ignored `runs/deepseek-first-m4/`, with a verified current-user-only Windows ACL. Auth headers and `.env` contents are never written.

## Offline evidence before dispatch

- Targeted runtime/audit suite: 34 passed after adding raw-response gate replay, private-channel leak mutation, delivery-barrier failure, hard request-cap, exact pilot-plan and Monitor prompt-renderer checks.
- Full repository suite on Python 3.12.4 / Windows 11: 546 passed, 1 opt-in host-dependent Windows listener-owner test skipped; see `docs/results/deepseek-first-m4/logs/pytest-full-offline-preflight.log`. That full run preceded the final documentation/freeze-plan regeneration edits; repeat it at the frozen commit before any API request.
- A deliberately malformed test-only pilot-plan artifact ending in a literal `\n` failed byte equality; the original failure is retained in `docs/results/deepseek-first-m4/logs/pilot-plan-freeze-newline-failure.log`. It was rewritten with one LF byte; the committed-plan reproduction test then passed.
- A direct `pytest` executable invocation had an import-path collection failure; the repository-supported `python -m pytest` invocation collected and passed. The error is preserved in `docs/results/deepseek-first-m4/logs/pytest-monitor-import-failure.log`.
- Local ACL preflight verified current-user-only access on a temporary directory. `.env` endpoint/model preflight passed without printing or persisting the key.
- No LLM/API calls, downloads, training, or M2 comparison have been run in this task as of this evidence state.

## Runtime audit record

The formal gate auditor in `src/colluscope/deepseek_m4_audit.py` reads raw request/response bytes, independently parses action fields, checks request and response hashes, reconstructs the expected private/public contexts, validates the A/B-only delivery barrier, and recomputes the plurality/tie-break, public welfare, regret, private bonus, realized task scores, and Public-only E. The two preselected groups must both pass this replay before bulk M4 can start. A gate or group failure stops the next Agent phase; failures are not replaced.

After live execution, append the final private run manifest hash, selected interface, returned provider model/fingerprint, assigned/completed/failed counts, physical attempts/HTTP 200/unknown outcomes, token usage, reserved and provider-reported cost, audit result, and exact replay commands below. Do not copy private message text into this tracked evidence file.
