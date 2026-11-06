#!/usr/bin/env bash
# Installs (or updates) the FireRed playtester in ~/firered-playtester.
#
# Install.bat runs this inside Ubuntu (WSL) for you. On Linux or an Apple
# Silicon Mac, run it yourself:  bash install/setup.sh
#
# It copies the program from this folder, makes a Python environment with
# the three packages the playtester needs (stable-retro, numpy, Pillow), and
# runs the tests to check everything works. Running it again updates the
# program and keeps your past runs.
set -euo pipefail

src="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
dest="$HOME/firered-playtester"

say() { printf '\n\033[1;36m%s\033[0m\n' "$*"; }

if ! command -v python3 >/dev/null; then
    echo "Python 3 isn't installed. On Ubuntu: sudo apt install python3 python3-venv" >&2
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    echo "Python 3.10 or newer is needed; this is $(python3 --version)." >&2
    exit 1
fi

say "Copying the playtester to $dest"
mkdir -p "$dest"
(cd "$src" && tar --exclude=.venv --exclude=runs --exclude=__pycache__ --exclude=states -cf - .) \
    | (cd "$dest" && tar -xf -)
mkdir -p "$dest/runs"
cd "$dest"

say "Setting up Python packages (the first time takes a few minutes)"
if [ ! -x .venv/bin/python ]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt pytest

say "Checking that everything works"
.venv/bin/python -m pytest -q -p no:cacheprovider tests

say "Installed. To run it from here:"
echo "  cd $dest && .venv/bin/python playtest.py path/to/rom.gba --hours 8"
