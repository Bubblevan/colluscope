# DeepSeek Real Coordination Pilot V4 — Decision

**Decision: GO for the single frozen V4 batch after this branch is committed and pushed.** Offline evidence is complete. This is not a scientific conclusion or evidence of latent intent. No V4 model requests have yet been sent.

## Why execution is now admissible

- V3 is terminally closed as `INVALID_EXPERIMENT`, with zero requests, after a source-level strict-schema audit found unsupported `null` and `maxLength` constructs and an inaccurate endpoint record. No V3 row is reused.
- V4 uses supported string schemas and `UNDECIDED` for no-choice; a local validator rejects text over 240 characters after preserving raw output. The runner and freezer independently check the strict-schema subset.
- The configured and actual strict function-call endpoint agree: `https://api.deepseek.com/beta/chat/completions`.
- Tests pass (31), V4 freeze check passes, offline-only runner check passes with zero calls, and the research registry audit passes with V4 as the sole open cycle.
- The user directed continuing the previously approved 40-request DeepSeek batch after pre-dispatch repairs. V3 used 0 of 40; V4 retains the same exact maximum and $0.50 hard cost cap. Project allowance is 1,200 calls, so at most 3 calls remain unused after all 40 V4 attempts.

## Bounded execution

After push, execute:

```powershell
python scripts/run_deepseek_real_coordination_v4.py --execute
python scripts/analyze_deepseek_real_coordination_v4.py --write
python scripts/researchctl.py audit
```

The first four requests test explicit fact delivery/absence. Proceed to the 36 game requests only if all four return correct, valid, complete actions with stable model/fingerprint identity. Any incorrect control, invalid or truncated output, HTTP/transport failure, identity drift, hash mismatch, privacy failure, or budget boundary stops the relevant dependent requests; a control failure stops the entire game schedule. No retry, message rewrite, resampling, or replacement is permitted. Preserve all 40 assigned rows and every started attempt.

## Claim boundary

The primary result is a finite descriptive comparison of joint ballots under actual message delivery versus no peer delivery with the same shared +20 incentive and same number of stages. Agreement in no-delivery remains compatible with independent parallel response to a shared target. A positive gate does not prove communication caused coordination in a population and cannot identify hidden intent. No Monitor or M2 inference is authorized by this decision.
