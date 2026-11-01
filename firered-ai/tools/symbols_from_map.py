"""Pull the RAM addresses the agent needs out of a pret linker map.

    python tools/symbols_from_map.py pokefirered.map > addresses.json

Use this for hacks whose RAM layout differs from vanilla FireRed.
"""

import json
import re
import sys

from firered_ai.ram import DEFAULT_ADDRESSES


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    wanted = set(DEFAULT_ADDRESSES)
    found = {}
    pattern = re.compile(r"^\s+0x([0-9a-fA-F]+)\s+(\w+)\s*$")
    with open(sys.argv[1]) as f:
        for line in f:
            m = pattern.match(line)
            if m and m.group(2) in wanted:
                found[m.group(2)] = f"0x{int(m.group(1), 16):08X}"
    missing = wanted - set(found)
    if missing:
        print(f"warning: not found, keeping defaults: {', '.join(sorted(missing))}", file=sys.stderr)
    json.dump(found, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
