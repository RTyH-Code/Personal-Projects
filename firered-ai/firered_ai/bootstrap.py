"""Get from power-on to standing in the player's bedroom, without a human.

The agent shouldn't spend its training budget on the title screen and Oak's
speech, so we skip them once with a script and train from a save state.
The script mashes A through the dialogue. On the naming screens, START
jumps to OK and A confirms, so it presses START now and then too.
"""

from __future__ import annotations

from .maps import MAP_NAMES
from .ram import DEFAULT_ADDRESSES, read_state

BEDROOM = next(k for k, v in MAP_NAMES.items() if v == "PalletTown_PlayersHouse_2F")


def skip_intro(emu, addresses=DEFAULT_ADDRESSES, max_presses: int = 3000, log=print) -> bool:
    """Press buttons until the player is in their bedroom. Returns True on success."""
    emu.press((), 120)  # let the game boot
    for i in range(max_presses):
        s = read_state(emu.read, addresses)
        if s.valid and s.map_id == BEDROOM:
            break
        emu.press(("START",) if i % 12 == 11 else ("A",), 4)
        emu.press((), 16)
        if log and i % 200 == 0:
            log(f"  intro: {i} presses")
    else:
        return False
    # Let the room fade in, then dismiss anything still on screen.
    emu.press((), 180)
    for _ in range(6):
        emu.press(("B",), 4)
        emu.press((), 30)
    s = read_state(emu.read, addresses)
    return s.valid and s.map_id == BEDROOM
