# Message Templates

Each `.tpl` file formats the note blocks of every channel whose `template` in
`config.toml` points to it. A template is a Python format string:

- `{timestamp}`: when the post was sent. The `strftime` codes after the colon
  pick the date format:
  - `{timestamp:%Y-%m-%d %H:%M}` -> `2026-08-24 14:03`
  - `{timestamp:%a, %d.%m.%Y}` -> `Mon, 24.08.2026`
- `{text}`: the note body.

Write literal braces as `{{` and `}}`. The bot checks every template at
startup and stops on an unknown placeholder.
