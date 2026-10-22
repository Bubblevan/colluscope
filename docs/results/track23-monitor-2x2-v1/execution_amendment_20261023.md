# Execution amendment: optional exact claim-text echo

The frozen schedule and research question remain unchanged. During the development Pilot, DeepSeek returned a complete HTTP 200 JSON response for `pilot-31-C1`, with the expected model alias and fingerprint, `finish_reason=stop`, valid usage, all nine claim IDs, allowed statuses, and citations that resolve to records in the request. Each claim also contained a `text` field echoing the claim presented to the model. For q9, that echo exactly matched the frozen input text.

The registered success gate requires the four decision fields (`claim_id`, `status`, `citations`, `short_reason`) and does not forbid extra fields. The first runner implemented a stricter exact-key check and therefore misclassified this response as a schema failure. The original `attempt_failed` row and raw response are preserved. The raw response hash is `ee3fb111b82a63da5b4dd4f2bd2f69c30db9941c5abb0111344912c87e3bd746`.

The compatibility parser accepts only one optional extra field, `text`, and only when it exactly equals the corresponding claim text in the frozen request. It removes that echo from the scoring projection and leaves status, citations, reasons, prompts, labels, schedule, metrics, and held-out pairs untouched. The request was received once; the response is reclassified offline and is not resent. The parser applies identically to all four arms and both stages.

The frozen no-call compatibility preflight passed. It counted four provider requests already received and eight still-unattempted Pilot requests. The first network attempt archived separately was denied by the local socket permission before TLS/HTTP; it received no provider response and is not counted as a DeepSeek call.

The machine-readable record is [execution_amendment.json](../../../research/experiments/track23-monitor-2x2-v1/execution_amendment.json); the compatibility runner is [continue_track23_monitor_v2_compat.py](../../../scripts/continue_track23_monitor_v2_compat.py). The Pilot still proceeds only on the fixed three development pairs, and its technical gate still ignores outcome direction.
