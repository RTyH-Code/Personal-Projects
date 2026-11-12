"""Boot a built ROM headless and save screenshots, to confirm it starts.

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
        python tools/boot_check.py build/hg-engine/test.nds out-dir

Needs py-desmume (pip install py-desmume). Presses A every two seconds for
90 seconds of game time and saves five screenshots along the way.
"""
import os
import sys

from desmume.controls import Keys, keymask
from desmume.emulator import DeSmuME

SHOTS = (600, 1800, 3000, 4200, 5400)


def main():
    rom, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    emu = DeSmuME()
    emu.open(rom)
    emu.volume_set(0)
    for frame in range(1, SHOTS[-1] + 1):
        if frame % 120 == 0:
            emu.input.keypad_add_key(keymask(Keys.KEY_A))
        elif frame % 120 == 6:
            emu.input.keypad_rm_key(keymask(Keys.KEY_A))
        emu.cycle(with_joystick=False)
        if frame in SHOTS:
            emu.screenshot().save(os.path.join(out, f"frame{frame}.png"))
    print(f"ran {SHOTS[-1]} frames")


if __name__ == "__main__":
    main()
