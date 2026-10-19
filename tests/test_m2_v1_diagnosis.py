from __future__ import annotations

import json
from pathlib import Path

from scripts.diagnose_m2_v1_responses import (
    EMPTY_THINK_PREFIX,
    _log_summary,
    inspect_reasoning_envelope,
)


def test_only_exact_anchored_empty_envelope_is_approved_for_v2() -> None:
    result = inspect_reasoning_envelope(EMPTY_THINK_PREFIX + '{"ok":true}')
    assert result["kind"] == "leading_think_envelope"
    assert result["closed"] is True
    assert result["inner_trimmed_empty"] is True
    assert result["exact_observed_empty_prefix"] is True
    assert json.loads(result["diagnostic_remainder"]) == {"ok": True}


def test_nonempty_reasoning_is_detected_and_not_approved() -> None:
    result = inspect_reasoning_envelope('<think>do not expose this</think>\n{"ok":true}')
    assert result["kind"] == "leading_think_envelope"
    assert result["inner_trimmed_empty"] is False
    assert result["exact_observed_empty_prefix"] is False
    assert result["diagnostic_remainder"] == '{"ok":true}'
    assert "do not expose this" not in json.dumps(result)


def test_unclosed_reasoning_is_not_parsed_as_json() -> None:
    result = inspect_reasoning_envelope("<think>unfinished")
    assert result["kind"] == "unclosed_leading_think"
    assert result["closed"] is False
    assert result["diagnostic_remainder"] is None


def test_unapproved_prefix_is_not_removed() -> None:
    raw = "commentary " + EMPTY_THINK_PREFIX + '{"ok":true}'
    result = inspect_reasoning_envelope(raw)
    assert result["kind"] == "absent"
    assert result["diagnostic_remainder"] == raw


def test_server_log_diagnostic_counts_only_markers(tmp_path: Path) -> None:
    log = tmp_path / "server.log"
    log.write_text("JSON schema converted grammar\nfailed to parse grammar\nrequest completed\n",
                    encoding="utf-8")
    result = _log_summary(log)
    assert result["exists"] is True
    assert result["markers"]["schema_conversion"] == 2
    assert result["markers"]["grammar_compilation"] == 1
    assert result["markers"]["error_or_warning"] == 1
    assert "Converted grammar" not in json.dumps(result)
