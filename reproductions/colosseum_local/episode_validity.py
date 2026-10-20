"""Independent, privacy-preserving validity assessment for local Jira episodes.

The validator does not trust the runner's `complete` status. It derives a
separate status from the per-agent stage trace, committed execution tool
events, request/response attempt ledger, and (for prospective runs) raw-capture
index. It never returns message text, prompts, tool arguments, or HTTP bodies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EXPECTED_AGENT_COUNT = 6
EXPECTED_PLANNING_ROUNDS = 4
EXPECTED_TURNS = EXPECTED_AGENT_COUNT * (EXPECTED_PLANNING_ROUNDS + 1)
MAX_GENERATIONS = EXPECTED_TURNS * 3


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL at line {line_no}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL line {line_no} is not an object")
        rows.append(value)
    return rows


def _locate_run(output_root: Path) -> tuple[Path | None, list[str]]:
    turns_files = sorted(output_root.rglob("agent_turns.json")) if output_root.exists() else []
    if len(turns_files) != 1:
        return None, ["missing_agent_turns" if not turns_files else "ambiguous_agent_turns_outputs"]
    return turns_files[0].parent, []


def _episode_rows(path: Path, episode_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], ["missing_ledger"]
    try:
        return [row for row in _read_jsonl(path) if row.get("episode_id") == episode_id], []
    except (OSError, ValueError):
        return [], ["malformed_ledger"]


def _tool_event_has_error(value: Any) -> bool:
    if isinstance(value, dict):
        if "error" in value or str(value.get("status", "")).lower() in {"error", "rejected", "invalid"}:
            return True
        return any(_tool_event_has_error(child) for child in value.values())
    if isinstance(value, list):
        return any(_tool_event_has_error(child) for child in value)
    return False


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def _validate_attempts(
    episode_id: str,
    request_rows: list[dict[str, Any]],
    capture_rows: list[dict[str, Any]] | None,
    capture_directory: Path | None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    invalid: list[str] = []
    uncertain: list[str] = []
    starts: dict[int, dict[str, Any]] = {}
    terminals: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in request_rows:
        event = row.get("event")
        attempt = row.get("attempt")
        if not isinstance(attempt, int):
            continue
        if event == "http_attempt_started":
            if attempt in starts:
                invalid.append("duplicate_http_attempt_start")
            starts[attempt] = row
        elif event in {"http_response", "http_exception"}:
            terminals[attempt].append(row)

    attempt_ids = set(starts)
    terminal_missing = [attempt for attempt in sorted(attempt_ids) if not terminals.get(attempt)]
    terminal_duplicate = [attempt for attempt in sorted(attempt_ids) if len(terminals.get(attempt, [])) > 1]
    if terminal_missing:
        uncertain.append("http_attempt_without_terminal_record")
    if terminal_duplicate:
        invalid.append("duplicate_http_attempt_terminal")
    response_statuses: list[int] = []
    for attempt in sorted(attempt_ids):
        for terminal in terminals.get(attempt, []):
            if terminal.get("event") == "http_exception":
                invalid.append("http_transport_exception")
            else:
                code = terminal.get("status_code")
                if not isinstance(code, int):
                    uncertain.append("http_response_status_missing")
                else:
                    response_statuses.append(code)
                    if code != 200:
                        invalid.append("non_200_http_response")

    if not starts:
        uncertain.append("no_http_attempts_recorded")

    capture_count: int | None = None
    if capture_rows is None:
        uncertain.append("raw_request_response_capture_missing")
    else:
        capture_starts = {
            row.get("attempt"): row for row in capture_rows
            if row.get("event") == "http_attempt_started"
        }
        capture_terminals: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in capture_rows:
            if row.get("event") == "http_attempt_terminal":
                capture_terminals[row.get("attempt")].append(row)
        capture_count = len(capture_starts)
        if set(capture_starts) != attempt_ids:
            uncertain.append("raw_capture_request_attempt_mismatch")
        if any(len(capture_terminals.get(attempt, [])) != 1 for attempt in capture_starts):
            uncertain.append("raw_capture_terminal_missing_or_duplicate")
        for attempt, request in starts.items():
            captured = capture_starts.get(attempt)
            if captured:
                if captured.get("episode_id") != episode_id or "headers" in captured or "Authorization" in captured:
                    invalid.append("raw_capture_episode_or_header_policy_mismatch")
                if not _is_sha256(request.get("request_sha256")) or not _is_sha256(captured.get("request_body_sha256")):
                    uncertain.append("request_body_hash_missing_or_malformed")
                elif request.get("request_sha256") != captured.get("request_body_sha256"):
                    invalid.append("raw_capture_request_hash_mismatch")
                if captured.get("endpoint") != "http://127.0.0.1:8081/v1/chat/completions":
                    invalid.append("raw_capture_endpoint_mismatch")
                if captured.get("method") != "POST" or captured.get("auth_headers_recorded") is not False:
                    invalid.append("raw_capture_method_or_auth_policy_mismatch")
                _verify_capture_file(
                    capture_directory, captured.get("request_body_path"),
                    captured.get("request_body_sha256"), captured.get("request_body_bytes"),
                    "request", invalid, uncertain,
                )
            outer_terminals = terminals.get(attempt, [])
            raw_terminals = capture_terminals.get(attempt, [])
            if len(outer_terminals) == 1 and len(raw_terminals) == 1:
                outer, raw = outer_terminals[0], raw_terminals[0]
                if raw.get("episode_id") != episode_id or "headers" in raw or "Authorization" in raw:
                    invalid.append("raw_capture_episode_or_header_policy_mismatch")
                if outer.get("event") == "http_response":
                    if raw.get("status") != "http_response":
                        invalid.append("raw_capture_terminal_kind_mismatch")
                    if outer.get("status_code") != raw.get("status_code"):
                        invalid.append("raw_capture_status_mismatch")
                    if not _is_sha256(outer.get("response_sha256")) or not _is_sha256(raw.get("response_body_sha256")):
                        uncertain.append("response_body_hash_missing_or_malformed")
                    elif outer.get("response_sha256") != raw.get("response_body_sha256"):
                        invalid.append("raw_capture_response_hash_mismatch")
                    if (
                        not isinstance(outer.get("response_bytes"), int)
                        or outer.get("response_bytes") != raw.get("response_body_bytes")
                    ):
                        invalid.append("raw_capture_response_length_mismatch")
                    _verify_capture_file(
                        capture_directory, raw.get("response_body_path"),
                        raw.get("response_body_sha256"), raw.get("response_body_bytes"),
                        "response", invalid, uncertain,
                    )
                elif raw.get("status") != "transport_or_capture_exception":
                    invalid.append("raw_capture_exception_kind_mismatch")

    summary = {
        "http_attempts": len(starts),
        "http_responses": len(response_statuses),
        "http_status_counts": {str(code): count for code, count in sorted(Counter(response_statuses).items())},
        "http_transport_exceptions": sum(
            row.get("event") == "http_exception" for rows in terminals.values() for row in rows
        ),
        "http_unclosed_attempts": len(terminal_missing),
        "capture_attempts": capture_count,
    }
    return summary, invalid, uncertain


def _verify_capture_file(
    directory: Path | None,
    filename: Any,
    expected_sha256: Any,
    expected_bytes: Any,
    label: str,
    invalid: list[str],
    uncertain: list[str],
) -> None:
    if directory is None or not isinstance(filename, str) or Path(filename).name != filename:
        invalid.append(f"raw_capture_{label}_path_invalid")
        return
    path = directory / filename
    if not path.is_file():
        uncertain.append(f"raw_capture_{label}_file_missing")
        return
    try:
        data = path.read_bytes()
    except OSError:
        uncertain.append(f"raw_capture_{label}_file_unreadable")
        return
    actual_sha = hashlib.sha256(data).hexdigest().upper()
    if not _is_sha256(expected_sha256) or actual_sha != expected_sha256:
        invalid.append(f"raw_capture_{label}_file_hash_mismatch")
    if not isinstance(expected_bytes, int) or expected_bytes != len(data):
        invalid.append(f"raw_capture_{label}_file_length_mismatch")


def assess_episode(
    *,
    episode_id: str,
    output_root: Path,
    progress_ledger: Path,
    request_ledger: Path,
    raw_capture_index: Path | None = None,
    require_raw_capture: bool = True,
) -> dict[str, Any]:
    """Return VALID_EPISODE/INVALID_EPISODE/INDETERMINATE_EPISODE and counts only."""
    invalid: list[str] = []
    uncertain: list[str] = []
    progress, progress_errors = _episode_rows(progress_ledger, episode_id)
    uncertain.extend(progress_errors)
    terminals = [row for row in progress if row.get("event") == "episode_terminal"]
    latest = terminals[-1] if terminals else None
    runner_status = latest.get("status") if latest else None
    if latest is None:
        uncertain.append("episode_terminal_missing")
    elif runner_status != "runner_returned":
        invalid.append("upstream_runner_did_not_return_normally")
    output_path_value = latest.get("upstream_output") if latest else None
    run_root = Path(output_path_value) if output_path_value else output_root
    if not run_root.is_absolute():
        run_root = output_root / run_root
    run_dir, locate_errors = _locate_run(run_root)
    uncertain.extend(locate_errors)

    turn_count = 0
    planning_turns = 0
    execution_turns = 0
    error_turns = 0
    logical_generations = 0
    committed_actions = 0
    committed_agents: Counter[str] = Counter()
    if run_dir is not None:
        for required in ("agent_turns.json", "tool_events.json", "final_summary.json"):
            if not (run_dir / required).is_file():
                uncertain.append(f"missing_{required.removesuffix('.json')}")
        try:
            turns = _read_json(run_dir / "agent_turns.json")
            tools = _read_json(run_dir / "tool_events.json")
            final = _read_json(run_dir / "final_summary.json")
            if not isinstance(turns, list) or not isinstance(tools, list) or not isinstance(final, dict):
                raise ValueError("episode artifacts have unexpected shapes")
        except (OSError, json.JSONDecodeError, ValueError):
            turns, tools, final = [], [], {}
            uncertain.append("malformed_episode_artifact")

        turn_count = len(turns)
        names_by_phase: dict[str, set[str]] = {"planning": set(), "execution": set()}
        observed_turns: Counter[tuple[str, str, int | None]] = Counter()
        for row in turns:
            if not isinstance(row, dict):
                invalid.append("malformed_agent_turn")
                continue
            phase = row.get("phase")
            agent = row.get("agent")
            round_number = row.get("planning_round")
            if phase not in names_by_phase or not isinstance(agent, str):
                invalid.append("malformed_agent_turn")
                continue
            names_by_phase[phase].add(agent)
            key_round = round_number if phase == "planning" else None
            observed_turns[(phase, agent, key_round)] += 1
            if str(row.get("response", "")).startswith("[ERROR]") or row.get("protocol_error"):
                error_turns += 1
            steps = row.get("conversation_steps")
            if not isinstance(steps, int) or isinstance(steps, bool) or steps < 1 or steps > 3:
                invalid.append("invalid_agent_generation_count")
            else:
                logical_generations += steps
        planning_turns = sum(1 for row in turns if isinstance(row, dict) and row.get("phase") == "planning")
        execution_turns = sum(1 for row in turns if isinstance(row, dict) and row.get("phase") == "execution")
        agents = names_by_phase["execution"]
        if len(agents) != EXPECTED_AGENT_COUNT or names_by_phase["planning"] != agents:
            invalid.append("agent_stage_coverage_mismatch")
        if turn_count != EXPECTED_TURNS:
            invalid.append("agent_turn_count_mismatch")
        for agent in agents:
            for round_number in range(1, EXPECTED_PLANNING_ROUNDS + 1):
                if observed_turns[("planning", agent, round_number)] != 1:
                    invalid.append("planning_turn_coverage_mismatch")
            if observed_turns[("execution", agent, None)] != 1:
                invalid.append("execution_turn_coverage_mismatch")
        if any(count > 1 for count in observed_turns.values()):
            invalid.append("duplicate_agent_stage_record")
        if error_turns:
            invalid.append("agent_turn_error_response")
        if logical_generations < EXPECTED_TURNS or logical_generations > MAX_GENERATIONS:
            invalid.append("logical_generation_count_out_of_bounds")

        if final.get("status") != "complete":
            invalid.append("environment_summary_not_complete")
        for event in tools:
            if not isinstance(event, dict):
                invalid.append("malformed_tool_event")
                continue
            result = event.get("result")
            if _tool_event_has_error(result):
                invalid.append("tool_event_rejected")
            if event.get("phase") == "execution" and event.get("tool_name") == "assign_task":
                nested = result.get("result") if isinstance(result, dict) else None
                if (
                    isinstance(result, dict)
                    and result.get("status") == "success"
                    and isinstance(nested, dict)
                    and isinstance(nested.get("state_updates"), dict)
                    and bool(nested["state_updates"])
                ):
                    committed_actions += 1
                    if isinstance(event.get("agent_name"), str):
                        committed_agents[event["agent_name"]] += 1
                else:
                    invalid.append("execution_action_not_committed")
        if committed_actions != EXPECTED_AGENT_COUNT:
            invalid.append("execution_commit_count_mismatch")
        if set(committed_agents) != agents or any(count != 1 for count in committed_agents.values()):
            invalid.append("execution_commit_agent_coverage_mismatch")

    request_rows, request_errors = _episode_rows(request_ledger, episode_id)
    uncertain.extend(request_errors)
    capture_rows: list[dict[str, Any]] | None = None
    if raw_capture_index is not None and raw_capture_index.exists():
        try:
            capture_rows = _read_jsonl(raw_capture_index)
        except (OSError, ValueError):
            uncertain.append("malformed_raw_capture_index")
    elif require_raw_capture:
        uncertain.append("raw_request_response_capture_missing")
    http_summary, http_invalid, http_uncertain = _validate_attempts(
        episode_id, request_rows, capture_rows,
        raw_capture_index.parent if raw_capture_index is not None else None,
    )
    invalid.extend(http_invalid)
    uncertain.extend(http_uncertain)
    if http_summary["http_attempts"] != logical_generations:
        invalid.append("http_attempt_vs_agent_generation_mismatch")
    # A legacy run can be known invalid even though it predates raw-body capture.
    if invalid:
        status = "INVALID_EPISODE"
    elif uncertain:
        status = "INDETERMINATE_EPISODE"
    else:
        status = "VALID_EPISODE"
    return {
        "episode_id": episode_id,
        "status": status,
        "valid_episode": status == "VALID_EPISODE",
        "runner_status_observed": runner_status,
        "turns": {
            "total": turn_count,
            "planning": planning_turns,
            "execution": execution_turns,
            "error_responses": error_turns,
            "committed_execution_actions": committed_actions,
            "logical_generations": logical_generations,
        },
        "http": http_summary,
        "reason_codes": sorted(set(invalid + uncertain)),
        "known_invalid_reason_codes": sorted(set(invalid)),
        "evidence_gaps": sorted(set(uncertain)),
        "private_content_exported": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--progress-ledger", type=Path, required=True)
    parser.add_argument("--request-ledger", type=Path, required=True)
    parser.add_argument("--raw-capture-index", type=Path)
    parser.add_argument("--allow-missing-raw-capture", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = assess_episode(
        episode_id=args.episode,
        output_root=args.output_root,
        progress_ledger=args.progress_ledger,
        request_ledger=args.request_ledger,
        raw_capture_index=args.raw_capture_index,
        require_raw_capture=not args.allow_missing_raw_capture,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if result["status"] == "VALID_EPISODE" else 2 if result["status"] == "INVALID_EPISODE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
