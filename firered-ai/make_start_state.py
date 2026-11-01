"""Create the save state that training starts from.

    python make_start_state.py path/to/firered.gba states/start.state
"""

import argparse
import sys

from firered_ai.bootstrap import skip_intro
from firered_ai.emulator import Emulator
from firered_ai.env import save_state_file
from firered_ai.maps import map_name
from firered_ai.ram import load_addresses, read_state


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom")
    p.add_argument("out", nargs="?", default="states/start.state")
    p.add_argument("--addresses", help="JSON file of RAM addresses (see tools/symbols_from_map.py)")
    p.add_argument("--screenshot", help="save a PNG of the final frame here")
    args = p.parse_args()

    addrs = load_addresses(args.addresses)
    emu = Emulator(args.rom)
    print("Skipping the intro (this takes a minute)...")
    ok = skip_intro(emu, addrs)
    s = read_state(emu.read, addrs)
    if args.screenshot:
        from PIL import Image

        Image.fromarray(emu.screen()).save(args.screenshot)
    if not ok:
        print(f"Couldn't reach the bedroom. Ended on {map_name(*s.map_id)} (valid={s.valid}).")
        print("If this is a hack with a different RAM layout, pass --addresses.")
        sys.exit(1)
    save_state_file(args.out, emu.save_state())
    print(f"Saved {args.out}: {map_name(*s.map_id)} at ({s.x}, {s.y}).")


if __name__ == "__main__":
    main()
