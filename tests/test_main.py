"""Tests for notebot.main."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from notebot.config import Channel
from notebot.main import _handle_audio

if TYPE_CHECKING:
    from telegram import Audio, Message

    from notebot.transcribe import Transcriber


class FakeTelegramFile:
    """Stands in for ``telegram.File``; the download writes dummy bytes."""

    async def download_to_drive(self, target: Path) -> None:
        target.write_bytes(b"audio")


class FakeAttachment:
    """Stands in for a ``telegram.Audio`` upload named ``memo.m4a``."""

    file_name = "memo.m4a"

    async def get_file(self) -> FakeTelegramFile:
        return FakeTelegramFile()


class FakeTranscriber:
    """Returns a fixed transcript; an empty one counts as a failure."""

    def __init__(self, transcript: str) -> None:
        self.transcript = transcript

    def transcribe(self, _audio_path: Path) -> str:
        return self.transcript


def handle_audio(tmp_path: Path, transcript: str, *, keep_audio: bool) -> str:
    """Run ``_handle_audio`` for one upload and return the note file text."""
    channel = Channel(
        note_file=tmp_path / "notes.md",
        template="{text}\n",
        keep_audio=keep_audio,
    )
    message = SimpleNamespace(date=datetime(2026, 11, 11, 9, 0, tzinfo=UTC))
    asyncio.run(
        _handle_audio(
            cast("Transcriber", FakeTranscriber(transcript)),
            channel,
            cast("Message", message),
            cast("Audio", FakeAttachment()),
        ),
    )
    return channel.note_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(("keep_audio", "kept_files"), [(True, 1), (False, 0)])
def test_keep_audio_decides_whether_transcribed_audio_stays(
    tmp_path: Path,
    keep_audio: bool,
    kept_files: int,
) -> None:
    """A transcribed upload is archived only when keep_audio is true."""
    note = handle_audio(tmp_path, "Buy oat milk.", keep_audio=keep_audio)

    assert note == "Buy oat milk.\n"
    assert len(list(tmp_path.glob("*.m4a"))) == kept_files


def test_failed_transcription_keeps_audio(tmp_path: Path) -> None:
    """With keep_audio false, the audio of a failure marker is still kept."""
    note = handle_audio(tmp_path, "", keep_audio=False)

    [audio_file] = tmp_path.glob("*.m4a")
    assert note == f"**failed transcription of audiofile {audio_file.name}**\n"
