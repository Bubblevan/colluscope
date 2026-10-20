import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.run_m4_offline import load_documents  # noqa: E402
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
