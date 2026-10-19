# M3 preflight failure records

Exact tool output is retained locally under Git-ignored `runs/m3/_prereg-audit-20261020/`.

- `m3-identity-ledger-test-fixture-failure.log`: the first new test expected `without a successful identity probe`; the implementation's actual diagnostic was `completed run has no successful identity probe`. Test matcher corrected.
- `m3-identity-ledger-session-fixture-failure.log`: the refactored identity audit referenced stale variable `successful_pids`; corrected to the session-ID set and covered by tests.
- `m3-acl-canary-fixture-failure.log`: the Windows ACL test fixture omitted its `Path` import; added the import. ACL behavior then passed the fake-ACE regression and the real local canary.
- `m3-schedule-recomputed.json`: byte-identical output from `freeze_m3_schedule.py`; its frozen counterpart and SHA are committed in `configs/` and `m3-schedule-recomputation.log`.

These were offline test/fixture failures before any M3 model call. None were removed from the local evidence history.
