# Research risk addendum — repeatability runner canary

| Risk | Offline evidence | Residual boundary |
|---|---|---|
| Duplicate or silently retried attempts | Six focused tests passed. Start IDs are unique in the clean run; an intentionally stale fixture with one duplicate start row was rejected before another request. An interrupted started slot was terminalized as unknown and not resent. | A live run still requires human review of terminal failures; no replacement is permitted. |
| Malformed output treated as success | One canned malformed HTTP 200 remained `HTTP_200_INVALID_OUTPUT`; it was neither repaired nor retried. | Canned outputs do not establish real provider parsing reliability. |
| HTTP/transport failure misclassified | Initial HTTP 400 test exposed usage-priority masking; the runner now records transport/HTTP failure first. Regression test passes. | Live server error bodies and provider changes are not tested. |
| Credentials or private prompts leak | Loopback server observed the fake Authorization header, while results, ledgers, request manifests, and request bodies did not contain the fake key. Protected run ACL verified. | The actual API key is read only after registration/approval gates; provider-side privacy remains a separate approval decision. |
| Wrong endpoint or unregistered dispatch | Offline transport rejects a non-loopback target. Production entry point fails with `NEW_EXPERIMENT_NOT_REGISTERED` before key loading. | No live call is authorized; approval, registration, official price/version recheck, and expiry remain required. |
| Scientific overclaim | Canary is explicitly `offline_engineering_preflight`, with 0 model calls. | It cannot support a monitor accuracy, semantic understanding, collusion, intent, or causal claim. |

No changes were made to the historical M4 experiment, its inputs, or its results.
