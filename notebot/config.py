"""Typed loader for the TOML configuration file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class Channel:
    """Where one channel's notes go and how each note block looks.

    ``template`` is the content of the channel's template file; see
    ``notebot.store.append_note`` for its placeholders.
    """

    note_file: Path
    template: str


@dataclass(frozen=True)
class WhisperConfig:
    """Whisper transcription settings."""

    model: str
    device: str
    compute_type: str


@dataclass(frozen=True)
class Config:
    """Fully resolved runtime configuration.

    ``channels`` maps a chat ID to its markdown file and note template.
    """

    bot_token: str
    channels: dict[int, Channel]
    whisper: WhisperConfig


def _load_template(config_path: Path, chat_id: int, template_value: str) -> str:
    """Read a template file and check its placeholders once, up front."""
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
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError(
            f"{config_path}: channel {chat_id}: invalid template"
            f" {template_path}: {exc!r}",
        ) from exc
    return template


def load_config(path: Path) -> Config:
    """Load and validate the config; missing required keys fail loudly."""
    raw = tomllib.loads(path.read_text(encoding="utf-8"))

    try:
        token_file = raw["token_file"]
        channels_raw = raw["channels"]
    except KeyError as exc:
        raise ValueError(f"{path}: missing required key {exc.args[0]!r}") from exc

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
                f"{path}: channel {chat_id}: expected"
                f' {{ file = "...", template = "..." }}, got {channel_value!r}',
            )
        file_value = channel_value.get("file")
        template_value = channel_value.get("template")
        if not isinstance(file_value, str) or not file_value.strip():
            raise ValueError(
                f"{path}: channel {chat_id}: markdown file"
                f" must be a non-empty string, got {file_value!r}",
            )
        note_file = Path(file_value).expanduser()
        if not note_file.stem:
            raise ValueError(
                f"{path}: channel {chat_id}: invalid markdown file {file_value!r}",
            )
        if not isinstance(template_value, str) or not template_value.strip():
            raise ValueError(
                f"{path}: channel {chat_id}: template file"
                f" must be a non-empty string, got {template_value!r}",
            )
        channels[chat_id] = Channel(
            note_file=note_file,
            template=_load_template(path, chat_id, template_value),
        )

    whisper_raw = raw.get("whisper", {})
    return Config(
        bot_token=bot_token,
        channels=channels,
        whisper=WhisperConfig(
            model=whisper_raw.get("model", "large-v3"),
            device=whisper_raw.get("device", "auto"),
            compute_type=whisper_raw.get("compute_type", "int8_float16"),
        ),
    )
