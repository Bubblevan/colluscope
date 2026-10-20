from pathlib import Path

from scripts.audit_deepseek_message_privacy import find_exact_message_matches


def test_exact_private_message_is_detected_without_exposing_content(tmp_path: Path) -> None:
    public = tmp_path / "report.md"
    private_message = "Distinctive private proposal phrase for exact leak detection."
    public.write_text(f"Public text. {private_message}", encoding="utf-8")

    matches = find_exact_message_matches([private_message], [public])

    assert matches == [public.as_posix()]
    assert private_message not in " ".join(matches)


def test_unmatched_private_message_passes_and_empty_message_is_ignored(tmp_path: Path) -> None:
    public = tmp_path / "report.md"
    public.write_text("Sanitized report without the private text.", encoding="utf-8")

    assert find_exact_message_matches(["", "private message absent here"], [public]) == []


def test_scanner_checks_all_messages_and_files(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.log"
    first.write_text("unrelated", encoding="utf-8")
    second.write_text("another exact phrase from private text", encoding="utf-8")

    matches = find_exact_message_matches(
        ["not present", "another exact phrase from private text"], [first, second]
    )

    assert matches == [second.as_posix()]
