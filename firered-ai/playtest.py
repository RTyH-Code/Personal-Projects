"""Playtest a FireRed ROM unattended: explore, hunt for bugs, write a report.

    python playtest.py path/to/rom.gba --hours 8

With no start points given, it makes new-game start states itself (for the
QoL + Hard hack: plain, Nuzlocke + level caps, and no items + Set style +
Exp. Share). Add your own to test later parts of the game:

    python playtest.py rom.gba --hours 8 --saves my-saves/*.sav --states states/*.state

.sav files are battery saves from mGBA (or any emulator that writes the raw
128 KiB flash). The playtester boots them and picks CONTINUE.

Results go to runs/playtest-<date>/: report.html (open it in a browser),
summary.json, and findings/ with a save state, inputs, screenshot and clip
for each problem. Stop early with Ctrl+C; the report is written either way.

Each run also keeps a save state of the furthest point each emulator reached
(furthest/ in the run folder). To carry on where the last run got to:

    python playtest.py rom.gba --hours 8 --continue-from latest
"""

from __future__ import annotations

import argparse
import os
import time

from firered_ai.runner import prepare, run


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom")
    p.add_argument("--hours", type=float, default=8.0, help="how long to play (default 8)")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                   help="emulators to run at once (default: all cores but one)")
    p.add_argument("--states", nargs="*", default=[], help="save states to start sessions from")
    p.add_argument("--saves", nargs="*", default=[], help="battery saves (.sav) to start sessions from")
    p.add_argument("--new-games", nargs="*", default=None, metavar="RULES",
                   help="new-game start states to make, one per argument, e.g. plain nuzlocke,level_caps "
                        "(default: three rule sets when no --states/--saves are given)")
    p.add_argument("--session-steps", type=int, default=2500, help="presses per session before a fresh start")
    p.add_argument("--out", default=None, help="results folder (default runs/playtest-<date>)")
    p.add_argument("--continue-from", metavar="RUN",
                   help="carry on where an earlier run got to: a run folder, or 'latest' for the newest in "
                        "the same place as --out")
    p.add_argument("--seed", type=int, default=int(time.time()) % 100000)
    p.add_argument("--addresses", help="JSON file of RAM addresses (see tools/symbols_from_map.py)")
    args = p.parse_args()
    if args.out is None:
        args.out = os.path.join("runs", time.strftime("playtest-%Y%m%d-%H%M"))

    config = prepare(args)
    print(f"Playing for {args.hours} h with {args.workers} workers. Results: {config['out']}")
    print("Open report.html in that folder at any time; it's refreshed every 5 minutes.")
    report = run(config, args.hours, args.workers)
    print(f"Done. Report: {report}")


if __name__ == "__main__":
    main()
