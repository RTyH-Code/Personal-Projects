#!/usr/bin/env python3
"""Does a save from the last release carry on in a new one?

    save_carry.py NEW_ROM OLD_SAVE.dsv OUT_DIR

NEW_ROM is a build of the new release (no test harness needed), OLD_SAVE a
DeSmuME battery save the last release wrote standing in grass (the next.dsv
this script left in its OUT_DIR last time will do). OLD_SAVE itself is never
written: it is copied to where DeSmuME looks for NEW_ROM's
(~/.config/desmume/<rom name>.dsv, which is overwritten), so the same save
can be checked again without spending its PP. The game is continued from
it, two wild battles are fought, each with the first move that still has PP
(a move the game refuses is passed over), and the game is saved again from
the menu.

It passes when the save loads into the field, both battles are won and the
save file changes. OUT_DIR gets the new save (next.dsv, for the next
release's check) and carry.png, a strip of screenshots.
"""
import hashlib
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import battle_test
import walk_test as w
from PIL import Image


def main():
    rom, old, out = sys.argv[1:4]
    os.makedirs(out, exist_ok=True)
    dsv = os.path.expanduser("~/.config/desmume/%s.dsv" % os.path.splitext(os.path.basename(rom))[0])
    os.makedirs(os.path.dirname(dsv), exist_ok=True)
    shutil.copyfile(old, dsv)
    digest = lambda: hashlib.md5(open(dsv, "rb").read()).hexdigest()[:8]
    g = w.Walker(rom)
    shots = []

    def slow(n):
        for _ in range(n):
            g.emu.cycle(with_joystick=False)

    # the title screen and Continue: press A until the player stands in the field
    slow(900)
    for i in range(60):
        g.key("a", after=30)
        if g.position() and g.avatar_calls > 0 and i > 15:
            calls = g.avatar_calls
            slow(30)
            if g.avatar_calls > calls:
                break
    slow(200)
    shots.append(g.emu.screenshot().copy())
    where = g.position()
    print("loaded at", where)

    # pace in the grass until a wild Pokemon appears, then fight it with the first move that has PP left
    battles = won = move = 0
    for steps in range(400):
        g.created = []
        g.step("left" if steps % 2 else "right")
        if not g.created:
            continue
        for _ in range(100):            # the battle's command menu
            g.run(20)
            if battle_test.screen_state(g.emu.screenshot()) == "menu":
                break
        else:
            print("no battle menu")
            break
        turns = 0
        for _ in range(400):
            state = battle_test.screen_state(g.emu.screenshot())
            if state == "menu":
                turns += 1
                g.touch(128, 73, after=40)
                g.touch(*battle_test.MOVE_BUTTONS[move], after=90)
            elif state == "moves":
                # still on the move list: the move was refused (no PP left), so the next one from now on
                move = (move + 1) % 4
                g.touch(*battle_test.MOVE_BUTTONS[move], after=90)
            elif state in ("party", "confirm"):
                g.key("b")
            else:
                g.key("a", after=30)
                if not battle_test.screen_state(g.emu.screenshot()) and g.in_field() and g.in_field():
                    break
            g.run(20)
        battles += 1
        won += turns < 30 and g.in_field()
        shots.append(g.emu.screenshot().copy())
        print("battle %d over after %d turns, in the field at %s" % (battles, turns, g.position()))
        if battles == 2:
            break

    # save from the menu: X, Save, yes; then wait for the file to stop changing
    for _ in range(3):
        g.key("b")
        slow(40)
    before = digest()
    g.key("x")
    slow(60)
    g.touch(124, 76)
    slow(120)
    for _ in range(3):
        g.key("a")
        slow(120)
    last, same = None, 0
    for _ in range(40):
        slow(300)
        now, box = digest(), w.text_box(g.emu.screenshot())
        if box:
            g.key("a")
            slow(30)
        same = same + 1 if now == last and not box else 0
        last = now
        if same >= 3:
            break
    after = digest()
    shots.append(g.emu.screenshot().copy())
    print("save file %s -> %s" % (before, after))
    shutil.copyfile(dsv, os.path.join(out, "next.dsv"))
    strip = Image.new("RGB", (256 * len(shots), 384))
    for i, shot in enumerate(shots):
        strip.paste(shot, (256 * i, 0))
    strip.save(os.path.join(out, "carry.png"))
    ok = bool(where) and won == 2 and after != before
    print("PASS" if ok else "FAIL", "(loaded %s, battles won %d of 2, saved %s)" % (bool(where), won, after != before))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
