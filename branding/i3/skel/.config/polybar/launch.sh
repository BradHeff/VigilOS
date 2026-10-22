#!/usr/bin/env bash
set -eu
pkill -u "$(id -u)" -x polybar || true
for attempt in {1..30}; do
    pgrep -u "$(id -u)" -x polybar >/dev/null || break
    sleep 0.1
done
while IFS= read -r monitor; do
    MONITOR="$monitor" polybar --reload main --config="$HOME/.config/polybar/config.ini" &
done < <(xrandr --query | awk '/ connected/ {print $1}')
