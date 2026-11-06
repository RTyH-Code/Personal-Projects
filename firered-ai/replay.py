"""Replay a playtest finding: load its save state, press the same buttons, see it happen.

    python replay.py path/to/rom.gba runs/playtest-.../findings/<folder> --out replay.gif

Prints what the detectors report during the replay and saves a GIF. You can
also load before.state in mGBA (File > Load State File): it's mGBA's own
save-state format. inputs.json lists the presses: [buttons, frames held,
frames waited, purpose].
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from firered_ai.emulator import Emulator
from firered_ai.explorer import Action
from firered_ai.game import detect
from firered_ai.ram import load_addresses
from firered_ai.tester import Tester, replay


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom")
    p.add_argument("finding", help="a findings/<folder> from a playtest run")
    p.add_argument("--out", default="replay.gif")
    p.add_argument("--addresses")
    args = p.parse_args()

    folder = Path(args.finding)
    info = json.loads((folder / "finding.json").read_text())
    print(f"Finding: {info['kind']}: {info['title']} ({info['map']})\n  {info['detail']}")
    game, note = detect(args.rom)
    print(f"ROM: {note}")
    emu = Emulator(args.rom)
    tester = Tester(emu, game, folder, addresses=load_addresses(args.addresses), log=None)
    emu.load_state((folder / "before.state").read_bytes())
    inputs = json.loads((folder / "inputs.json").read_text())
    frames = []
    orig_do = tester.do

    def do(a: Action):
        held = orig_do(a)
        frames.append(emu.screen().copy())
        return held

    tester.do = do
    found = replay(tester, inputs)
    same = [f for f in found if f.check == info["check"] and f.title == info["title"]]
    print(f"Replayed {len(inputs)} presses: {'reproduced' if same else 'did not reproduce'}.")
    for f in found:
        print(f"  step {f.step}: {f.kind}: {f.title}")
    if frames:
        from PIL import Image

        imgs = [Image.fromarray(fr) for fr in frames]
        imgs[0].save(args.out, save_all=True, append_images=imgs[1:], duration=50, loop=0)
        print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
