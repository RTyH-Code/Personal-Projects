#!/usr/bin/env bash
# Starts a playtest run. The Windows launcher (Playtest.bat) calls this inside
# Ubuntu; you can also call it directly:
#
#   bash ~/firered-playtester/install/run.sh ROM [HOURS] [START] [SAVES_FOLDER] [RUN_NAME]
#
# START is where sessions begin:
#   new       new games, one per set of challenge rules (the default)
#   saves     only the .sav files in SAVES_FOLDER: points you want checked
#   continue  where the last run got to (its furthest points and saved states)
# SAVES_FOLDER is only used with "saves"; pass - otherwise.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

rom="$1"
hours="${2:-8}"
start="${3:-new}"
saves="${4:-}"
[ "$saves" = "-" ] && saves=""  # the Windows launcher's "none"
name="${5:-playtest-$(date +%Y%m%d-%H%M)}"

if [ ! -f "$rom" ]; then
    echo "Can't find the ROM: $rom" >&2
    exit 1
fi

case "$start" in
    new)
        args=(--new-games plain nuzlocke,level_caps no_items,set_style,exp_share)
        ;;
    saves)
        if [ -z "$saves" ] || [ ! -d "$saves" ]; then
            echo "Can't find the saves folder: $saves" >&2
            exit 1
        fi
        shopt -s nullglob nocaseglob
        files=("$saves"/*.sav)
        shopt -u nullglob nocaseglob
        if [ ${#files[@]} -eq 0 ]; then
            echo "There are no .sav files in $saves" >&2
            exit 1
        fi
        echo "Starting sessions from ${#files[@]} save file(s)."
        args=(--saves "${files[@]}")
        ;;
    continue)
        args=(--continue-from latest)
        ;;
    *)
        echo "Unknown start: $start (use new, saves or continue)" >&2
        exit 1
        ;;
esac

exec .venv/bin/python playtest.py "$rom" --hours "$hours" --out "runs/$name" "${args[@]}"
