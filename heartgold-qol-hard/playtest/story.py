"""The story, stage by stage, for story_bot.py: New Bark Town to Bugsy's badge.

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


def mystery_egg(bot):
    # Elm's aide waits in the Violet Poke Mart with the Mystery Egg; without it, a man on Route 32 sends the
    # player back
    bot.travel("T22FS0101")
    bot.talk("T22FS0101", 4)
    bot.expect("FLAG_UNK_070", "getting the Mystery Egg")


def to_azalea(bot):
    # south down Route 32, through Union Cave and along Route 33 to Azalea Town, where Team Rocket has taken over
    # the Slowpoke Well
    bot.travel("T23")


def kurt(bot):
    # Kurt hears about the Rockets and storms off to the well
    bot.travel("T23R0501")
    bot.talk("T23R0501", 0)
    bot.go_through("T23R0501", 0)


def slowpoke_well(bot):
    # down the well, past the Grunts, to Proton; after him Kurt takes the player home. Until then a Grunt
    # stands in front of the gym door
    bot.travel("D26R0102")
    bot.talk("D26R0102", 4)
    bot.settle()
    bot.expect("FLAG_BEAT_AZALEA_ROCKETS", "beating Proton in the Slowpoke Well")


GYM = "T23GYM0102"


def ride(bot, stop, lands):
    """Azalea Gym: step onto the Spinarak cart at a stop and ride it along the web. The stops are tiles at the
    edge of each floor: 0-2 on the ground floor at x = 3, 9, 15, 3-5 and 6-8 at the foot and head of the middle
    floor, 9-11 on the top floor. Where a cart goes from the middle and top floors depends on the gym's two
    switches; carts only wait at four stops at a time (at first 0, 1, 2 and 7) and move to where they end up."""
    # walk up to the stop and take the last step by hand: the ride starts the moment the player steps on
    step = "up" if stop[1] in (32, 17) else "down"
    bot.walk(GYM, [(stop[0], stop[1] + (1 if step == "up" else -1))])
    bot.step(step)
    # the ride takes a while, and the player's tile only changes when it ends
    for _ in range(100):
        bot.game.run(20)
        here = bot.where()
        if here and here[1] == lands[0] and abs(here[2] - lands[1]) <= 1:
            break
    bot.settle()
    here = bot.where()
    if not here or abs(here[1] - lands[0]) > 0 or abs(here[2] - lands[1]) > 1:
        bot.stuck("the cart at %s ended at %s, not by %s" % (stop, here, lands))


def azalea_gym(bot):
    # out of Kurt's house and into Bugsy's gym. Bugsy stands at the head of the top floor's middle section,
    # which only the carts reach: switch 0 (top floor, and the middle floor's middle section) and switch 1 (the
    # middle floor's left section) flip their ends. With both switches off:
    bot.go_through("T23R0501", 0)
    bot.travel(GYM)
    ride(bot, (3, 32), (9, 24))      # stop 0 to the middle floor's middle section (stop 4)
    ride(bot, (9, 17), (3, 9))       # stop 7 to the top floor's left section (stop 9), past a Bug Catcher
    bot.talk(GYM, (4, 7))            # switch 0 on, by the Twins
    ride(bot, (3, 9), (3, 18))       # stop 9, now to the middle floor's left section (stop 6; off the cart at its foot)
    bot.talk(GYM, (2, 18))           # switch 1 on
    ride(bot, (3, 17), (9, 9))       # stop 6, with both switches on, to Bugsy's section (stop 10)
    bot.talk(GYM, 5)
    bot.expect("FLAG_GOT_TM89_FROM_BUGSY", "beating Bugsy")


STAGES = [leave_bedroom, meet_mom, elms_lab, choose_starter, elms_errand, pokegear, to_mr_pokemon, mr_pokemon, elms_call,
          back_to_elm, stolen_pokemon, to_violet, sprout_tower,
          violet_gym, mystery_egg, to_azalea, kurt, slowpoke_well, azalea_gym]
