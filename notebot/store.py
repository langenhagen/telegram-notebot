"""Note storage: per-channel markdown files and archived audio."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def transcription_failure_note(audio_file: str) -> str:
    """Marker body stored when an audio note could not be transcribed."""
    return f"**failed transcription of audiofile {audio_file}**"


def download_failure_note(audio_file: str) -> str:
    """Marker body stored when an audio upload could not be downloaded."""
    return f"**failed download of audiofile {audio_file}**"


def append_note(
    note_file: Path,
    text: str,
    *,
    now: datetime | None = None,
) -> Path:
    """Append one note block to ``note_file``.

    A block is a timestamp heading, the note body, and a horizontal rule,
    separated by blank lines. The parent folder is created if missing.
    """
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    block = f"## {timestamp}\n\n{text.strip()}\n\n---\n\n"

    note_file.parent.mkdir(parents=True, exist_ok=True)
    with note_file.open("a", encoding="utf-8") as fh:
        fh.write(block)
    return note_file


def media_path(
    media_dir: Path,
    note_stem: str,
    suffix: str,
    *,
    now: datetime | None = None,
) -> Path:
    """Return ``<media_dir>/<YYYY-MM-DD-HH-MM-SS>-<note_stem><suffix>``."""
    stamp = (now or datetime.now()).strftime("%Y-%m-%d-%H-%M-%S")
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    media_dir.mkdir(parents=True, exist_ok=True)
    return media_dir / f"{stamp}-{note_stem}{suffix}"
