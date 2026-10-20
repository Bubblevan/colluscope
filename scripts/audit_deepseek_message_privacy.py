#!/usr/bin/env python3
"""Check that locally captured Agent messages are absent from public files.

The scanner never prints message text. It reports only aggregate counts and
public file paths containing exact message matches.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Iterable


SKIP_SUFFIXES = {".bin", ".jpg", ".jpeg", ".png", ".pdf", ".pyc", ".zip"}
SKIP_PREFIXES = ("runs/", "reference/")


def public_paths(root: Path) -> list[Path]:
    def git_paths(*args: str) -> list[str]:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", *args, "-z"],
            check=True,
            stdout=subprocess.PIPE,
        )
        return [p for p in result.stdout.decode("utf-8").split("\0") if p]

    names = set(git_paths()) | set(git_paths("--others", "--exclude-standard"))
    paths = []
    for name in sorted(names):
        normalized = name.replace("\\", "/")
        if normalized.startswith(SKIP_PREFIXES) or Path(name).suffix.lower() in SKIP_SUFFIXES:
            continue
        path = root / name
        if path.is_file():
            paths.append(path)
    return paths


def extract_messages(response_dir: Path) -> list[str]:
    messages: list[str] = []
    for path in sorted(response_dir.glob("*-message-*.bin")):
        try:
            body = json.loads(path.read_bytes())
            for choice in body.get("choices", []):
                calls = choice.get("message", {}).get("tool_calls", [])
                for call in calls:
                    args = json.loads(call.get("function", {}).get("arguments", "{}"))
                    value = args.get("text")
                    if isinstance(value, str) and value:
                        messages.append(value)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError) as exc:
            raise ValueError(f"could not parse private response record {path.name}: {type(exc).__name__}") from None
    return messages


def find_exact_message_matches(messages: Iterable[str], paths: Iterable[Path]) -> list[str]:
    needles = {m.encode("utf-8") for m in messages if m}
    matches = []
    for path in paths:
        try:
            haystack = path.read_bytes()
        except OSError:
            continue
        if any(needle in haystack for needle in needles):
            matches.append(path.as_posix())
    return matches


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    response_dir = root / "runs" / "deepseek-first-m4" / "agent" / "responses"
    if not response_dir.is_dir():
        print(json.dumps({"status": "BLOCKED", "reason": "local_raw_agent_responses_missing"}))
        return 2
    messages = extract_messages(response_dir)
    paths = public_paths(root)
    matches = find_exact_message_matches(messages, paths)
    result = {
        "status": "PASS" if not matches else "FAIL",
        "private_messages_scanned": len(messages),
        "public_files_scanned": len(paths),
        "matching_public_files": matches,
        "message_text_emitted": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if not matches else 1


if __name__ == "__main__":
    sys.exit(main())
