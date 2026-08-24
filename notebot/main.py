"""One-shot Telegram drain: store channel posts as notes, transcribing audio."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from telegram import Audio, Bot, Message, Update, Voice

from notebot.config import Config, load_config
from notebot.store import (
    append_note,
    download_failure_note,
    media_path,
    transcription_failure_note,
)
from notebot.transcribe import Transcriber

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)

POLL_TIMEOUT = 2
READ_TIMEOUT = POLL_TIMEOUT + 5


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="path to the TOML config file (default: ./config.toml)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="logging level (default: INFO)",
    )
    return parser.parse_args()


def _note_time(message: Message) -> datetime:
    return message.date.astimezone()


async def _handle_audio(
    transcriber: Transcriber,
    note_file: Path,
    message: Message,
    attachment: Voice | Audio,
) -> None:
    now = _note_time(message)
    suffix = ".ogg"
    file_name = getattr(attachment, "file_name", None)
    if file_name:
        suffix = Path(file_name).suffix or suffix

    target = media_path(note_file.parent, note_file.stem, suffix, now=now)

    try:
        tg_file = await attachment.get_file()
        await tg_file.download_to_drive(target)
    except Exception:
        target.unlink(missing_ok=True)
        logger.exception("[%s] downloading %s failed", note_file.stem, target.name)
        append_note(
            note_file,
            download_failure_note(target.name),
            now=now,
        )
        return

    try:
        transcript = await asyncio.to_thread(transcriber.transcribe, target)
    except Exception:
        logger.exception("[%s] transcribing %s failed", note_file.stem, target.name)
        transcript = ""

    if not transcript:
        append_note(
            note_file,
            transcription_failure_note(target.name),
            now=now,
        )
        logger.warning("[%s] no transcript for %s", note_file.stem, target.name)
        return

    append_note(note_file, transcript, now=now)
    logger.info("[%s] stored transcript (%d chars)", note_file.stem, len(transcript))


async def process_update(
    config: Config,
    transcriber: Transcriber,
    update: Update,
) -> None:
    """Store one update's text, or download and transcribe its audio."""
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return

    note_file = config.channels.get(chat.id)
    if note_file is None:
        logger.info("Ignoring unmapped chat id=%s title=%r", chat.id, chat.title)
        return

    if message.text:
        append_note(note_file, message.text, now=_note_time(message))
        logger.info(
            "[%s] stored text note (%d chars)",
            note_file.stem,
            len(message.text),
        )
        return

    attachment = message.voice or message.audio
    if attachment is None:
        return

    await _handle_audio(transcriber, note_file, message, attachment)


async def drain(config: Config, transcriber: Transcriber) -> None:
    """Fetch and handle all pending updates once, then return."""
    async with Bot(config.bot_token) as bot:
        offset: int | None = None
        while True:
            updates = await bot.get_updates(
                offset=offset,
                timeout=POLL_TIMEOUT,
                read_timeout=READ_TIMEOUT,
                allowed_updates=[Update.MESSAGE, Update.CHANNEL_POST],
            )
            if not updates:
                break
            for update in updates:
                try:
                    await process_update(config, transcriber, update)
                except Exception:
                    logger.exception("Failed to handle update %s", update.update_id)
                finally:
                    offset = update.update_id + 1


def main() -> None:
    """Entry point: load the config and drain pending posts once."""
    args = parse_args()
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = load_config(args.config)
    transcriber = Transcriber(config.whisper)
    logger.info(
        "Draining pending posts for %d channel(s): %s",
        len(config.channels),
        sorted(config.channels.values()),
    )
    asyncio.run(drain(config, transcriber))
    logger.info("Done")
