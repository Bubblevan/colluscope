# V5 research-risk follow-up — 2026-10-21

| ID | Risk | Current evidence | Control / interpretation |
|---|---|---|---|
| RV-250 | A pre-HTTP resolver failure may be mislabeled as proxy misconfiguration, provider outage, or model incapability. | V4 client has proxies disabled; its first request got Windows `getaddrinfo failed` before HTTP. A later direct no-proxy GET reached the official host and returned 401. | Keep V4 `EXECUTION_BLOCKED`; infer no behavior. V5 has fresh IDs and logs. |
| RV-251 | A V5 execution of the same temperature-zero fixed prompts may be misrepresented as independent replication or pooled with V4. | V4 had no HTTP response; V5 uses the same alias and fixed contexts under a separate registration. | Report separately, do not count fixed contexts as population/model replication, and make no latent-intent claim. |
| RV-252 | Updating shared research logs can invalidate previously hash-pinned experiment records. | The first V5 audit after modifying the shared iteration/risk files reported both M4 campaign output hashes mismatched. Restoring those files returned them to their frozen bytes. | Put later-cycle updates in versioned follow-up sidecars when shared files are frozen; retain the failed audit output. |


## V5 post-run observation — 2026-10-21

The model request failed at local name resolution even though no proxy was configured. Three immediate official-host direct probes and both active WLAN resolver queries succeeded. This indicates intermittent name-resolution behavior but does not identify its Windows/network cause. V5 remains terminal; no retry is authorized by its protocol. The analyzer's request-hash warning is independently falsified by raw byte hashing and preserved as an evaluator defect.
