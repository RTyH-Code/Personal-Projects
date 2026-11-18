"""The story, stage by stage, for story_bot.py: New Bark Town to Falkner's badge.

Each stage is a function of the bot. Places are map codes (see
tools/data/map_names.json) and tiles; warps are numbered as in the map's
event file.
"""


def leave_bedroom(bot):
    bot.go_through("T20R0202", 0)


def meet_mom(bot):
    # Mom stops the player at the foot of the stairs and hands over the Pokegear
    bot.settle()
    bot.go_through("T20R0201", 0)


def elms_lab(bot):
    # Professor Elm's lab: his introduction plays as the player walks in
    bot.go_through("T20", 0)
    bot.settle()


def choose_starter(bot):
    # the starters wait in the machine at the back of the lab; examining it opens the choice
    bot.talk("T20R0101", (8, 4))


def elms_errand(bot):
    # Elm explains the errand to Mr. Pokemon and his aide hands over Potions; then out of the lab
    bot.settle()
    bot.go_through("T20R0101", 0)


def to_mr_pokemon(bot):
    # west along Route 29 to Cherrygrove City, where the Guide Gent shows the player round, then north up
    # Route 30 to Mr. Pokemon's house
    bot.go_through("R30", 0)


def mr_pokemon(bot):
    # Mr. Pokemon hands over the Mystery Egg, and Professor Oak the Pokedex
    bot.settle()
    bot.talk("R30R0201", 0)


STAGES = [leave_bedroom, meet_mom, elms_lab, choose_starter, elms_errand, to_mr_pokemon, mr_pokemon]
