"""Get from power-on to standing in the player's bedroom, without a human.

The agent shouldn't spend its time on the title screen and Oak's speech,
so we skip them once with a script and save a state to start from. The
script mashes A through the dialogue. On the naming screens, START jumps to
OK and A confirms, so it presses START now and then too.

FireRed QoL + Hard then shows its challenge menu in the bedroom
(src/hack_challenge.c). Its rows are Nuzlocke, level caps, no items in
battle, Set battle style and party Exp. Share, then START ADVENTURE. The
script picks rules like this:
- B advances the intro text. In the menu, B only moves the cursor to START
  ADVENTURE, so extra presses are harmless.
- From START ADVENTURE, Down wraps to the first row. On each row, A toggles
  the rule and Down moves on.
- A on START ADVENTURE closes the menu, and A again answers YES to "Is this OK?".
Afterwards it reads the rule flags back to check they took.
"""

from __future__ import annotations

from .ram import DEFAULT_ADDRESSES, read_state

CHALLENGE_ROWS = ["nuzlocke", "level_caps", "no_items", "set_style", "exp_share"]
CHALLENGE_FLAGS = {
    "nuzlocke": "HACK_NUZLOCKE",
    "level_caps": "HACK_LEVEL_CAP",
    "no_items": "HACK_NO_BATTLE_ITEMS",
    "set_style": "HACK_SET_ONLY",
    "exp_share": "HACK_PARTY_EXP_SHARE",
}


def _bedroom(game):
    return next(k for k, m in game.maps.items() if m["name"] == "PalletTown_PlayersHouse_2F")


def tap(emu, buttons, wait):
    emu.press(buttons, 6)
    emu.press((), wait)


def skip_intro(emu, game=None, rules=(), addresses=DEFAULT_ADDRESSES, max_presses: int = 3000, log=print) -> bool:
    """Press buttons until the player is free in their bedroom. Returns True on success.

    `rules` lists challenge rules to switch on (see CHALLENGE_ROWS); only the
    QoL + Hard hack has them.
    """
    if game is None:
        from .game import Game

        game = Game.load("firered")
    bedroom = _bedroom(game)
    layout = game.layout
    emu.press((), 120)  # let the game boot
    for i in range(max_presses):
        s = read_state(emu.read, addresses, layout)
        if s.valid and s.map_id == bedroom:
            break
        emu.press(("START",) if i % 12 == 11 else ("A",), 4)
        emu.press((), 16)
        if log and i % 200 == 0:
            log(f"  intro: {i} presses")
    else:
        return False
    emu.press((), 180)  # let the room fade in

    if "HACK_NUZLOCKE" not in game.flags:
        unknown = set(rules)
        if unknown:
            raise ValueError(f"{game.name} has no challenge rules ({', '.join(sorted(unknown))})")
        for _ in range(6):
            tap(emu, ("B",), 30)
        s = read_state(emu.read, addresses, layout)
        return s.valid and s.map_id == bedroom

    unknown = set(rules) - set(CHALLENGE_ROWS)
    if unknown:
        raise ValueError(f"unknown challenge rule(s): {', '.join(sorted(unknown))}")
    for _ in range(40):  # through the intro text; the menu cursor ends on START ADVENTURE
        tap(emu, ("B",), 20)
    tap(emu, ("DOWN",), 20)  # wrap to the first row
    for row in CHALLENGE_ROWS:
        if row in rules:
            tap(emu, ("A",), 20)
        tap(emu, ("DOWN",), 20)
    tap(emu, ("A",), 90)  # START ADVENTURE
    for _ in range(3):  # "Is this OK?" -> YES (the default)
        tap(emu, ("A",), 60)
    for _ in range(12):  # the Nuzlocke rules text, if shown, and anything A opened
        tap(emu, ("B",), 30)

    s = read_state(emu.read, addresses, layout)
    if not (s.valid and s.map_id == bedroom):
        return False
    got = {r for r, f in CHALLENGE_FLAGS.items() if s.flag(game.flags[f])}
    if got != set(rules):
        if log:
            log(f"  challenge menu: asked for {sorted(rules)}, got {sorted(got)}")
        return False
    return True


def continue_from_save(emu, game, addresses=DEFAULT_ADDRESSES, max_presses: int = 300, log=print) -> bool:
    """After booting with a battery save: CONTINUE from the title menu, skip the recap.

    Returns True once the save is loaded and the player is on a real map.
    """
    layout = game.layout
    emu.press((), 120)
    for i in range(max_presses):
        s = read_state(emu.read, addresses, layout)
        # Before a save is loaded the save blocks are all zero: map (0, 0) at (0, 0).
        if s.valid and s.map_id != (0, 0) and s.map_id in game.maps and s.party_count <= 6:
            break
        tap(emu, ("START",) if i % 3 == 0 else ("A",), 30)
    else:
        if log:
            log("  couldn't get past the title screen with this save")
        return False
    for _ in range(15):  # "Previously on your quest..."
        tap(emu, ("B",), 30)
    return True
