"""Tests for notebot.config."""

from pathlib import Path

import pytest

from notebot.config import Channel, WhisperConfig, load_config

TEMPLATE = "## {timestamp:%Y-%m-%d}\n\n{text}\n\n"
WHISPER = 'model = "small"\ndevice = "cpu"\ncompute_type = "int8"\n'


def write_config(
    tmp_path: Path,
    token_ref: Path,
    channel: str | None = None,
    *,
    whisper: str = WHISPER,
) -> Path:
    """Write a config pointing at ``token_ref`` with one channel.

    ``channel`` is the channel's raw TOML value; by default it names
    ``notes/recipes.md``, a valid template file in ``tmp_path``, and
    ``keep_audio = false``. ``whisper`` is the body of the ``[whisper]`` table.
    """
    if channel is None:
        channel = channel_table(tmp_path, keep_audio="false")
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        f'token_file = "{token_ref}"\n\n'
        f"[whisper]\n{whisper}\n"
        f'[channels]\n"-1001234567890" = {channel}\n',
        encoding="utf-8",
    )
    return config_path


def channel_table(tmp_path: Path, *, keep_audio: str | None) -> str:
    """Return a channel's TOML table with a valid template file in ``tmp_path``.

    ``keep_audio`` is the raw TOML value, or None to leave the key out.
    """
    template_file = tmp_path / "default.tpl"
    template_file.write_text(TEMPLATE, encoding="utf-8")
    keep_audio_part = "" if keep_audio is None else f", keep_audio = {keep_audio}"
    return (
        f'{{ file = "notes/recipes.md", template = "{template_file}"'
        f"{keep_audio_part} }}"
    )


def write_token(tmp_path: Path) -> Path:
    """Write a valid token file and return its path."""
    token_file = tmp_path / "token"
    token_file.write_text("secret-token\n", encoding="utf-8")
    return token_file


def test_loads_full_config(tmp_path: Path) -> None:
    """Token and channel template load from files; other keys load as written."""
    config = load_config(write_config(tmp_path, write_token(tmp_path)))

    assert config.bot_token == "secret-token"
    assert config.channels == {
        -1001234567890: Channel(
            note_file=Path("notes/recipes.md"),
            template=TEMPLATE,
            keep_audio=False,
        ),
    }
    assert config.whisper == WhisperConfig(
        model="small",
        device="cpu",
        compute_type="int8",
    )


def test_missing_keep_audio_raises(tmp_path: Path) -> None:
    """A channel's keep_audio has no default; leaving it out fails loudly."""
    channel = channel_table(tmp_path, keep_audio=None)
    config = write_config(tmp_path, write_token(tmp_path), channel)

    with pytest.raises(ValueError, match="keep_audio"):
        load_config(config)


def test_non_bool_keep_audio_raises(tmp_path: Path) -> None:
    """A channel's keep_audio must be a TOML boolean, not a string."""
    channel = channel_table(tmp_path, keep_audio='"yes"')
    config = write_config(tmp_path, write_token(tmp_path), channel)

    with pytest.raises(TypeError, match="keep_audio"):
        load_config(config)


def test_missing_whisper_key_raises(tmp_path: Path) -> None:
    """Whisper settings have no defaults; a missing one is named in the error."""
    config = write_config(
        tmp_path,
        write_token(tmp_path),
        whisper='model = "small"\ndevice = "cpu"\n',
    )

    with pytest.raises(ValueError, match="whisper.compute_type"):
        load_config(config)


def test_empty_channel_file_raises(tmp_path: Path) -> None:
    """Empty or root-only markdown file paths fail loudly."""
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
        f'{{ file = "notes/recipes.md", template = "{tmp_path / "nope.tpl"}",'
        " keep_audio = false }",
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
        f'{{ file = "notes/recipes.md", template = "{template_file}",'
        " keep_audio = false }",
    )

    with pytest.raises(ValueError, match="invalid template"):
        load_config(config)


def test_template_without_text_raises(tmp_path: Path) -> None:
    """A template that would drop every note body fails at load time."""
    template_file = tmp_path / "no-text.tpl"
    template_file.write_text("## {timestamp:%Y-%m-%d}\n", encoding="utf-8")
    config = write_config(
        tmp_path,
        write_token(tmp_path),
        f'{{ file = "notes/recipes.md", template = "{template_file}",'
        " keep_audio = false }",
    )

    with pytest.raises(ValueError, match="no {text} placeholder"):
        load_config(config)


@pytest.mark.parametrize("placeholder", ["{text.foo}", "{timestamp[0]}"])
def test_bad_placeholder_access_raises(tmp_path: Path, placeholder: str) -> None:
    """Attribute or index access that fails is reported as an invalid template."""
    template_file = tmp_path / "bad.tpl"
    template_file.write_text(f"{placeholder} {{text}}\n", encoding="utf-8")
    config = write_config(
        tmp_path,
        write_token(tmp_path),
        f'{{ file = "notes/recipes.md", template = "{template_file}",'
        " keep_audio = false }",
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
