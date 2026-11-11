"""Tests for notebot.config."""

from pathlib import Path

import pytest

from notebot.config import Channel, load_config

TEMPLATE = "## {timestamp:%Y-%m-%d}\n\n{text}\n\n"


def write_config(tmp_path: Path, token_ref: Path, channel: str | None = None) -> Path:
    """Write a config pointing at ``token_ref`` with one channel.

    ``channel`` is the channel's raw TOML value; by default it names
    ``notes/recipes.md`` and a valid template file in ``tmp_path``.
    """
    if channel is None:
        template_file = tmp_path / "default.tpl"
        template_file.write_text(TEMPLATE, encoding="utf-8")
        channel = f'{{ file = "notes/recipes.md", template = "{template_file}" }}'
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'token_file = "{token_ref}"\n\n[channels]\n"-1001234567890" = {channel}\n',
        encoding="utf-8",
    )
    return config_path


def write_token(tmp_path: Path) -> Path:
    """Write a valid token file and return its path."""
    token_file = tmp_path / "token"
    token_file.write_text("secret-token\n", encoding="utf-8")
    return token_file


def test_loads_token_from_file_with_defaults(tmp_path: Path) -> None:
    """Token and channel template load from files; unset sections use defaults."""
    config = load_config(write_config(tmp_path, write_token(tmp_path)))

    assert config.bot_token == "secret-token"
    assert config.channels == {
        -1001234567890: Channel(note_file=Path("notes/recipes.md"), template=TEMPLATE),
    }
    assert config.whisper.model == "large-v3"
    assert config.whisper.device == "auto"
    assert config.whisper.compute_type == "int8_float16"


def test_empty_channel_directory_raises(tmp_path: Path) -> None:
    """Empty or root-only channel directories fail loudly."""
    token_ref = write_token(tmp_path)
    for dir_value in ("", ".", "/"):
        config_path = write_config(
            tmp_path,
            token_ref,
            f'{{ file = "{dir_value}", template = "default.tpl" }}',
        )

        with pytest.raises(ValueError, match="markdown file"):
            load_config(config_path)


def test_plain_path_channel_raises(tmp_path: Path) -> None:
    """A channel given as a bare path, without a template, fails loudly."""
    config = write_config(tmp_path, write_token(tmp_path), '"notes/recipes.md"')

    with pytest.raises(TypeError, match="expected"):
        load_config(config)


def test_missing_template_key_raises(tmp_path: Path) -> None:
    """A channel table without a template fails loudly."""
    config = write_config(
        tmp_path,
        write_token(tmp_path),
        '{ file = "notes/recipes.md" }',
    )

    with pytest.raises(ValueError, match="template file"):
        load_config(config)


def test_missing_template_file_raises(tmp_path: Path) -> None:
    """A template file that cannot be read fails loudly."""
    config = write_config(
        tmp_path,
        write_token(tmp_path),
        f'{{ file = "notes/recipes.md", template = "{tmp_path / "nope.tpl"}" }}',
    )

    with pytest.raises(ValueError, match="cannot read template"):
        load_config(config)


def test_unknown_template_placeholder_raises(tmp_path: Path) -> None:
    """A template with a misspelled placeholder fails at load time."""
    template_file = tmp_path / "typo.tpl"
    template_file.write_text("{txt}\n", encoding="utf-8")
    config = write_config(
        tmp_path,
        write_token(tmp_path),
        f'{{ file = "notes/recipes.md", template = "{template_file}" }}',
    )

    with pytest.raises(ValueError, match="invalid template"):
        load_config(config)


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
