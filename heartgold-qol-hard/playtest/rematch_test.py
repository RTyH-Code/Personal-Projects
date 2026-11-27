#!/usr/bin/env python3
"""Fight any trainer with a team set from team_sets.py, played by the story bot.

    rematch_test.py TEST_ROM TREE DUMP OUT SET LEVEL TRIES TRAINER_ID...

TEST_ROM, TREE and DUMP are as for walk_test.py (a build with the test
harness). For each trainer, TRIES times: from a save state at the bedroom PC
the harness gives one Pokemon, the bot writes SET at LEVEL over the party
(the set's moves, items, natures, IVs and EVs, as before a boss in the
story), and the harness starts the battle with that trainer; the bot plays
it as in the story, with smart turns when STORY_SMART=1 (its potions stocked
in the bag as there). It is the way to reach fights the story bot has no
stage for, such as the Gym Leader rematches, which the game holds at the
Fighting Dojo on given days once each leader's number is in the Pokegear.

Each battle goes to OUT/battles.jsonl as in the story bot, and a line per
trainer is printed: wins out of tries, and which of theirs took the most of
ours.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import battle_test
import story_bot


def fight(bot, state, trainer):
    """One battle with the set already chosen. Returns "won", "lost" or "stuck"."""
    g = bot.game
    g.emu.savestate.load_file(state)
    g.vars_pointer, g.frames = None, 0
    g.run(40)
    if g.vars_pointer is None:
        return "stuck"
    # first only a Pokemon to build the set on (0x400E 3: the harness gives the party and stops)
    template = bot.data["species"]["PIKACHU"]
    for i in range(6):
        g.set_var(0x4000 + i, template if i == 0 else 0)
        g.set_var(0x4006 + i, 50)
        g.set_var(0x4010 + i, 0)
    for k in range(24):
        g.set_var(0x4020 + k, 0)
    g.set_var(0x400E, 3)
    g.key("a", after=120)
    g.run(120)
    bot.swap_team(bot.rematch_set, bot.rematch_level)
    if story_bot.SMART and bot.find_bag():
        bot.restock_field()
    # then the battle, with no Pokemon given: the party is the set
    for i in range(6):
        g.set_var(0x4000 + i, 0)
    g.set_var(0x400E, 0)
    g.set_var(0x400C, trainer)
    g.set_var(0x400F, 0)
    g.key("a", after=60)
    try:
        bot.settle()
    except story_bot.Stuck as e:
        if not str(e).startswith("lost a battle"):
            print("  stuck: %s" % e, flush=True)
            return "stuck"
    result = g.get_var(0x400F)
    return {2: "won", 1: "lost"}.get(result, "lost" if bot.party_fainted() else "stuck")


def main():
    rom, tree, dump, out, name, level, tries = sys.argv[1:8]
    trainers = [int(x) for x in sys.argv[8:]]
    os.makedirs(out, exist_ok=True)
    state = os.path.join(out, "bedroom.dst")
    if not os.path.exists(state):
        battle_test.Game(rom).make_state(state)
    bot = story_bot.Bot(rom, tree, dump, out)
    bot.rematch_set, bot.rematch_level = name, int(level)
    data = bot.data["trainers"]
    for trainer in trainers:
        results = []
        start = sum(1 for _ in open(os.path.join(out, "battles.jsonl"))) if os.path.exists(
            os.path.join(out, "battles.jsonl")) else 0
        for _ in range(int(tries)):
            results.append(fight(bot, state, trainer))
            if results[-1] == "won":
                break
        took = collections.Counter()
        if os.path.exists(os.path.join(out, "battles.jsonl")):
            for line in list(open(os.path.join(out, "battles.jsonl")))[start:]:
                r = json.loads(line)
                if r["result"] == "lost":
                    took.update(k["by"] for k in r["kos"] if k["side"] == "player")
        t = data.get(trainer, {})
        print("%3d %-12s %s: %s%s" % (trainer, t.get("name"), name, results,
                                     "  took the most: %s" % took.most_common(3) if took else ""), flush=True)


if __name__ == "__main__":
    main()
