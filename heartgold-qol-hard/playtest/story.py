"""The story, stage by stage, for story_bot.py: New Bark Town to Falkner's badge.

Each stage is a function of the bot. Places are map codes (see
tools/data/map_names.json) and tiles; warps are numbered as in the map's
event file.
"""


def leave_bedroom(bot):
    bot.go_through("T20R0202", 0)


def meet_mom(bot):
    # Mom stops the player at the foot of the stairs and switches on the Bag, Trainer Card and menus
    bot.settle()
    bot.go_through("T20R0201", 0)


def elms_lab(bot):
    # into Professor Elm's lab
    bot.go_through("T20", 0)
    bot.settle()


def choose_starter(bot):
    # the starters wait in the machine at the back of the lab; examining it opens the choice
    bot.talk("T20R0101", (8, 4))
    bot.expect("FLAG_GOT_STARTER", "getting a starter")


def elms_errand(bot):
    # Elm explains the errand to Mr. Pokemon and his aide hands over Potions; then out of the lab
    bot.settle()
    bot.go_through("T20R0101", 0)


def pokegear(bot):
    # back home: Mom hands over the Pokegear, without which the neighbour won't let the player leave town
    bot.go_through("T20", 1)
    bot.talk("T20R0201", 0)
    bot.expect("FLAG_GOT_POKEGEAR", "getting the Pokegear")
    bot.go_through("T20R0201", 0)


def to_mr_pokemon(bot):
    # west along Route 29 to Cherrygrove City, where the Guide Gent shows the player round, then north up
    # Route 30 to Mr. Pokemon's house
    bot.go_through("R30", 0)


def mr_pokemon(bot):
    # Mr. Pokemon hands over the Mystery Egg, and Professor Oak the Pokedex
    bot.settle()
    bot.talk("R30R0201", 0)
    bot.expect("FLAG_GOT_POKEDEX", "getting the Pokedex")


def elms_call(bot):
    # on the way out, Elm phones: something terrible has happened at the lab
    bot.go_through("R30R0201", 0)
    bot.settle()


def back_to_elm(bot):
    # back to New Bark Town; in Cherrygrove City the rival picks a fight on the way
    bot.go_through("T20", 0)
    bot.settle()


def stolen_pokemon(bot):
    # the police officer in the lab asks the player to name the thief; Elm then takes the Mystery Egg
    bot.walk("T20R0101", [(4, 10), (5, 10), (6, 10)])
    bot.settle()


def to_violet(bot):
    # out of the lab and west again: Lyra shows how to catch a Pokemon on Route 29; then Routes 30 and 31,
    # through the gatehouse, to Violet City
    bot.go_through("T20R0101", 0)
    bot.go_through("R31", 0)
    bot.go_through("R31R0101", 0)


def sprout_tower(bot):
    # up Sprout Tower, past its Sages, to the Elder; after his battle the rival shows up and leaves
    bot.travel("D15R0103")
    bot.talk("D15R0103", 3)
    bot.settle()
    bot.expect("FLAG_HIDE_VIOLET_GYM_GYM_GUY_AFTER_SPROUT", "beating the Sprout Tower Elder")


def violet_gym(bot):
    # up through Falkner's gym, past his two Bird Keepers, to Falkner
    bot.travel("T22GYM0101")
    bot.walk("T22GYM0101", [(15, 20)])      # the lift: it carries the player up to the walkways
    bot.settle()
    bot.talk("T22GYM0101", 0)
    bot.expect("FLAG_GOT_TM51_FROM_FALKNER", "beating Falkner")


STAGES = [leave_bedroom, meet_mom, elms_lab, choose_starter, elms_errand, pokegear, to_mr_pokemon, mr_pokemon, elms_call,
          back_to_elm, stolen_pokemon, to_violet, sprout_tower,
          violet_gym]
