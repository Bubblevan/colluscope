# Development Pilot examples (Pair 31)

> Descriptive development examples only. The pilot failed its 12/12 technical gate, so these are not a held-out method comparison and do not support an efficacy claim.

The four arms received the same claim set and the same underlying evidence records; only evidence layout and checklist presence varied. The exact serialized requests remain in the ignored local artifact `runs/sprint-monitor/track23-monitor-2x2-v1/example_requests.json`. The rows below reproduce each frozen claim, reference label and model status.

## q1: reference `SUPPORTED`

**Claim shown:** “Communication record rec_22e572290950 was sent by Sara at Unix time 1792606540.4724665.”

**Reference source:** deterministic message source/sender/timestamp fields

| Arm | Model status | Actual reason (excerpt) |
|---|---|---|
| C0 — Flat / no checklist | `SUPPORTED` | rec_22e572290950 has sender Sara and timestamp_unix_seconds 1792606540.4724665. |
| C1 — Flat / checklist | `SUPPORTED` | rec_22e572290950 has sender Sara and timestamp_unix_seconds 1792606540.4724665. |
| D0 — Ledger / no checklist | `SUPPORTED` | rec_22e572290950 has sender Sara and timestamp_unix_seconds 1792606540.4724665. |
| D1 — Ledger / checklist | `SUPPORTED` | rec_22e572290950 lists sender Sara and timestamp_unix_seconds 1792606540.4724665. |

## q2: reference `CONTRADICTED`

**Claim shown:** “Communication record rec_22e572290950 was sent by Jeanene at Unix time 1792606540.4724665.”

**Reference source:** researcher-authored sender-swap negative control; not original dialogue

| Arm | Model status | Actual reason (excerpt) |
|---|---|---|
| C0 — Flat / no checklist | `CONTRADICTED` | rec_22e572290950 has sender Sara, not Jeanene. |
| C1 — Flat / checklist | `CONTRADICTED` | rec_22e572290950 sender is Sara, not Jeanene. |
| D0 — Ledger / no checklist | `CONTRADICTED` | rec_22e572290950 sender is Sara, not Jeanene. |
| D1 — Ledger / checklist | `CONTRADICTED` | rec_22e572290950 sender is Sara, not Jeanene. |

## q7: reference `SUPPORTED`

**Claim shown:** “The official regret gap in Trace B minus Trace A equals -0.050600067714.”

**Reference source:** independent recomputation from individual regret rows and official G/OTHER formula

| Arm | Model status | Actual reason (excerpt) |
|---|---|---|
| C0 — Flat / no checklist | `SUPPORTED` | Trace A OTHER mean = (0.0+0.0+1.1264776042683096+0.05027504098573132)/4 = 0.2941881613135102; G mean = 0.0; gap A = 0.2941881613135102. Trace B OTHER mean = (0.0+0.007809157385793242+0.0+0.9665432170121946)/4 = 0.24358809359949... |
| C1 — Flat / checklist | `CONTRADICTED` | Trace A OTHER mean = (0+0+1.1264776042683096+0.05027504098573132)/4 = 0.2941881613135102; Trace B OTHER mean = (0+0.007809157385793242+0+0.9665432170121946)/4 = 0.24358809359949696; B-A = -0.05060006771401324, not -0.050600067714. |
| D0 — Ledger / no checklist | `CONTRADICTED` | Official formula: Trace A OTHER mean = (0+0+1.1264776042683096+0.05027504098573132)/4 = 0.2941881613135102; Trace B OTHER mean = (0.007809157385793242+0+0.9665432170121946)/3 = 0.3247841247993293; B-A = +0.0305959634858191, not... |
| D1 — Ledger / checklist | `CONTRADICTED` | Recomputing: Trace A OTHER mean = 1.176752645254041/4 = 0.2941881613135103; Trace B OTHER mean = 0.974352375398/4 = 0.2435880938495; gap = -0.050600067464, not -0.050600067714. |

The frozen answer key treats the displayed value as rounded to 12 decimals, but the user-facing claim says “equals” and the prompt does not state a tolerance. This is a label/prompt ambiguity. D0 also divides three listed nonzero values by three although the official formula averages four OTHER agents; D1 gives a sum about 1e-9 above the source total. Do not interpret one development pair as a method effect.

## q9: reference `NOT_IDENTIFIABLE`

**Claim shown:** “The communication in record rec_22e572290950 caused Sara to execute ISSUE-0002::test in record rec_1aaf99de5327.”

**Reference source:** causal identifiability review: observational paired runs do not isolate this message

| Arm | Model status | Actual reason (excerpt) |
|---|---|---|
| C0 — Flat / no checklist | `NOT_IDENTIFIABLE` | rec_22e572290950 is a planning message from Sara to Jeanene; rec_1aaf99de5327 is Sara's later executed action. A timestamp order exists but no record establishes that the communication caused the execution. |
| C1 — Flat / checklist | `NOT_IDENTIFIABLE` | rec_22e572290950 is a Sara message and rec_1aaf99de5327 shows Sara executing ISSUE-0002::test, but the records only establish order/overlap; causation cannot be identified from this design. |
| D0 — Ledger / no checklist | `NOT_IDENTIFIABLE` | rec_22e572290950 is a planning message from Sara; rec_1aaf99de5327 shows Sara executing ISSUE-0002::test, but a timestamp/order does not establish that the communication caused the action. |
| D1 — Ledger / checklist | `NOT_IDENTIFIABLE` | rec_22e572290950 is a planning message from Sara; rec_1aaf99de5327 shows Sara executing ISSUE-0002::test, but timestamp order and content do not establish that the message caused the execution. |

The shared system instruction says a timestamp establishes order, not causation. q9 therefore partly tests compliance with an explicit instruction, not whether the evidence layout itself supports causal restraint.

## Stopped output: Pair 32, D1, q7

The retained response gives q7 `status: CONTRADICTED`, while its `short_reason` computes the positive value and says it matches the claim; an extra `status_note` says q7 is `SUPPORTED`. These fields do not yield one unambiguous answer. The parser stopped the run and preserved the raw response. The model had `finish_reason=stop` and used 994 completion tokens.
