#!/usr/bin/env bash
# Starts a playtest run. The Windows launcher (Playtest.bat) calls this inside
# Ubuntu; you can also call it directly:
#
#   bash ~/firered-playtester/install/run.sh ROM [HOURS] [SAVES_FOLDER or -] [RUN_NAME] [watch]
#
# It always makes new-game start states for three sets of challenge rules.
# If SAVES_FOLDER holds .sav files, sessions also start from those.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

rom="$1"
hours="${2:-8}"
saves="${3:-}"
[ "$saves" = "-" ] && saves=""  # the Windows launcher's "no saves"
name="${4:-playtest-$(date +%Y%m%d-%H%M)}"
watch="${5:-}"  # "watch": one emulator plays at normal speed for the live view

if [ ! -f "$rom" ]; then
    echo "Can't find the ROM: $rom" >&2
    exit 1
fi

args=(--new-games plain nuzlocke,level_caps no_items,set_style,exp_share)
if [ "$watch" = "watch" ]; then
    args+=(--watch)
fi
if [ -n "$saves" ]; then
    shopt -s nullglob nocaseglob
    files=("$saves"/*.sav)
    shopt -u nullglob nocaseglob
    if [ ${#files[@]} -gt 0 ]; then
        echo "Starting sessions from ${#files[@]} save file(s) as well as new games."
        args+=(--saves "${files[@]}")
    else
        echo "No .sav files in $saves; starting from new games only."
    fi
fi

exec .venv/bin/python playtest.py "$rom" --hours "$hours" --out "runs/$name" "${args[@]}"
