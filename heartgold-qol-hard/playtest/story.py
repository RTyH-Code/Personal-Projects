"""The story, stage by stage, for story_bot.py: New Bark Town to Morty's badge.

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
    # the Falkner set from the Pokemon Center, then up through his gym, past two Bird Keepers, to Falkner
    heal(bot, "T22PC0101", team="falkner")
    bot.travel("T22GYM0101")
    bot.walk("T22GYM0101", [(15, 20)])      # the lift: it carries the player up to the walkways
    bot.settle()
    bot.talk("T22GYM0101", 0)
    bot.expect("FLAG_GOT_TM51_FROM_FALKNER", "beating Falkner")


def mystery_egg(bot):
    # Elm's aide waits in the Violet Poke Mart with the Mystery Egg; without it, a man on Route 32 sends the
    # player back
    heal(bot, "T22PC0101")                      # after the gym
    bot.travel("T22FS0101")
    bot.talk("T22FS0101", 4)
    bot.expect("FLAG_UNK_070", "getting the Mystery Egg")


def heal(bot, pc, team=None):
    # at a Pokemon Center: the nurse is across the counter, at (8, 11); "Shall we heal your Pokemon?" Yes. With
    # a team, the party is then boxed and the boss's set (team_sets.py) taken out
    bot.travel(pc)
    bot.walk(pc, [(8, 13)], face="up")
    bot.game.key("a", after=30)
    bot.settle()
    if team:
        bot.swap_team(team)
    bot.go_through(pc, 0)


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
    heal(bot, "T23PC0101", team="bugsy")
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
    heal(bot, "T23PC0101")
    bot.travel(GYM)
    ride(bot, (3, 32), (9, 24))      # stop 0 to the middle floor's middle section (stop 4)
    ride(bot, (9, 17), (3, 9))       # stop 7 to the top floor's left section (stop 9), past a Bug Catcher
    bot.talk(GYM, (4, 7))            # switch 0 on, by the Twins
    ride(bot, (3, 9), (3, 18))       # stop 9, now to the middle floor's left section (stop 6; off the cart at its foot)
    bot.talk(GYM, (2, 18))           # switch 1 on
    ride(bot, (3, 17), (9, 9))       # stop 6, with both switches on, to Bugsy's section (stop 10)
    bot.talk(GYM, 5)
    bot.expect("FLAG_GOT_TM89_FROM_BUGSY", "beating Bugsy")
    # and back out the same way: the carts now wait at stops 1, 2, 4 and 10
    ride(bot, (9, 9), (3, 18))       # stop 10, both switches on, to the middle floor's left section
    bot.talk(GYM, (2, 18))           # switch 1 off
    ride(bot, (3, 17), (3, 9))       # stop 6 to the top floor's left section
    bot.talk(GYM, (4, 7))            # switch 0 off
    ride(bot, (3, 9), (9, 17))       # stop 9 to the middle floor's middle section
    ride(bot, (9, 24), (3, 32))      # stop 4 to the ground floor


ILEX = "D36R0101"
# the twig patches round the two lost Farfetch'd: stepping on one makes a noise that turns or moves a bird
TWIGS = {name: {(x + i, z + j) for i in range(2) for j in range(2)}
         for name, (x, z) in dict(first=(25, 66), first_b=(28, 63), second_a=(50, 49), second=(52, 53),
                                  second_c=(46, 64), second_d=(45, 53)).items()}


def twigs_but(*keep):
    return set().union(*(t for name, t in TWIGS.items() if name not in keep))


def to_ilex(bot):
    # a heal after the gym, then west out of Azalea Town, where the rival picks a fight at the gatehouse, into
    # Ilex Forest; the Charcoal Kiln's apprentice has lost his master's two Farfetch'd
    heal(bot, "T23PC0101")
    bot.travel(ILEX)
    bot.settle()


def farfetchd(bot):
    # From the forest's script. The first bird, at (25, 62), is caught by stepping on the twigs south of it and
    # then talking to it from the north. The second, at (41, 54), runs east to (49, 54) when talked to from the
    # south; there it is caught by stepping on the twigs east of it and then talking to it from the west. The
    # other twig patches would undo that, so the bot keeps off them. With both found the master gives HM01.
    people = bot.objects()
    if people.get(0) != (25, 62) or people.get(2) != (41, 54):
        bot.stuck("the Farfetch'd are not where they start: %s, %s" % (people.get(0), people.get(2)))
    bot.walk(ILEX, sorted(TWIGS["first"]), avoid=twigs_but("first"))
    bot.settle()
    bot.walk(ILEX, [(25, 61)], avoid=twigs_but(), face="down")
    bot.game.key("a", after=30)
    bot.settle()
    bot.expect("FLAG_FOUND_FIRST_FARFETCHD", "catching the first Farfetch'd")
    bot.walk(ILEX, [(41, 55)], avoid=twigs_but(), face="up")
    bot.game.key("a", after=30)
    bot.settle()
    if bot.objects().get(2) != (49, 54):
        bot.stuck("the second Farfetch'd did not run to (49, 54): %s" % (bot.objects().get(2),))
    bot.walk(ILEX, sorted(TWIGS["second"]), avoid=twigs_but("second"))
    bot.settle()
    bot.walk(ILEX, [(48, 54)], avoid=twigs_but(), face="right")
    bot.game.key("a", after=30)
    bot.settle()
    bot.expect("FLAG_GOT_HM01", "getting HM01 from the Charcoal Kiln's master")


def to_goldenrod(bot):
    # Cut the tree (the hack lets the player use Cut from the bag with the Hive Badge), then north out of the
    # forest and up Route 34 to Goldenrod City
    bot.talk(ILEX, 5)
    bot.travel("T25")


def radio_card(bot):
    # Whitney is at the Radio Tower, and a woman stands in her gym's doorway until the player takes the tower's
    # quiz on the first floor: Yes to start it, then Yes, Yes, No, Yes, No (the answers in the tower's script).
    # The prize is the Radio Card; Whitney then hurries back to her gym
    bot.travel("D23R0101")
    bot.talk("D23R0101", 2, answers=["a", "a", "a", "b", "a", "b"])
    bot.expect("FLAG_GOT_RADIO_CARD", "winning the Radio Tower quiz")
    bot.expect("FLAG_UNK_318", "Whitney going back to her gym")
    bot.go_through("D23R0101", 0)


def whitney_gym(bot):
    # the Whitney set from the Pokemon Center, then through the gym's maze to Whitney. She cries when she loses;
    # a girl by the entrance has a word, and then Whitney hands over the badge
    heal(bot, "T25PC0101", team="whitney")
    bot.travel("T25GYM0101")
    bot.talk("T25GYM0101", 0)
    # one step onto (13, 11) starts the girl's scene, which ends with the player stepped back to (13, 10)
    bot.walk("T25GYM0101", [(13, 10)])
    bot.step("down")
    bot.settle()
    bot.talk("T25GYM0101", 0)
    bot.expect("FLAG_GOT_TM45_FROM_WHITNEY", "beating Whitney")


def squirt_bottle(bot):
    # a heal after the gym; then, with the Plain Badge, the Goldenrod Flower Shop's owner gives the SquirtBottle,
    # for the odd tree on Route 36
    heal(bot, "T25PC0101")
    bot.travel("T25R0601")
    bot.talk("T25R0601", 0)
    bot.expect_item("SQUIRT_BOTTLE", "getting the SquirtBottle")
    bot.go_through("T25R0601", 0)


def sudowoodo(bot):
    # the tree on Route 36 is a Sudowoodo: water it (Yes) and it fights
    bot.travel("R36")
    bot.talk("R36", 4)
    bot.settle()
    bot.expect("FLAG_HIDE_ROUTE_36_SUDOWOODO", "moving the Sudowoodo")


def to_ecruteak(bot):
    # north up Route 37 to Ecruteak City
    bot.travel("T27")


BURNED_TOWER = "D18R0101"


def burned_tower(bot):
    # Eusine and Morty wait inside, and the rival picks a fight; then down through the hole in the floor, where
    # the three beasts wake and run. After that Morty goes back to his gym
    bot.travel(BURNED_TOWER)
    bot.walk(BURNED_TOWER, [(19, 23)])          # Eusine and Morty
    bot.settle()
    bot.walk(BURNED_TOWER, [(22, 19)])          # the rival
    bot.settle()
    bot.go_through(BURNED_TOWER, 1)             # the hole
    bot.settle()
    bot.walk("D18R0102", [(20, 16), (20, 17)])  # the beasts
    bot.settle()
    bot.expect("FLAG_UNK_247", "the beasts waking in the Burned Tower")


MORTY_GYM = "T27GYM0101"
# Morty's gym is dark: the floor is a hidden path, and stepping off it (these tiles) sends the player back to
# the door
MORTY_DROPS = {(11, 12), (9, 12), (9, 21), (8, 29), (9, 30), (12, 31), (15, 30), (13, 38), (12, 19), (12, 21),
               (14, 20), (12, 24), (21, 29), (20, 32), (17, 40)}


def morty_gym(bot):
    # the Morty set from the Pokemon Center, then along the hidden path, past four Mediums, to Morty
    heal(bot, "T27PC0101", team="morty")
    bot.travel(MORTY_GYM)
    bot.talk(MORTY_GYM, 1, never=MORTY_DROPS)
    bot.expect("FLAG_GOT_TM30_FROM_MORTY", "beating Morty")


STAGES = [leave_bedroom, meet_mom, elms_lab, choose_starter, elms_errand, pokegear, to_mr_pokemon, mr_pokemon, elms_call,
          back_to_elm, stolen_pokemon, to_violet, sprout_tower,
          violet_gym, mystery_egg, to_azalea, kurt, slowpoke_well, azalea_gym, to_ilex, farfetchd,
          to_goldenrod, radio_card, whitney_gym, squirt_bottle, sudowoodo,
          to_ecruteak, burned_tower, morty_gym]
