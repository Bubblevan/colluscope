# Offline attempt 003 — retained failure

- Command: `python -m pytest -q tests/test_deepseek_real_coordination_v1.py tests/test_deepseek_real_coordination_analysis_v1.py`
- Result: **1 failed, 14 passed**.
- Counterexample: independent replay accepted a request whose bytes had been modified by an added trailing space, because it compared canonicalized JSON values instead of the exact frozen serialized request bytes.
- Repair: compare reconstructed canonical request bytes directly to the stored request body. The semantic JSON is unchanged, but the raw artifact no longer passes as an exact replay.
- The test remains and verifies raw tampering detection even when local attempt hashes are rewritten consistently.
