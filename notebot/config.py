"""Typed loader for the TOML configuration file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from string import Formatter


@dataclass(frozen=True)
class Channel:
    """Where one channel's notes go and how each note block looks.

    ``template`` is the content of the channel's template file; see
    ``notebot.store.append_note`` for its placeholders. ``keep_audio`` keeps
    archived audio after a successful transcription.
    """

    note_file: Path
    template: str
    keep_audio: bool


@dataclass(frozen=True)
class WhisperConfig:
    """Whisper transcription settings."""

    model: str
    device: str
    compute_type: str


@dataclass(frozen=True)
class Config:
    """Fully resolved runtime configuration.

    ``channels`` maps a chat ID to its markdown file, note template, and
    audio setting.
    """

    bot_token: str
    channels: dict[int, Channel]
    whisper: WhisperConfig


def _load_template(config_path: Path, chat_id: int, template_value: str) -> str:
    """Read a template file and check its placeholders once, up front.

    The template must contain ``{text}``; without it every note body would be
    dropped silently.
    """
    template_path = Path(template_value).expanduser()
    try:
        template = template_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(
            f"{config_path}: channel {chat_id}: cannot read template"
            f" {template_path}: {exc}",
        ) from exc
    try:
        template.format(timestamp=datetime.now(tz=UTC), text="")
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"{config_path}: channel {chat_id}: invalid template"
            f" {template_path}: {exc!r}",
        ) from exc
    if "text" not in {field for _, field, _, _ in Formatter().parse(template)}:
        raise ValueError(
            f"{config_path}: channel {chat_id}: template {template_path}"
            " has no {text} placeholder",
        )
    return template


def load_config(path: Path) -> Config:
    """Load and validate the config; missing required keys fail loudly."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))

    try:
        token_file = raw["token_file"]
        channels_raw = raw["channels"]
        whisper_raw = raw["whisper"]
    except KeyError as exc:
        raise ValueError(f"{path}: missing required key {exc.args[0]!r}") from exc
    try:
        whisper = WhisperConfig(
            model=whisper_raw["model"],
            device=whisper_raw["device"],
            compute_type=whisper_raw["compute_type"],
        )
    except KeyError as exc:
        raise ValueError(
            f"{path}: missing required key 'whisper.{exc.args[0]}'",
        ) from exc

    token_path = Path(str(token_file)).expanduser()
    try:
        bot_token = token_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"{path}: cannot read token file {token_path}: {exc}") from exc
    if not bot_token:
        raise ValueError(f"{path}: token file {token_path} is empty")

    channels: dict[int, Channel] = {}
    for chat_id_raw, channel_value in channels_raw.items():
        chat_id = int(chat_id_raw)
        if not isinstance(channel_value, dict):
            raise TypeError(
                f'{path}: channel {chat_id}: expected a [channels."{chat_id}"]'
                f" section with file, template, and keep_audio, got {channel_value!r}",
            )
        for key in ("file", "template", "keep_audio"):
            if key not in channel_value:
                raise ValueError(
                    f"{path}: channel {chat_id}: missing required key {key!r}",
                )
        file_value = channel_value["file"]
        template_value = channel_value["template"]
        keep_audio = channel_value["keep_audio"]
        if not isinstance(file_value, str) or not file_value.strip():
            raise ValueError(
                f"{path}: channel {chat_id}: 'file' must be a non-empty string,"
                f" got {file_value!r}",
            )
        note_file = Path(file_value).expanduser()
        if not note_file.stem:
            raise ValueError(
                f"{path}: channel {chat_id}: 'file' {file_value!r} has no file name",
            )
        if not isinstance(template_value, str) or not template_value.strip():
            raise ValueError(
                f"{path}: channel {chat_id}: 'template' must be a non-empty string,"
                f" got {template_value!r}",
            )
        if not isinstance(keep_audio, bool):
            raise TypeError(
                f"{path}: channel {chat_id}: keep_audio must be True or False,"
                f" got {keep_audio!r}",
            )
        channels[chat_id] = Channel(
            note_file=note_file,
            template=_load_template(path, chat_id, template_value),
            keep_audio=keep_audio,
        )

    return Config(
        bot_token=bot_token,
        channels=channels,
        whisper=whisper,
    )
