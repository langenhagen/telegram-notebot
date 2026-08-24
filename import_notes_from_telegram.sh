#!/bin/bash
# Import new notes from Telegram.
# Log and send a push notification in case of error.
#
# author: andreasl
set -e

cd "$(dirname "${BASH_SOURCE[0]}")"

date '+%Y-%m-%d--%H-%M-%S' >>"$HOME/.notebot_log"

.venv/bin/notebot 1>>"$HOME/.notebot_log" 2>&1 ||
    notify-send 'Something went wrong with Notebot drain'
