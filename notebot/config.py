"""Typed loader for the TOML configuration file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WhisperConfig:
    """Whisper transcription settings."""

    model: str
    device: str
    compute_type: str


@dataclass(frozen=True)
class Config:
    """Fully resolved runtime configuration.

    ``channels`` maps a chat ID to the markdown file its notes append to.
    """

    bot_token: str
    channels: dict[int, Path]
    whisper: WhisperConfig


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

    channels: dict[int, Path] = {}
    for chat_id_raw, file_value in channels_raw.items():
        chat_id = int(chat_id_raw)
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
        channels[chat_id] = note_file

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
