# Research Risk Register Follow-up — Repeatability Profile Clustering

- **Date:** 2026-10-21
- **Scope:** unregistered `m4-b5-view-repeatability-v2` candidate; no live calls

| ID | Risk / counterexample | Evidence | Required handling |
|---|---|---|---|
| RV-268 | Treating 48 context/view cells as 48 unique model inputs | Prepared manifest has 47 distinct body hashes: 23 Public-only, 24 Privileged-original. One public hash maps to two source contexts and receives six assignments. | Report both cell and body-profile denominators. Use the 23 unique Public-only profiles as primary clusters; count the shared baseline once. |
| RV-269 | Double-counting one shared public control in two context-pair changes | One identical public request body links to two distinct privileged request bodies. | Keep 24 paired context results as secondary descriptive rows; cluster primary gates by the unique public body. The shared cluster is changed if either linked privileged mode differs, but counts once. |
| RV-270 | Overstating input equality as hidden-intent evidence | Byte-identical Public-only requests correspond to two different source-unit hashes; private histories are not visible in that request. | This supports only a finite evidence-boundary observation. It does not establish hidden agreement, intent, or model understanding. |
| RV-271 | Treating the preparation audit as an independent prompt compiler | The auditor hashes prepared request bytes and reuses frozen runtime constants to locate historical source files; it does not independently recompile all prompt bodies. | Describe it as a profile-aware read-only manifest audit. Preserve exact source/body hashes and keep the prompt compiler as a separate provenance layer. |
| RV-272 | Interpreting historical exact-request disagreement as randomness or provider nondeterminism | Existing raw audit shows 19/48 label disagreements across historical/current observations with matching bytes and reported fingerprints. | Use “response variation across retained observations.” Hidden serving state and routing are not identified. |
| RV-273 | Sending private evidence without explicit scope approval | 72 Privileged-original requests contain two historical private-message events each. | Any new approval must explicitly cover 144 event appearances and the provider. The consumed 232-call approval cannot be reused. |

This addendum does not alter the frozen 232-call campaign, original candidate protocol, raw local runs, or previous audits.
