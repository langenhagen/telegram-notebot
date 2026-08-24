"""Tests for notebot.store."""

from datetime import datetime
from pathlib import Path

from notebot.store import (
    append_note,
    download_failure_note,
    media_path,
    transcription_failure_note,
)


def test_append_note_creates_markdown_block(tmp_path: Path) -> None:
    """A note appends one timestamped markdown block into the channel file."""
    now = datetime(2026, 8, 24, 14, 3)

    path = append_note(tmp_path / "recipes.md", "Simmer 20 minutes.", now=now)

    assert path == tmp_path / "recipes.md"
    assert path.read_text(encoding="utf-8") == (
        "## 2026-08-24 14:03:00\n\nSimmer 20 minutes.\n\n---\n\n"
    )


def test_append_note_decouples_file_from_folder(tmp_path: Path) -> None:
    """Repeated appends share the configured file regardless of folder name."""
    first = append_note(
        tmp_path / "Meeting Notes" / "journal.md",
        "Agenda sent.",
        now=datetime(2026, 8, 24, 9, 0),
    )
    second = append_note(
        tmp_path / "Meeting Notes" / "journal.md",
        "Follow-up done.",
        now=datetime(2026, 8, 24, 15, 30),
    )

    assert first == second == tmp_path / "Meeting Notes" / "journal.md"
    assert second.read_text(encoding="utf-8") == (
        "## 2026-08-24 09:00:00\n\nAgenda sent.\n\n---\n\n"
        "## 2026-08-24 15:30:00\n\nFollow-up done.\n\n---\n\n"
    )


def test_append_note_keeps_multiline_body(tmp_path: Path) -> None:
    """Multi-line bodies survive verbatim inside one block."""
    path = append_note(
        tmp_path / "ideas.md",
        "line one\nline two",
        now=datetime(2026, 1, 1, 0, 0),
    )

    assert path.read_text(encoding="utf-8") == (
        "## 2026-01-01 00:00:00\n\nline one\nline two\n\n---\n\n"
    )


def test_media_path_names_audio_after_note_file(tmp_path: Path) -> None:
    """Audio paths combine timestamp and note-file stem inside its folder."""
    now = datetime(2026, 8, 24, 14, 3, 22)

    path = media_path(tmp_path / "meeting-notes", "journal", ".ogg", now=now)

    assert path == tmp_path / "meeting-notes" / "2026-08-24-14-03-22-journal.ogg"
    assert path.parent.is_dir()


def test_media_path_adds_missing_suffix(tmp_path: Path) -> None:
    """Missing suffix dots are added to media filenames."""
    path = media_path(
        tmp_path / "ideas",
        "ideas",
        "mp3",
        now=datetime(2026, 1, 1, 0, 0),
    )

    assert path.name == "2026-01-01-00-00-00-ideas.mp3"


def test_failure_note_formats() -> None:
    """Failure markers render the expected bold text."""
    assert transcription_failure_note("x.ogg") == (
        "**failed transcription of audiofile x.ogg**"
    )
    assert download_failure_note("x.ogg") == ("**failed download of audiofile x.ogg**")
