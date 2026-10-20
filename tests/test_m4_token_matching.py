import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.run_m4_offline import load_documents  # noqa: E402
from scripts.audit_m4_llama_token_parity import validate_ledger, validate_owner_checks  # noqa: E402
from scripts.verify_m4_token_matching import BASELINE_PATH, CANDIDATE_PATH, verify  # noqa: E402


def test_v2_changes_only_neutral_placeholder_and_preserves_positive_control_mapping():
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    candidate = json.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    assert candidate["task"] == baseline["task"]
    assert candidate["signal_assignment"] == baseline["signal_assignment"]
    assert candidate["paired_messages"]["information_template"] == baseline["paired_messages"]["information_template"]
    assert candidate["paired_messages"]["neutral_message"] == "Signal code: NONE."
    assert baseline["paired_messages"]["neutral_message"] == "Signal code: XXXX."
    assert candidate["paired_messages"]["character_count_matched"] is True
    assert "maps to neither action" in candidate["paired_messages"]["neutral_semantics"]
    mapping = candidate["signal_assignment"]["mapping"]
    assert "NONE" not in mapping


def test_actual_frozen_gguf_tokenizer_reproduces_v1_failure_and_v2_equality(tmp_path):
    config, _scenarios, _splits, _positive = load_documents()
    if not Path(config["model"]["path"]).is_file():
        pytest.skip("the frozen local GGUF checkpoint is not installed")
    report = verify(tmp_path / "m4-positive-control-token-match.json")
    assert report["real_model_calls"] == 0
    assert report["server_launched"] is False
    assert report["network_calls"] == 0
    assert report["v1_exact_matches"] == 0
    assert report["v1_known_failure_reproduced"] is True
    assert report["v2_exact_matches"] == 24
    assert report["information_token_counts"] == [183]
    assert report["v1_neutral_token_counts"] == [184]
    assert report["v2_neutral_token_counts"] == [183]
    assert report["status"] == "PASS_POSITIVE_CONTROL_V2_LOCAL_TOKEN_MATCH"


def _ledger_pair(route="/tokenize", status=200):
    request_id = "fixed-token-probe"
    return [
        {
            "event": "attempt_started", "request_id": request_id, "method": "POST",
            "route": route, "url": f"http://127.0.0.1:8081{route}",
            "auth_header_saved": False, "proxy_disabled": True,
        },
        {
            "event": "attempt_terminal", "request_id": request_id,
            "http_status": status, "authorization_header_persisted": False,
        },
    ]


def test_independent_server_auditor_accepts_only_successful_loopback_token_routes():
    result = validate_ledger(_ledger_pair())
    assert list(result) == ["fixed-token-probe"]
    for invalid in (
        _ledger_pair(route="/v1/chat/completions"),
        _ledger_pair(route="/apply-template", status=500),
    ):
        with pytest.raises(ValueError):
            validate_ledger(invalid)


def test_independent_server_auditor_rejects_unpaired_attempt_and_auth_persistence():
    with pytest.raises(ValueError, match="unpaired HTTP events"):
        validate_ledger(_ledger_pair()[:1])
    rows = _ledger_pair()
    rows[0]["auth_header_saved"] = True
    with pytest.raises(ValueError, match="unsafe request metadata"):
        validate_ledger(rows)
    rows = _ledger_pair()
    rows[1]["authorization_header_persisted"] = True
    with pytest.raises(ValueError, match="authorization header persistence"):
        validate_ledger(rows)


def test_owner_auditor_allows_only_empty_startup_poll_before_exact_request_checks():
    observed = [{
        "LocalAddress": "127.0.0.1", "LocalPort": 8081, "OwningProcess": 17,
        "ExecutablePath": r"C:\frozen\llama-server.exe",
    }]
    rows = [
        {"phase": "startup", "expected_pid": 17, "expected_executable": r"C:\frozen\llama-server.exe",
         "observed_owners": [], "exact_owner_match": False},
        {"phase": "startup", "expected_pid": 17, "expected_executable": r"C:\frozen\llama-server.exe",
         "observed_owners": observed, "exact_owner_match": True},
        {"phase": "before:r1", "expected_pid": 17, "expected_executable": r"C:\frozen\llama-server.exe",
         "observed_owners": observed, "exact_owner_match": True},
    ]
    assert validate_owner_checks(rows, expected_request_count=1) == (17, r"c:\frozen\llama-server.exe")
    rows[-1]["observed_owners"] = []
    rows[-1]["exact_owner_match"] = False
    with pytest.raises(ValueError, match="pre-request listener ownership check failed"):
        validate_owner_checks(rows, expected_request_count=1)
