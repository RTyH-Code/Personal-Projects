#!/usr/bin/env python3
"""Add the battle harness to a test build of the hack. Never part of a release.

Replaces the script of the PC in the player's bedroom with one that gives
the player up to six Pokemon and starts a trainer battle, all taken from
script variables that battle_test.py writes through the emulator:

    0x4000-0x4005  species of the six party Pokemon (0 = no Pokemon)
    0x4006-0x400B  their levels
    0x4010-0x4015  their held items
    0x4020-0x4037  their moves, four per Pokemon (0 = empty slot)
    0x400C         the trainer to fight
    0x400F         result, written after the battle: 1 lost, 2 won

    python3 playtest/make_harness.py /path/to/dumped/hg-engine /path/to/test/hg-engine

The first tree is a vanilla `make dump_scripts` dump (see
tools/hack/fossil_reviver.py); the second is a built copy of the hack, which
then needs `make` run again. Keep that copy for testing only.
"""
import os
import re
import shutil
import sys

SCRIPT = "data/scr_seq/scr_seq_0846_T20R0202.s"
INCLUDE = "data/scr_seq/include/event_T20R0202.inc"

HARNESS = """scr_seq_T20R0202_000:
	lockall
%s	trainer_battle 0x400C, 0, 0, 0
	check_battle_won VAR_SPECIAL_RESULT
	copyvar 0x400F, VAR_SPECIAL_RESULT
	addvar 0x400F, 1
	releaseall
	end

"""
GIVE = """	compare 0x40%02X, 0
	goto_if_eq _harness_skip_%d
	give_mon 0x40%02X, 0x40%02X, 0x40%02X, 0, 0, VAR_SPECIAL_RESULT
	set_mon_move %d, 0, 0x40%02X
	set_mon_move %d, 1, 0x40%02X
	set_mon_move %d, 2, 0x40%02X
	set_mon_move %d, 3, 0x40%02X
_harness_skip_%d:
"""


def main():
    dump, target = sys.argv[1], sys.argv[2]
    text = open(os.path.join(dump, SCRIPT), encoding="utf-8", newline="").read()
    gives = "".join(GIVE % (i, i, i, 6 + i, 0x10 + i, i, 0x20 + 4 * i, i, 0x21 + 4 * i, i, 0x22 + 4 * i,
                                   i, 0x23 + 4 * i, i) for i in range(6))
    text, n = re.subn(r"^scr_seq_T20R0202_000:\n.*?(?=^scr_seq_T20R0202_001:)", lambda _: HARNESS % gives,
                      text, flags=re.S | re.M)
    if n != 1:
        sys.exit("could not find the bedroom PC script")
    os.makedirs(os.path.join(target, os.path.dirname(INCLUDE)), exist_ok=True)
    open(os.path.join(target, SCRIPT), "w", encoding="utf-8", newline="").write(text)
    shutil.copy(os.path.join(dump, INCLUDE), os.path.join(target, INCLUDE))
    print("wrote the harness into", target)


if __name__ == "__main__":
    main()
