# telegram-notebot

A minimal Telegram bot that turns private channel posts into markdown notes.
Text messages are stored as-is; voice notes and audio files are transcribed
locally with faster-whisper (Large v3, quantized, auto German/English
detection) before storing.

Notes are organized per channel: each monitored channel maps to its own
markdown file under `[channels]`, and every post is appended there; audio
uploads are archived next to that file.

## Requirements

- Python 3.13 (managed via [uv](https://docs.astral.sh/uv/))
- A Telegram bot token (create a bot with [@BotFather](https://t.me/BotFather))
- The bot added as an **admin** to every private channel you want to monitor

## Setup

```sh
uv sync
cp config.example.toml config.toml
```

Store the bot token once in a file outside this repo:

```sh
echo '123456:ABC-your-token-from-BotFather' > /path/to/your/token-file
chmod 600 /path/to/your/token-file
```

Edit `config.toml`:

1. Point `token_file` at that file's path.
2. Map your channels under `[channels]`: Telegram chat ID -> markdown file
   for its notes (absolute, `~/...`, or relative to the working directory).
   Missing folders on that path are created.

### Finding the Channel ID

Private channels never show their numeric ID in any Telegram app, and an
invite link (`t.me/+AbCdEf...`) is not the ID. Any of these works:

- **Bot log (recommended)**:

1. Add the bot as an admin to the channel, then post anything. Unmapped channels are logged as:
  ```text
  Ignoring unmapped chat id=-1001234567890 title='My Channel'
  ```
2. Post any message into the channel
2. Then run `uv run notebot`
3. You'll see `Ignoring unmapped chat id=-100... title='...'` - copy that ID into [channels], run once
   more. In case nothing came through, you might have to repeat steps 2 and 3.

  Copy the `-100...` number into `[channels]` and run the bot again. No
  third-party tools needed.
- **Forward to an ID bot**: forward any post from the channel to
  [@getidsbot](https://t.me/getidsbot) or
  [@userinfobot](https://t.me/userinfobot); it replies with the origin chat ID.
- **Telegram Web**: open the channel at web.telegram.org; the URL fragment
  contains the internal ID, e.g. `#-1001234567890`.

Use the exact `-100` + digits form shown by the bot log when filling
`[channels]`; copying from there avoids conversion mistakes.

## Run

The bot is a one-shot job: it connects, processes **all pending channel
posts** (text, voice, audio), then exits. Undelivered updates stay queued
server-side for 24 hours, so keep runs spaced closer together than that -
see [Scheduling](#scheduling) below.

```sh
uv run notebot                  # uses ./config.toml
uv run notebot --config path/to/config.toml
```

### Scheduling

`import_notes_from_telegram.sh` wraps a drain for cron: it logs to
`~/.notebot_log` and sends a desktop notification on failure. Wire it up in
`crontab -e` (no username column there), e.g. every 40 minutes:

```sh
*/40 * * * *  /bin/bash /path/to/telegram-notebot/import_notes_from_telegram.sh
```

Note that cron does not fire while the machine is suspended; if missed runs
during sleep are a concern, use a systemd timer with `Persistent=true`
instead.

## Note Format

Each channel's `[channels]` entry names its markdown file: that file
collects the note blocks, and original uploads are archived next to it as
`YYYY-MM-DD-HH-MM-SS-<file-stem>.<ext>`.

A note block looks like:

```markdown
## 2026-08-24 14:03:22

Der gesprochene Text oder die Nachricht...

---
```

If an upload cannot be downloaded, or transcription fails or produces no
text, a marker entry referencing the (intended) audio file name is appended:

```markdown
## 2026-08-24 14:03:22

**failed transcription of audiofile 2026-08-24-14-03-22-journal.ogg**

---
```

## Configuration Reference

| Key                    | Default        | Meaning                                 |
|------------------------|----------------|-----------------------------------------|
| `token_file`           | required       | File holding the bot token (one line)   |
| `whisper.model`        | `large-v3`     | Any faster-whisper model name           |
| `whisper.device`       | `auto`         | `auto`, `cpu`, or `cuda`                |
| `whisper.compute_type` | `int8_float16` | Quantized; GPU-only. Use `int8` on CPU  |
| `channels`             | required       | Map of channel ID -> markdown note file |

## Troubleshooting

**`CUBLAS_STATUS_NOT_SUPPORTED` on RTX 50-series (Blackwell)**: ctranslate2
loads `libcublas.so.12`, but CUDA 12 cuBLAS lacks Blackwell support. The
reliable default is CPU (`device = "cpu"`, `compute_type = "int8"`). If you
want GPU speed anyway, install CUDA 13 cuBLAS and shadow the `.12` soname
(hacky; apt updates may revert it):

```sh
sudo apt install libcublas-13-1
sudo ln -sf /usr/local/cuda-13.1/targets/x86_64-linux/lib/libcublasLt.so.13 \
            /usr/lib/x86_64-linux-gnu/libcublasLt.so.12
sudo ln -sf /usr/local/cuda-13.1/targets/x86_64-linux/lib/libcublas.so.13 \
            /usr/lib/x86_64-linux-gnu/libcublas.so.12
```

**`Requested int8_float16 compute type, but ... do not support`**: you paired
`device = "cpu"` with `compute_type = "int8_float16"`. That mode exists only
on GPU; use `int8` on CPU.

## Tests

```sh
uv run pytest
```

## License
See [LICENSE](LICENSE) file.
