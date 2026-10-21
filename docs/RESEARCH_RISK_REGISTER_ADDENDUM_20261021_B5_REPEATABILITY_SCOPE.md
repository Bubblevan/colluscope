# Research risk addendum — M4 B5 repeatability scope

This dated addendum supplements the main risk register without editing prior hash-pinned records.

| Risk | Current evidence | Mitigation / remaining boundary |
|---|---|---|
| Repeated-call instability masks evidence-view comparisons | 19/48 historical/current exact-request pairs had different raw labels under matching request bytes and reported fingerprints. | Candidate repeats each exact view three times within one randomized run. This estimates finite repeat agreement only; it cannot identify provider randomness or hidden serving state. |
| Cross-view contrast is confounded | Public-only and Privileged-original differ in permission, delivered event package, metadata, wording, salience, token count, and content. | Interpret only as bundled evidence-package response sensitivity. Do not claim semantic comprehension, communication causality, collusion, or intent. |
| External disclosure of private communication | The candidate sends 72 privileged requests with two historical private-message events each (144 event appearances). | Keep raw payloads local, restrict ACLs, and require explicit scope-specific user approval before any external transfer. Current 232-call approval is consumed and does not cover this candidate. |
| Mutable provider identity | `deepseek-flash` is an alias, not a pinned weight file. | Recheck official model version; enforce returned-model and fingerprint gates. Any drift stops the run; matching fingerprints are not proof of identical hidden serving state. |
| Silent replacement or retry inflates evidence | Historical failure paths show why terminal rows must remain visible. | Candidate ceiling is 144 physical attempts, zero retries, zero replacements; pre-attempt append-only ledger and exact resume semantics are required before registration. |
| Engineering work outruns claim value | The prior proposal bundled a 320-call synthetic factorial with a 144-call repeatability question. | Defer the factorial. Continue only if the smaller repeatability result can change the interpretation of the already observed M4 contrast. |

No new model calls were made for this addendum.
