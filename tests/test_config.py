"""Tests for notebot.config."""

from pathlib import Path

import pytest

from notebot.config import load_config


def write_config(tmp_path: Path, token_ref: Path) -> Path:
    """Write a minimal valid config pointing at ``token_ref``."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'token_file = "{token_ref}"\n\n[channels]'
        f'\n"-1001234567890" = "notes/recipes.md"\n',
        encoding="utf-8",
    )
    return config_path


def test_loads_token_from_file_with_defaults(tmp_path: Path) -> None:
    """Token loads from file; unset sections fall back to defaults."""
    token_file = tmp_path / "token"
    token_file.write_text("secret-token\n", encoding="utf-8")

    config = load_config(write_config(tmp_path, token_file))

    assert config.bot_token == "secret-token"
    assert config.channels == {-1001234567890: Path("notes/recipes.md")}
    assert config.whisper.model == "large-v3"
    assert config.whisper.device == "auto"
    assert config.whisper.compute_type == "int8_float16"


def test_empty_channel_directory_raises(tmp_path: Path) -> None:
    """Empty or root-only channel directories fail loudly."""
    token_ref = tmp_path / "token"
    token_ref.write_text("secret-token\n", encoding="utf-8")
    config_path = tmp_path / "config.toml"
    for dir_value in ('""', '"."', '"/"'):
        config_path.write_text(
            f'token_file = "{token_ref}"\n\n[channels]\n"-1001234567890"'
            f" = {dir_value}\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="markdown file"):
            load_config(config_path)


def test_missing_token_file_key_raises(tmp_path: Path) -> None:
    """Missing token_file key fails loudly."""
    config_path = tmp_path / "config.toml"
    config_path.write_text("[channels]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="token_file"):
        load_config(config_path)


def test_unreadable_token_file_raises(tmp_path: Path) -> None:
    """Unreadable token file fails loudly."""
    config = write_config(tmp_path, tmp_path / "does-not-exist")

    with pytest.raises(ValueError, match="cannot read token file"):
        load_config(config)


def test_empty_token_file_raises(tmp_path: Path) -> None:
    """Whitespace-only token file fails loudly."""
    token_file = tmp_path / "token"
    token_file.write_text("   \n", encoding="utf-8")
    config = write_config(tmp_path, token_file)

    with pytest.raises(ValueError, match="is empty"):
        load_config(config)
