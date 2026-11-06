"""Create a save state in the bedroom at the start of a new game.

    python make_start_state.py path/to/rom.gba states/start.state
    python make_start_state.py path/to/rom.gba states/nuzlocke.state --rules nuzlocke,level_caps

For FireRed QoL + Hard, --rules picks the challenge settings from the menu in
the bedroom: nuzlocke, level_caps, no_items, set_style, exp_share. Leave it
out for none. Making one state per rule set lets the playtester test them all.
"""

import argparse
import sys

from firered_ai.bootstrap import CHALLENGE_ROWS, skip_intro
from firered_ai.emulator import Emulator
from firered_ai.states import save_state_file
from firered_ai.game import detect
from firered_ai.ram import load_addresses, read_state


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom")
    p.add_argument("out", nargs="?", default="states/start.state")
    p.add_argument("--rules", default="", help=f"challenge rules to switch on: {', '.join(CHALLENGE_ROWS)}")
    p.add_argument("--addresses", help="JSON file of RAM addresses (see tools/symbols_from_map.py)")
    p.add_argument("--screenshot", help="save a PNG of the final frame here")
    args = p.parse_args()

    game, note = detect(args.rom)
    print(f"ROM: {note}")
    rules = [r.strip() for r in args.rules.split(",") if r.strip()]
    addrs = load_addresses(args.addresses)
    emu = Emulator(args.rom)
    print("Skipping the intro (this takes a minute)...")
    try:
        ok = skip_intro(emu, game, rules, addrs)
    except ValueError as e:
        p.error(str(e))
    s = read_state(emu.read, addrs, game.layout)
    if args.screenshot:
        from PIL import Image

        Image.fromarray(emu.screen()).save(args.screenshot)
    if not ok:
        print(f"Couldn't finish the new-game setup. Ended on {game.map_name(*s.map_id)} (valid={s.valid}).")
        print("Check the screenshot (--screenshot). If this is a hack with a different RAM layout, pass --addresses.")
        sys.exit(1)
    save_state_file(args.out, emu.save_state())
    print(f"Saved {args.out}: {game.map_name(*s.map_id)} at ({s.x}, {s.y})"
          + (f", rules: {', '.join(rules)}" if rules else "") + ".")


if __name__ == "__main__":
    main()
