"""Tests for notebot.main."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

from notebot.config import Channel, Config, WhisperConfig
from notebot.main import _handle_audio, process_update

if TYPE_CHECKING:
    from telegram import Audio, Message, Update

    from notebot.transcribe import Transcriber

SENT_AT = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)


class FakeTelegramFile:
    """Stands in for ``telegram.File``; the download writes dummy bytes."""

    async def download_to_drive(self, target: Path) -> None:
        target.write_bytes(b"audio")


class FailingTelegramFile:
    """A ``telegram.File`` whose download breaks after writing part of it."""

    async def download_to_drive(self, target: Path) -> None:
        target.write_bytes(b"partial")
        raise ConnectionError("network down")


class FakeAttachment:
    """Stands in for a ``telegram.Audio`` upload named ``memo.m4a``."""

    file_name = "memo.m4a"

    def __init__(self, tg_file: FakeTelegramFile | FailingTelegramFile) -> None:
        self.tg_file = tg_file

    async def get_file(self) -> FakeTelegramFile | FailingTelegramFile:
        return self.tg_file


class FakeTranscriber:
    """Returns a fixed transcript; an empty one counts as a failure."""

    def __init__(self, transcript: str) -> None:
        self.transcript = transcript

    def transcribe(self, _audio_path: Path) -> str:
        return self.transcript


class FailingTranscriber:
    """Raises like faster-whisper does on a corrupt audio file."""

    def transcribe(self, _audio_path: Path) -> str:
        raise RuntimeError("corrupt audio")


def handle_audio(
    tmp_path: Path,
    transcriber: FakeTranscriber | FailingTranscriber,
    *,
    keep_audio: bool,
    tg_file: FakeTelegramFile | FailingTelegramFile | None = None,
) -> str:
    """Run ``_handle_audio`` for one upload and return the note file text."""
    channel = Channel(
        note_file=tmp_path / "notes.md",
        template="{text}\n",
        keep_audio=keep_audio,
    )
    attachment = FakeAttachment(tg_file or FakeTelegramFile())
    asyncio.run(
        _handle_audio(
            cast("Transcriber", transcriber),
            channel,
            cast("Message", SimpleNamespace(date=SENT_AT)),
            cast("Audio", attachment),
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
    note = handle_audio(
        tmp_path, FakeTranscriber("Buy oat milk."), keep_audio=keep_audio
    )

    assert note == "Buy oat milk.\n"
    assert len(list(tmp_path.glob("*.m4a"))) == kept_files


@pytest.mark.parametrize(
    "transcriber",
    [FakeTranscriber(""), FailingTranscriber()],
    ids=["empty-transcript", "transcriber-raises"],
)
def test_failed_transcription_keeps_audio(
    tmp_path: Path,
    transcriber: FakeTranscriber | FailingTranscriber,
) -> None:
    """With keep_audio false, the audio named by a failure marker is kept."""
    note = handle_audio(tmp_path, transcriber, keep_audio=False)

    [audio_file] = tmp_path.glob("*.m4a")
    assert note == f"**failed transcription of audiofile {audio_file.name}**\n"


def test_failed_download_leaves_no_partial_file(tmp_path: Path) -> None:
    """A broken download is removed and noted as a download failure."""
    note = handle_audio(
        tmp_path,
        FakeTranscriber("never used"),
        keep_audio=True,
        tg_file=FailingTelegramFile(),
    )

    assert note.startswith("**failed download of audiofile ")
    assert not list(tmp_path.glob("*.m4a"))


def test_failed_note_write_keeps_audio(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audio is deleted only after its transcript is stored, never before."""

    def fail_append_note(*_args: object, **_kwargs: object) -> Path:
        raise OSError("disk full")

    monkeypatch.setattr("notebot.main.append_note", fail_append_note)

    with pytest.raises(OSError, match="disk full"):
        handle_audio(tmp_path, FakeTranscriber("Buy oat milk."), keep_audio=False)

    assert len(list(tmp_path.glob("*.m4a"))) == 1


def test_text_post_goes_to_its_channel_file(tmp_path: Path) -> None:
    """process_update routes by chat ID and ignores unmapped chats."""
    config = Config(
        bot_token="unused",
        channels={
            -1: Channel(
                note_file=tmp_path / "one.md", template="{text}\n", keep_audio=True
            ),
            -2: Channel(
                note_file=tmp_path / "two.md", template="{text}\n", keep_audio=True
            ),
        },
        whisper=WhisperConfig(model="unused", device="cpu", compute_type="int8"),
    )
    transcriber = cast("Transcriber", FakeTranscriber("never used"))

    for chat_id, text in [(-2, "for two"), (-3, "for nobody")]:
        update = SimpleNamespace(
            effective_message=SimpleNamespace(text=text, date=SENT_AT),
            effective_chat=SimpleNamespace(id=chat_id, title="Test Channel"),
        )
        asyncio.run(process_update(config, transcriber, cast("Update", update)))

    assert (tmp_path / "two.md").read_text(encoding="utf-8") == "for two\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["two.md"]
