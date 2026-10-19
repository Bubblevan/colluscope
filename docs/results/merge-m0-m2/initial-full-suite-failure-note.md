# Retained M0–M2 full-suite initial failure

The first full-suite invocation in the merge-validation turn reported six loopback integration failures with Windows `WinError 10013` (access was denied) and `306 passed, 1 skipped`. This failure was surfaced in the tool response but its full output was truncated before it could be saved byte-for-byte. This note preserves the observed summary and explicitly records that the complete raw stack trace is unavailable; it is not represented as a verbatim raw log.

A subsequent run was executed both with the required local-process/network sandbox escalation and under the ordinary sandbox. Both completed with `312 passed, 1 skipped`. The successful ordinary-sandbox log is retained in `pytest-full-suite-pre-m3-success.log`. M3-specific tests are added after that baseline and will have their own saved final log.
