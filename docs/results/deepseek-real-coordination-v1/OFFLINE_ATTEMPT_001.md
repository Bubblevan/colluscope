# Offline attempt 001 — retained failure

- Command: `python -m pytest -q tests/test_deepseek_real_coordination_v1.py`
- Result: **1 failed, 11 passed** (2026-10-21 local run; before freeze).
- Failure: `test_invalid_dependency_cannot_be_rendered_as_a_valid_ballot` expected `KeyError`; the implementation correctly raised `ValueError` when a required proposal/reply dependency was absent.
- Repair: corrected the test to assert the existing explicit dependency-block behavior. The missing-dependency case was retained; no scenario or failure row was removed.
- Re-run: **12 passed**. The new runner integration test additionally injects each of the four possible first-control failure positions and verifies no game request is issued after the first incorrect control.
