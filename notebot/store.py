"""Note storage: per-channel markdown files and archived audio.

Note blocks are formatted by each channel's template file (see
``notebot.config``). The failure markers and archived audio names are the
templates at the top of this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

# Note bodies stored when audio handling fails. Placeholder: {audio_file}.
TRANSCRIPTION_FAILURE_TEMPLATE = "**failed transcription of audiofile {audio_file}**"
DOWNLOAD_FAILURE_TEMPLATE = "**failed download of audiofile {audio_file}**"

# strftime pattern for {timestamp} in MEDIA_NAME_TEMPLATE.
MEDIA_TIMESTAMP_FORMAT = "%Y-%m-%d-%H-%M-%S"

# File name of an archived audio upload.
# Placeholders: {timestamp}, {note_stem} (note file name without extension),
# {suffix} (audio extension including the dot).
MEDIA_NAME_TEMPLATE = "{timestamp}-{note_stem}{suffix}"


def transcription_failure_note(audio_file: str) -> str:
    """Marker body stored when an audio note could not be transcribed."""
    return TRANSCRIPTION_FAILURE_TEMPLATE.format(audio_file=audio_file)


def download_failure_note(audio_file: str) -> str:
    """Marker body stored when an audio upload could not be downloaded."""
    return DOWNLOAD_FAILURE_TEMPLATE.format(audio_file=audio_file)


def append_note(
    note_file: Path,
    text: str,
    template: str,
    *,
    now: datetime | None = None,
) -> Path:
    """Append one note block, formatted by ``template``, to ``note_file``.

    ``template`` is a ``str.format`` string with the placeholders
    ``{timestamp}`` (a datetime, so ``{timestamp:%Y-%m-%d}`` picks its
    format) and ``{text}`` (the note body, stripped). The parent folder is
    created if missing.
    """
    block = template.format(timestamp=now or datetime.now(), text=text.strip())

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
    """Return ``media_dir`` joined with a name built by ``MEDIA_NAME_TEMPLATE``."""
    timestamp = (now or datetime.now()).strftime(MEDIA_TIMESTAMP_FORMAT)
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    media_dir.mkdir(parents=True, exist_ok=True)
    name = MEDIA_NAME_TEMPLATE.format(
        timestamp=timestamp,
        note_stem=note_stem,
        suffix=suffix,
    )
    return media_dir / name
