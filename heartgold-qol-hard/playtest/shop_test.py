#!/usr/bin/env python3
"""What the Goldenrod Department Store's 4F clerk sells, by badges held.

    shop_test.py TEST_ROM TREE DUMP OUT [BADGES...]

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test
harness). For each badge count (default 2, 4, 6 and 7, the evolution items'
tiers) the harness puts the player in the store's 4F with that many badges,
across the counter from the clerk (23, 7); the bot talks to them, picks Buy
and pages through the list. Each count's pages go side by side into
OUT/list_<badges>.png, one bottom screen per page, to be read off: the shop
builds its list where the bot can't read it back from memory.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import battle_test
import story_bot
from PIL import Image

STORE_4F = "T25R1004"
PAGES = 6               # six items a page: the vitamins and every evolution item fit in six


def main():
    rom, tree, dump, out = sys.argv[1:5]
    counts = [int(x) for x in sys.argv[5:]] or [2, 4, 6, 7]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        battle_test.Game(rom).make_state(state)
    bot = story_bot.Bot(rom, tree, dump, out)
    g = bot.game
    for badges in counts:
        g.run(400)
        if not g.start(state, bot.data, bot.world, STORE_4F, (22, 9), badges=badges, facing=0):
            sys.exit("the harness did not place the player")
        g.run(200)
        bot.walk(STORE_4F, [(23, 9)])           # across the counter from the clerk
        g.key("up", hold=3, after=20)
        for _ in range(2):                      # talk, then Buy
            g.key("a", after=60)
            g.run(120)
        shots = []
        for _ in range(PAGES):
            shots.append(g.emu.screenshot().copy())
            g.touch(58, 172, after=40)          # the next page's arrow
            g.run(30)
        strip = Image.new("RGB", (256 * len(shots), 192))
        for i, im in enumerate(shots):
            strip.paste(im.crop((0, 192, 256, 384)), (256 * i, 0))
        path = os.path.join(out, "list_%d.png" % badges)
        strip.save(path)
        print("%d badges: %s" % (badges, path), flush=True)


if __name__ == "__main__":
    main()
