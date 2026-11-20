"""The story, stage by stage, for story_bot.py: New Bark Town to Blackthorn City.

Each stage is a function of the bot. Places are map codes (see
tools/data/map_names.json) and tiles; warps are numbered as in the map's
event file.
"""
import walk_test
from walk_test import DIRS


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
    bot.walk("T22GYM0101", [(15, 20)])      # and the lift back down
    bot.settle()


def mystery_egg(bot):
    # Elm's aide waits in the Violet Poke Mart with the Mystery Egg; without it, a man on Route 32 sends the
    # player back
    heal(bot, "T22PC0101")                      # after the gym
    bot.travel("T22FS0101")
    bot.talk("T22FS0101", 4)
    bot.expect("FLAG_UNK_070", "getting the Mystery Egg")


def heal(bot, pc, team=None):
    # STORY_TEAM_<SET>=<other set> runs a stage with another set in place of its own (to compare sets)
    import os
    if team:
        team = os.environ.get("STORY_TEAM_" + team.upper(), team)
    # at a Pokemon Center: the nurse is across the counter, at (8, 11); "Shall we heal your Pokemon?" Yes. With
    # a team, the party is then boxed and the boss's set (team_sets.py) taken out
    bot.travel(pc)
    for _ in range(3):
        bot.talk(pc, (8, 11))                   # across the counter, facing her
        if bot.party_healthy():
            break
    else:
        bot.stuck("the nurse at %s did not heal the party" % pc)
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
    bot.travel("T23R0101")                  # the rival stops the player on the way to the gatehouse
    heal(bot, "T23PC0101")                  # and a heal after him, before the forest
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
    # the Morty set from Ecruteak's Pokemon Center (the rival here is the first boss it meets); then Eusine and
    # Morty wait inside, and the rival picks a fight; then down through the hole in the floor, where the three
    # beasts wake and run. After that Morty goes back to his gym
    heal(bot, "T27PC0101", team="morty")
    bot.travel(BURNED_TOWER)
    bot.walk(BURNED_TOWER, [(19, 23)])          # Eusine and Morty
    bot.settle()
    bot.walk(BURNED_TOWER, [(22, 19)])          # the rival
    bot.settle()
    bot.go_through(BURNED_TOWER, 1)             # the hole
    bot.settle()
    # the beasts wake when the player steps onto (20, 16) or (20, 17). The drop can land the player on them, and
    # the walking Pokemon can be in the way, so step off to either side and back on until they do
    for _ in range(5):
        if bot.flag("FLAG_UNK_247"):
            break
        side = bot.walk("D18R0102", [(19, 16), (19, 17), (21, 16), (21, 17)])
        bot.step("right" if side[0] == 19 else "left")
        bot.settle()
    bot.expect("FLAG_UNK_247", "the beasts waking in the Burned Tower")


MORTY_GYM = "T27GYM0101"
# Morty's gym is dark: the floor is a hidden path, and stepping off it (onto the gym's trigger areas) spins the
# player back to the door
def morty_drops(bot):
    return {(c["x"] + i, c["z"] + j) for c in bot.world.events(MORTY_GYM)["coord_events"]
            for i in range(c["width"]) for j in range(c["length"])}


def morty_gym(bot):
    # a heal, then along the hidden path, past four Mediums, to Morty
    heal(bot, "T27PC0101")
    bot.travel(MORTY_GYM)
    bot.talk(MORTY_GYM, 1, never=morty_drops(bot))
    bot.expect("FLAG_GOT_TM30_FROM_MORTY", "beating Morty")


def surf(bot):
    # a heal after the gym; then at the Dance Theater a Rocket Grunt is bothering a Kimono Girl. Beat him, and
    # on the way out the gentleman gives HM03 (the hack lets the player Surf from the bag with the Fog Badge)
    heal(bot, "T27PC0101")
    bot.travel("T27R0501")
    bot.talk("T27R0501", 9)
    bot.walk("T27R0501", [(3, 8), (11, 8)])
    bot.settle()
    bot.expect("FLAG_GOT_HM03", "getting HM03 at the Dance Theater")
    bot.go_through("T27R0501", 0)


def to_olivine(bot):
    # west along Routes 38 and 39 to Olivine City
    bot.travel("T26")


def to_cianwood(bot):
    # a heal, then by water down Routes 40 and 41, past the Whirl Islands, to Cianwood City
    heal(bot, "T26PC0101")
    bot.travel("T24")


def chuck_gym(bot):
    # the Chuck set from the Pokemon Center, then past four Black Belts to the winch and Chuck
    heal(bot, "T24PC0101", team="chuck")
    bot.travel("T24GYM0101")
    # Chuck trains under a waterfall and won't fight until the winch at the back stops it (Yes)
    bot.talk("T24GYM0101", (10, 2))
    bot.talk("T24GYM0101", 0)
    bot.expect("FLAG_GOT_TM01_FROM_CHUCK", "beating Chuck")


LIGHT_ROOM = "D27R0107"


def climb_lighthouse(bot):
    # the 4F stairs from 3F arrive in a part of 4F with no way up; out of its east side (15, 9), onto the
    # ledge outside (a way the map's warps don't list), whose door leads back in to the stairs up
    bot.travel("D27R0105")
    bot.walk("D27R0105", [(15, 9)])
    bot.game.key("right", hold=16, after=30)
    bot.settle()
    if not bot.where() or bot.where()[0] != "D27R0103":
        bot.stuck("did not get out onto the Lighthouse's ledge")
    bot.travel(LIGHT_ROOM)


def leave_lighthouse(bot):
    # down in the Light Room's elevator: it takes the player to the floor they did not come from (1F)
    bot.go_through(LIGHT_ROOM, 1)
    bot.settle()
    bot.go_through("D27R0108", 0)
    bot.settle()
    if not bot.where() or bot.where()[0] != "D27R0101":
        bot.stuck("the Lighthouse elevator did not go down to 1F")


def lighthouse(bot):
    # a heal after the gym, back across the water to Olivine, and up the Lighthouse to Jasmine, who is nursing
    # the sick Ampharos that lights it. She asks for medicine from Cianwood
    heal(bot, "T24PC0101")
    climb_lighthouse(bot)
    bot.talk(LIGHT_ROOM, 1)
    bot.expect("FLAG_UNK_1D8", "Jasmine asking for medicine")
    leave_lighthouse(bot)


def secret_potion(bot):
    # back to Cianwood, where the pharmacist, told of the Ampharos, hands over the SecretPotion
    bot.travel("T24R0501")
    bot.talk("T24R0501", 0)
    bot.expect("FLAG_GOT_SECRETPOTION", "getting the SecretPotion")
    bot.go_through("T24R0501", 0)


def ampharos(bot):
    # and up the Lighthouse once more: the medicine cures Ampharos, and Jasmine goes back to her gym
    climb_lighthouse(bot)
    bot.talk(LIGHT_ROOM, 1)
    bot.expect("FLAG_UNK_96A", "curing the Lighthouse's Ampharos")
    leave_lighthouse(bot)


def jasmine_gym(bot):
    # the Jasmine set from the Pokemon Center, and Jasmine
    heal(bot, "T26PC0101", team="jasmine")
    bot.travel("T26GYM0101")
    bot.talk("T26GYM0101", 0)
    bot.expect("FLAG_GOT_TM23_FROM_JASMINE", "beating Jasmine")


def to_mahogany(bot):
    # a heal after the gym, then back to Ecruteak and east along Route 42, round and over Mt. Mortar, to
    # Mahogany Town
    heal(bot, "T26PC0101")
    bot.travel("T28")


def red_gyarados(bot):
    # a heal, then north up Route 43 to the Lake of Rage, out on the water to the red Gyarados, and its battle
    # (Lv. 30); after it, the Red Scale, and Lance on the shore
    heal(bot, "T28PC0101")
    bot.travel("T29")
    # a battle that ends some other way than a win (it can end in a run) leaves the Gyarados there to try again
    for _ in range(4):
        bot.talk("T29", 3)
        bot.settle()
        if bot.flag("FLAG_GOT_RED_SCALE"):
            break
    bot.expect("FLAG_GOT_RED_SCALE", "the red Gyarados")


def lance(bot):
    # Lance asks the player to help him look into Mahogany (Yes); he goes ahead to the souvenir shop
    bot.talk("T29", 8, answers=["a"])
    bot.expect("FLAG_HIDE_LAKE_OF_RAGE_LANCE", "agreeing to help Lance")


def into_hideout(bot):
    # a heal in Mahogany, then the souvenir shop, where Lance has seen off the shady salesman and opened the
    # stairs down to Team Rocket's hideout
    heal(bot, "T28PC0101")
    bot.travel("D35R0102")
    bot.settle()


HIDEOUT_B1F, HIDEOUT_B2F, HIDEOUT_B3F = "D35R0102", "D35R0103", "D35R0104"


def hideout_traps(bot):
    # B1F's trap tiles: each starts a battle with a Voltorb, Geodude or Koffing (which explode)
    return {(c["x"], c["z"]) for c in bot.world.events(HIDEOUT_B1F)["coord_events"]
            if c["var"].startswith("VAR_ROCKET_TRAP")}


def hideout_b1f(bot):
    # B1F: Persian statues stand across the corridors and sound the alarm, which calls two Grunts to fight,
    # when the player walks past; there is no way round them, so the bot takes the fights. One tile near the
    # stairs (16, 28) sends the player back to the start of the floor: keep off it, and off the floor of traps
    # (wild battles with Pokemon that explode). Then down the stairs to B2F
    bot.forbid(HIDEOUT_B1F, {(16, 28)} | hideout_traps(bot))
    bot.travel(HIDEOUT_B2F)


def hideout_b2f(bot):
    # B2F: on to the stairs down to B3F
    bot.travel(HIDEOUT_B3F)
    bot.settle()


def hideout_b3f(bot):
    # B3F: the door to the boss's room opens once the two Grunts who know the password are beaten (the woman
    # at (38, 15), the man at (15, 25)). Through the door, the boss turns out to be Petrel in disguise, and
    # fights; the Murkrow in the room says the password too
    bot.talk(HIDEOUT_B3F, 4)                  # the Grunt at (38, 15)
    bot.talk(HIDEOUT_B3F, 3)                  # the Grunt at (15, 25)
    bot.travel(HIDEOUT_B3F, near=(23, 16))    # the door's side of B3F is reached by the west stairs from B2F
    bot.talk(HIDEOUT_B3F, 10)                 # the door
    bot.walk(HIDEOUT_B3F, [(23, 12), (24, 12)])
    bot.settle()
    if 9 in bot.objects():
        bot.talk(HIDEOUT_B3F, 9)              # the Murkrow, inside the room


# where the Hideout's next scene starts, by the value of VAR_UNK_40AC (the scripts move it on as each one ends)
HIDEOUT_SCENES = {2: (HIDEOUT_B3F, (20, 17)), 3: (HIDEOUT_B3F, (23, 12)), 4: (HIDEOUT_B2F, (11, 4)),
                  5: (HIDEOUT_B3F, (50, 4)), 6: (HIDEOUT_B2F, (50, 29)), 7: (HIDEOUT_B2F, (29, 27)),
                  8: (HIDEOUT_B2F, (30, 19))}


def hideout_end(bot):
    # the rest of the Hideout is a chain of scenes (Lance, Ariana and a Grunt in a double battle, the
    # generator room); then the three Electrode that power the radio signal, each a battle. The last one
    # ends it, and the man at Pryce's door goes. First, out to Mahogany's Pokemon Center to heal after Petrel
    # (keeping off B1F's traps: the team is worn down)
    bot.forbid(HIDEOUT_B1F, {(16, 28)} | hideout_traps(bot))
    heal(bot, "T28PC0101")
    for _ in range(16):
        if bot.flag("FLAG_UNK_1F9"):
            break
        stage = bot.game.get_var(0x40AC)
        if stage in HIDEOUT_SCENES:
            code, tile = HIDEOUT_SCENES[stage]
            bot.travel(code, near=tile)
            bot.walk(code, [tile])
            bot.settle()
            if bot.game.get_var(0x40AC) == stage:     # stood on it already: step off and on again
                side = bot.walk(code, [(tile[0] + dx, tile[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))])
                bot.walk(code, [tile])
                bot.settle()
        else:
            bot.travel(HIDEOUT_B2F, near=(20, 14))     # the floor beside the three Electrode
            for electrode in (9, 10, 11):
                if electrode in bot.objects():
                    bot.talk(HIDEOUT_B2F, electrode)
                    bot.settle()
    bot.expect("FLAG_UNK_1F9", "clearing Team Rocket out of the Hideout")


def pryce_gym(bot):
    # the Pryce set from the Pokemon Center, then three rooms of ice floors (the player slides until
    # something stops them) to Pryce
    heal(bot, "T28PC0101", team="pryce")
    bot.travel("T28GYM0101")
    bot.talk("T28GYM0101", 0)
    bot.expect("FLAG_GOT_TM07_FROM_PRYCE", "beating Pryce")


# ---------------------------------------------------------------- the Radio Tower takeover

TAKEOVER = 0x4077       # VAR_SCENE_ROCKET_TAKEOVER: 1 after Pryce, 2 once the Rockets hold the Radio Tower, 3 in
                        # the Rocket disguise, 4 after the rival on 1F, 5 once Archer is beaten
RADIO_1F, RADIO_3F, RADIO_4F, RADIO_5F, DIRECTORS_OFFICE, RADIO_ELEVATOR = "D23R0101", "D23R0103", "D23R0104", "D23R0105", "D23R0106", "D23R0107"
UNDERGROUND, SWITCH_ROOM, WAREHOUSE = "D37R0102", "D37R0104", "D37R0105"
PROTON, ARIANA = 706, 478       # their trainer numbers in the tower


def expect_takeover(bot, value, what):
    if bot.game.get_var(TAKEOVER) < value:
        bot.stuck("%s did not happen (the takeover is at %d)" % (what, bot.game.get_var(TAKEOVER)))


def to_goldenrod_takeover(bot):
    # leaving Pryce's gym, Elm's aide calls: the Rockets have taken over the Radio Tower. A heal, then back
    # west over Mt. Mortar's water, through Ecruteak and down Routes 37, 36 and 35 to Goldenrod, and the
    # Radio Tower set at its Pokemon Center
    heal(bot, "T28PC0101")
    expect_takeover(bot, 2, "the Rockets taking the Radio Tower")
    heal(bot, "T25PC0101", team="radio_tower")


def rocket_disguise(bot):
    # a Grunt guards the Radio Tower's stairs. In the Goldenrod Underground, a Rocket by the shops (the strip
    # x = 15, z = 7 to 13) mistakes the player for a recruit and hands over a uniform
    bot.travel(UNDERGROUND, near=(16, 10))
    bot.walk(UNDERGROUND, [(15, z) for z in range(7, 14)])
    bot.settle()
    expect_takeover(bot, 3, "getting the Rocket disguise")


def radio_tower_rival(bot):
    # the Grunt stands on the 1F stairs (23, 5); talked to in the disguise, he steps aside. On the stairs the
    # rival arrives and battles
    bot.travel(RADIO_1F, near=(23, 7))
    bot.talk(RADIO_1F, 6)
    bot.walk(RADIO_1F, [(23, 5)])
    bot.settle()
    expect_takeover(bot, 4, "the rival in the Radio Tower")


def fake_director(bot):
    # a heal, then up to 5F, where the "Director" is Petrel in disguise: he battles and hands over the
    # Basement Key, and the real Director is said to be held in the Underground warehouse
    heal(bot, "T25PC0101")
    bot.travel(RADIO_5F)
    bot.talk(RADIO_5F, 0)
    bot.expect_item("BASEMENT_KEY", "Petrel giving the Basement Key")


def underground_door(bot):
    # a heal, then the locked door at the Underground's east end (25, 30), which the Basement Key opens
    heal(bot, "T25PC0101")
    bot.travel(UNDERGROUND, near=(25, 31))
    bot.talk(UNDERGROUND, 11)
    bot.expect("FLAG_UNK_1C0", "the Basement Key opening the Underground door")    # the shutter rolls up


SWITCHES = [(8, 8), (9, 8), (10, 8), (23, 14)]
SWITCH_ROOM_EXIT, WAREHOUSE_DOOR = (27, 4), (26, 14)


def through_switch_room(bot, goal):
    # three switches on the wall at (8, 8), (9, 8) and (10, 8) each open some of the room's shutters and close
    # others; an emergency switch by the warehouse door (23, 14) opens the shutter beside it, for the way back. Each flips its own set, so what is open depends only on which switches have been pressed an odd
    # number of times; and the shutters are put back as they were whenever the player comes in. The bot tries
    # each choice from a save state (pressing a switch only if it can get to it then) until the goal can be
    # reached, then walks there
    import os
    state = os.path.join(bot.out, "switch_room.dst")
    bot.save(state)
    beside = {(goal[0] + dx, goal[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))}
    for n in range(16):
        if n:
            bot.game.emu.savestate.load_file(state)
            bot.game.run(60)
        pick = [sw for i, sw in enumerate(SWITCHES) if n >> i & 1]
        try:
            for sw in pick:
                here = bot.where()
                if (sw[0], sw[1] + 1) not in bot.reach(SWITCH_ROOM, (here[1], here[2])):
                    raise LookupError("switch out of reach")
                bot.talk(SWITCH_ROOM, sw)
        except LookupError:
            continue
        here = bot.where()
        if beside & set(bot.reach(SWITCH_ROOM, (here[1], here[2]))):
            bot.walk(SWITCH_ROOM, [goal])
            bot.settle()
            return
    bot.stuck("no choice of switches opened the way to %s" % (goal,))


def switch_room(bot):
    # the room behind the door: the rival waits just inside (a battle), then the switches, to the warehouse
    bot.travel(SWITCH_ROOM)
    bot.settle()
    through_switch_room(bot, WAREHOUSE_DOOR)


def warehouse(bot):
    # the warehouse: Grunts, and the real Director tied up at the back, who hands over the Card Key
    bot.talk(WAREHOUSE, 3)
    bot.expect_item("CARD_KEY_JOHTO", "the Director giving the Card Key")


def card_key(bot):
    # back through the switch room (its shutters are as they first were again), a heal, then the Card Key in
    # the slot by the 3F shutter (22, 11), which opens the way up the tower's east side to 4F (Proton) and 5F
    # (Ariana)
    bot.travel(SWITCH_ROOM)
    bot.settle()
    through_switch_room(bot, SWITCH_ROOM_EXIT)
    heal(bot, "T25PC0101")
    bot.travel(RADIO_3F, near=(22, 12))
    bot.talk(RADIO_3F, (22, 11))
    bot.expect("FLAG_UNK_090", "the Card Key opening the 3F shutter")


def proton(bot):
    # a heal, then up the east side to 4F, where Proton battles (Golbat, Qwilfish, Houndoom, Muk, Weezing)
    heal(bot, "T25PC0101")
    bot.travel(RADIO_4F, near=(23, 9))
    bot.talk(RADIO_4F, 3)
    if not bot.beaten(PROTON):
        bot.stuck("Proton was not beaten")


def ariana(bot):
    # back to the Pokemon Center to heal (a player could use potions instead), then 5F, where Ariana battles
    heal(bot, "T25PC0101")
    bot.travel(RADIO_5F, near=(11, 5))
    bot.talk(RADIO_5F, 1)
    if not bot.beaten(ARIANA):
        bot.stuck("Ariana was not beaten")


def archer(bot):
    # a heal, then the elevator at the top of 5F (13, 2): stepping in, it rides by itself between 5F and the
    # Observation Deck, and its door then leads to whichever floor it went to (a warp the route planner can't
    # follow). On the deck, Archer battles; beating him ends the takeover
    heal(bot, "T25PC0101")
    bot.travel(RADIO_5F, near=(13, 3))
    bot.go_through(RADIO_5F, 1)
    bot.settle()
    bot.go_through(RADIO_ELEVATOR, 0)
    bot.settle()
    if not bot.where() or bot.where()[0] != DIRECTORS_OFFICE:
        bot.stuck("the Radio Tower elevator did not go up to the Observation Deck")
    bot.talk(DIRECTORS_OFFICE, 0)
    # after the battle the screen fades out and in (Archer goes) before the Director's scene: the wait for
    # the scene to end can stop at the fade
    for _ in range(3):
        if bot.flag("FLAG_BEAT_RADIO_TOWER_ROCKETS"):
            break
        bot.settle()
    bot.expect("FLAG_BEAT_RADIO_TOWER_ROCKETS", "beating Archer")


# ---------------------------------------------------------------- the Ice Path to Blackthorn

ICE_1F, ICE_B1F, BLACKTHORN_GYM = "D39R0101", "D39R0102", "T30GYM0101"


def ice_path_holes(bot):
    # B1F's holes: stepping on one drops the player to B2F (a coord event on each)
    return {(c["x"], c["z"]) for c in bot.world.events(ICE_B1F)["coord_events"] if c["var"] == "VAR_UNK_40AA"}


def to_ice_path(bot):
    # down from the Observation Deck by its elevator, a heal, then back east to Mahogany (the hiker on
    # Route 42 gave HM04 on the way there the first time) and on along Route 44 to the Ice Path
    bot.go_through(DIRECTORS_OFFICE, 0)
    bot.settle()
    bot.go_through(RADIO_ELEVATOR, 0)
    bot.settle()
    heal(bot, "T25PC0101")
    bot.travel("T28")
    heal(bot, "T28PC0101")
    bot.travel(ICE_1F)


def ice_path_boulders(bot):
    # 1F's ice to the stairs down (HM07 on the way); on B1F four Strength boulders and four holes. Each boulder pushed into a
    # hole lands on B2F's ice, where it is something to stop against on the way across. The hack lets the
    # player use Strength from the bag (HM04, and the Plain Badge). boulders.py plans the pushes
    # first HM07 (Waterfall), an item ball on 1F's ice at (47, 10): until it is picked up, a man by the stairs
    # down turns the player back
    if 0 in bot.objects():
        bot.talk(ICE_1F, 0)
    bot.forbid(ICE_B1F, ice_path_holes(bot))
    bot.travel(ICE_B1F, near=(7, 19))
    bot.drop_boulders(ICE_B1F, ice_path_holes(bot), goals=[(25, 9)])


def to_blackthorn(bot):
    # down to B2F by the stairs past the holes, across its ice (sliding to the fallen boulders) to B3F, back
    # up to B2F's east side, B1F and 1F, and out to Blackthorn City
    bot.forbid(ICE_B1F, ice_path_holes(bot))
    bot.travel(ICE_1F, near=(55, 21))      # 1F's east side, from B1F
    # a Kimono Girl stands on the last ice slope (55, 29). Talked to from above, she asks whether the player
    # is in a hurry: Yes, and she leaves
    if 2 in bot.objects():
        bot.walk(ICE_1F, [(55, 28)])
        bot.talk(ICE_1F, 2, answers=["a"])
        bot.expect("FLAG_UNK_239", "the Kimono Girl on the Ice Path moving aside")
    bot.travel("T30")
    heal(bot, "T30PC0101")


GYM_TRAPS = [(5, 9), (23, 41), (3, 62)]      # spin the player back to the door
# the buttons, in order, that the search found to get across Clair's gym (23 presses): a run starts with these,
# and searches only if they don't lead to her
CLAIR_ROUTE = [(12, 75), (8, 75), (8, 75), (9, 75), (9, 57), (9, 54), (10, 54), (13, 54), (13, 54), (14, 54),
               (13, 32), (9, 32), (9, 32), (10, 32), (14, 32), (14, 31), (14, 26), (14, 21), (14, 17), (15, 17),
               (19, 17), (19, 16), (19, 11)]


def platform_layout(bot):
    # the platforms, and the part of the gym the player can walk in (where exactly they stand in it doesn't
    # matter)
    here = bot.where()
    area = min(bot.reach(BLACKTHORN_GYM, (here[1], here[2]))) if here else None
    return (tuple(tuple(sorted(p["floor"])) for p in bot.platforms()), area)


def press_gym_button(bot, b):
    # walk to a tile beside a platform button, keeping off the others, then step onto it: the platform then
    # moves, taking the player with it, so the walk must not be the one to arrive. Whether it worked is for the
    # caller to see
    here = bot.where()
    pos = (here[1], here[2])
    buttons = {t for p in bot.platforms() for t in (p["rotate"], p["left"], p["right"])}
    tiles = bot.tiles(BLACKTHORN_GYM)
    beside = {(b[0] - dx, b[1] - dz): d for d, (dx, dz, _) in DIRS.items()
              if (b[0] - dx, b[1] - dz) in tiles and (b[0] - dx, b[1] - dz) not in buttons}
    if not beside:
        return False
    if b == pos:
        # standing on it already (a platform stops with the player on its next button): step off and back on
        d = next(iter(beside.values()))
        dx, dz, _ = DIRS[d]
        back = {"up": "down", "down": "up", "left": "right", "right": "left"}[d]
        if not bot.step(back):
            return False
        beside = {(b[0] - dx, b[1] - dz): d}
    elif bot.path(BLACKTHORN_GYM, pos, set(beside), avoid=buttons) is None:
        return False
    try:
        at = bot.walk(BLACKTHORN_GYM, list(beside), never=buttons)
    except Exception as e:
        if type(e).__name__ != "Stuck" or str(e).startswith("lost a battle"):
            raise
        return False
    bot.step(beside[at])
    bot.game.run(300)
    bot.settle()
    return True


def clair_gym(bot):
    # the Clair set from the Pokemon Center, then the gym: islands in lava, joined by three platforms that
    # rotate or slide when the player steps on one of their buttons (each has a rotate button and two to move
    # it). The bot reads the platforms from memory and searches over which buttons to step on, the layouts that
    # let it walk furthest north (towards Clair) first: from a save state of each new layout it tries every
    # button, until it can walk to Clair. The buttons that got it there are kept (out/clair_route.json, and
    # CLAIR_ROUTE above from the first search), so a retry after a loss, or a later run, just steps on them again
    import heapq
    import json
    import os
    heal(bot, "T30PC0101", team="clair")
    bot.travel(BLACKTHORN_GYM)
    bot.settle()
    bot.forbid(BLACKTHORN_GYM, set(GYM_TRAPS))
    clair = (12, 4)                          # the tile in front of her
    route_file = os.path.join(bot.out, "clair_route.json")
    route = [tuple(b) for b in json.load(open(route_file))] if os.path.exists(route_file) else CLAIR_ROUTE
    if route:
        for b in route:
            press_gym_button(bot, b)
        here = bot.where()
        if bot.path(BLACKTHORN_GYM, (here[1], here[2]), {clair}) is None:
            route = None                     # it didn't work out the same: search after all
            bot.travel("T30")
            bot.travel(BLACKTHORN_GYM)
            bot.settle()
    if not route:
        def northmost():
            here = bot.where()
            return min(z for _, z in bot.reach(BLACKTHORN_GYM, (here[1], here[2])))
        first = os.path.join(bot.out, "gym_0.dst")
        bot.save(first)
        queue, seen, n = [(northmost(), 0, first, [])], {platform_layout(bot)}, 0
        while queue:
            _, _, state, presses = heapq.heappop(queue)
            bot.game.emu.savestate.load_file(state)
            bot.game.run(60)
            here = bot.where()
            if bot.path(BLACKTHORN_GYM, (here[1], here[2]), {clair}) is not None:
                json.dump(presses, open(route_file, "w"))
                print("  gym: way to Clair, by the buttons %s" % presses, flush=True)
                break
            for b in [t for p in bot.platforms() for t in (p["rotate"], p["left"], p["right"])]:
                bot.game.emu.savestate.load_file(state)
                bot.game.run(60)
                if not press_gym_button(bot, b):
                    continue
                layout = platform_layout(bot)
                print("  gym: pressed %s, now at %s, platforms at %s%s" % (
                    b, bot.where()[1:3], [min(p["floor"]) for p in bot.platforms()],
                    " (seen)" if layout in seen else ""), flush=True)
                if layout in seen:
                    continue
                seen.add(layout)
                n += 1
                nxt = os.path.join(bot.out, "gym_%d.dst" % n)
                bot.save(nxt)
                heapq.heappush(queue, (northmost(), n, nxt, presses + [list(b)]))
            if n > 300:
                break
        else:
            bot.stuck("no way across Clair's gym found (%d layouts tried)" % len(seen))
    bot.walk(BLACKTHORN_GYM, [clair])
    # the gym's five Ace Trainers stand between the door and her, and there is nowhere to heal inside: a
    # player would use potions here, which the bot can't. So the harness heals the party where it stands
    bot.restore_party("before Clair, after her gym's trainers")
    bot.talk(BLACKTHORN_GYM, 0)
    # she won't hand over the badge yet: the Dragon's Den comes first (FLAG_UNK_0D1: beaten, the Den's guard
    # steps aside)
    bot.expect("FLAG_UNK_0D1", "beating Clair")


# ---------------------------------------------------------------- the Dragon's Den

DEN, SHRINE = "D44R0102", "D44R0103"
# the elder's five questions, three answers each: the script marks the wrong ones, so these are the right
# answers' places in each list (0 = the first)
SHRINE_QUIZ = [0, 0, 1, 0, 1]


QUIZ_BUTTONS = [(128, 192 + 48), (128, 192 + 96), (128, 192 + 144)]   # the three answers, on the touch screen


def answers_shown(bot):
    # the quiz's three answer buttons on the touch screen: light grey bars at these heights
    image = bot.game.emu.screenshot()
    return all(min(image.getpixel(p)[:3]) > 180 for p in QUIZ_BUTTONS)


def answer_quiz(bot, picks, limit=8000):
    # press through the scene; when the answers show, touch the right one
    picks = list(picks)
    g, frames, calm = bot.game, 0, 0
    while frames < limit:
        if g.in_field() and walk_test.text_box(g.emu.screenshot()):
            calm = 0
            # the answers come up a moment after the question (an A before then is "Huh? I didn't catch that")
            g.run_every_frame(40)
            if answers_shown(bot) and picks:
                # the menu has a cursor (on the first answer): down to the right one, and A. The answer counts
                # once its buttons have gone
                for _ in range(picks[0]):
                    g.key("down", hold=4, after=12)
                g.key("a", hold=4, after=12)
                for _ in range(10):
                    g.run_every_frame(10)
                    if not answers_shown(bot):
                        picks.pop(0)
                        break
            else:
                g.key("a", after=20)
            frames += 30
            continue
        calm += 1
        if calm >= 10:
            break
        g.run(20)
        frames += 20
    bot.settle()
    return not picks


def dragons_den(bot):
    # Clair holds back the badge until the player has passed the Dragon Shrine's test: a heal, the Den behind
    # the gym, across its water to the shrine, where the elder asks five questions as the player walks in
    here = bot.where()
    if here and here[0] == BLACKTHORN_GYM:
        # the platforms are left where they took the player to Clair, which is no way back: the spin trap on her
        # island (5, 9) sends the player to the door
        bot.walk(BLACKTHORN_GYM, [(6, 9)])
        bot.step("left")
        bot.settle()
        bot.forbidden.pop(BLACKTHORN_GYM, None)
    heal(bot, "T30PC0101")
    bot.travel(DEN, near=(28, 51))          # the shrine door is entered from the south
    # through the shrine door by hand: the quiz starts as the player walks in, and the route planner's own
    # pressing through messages would answer it
    bot.go_through(DEN, 2)
    if bot.flag("FLAG_FAILED_DRAGONS_DEN_QUIZ"):
        # failed once already: the quiz isn't asked on the way in again; the elder asks whether to retake it
        bot.walk(SHRINE, [(6, 10)], face="up")
        bot.game.key("a", after=30)
    if not answer_quiz(bot, SHRINE_QUIZ):
        bot.stuck("the shrine's quiz did not run to its end")
    bot.expect("FLAG_UNK_0EA", "passing the Dragon Shrine's test (and the Rising Badge)")


# ---------------------------------------------------------------- Victory Road and the Pokemon League

VICTORY_ROAD_1F, INDIGO, BELL_TOWER_ROOF = "D43R0101", "T10", "D17R0110"


def var(bot, name):
    return bot.game.get_var(bot.world.vars[name])


def elms_news(bot):
    # out of the shrine, a heal in Blackthorn and the Elite Four set (taken from here on), then south along
    # Routes 45 and 46 to New Bark Town: Mom stops the player at its east edge until they have seen Elm, who has
    # news of the legendary Pokemon (VAR_SCENE_NEW_BARK_EAST_EXIT goes from 1 to 2)
    heal(bot, "T30PC0101", team="elite_four")
    if var(bot, "VAR_SCENE_NEW_BARK_EAST_EXIT") == 1:
        bot.travel("T20R0101")
        bot.talk("T20R0101", 0)
    if var(bot, "VAR_SCENE_NEW_BARK_EAST_EXIT") != 2:
        bot.stuck("Elm's news after the Dragon's Den did not happen")


def kimono_girls(bot):
    # then Lyra waits at the east edge instead, until the player has met Ho-Oh. West to Ecruteak: by its Pokemon
    # Center the rival appears (VAR_UNK_4079 = 3), and the five Kimono Girls are called to the Dance Theater.
    # Walking in starts their five battles, in a row; after them, the Clear Bell
    heal(bot, "T27PC0101")
    if var(bot, "VAR_UNK_4079") == 3:
        bot.travel("T27", near=(397, 175))
        bot.walk("T27", [(397, 174)])
        bot.settle()
    # through the theater door by hand: walking in, a Kimono Girl asks if the player is ready, and the route
    # planner's pressing through messages can answer before the Yes/No shows (which is No: they wait)
    door = next(i for i, w in enumerate(bot.world.events("T27")["warp_events"]) if w["dest_header_id"] == "MAP_T27R0501")
    bot.go_through("T27", door)
    bot.settle(["a"])
    # five battles, with dances and long talks between them: the scene can seem over in a pause, so keep on
    # until the Clear Bell is given
    for _ in range(20):
        if bot.flag("FLAG_UNK_103"):
            break
        bot.game.run(60)
        bot.settle()
    bot.expect("FLAG_UNK_103", "the Kimono Girls' battles and the Clear Bell")


def ho_oh(bot):
    # a heal, then up the Bell Tower to its roof: there the Kimono Girls dance (15, 20) and Ho-Oh comes down, a
    # battle (Lv. 52 in the hack). Beating it does (only losing or running doesn't); then Lyra lets the player go
    heal(bot, "T27PC0101")
    # the monk in the Bell Tower's barrier station stands in the way until talked to (with the Fog Badge he
    # steps aside, until the map is next loaded)
    bot.travel("T27R0201")
    bot.talk("T27R0201", 0)
    bot.travel(BELL_TOWER_ROOF, near=(15, 21))
    bot.walk(BELL_TOWER_ROOF, [(15, 20)])
    bot.settle()
    for _ in range(3):
        if var(bot, "VAR_UNK_40FA") != 1:
            break
        # the dance starts as the player steps onto (15, 20): arriving another way doesn't count
        bot.walk(BELL_TOWER_ROOF, [(15, 21)])
        bot.step("up")
        bot.settle()
    if 5 in bot.objects():
        bot.talk(BELL_TOWER_ROOF, 5)
        bot.settle()
    if var(bot, "VAR_SCENE_NEW_BARK_EAST_EXIT") != 3:
        bot.stuck("meeting Ho-Oh did not happen")


def to_victory_road(bot):
    # a heal, then east from New Bark over the water of Route 27, up Tohjo Falls (Waterfall, from the bag), Route
    # 26, and the Pokemon League gate, whose guards check the eight badges, to Victory Road
    heal(bot, "T27PC0101")
    bot.travel(VICTORY_ROAD_1F)


STAGES = [leave_bedroom, meet_mom, elms_lab, choose_starter, elms_errand, pokegear, to_mr_pokemon, mr_pokemon, elms_call,
          back_to_elm, stolen_pokemon, to_violet, sprout_tower,
          violet_gym, mystery_egg, to_azalea, kurt, slowpoke_well, azalea_gym, to_ilex, farfetchd,
          to_goldenrod, radio_card, whitney_gym, squirt_bottle, sudowoodo,
          to_ecruteak, burned_tower, morty_gym, surf, to_olivine, to_cianwood,
          chuck_gym, lighthouse, secret_potion, ampharos, jasmine_gym,
          to_mahogany, red_gyarados, lance, into_hideout, hideout_b1f, hideout_b2f, hideout_b3f, hideout_end, pryce_gym,
          to_goldenrod_takeover, rocket_disguise, radio_tower_rival, fake_director,
          underground_door, switch_room, warehouse, card_key, proton, ariana, archer,
          to_ice_path, ice_path_boulders, to_blackthorn, clair_gym, dragons_den,
          elms_news, kimono_girls, ho_oh, to_victory_road]
