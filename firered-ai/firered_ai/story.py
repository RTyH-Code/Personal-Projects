"""The story guide: every point where FireRed (and FireRed QoL + Hard) stops you
until you've done something, as objectives the playtester works through.

Found by reading the game's scripts: trigger tiles that turn you back (gates),
people who stand in the way until a flag hides them (Snorlax, Rockets,
guards), and the items and events each one waits for. Every name below is a
real map, person, sign, trigger, flag, var or item in the game's source;
tests/test_story.py checks them against the game profile and world data.

An objective is done when its check passes. Its steps say where to go and
what to do there, in priority order: the playtester does the first step whose
`when` holds, going to that step's map if it isn't there:
- talk:  people or signs (matched by their script's name), visited in turn
- step:  trigger tiles to walk onto (matched by script name)
- enter: just get there (the check is usually "visited this town")
An objective is worked on once its `needs` hold; later ones wait.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --- conditions on the game state --------------------------------------------------------

@dataclass(frozen=True)
class Cond:
    kind: str  # flag, var, item, all, any, not, true, party
    name: str = ""
    op: str = ""
    value: int = 0
    parts: tuple = ()

    def __call__(self, s, game) -> bool:
        k = self.kind
        if k == "true":
            return True
        if k == "flag":
            n = game.flags.get(self.name)
            return n is not None and s.flag(n)
        if k == "var":
            n = game.vars.get(self.name)
            v = s.var(n) if n is not None else 0
            return {"==": v == self.value, ">=": v >= self.value, "!=": v != self.value}[self.op]
        if k == "item":
            n = game.item(self.name)
            return n is not None and s.item_count(n) > 0
        if k == "party":
            return len([m for m in s.party if not m.is_egg]) >= self.value
        if k == "all":
            return all(p(s, game) for p in self.parts)
        if k == "any":
            return any(p(s, game) for p in self.parts)
        if k == "not":
            return not self.parts[0](s, game)
        raise ValueError(k)

    def names(self):
        """(kind, name) of everything this refers to, for checking against the game."""
        if self.kind in ("flag", "var", "item"):
            yield self.kind, self.name
        for p in self.parts:
            yield from p.names()


def flag(name):
    return Cond("flag", name)


def var(name, op, value):
    return Cond("var", name, op, value)


def item(name):
    return Cond("item", name)


def all_of(*parts):
    return Cond("all", parts=parts)


def any_of(*parts):
    return Cond("any", parts=parts)


def not_(c):
    return Cond("not", parts=(c,))


TRUE = Cond("true")


def badge(n):
    return flag(f"BADGE0{n}_GET")


# Field moves (FireRed QoL + Hard: the HM in the bag and its badge, no Pokémon needed).
CAN_CUT = all_of(item("HM01"), badge(2))
CAN_STRENGTH = all_of(item("HM04"), badge(4))
CAN_SURF = all_of(item("HM03"), badge(5))
CAN_ROCK_SMASH = all_of(item("HM06"), badge(6))
CAN_WATERFALL = all_of(item("HM07"), badge(7))


# --- gates: trigger tiles that turn you back ---------------------------------------------------

# A gate trigger is active while its var equals its value. While active, the
# route planner avoids it unless its pass condition holds (then the script
# lets you through). Gates not listed here are avoided while active.
GATE_PASS = {
    "VermilionCity_EventScript_CheckTicket": flag("GOT_SS_TICKET"),
    "_EventScript_GuardTrigger": flag("GOT_TEA"),  # the four Saffron gates
    "PewterCity_EventScript_GymGuideTrigger": badge(1),
    "_EventScript_NeedBikeTrigger": item("BICYCLE"),
    "FuchsiaCity_SafariZone_Entrance_EventScript_EntryTrigger": TRUE,  # pay and go in
    "PewterCity_Museum_1F_EventScript_EntranceTrigger": TRUE,  # pay and go in
    "TrainerTower_EventScript_DoubleBattleTrigger": Cond("party", value=2),
    "PalletTown_EventScript_OakTrigger": TRUE,  # Oak takes you to the lab: wanted
    "PalletTown_ProfessorOaksLab_EventScript_LeaveStarterSceneTrigger": TRUE,
    "PalletTown_ProfessorOaksLab_EventScript_RivalBattleTrigger": TRUE,
    "PalletTown_EventScript_SignLadyTrigger": TRUE,
    "ViridianCity_EventScript_TutorialTrigger": TRUE,  # the old man's catching demo: wanted
    "PewterCity_EventScript_RunningShoesAideTrigger": TRUE,  # gives the Running Shoes
    # These two vars are set when the map loads, so off the map the var says nothing: use the flags.
    "CinnabarIsland_EventScript_GymDoorLocked": flag("HIDE_POKEMON_MANSION_B1F_SECRET_KEY"),
    "ViridianCity_EventScript_GymDoorLocked": all_of(*(badge(n) for n in range(2, 8))),
}

# Gates whose var is reset whenever their map loads (VAR_TEMP_*, the gym doors
# above): their var only means something while standing on that map.
def gate_var_is_live(var_name: str) -> bool:
    return not var_name.startswith("VAR_TEMP_")


def gate_passable(script: str, s, game) -> bool:
    for key, cond in GATE_PASS.items():
        if key in script:
            return cond(s, game)
    return False


# People a map's script moves into the way (or out of it) when the map loads:
# (map, local id) -> [(when, x, y)]. They stand at the first (x, y) whose `when` holds.
MOVED = {
    ("ViridianCity", "LOCALID_TUTORIAL_MAN"): [  # lying across the road until you have the Pokédex
        (var("MAP_SCENE_VIRIDIAN_CITY_OLD_MAN", "==", 0), 21, 11),
        (var("MAP_SCENE_VIRIDIAN_CITY_OLD_MAN", "==", 1), 21, 8)],
    ("CeruleanCity", "LOCALID_CERULEAN_POLICEMAN"): [(not_(flag("GOT_SS_TICKET")), 30, 12)],  # Route 5 exit
    ("CeruleanCity", "LOCALID_CERULEAN_SLOWBRO"): [(not_(flag("GOT_SS_TICKET")), 26, 31)],  # Route 9 path
    ("CeruleanCity", "LOCALID_CERULEAN_LASS"): [(not_(flag("GOT_SS_TICKET")), 27, 31)],
    ("SaffronCity", "LOCALID_SAFFRON_DOOR_GUARD_GRUNT"): [(not_(flag("RESCUED_MR_FUJI")), 33, 31)],
    ("IndigoPlateau_PokemonCenter_1F", "LOCALID_LEAGUE_DOOR_GUARD"):
        [(all_of(flag("SYS_NATIONAL_DEX"), not_(flag("SYS_CAN_LINK_WITH_RS"))), 4, 2)],
}


def placed(map_name: str, local_id: str, x: int, y: int, s, game) -> tuple[int, int]:
    """Where a person stands now, given MOVED."""
    for when, mx, my in MOVED.get((map_name, local_id), ()):
        if when(s, game):
            return mx, my
    return x, y


# The Seagallop ferry (Vermilion and the Sevii Islands): talking to its sailor
# offers a list of islands. The planner can't see where it goes, so it's a
# step to try when an island objective has no way by foot.
FERRY_SAILORS = ("FerrySailor", "Harbor_EventScript_Sailor")


# --- objectives -------------------------------------------------------------------------------

@dataclass(frozen=True)
class Step:
    map: str
    talk: tuple = ()  # people (object scripts) or signs, by part of their script's name
    step: tuple = ()  # trigger tiles, by part of their script's name
    when: Cond = TRUE


@dataclass(frozen=True)
class Objective:
    key: str
    title: str
    done: Cond
    steps: tuple
    needs: Cond = TRUE
    post_game: bool = False


def O(key, title, done, *steps, needs=TRUE, post_game=False):
    return Objective(key, title, done, tuple(steps), needs, post_game)


def S(map_name, talk=(), step=(), when=TRUE):
    return Step(map_name, tuple(talk), tuple(step), when)


STORY: list[Objective] = [
    # --- Pallet Town and Viridian City --------------------------------------------------------
    O("starter", "Get a starter from Professor Oak", flag("SYS_POKEMON_GET"),
      S("PalletTown_ProfessorOaksLab", talk=["BulbasaurBall", "SquirtleBall", "CharmanderBall"],
        when=var("MAP_SCENE_PALLET_TOWN_OAK", ">=", 1)),
      S("PalletTown", step=["OakTrigger"])),
    O("parcel", "Collect Oak's Parcel at the Viridian City Poké Mart",
      any_of(item("OAKS_PARCEL"), flag("SYS_POKEDEX_GET")),
      S("ViridianCity_Mart", talk=["Clerk"])),
    O("pokedex", "Deliver the parcel to Oak and get the Pokédex", flag("SYS_POKEDEX_GET"),
      S("PalletTown_ProfessorOaksLab", talk=["ProfOak"]), needs=item("OAKS_PARCEL")),
    O("viridian_old_man", "Watch the old man's catching tutorial (opens Route 2)",
      var("MAP_SCENE_VIRIDIAN_CITY_OLD_MAN", ">=", 2),
      S("ViridianCity", step=["TutorialTrigger"]), needs=flag("SYS_POKEDEX_GET")),
    # --- Pewter, Mt. Moon, Cerulean ----------------------------------------------------------------
    O("badge1", "Beat Brock (Boulder Badge)", badge(1), S("PewterCity_Gym", talk=["Brock"])),
    O("mt_moon_fossil", "Get past the Super Nerd in Mt. Moon (take a fossil)",
      any_of(flag("GOT_FOSSIL_FROM_MT_MOON"), flag("GOT_DOME_FOSSIL"), flag("GOT_HELIX_FOSSIL")),
      S("MtMoon_B2F", talk=["DomeFossil", "HelixFossil", "Miguel"]), needs=badge(1)),
    O("reach_cerulean", "Reach Cerulean City", flag("WORLD_MAP_CERULEAN_CITY"),
      S("CeruleanCity"), needs=badge(1)),
    O("badge2", "Beat Misty (Cascade Badge)", badge(2), S("CeruleanCity_Gym", talk=["Misty"])),
    O("bill", "Help Bill at the Sea Cottage and get the S.S. Ticket", flag("GOT_SS_TICKET"),
      S("Route25_SeaCottage", talk=["Bill", "Computer"]), needs=flag("WORLD_MAP_CERULEAN_CITY")),
    O("cerulean_rocket", "Beat the Rocket behind the burgled house (opens Route 9)",
      flag("GOT_TM28_FROM_ROCKET"), S("CeruleanCity", step=["GruntTrigger"]), needs=badge(2)),
    # --- Vermilion ----------------------------------------------------------------------------------
    O("ss_anne", "Board the S.S. Anne and get HM01 Cut from the Captain", flag("GOT_HM01"),
      S("SSAnne_CaptainsOffice", talk=["Captain"]),
      S("VermilionCity", step=["CheckTicket"]), needs=flag("GOT_SS_TICKET")),
    O("badge3", "Beat Lt. Surge (Thunder Badge)", badge(3),
      S("VermilionCity_Gym", talk=["TrashCan", "LtSurge"]), needs=CAN_CUT),
    O("bike_voucher", "Get the Bike Voucher from the Pokémon Fan Club", flag("GOT_BIKE_VOUCHER"),
      S("VermilionCity_PokemonFanClub", talk=["Chairman"]), needs=flag("WORLD_MAP_VERMILION_CITY")),
    O("bicycle", "Swap the voucher for a Bicycle in Cerulean", flag("GOT_BICYCLE"),
      S("CeruleanCity_BikeShop", talk=["Clerk"]), needs=item("BIKE_VOUCHER")),
    # --- Lavender, Celadon ------------------------------------------------------------------------
    O("reach_lavender", "Reach Lavender Town (Route 9, Rock Tunnel)", flag("WORLD_MAP_LAVENDER_TOWN"),
      S("LavenderTown"), needs=all_of(CAN_CUT, flag("GOT_TM28_FROM_ROCKET"))),
    O("reach_celadon", "Reach Celadon City (Route 8, Underground Path, Route 7)",
      flag("WORLD_MAP_CELADON_CITY"), S("CeladonCity"), needs=flag("WORLD_MAP_LAVENDER_TOWN")),
    O("badge4", "Beat Erika (Rainbow Badge)", badge(4), S("CeladonCity_Gym", talk=["Erika"]),
      needs=CAN_CUT),
    O("tea", "Get the Tea in Celadon Mansion (Saffron's guards want it)", flag("GOT_TEA"),
      S("CeladonCity_Condominiums_1F", talk=["TeaWoman"]), needs=flag("WORLD_MAP_CELADON_CITY")),
    O("silph_scope", "Clear the Rocket Hideout under the Game Corner and take the Silph Scope",
      any_of(item("SILPH_SCOPE"), flag("RESCUED_MR_FUJI")),
      S("RocketHideout_B4F", talk=["Giovanni", "SilphScope", "LiftKey"]),
      S("CeladonCity_GameCorner", talk=["Poster"]), needs=flag("WORLD_MAP_CELADON_CITY")),
    O("mr_fuji", "Climb Pokémon Tower with the Silph Scope and rescue Mr. Fuji", flag("RESCUED_MR_FUJI"),
      S("PokemonTower_7F", talk=["MrFuji"]), needs=item("SILPH_SCOPE")),
    O("poke_flute", "Get the Poké Flute from Mr. Fuji", flag("GOT_POKE_FLUTE"),
      S("LavenderTown_VolunteerPokemonHouse", talk=["MrFuji"]), needs=flag("RESCUED_MR_FUJI")),
    O("snorlax", "Wake a Snorlax with the Poké Flute (opens the way to Fuchsia)",
      any_of(flag("HIDE_ROUTE_12_SNORLAX"), flag("HIDE_ROUTE_16_SNORLAX")),
      S("Route12", talk=["Snorlax"]), S("Route16", talk=["Snorlax"]), needs=flag("GOT_POKE_FLUTE")),
    # --- Fuchsia ----------------------------------------------------------------------------------
    O("badge5", "Beat Koga (Soul Badge)", badge(5), S("FuchsiaCity_Gym", talk=["Koga"]),
      needs=any_of(flag("HIDE_ROUTE_12_SNORLAX"), flag("HIDE_ROUTE_16_SNORLAX"))),
    O("surf", "Find the Safari Zone's Secret House for HM03 Surf", flag("GOT_HM03"),
      S("SafariZone_SecretHouse", talk=["Attendant"]), needs=flag("WORLD_MAP_FUCHSIA_CITY")),
    O("gold_teeth", "Find the Warden's Gold Teeth in the Safari Zone",
      any_of(item("GOLD_TEETH"), flag("GOT_HM04")),
      S("SafariZone_West", talk=["ItemGoldTeeth"]), needs=flag("WORLD_MAP_FUCHSIA_CITY")),
    O("strength", "Return the Gold Teeth to the Warden for HM04 Strength", flag("GOT_HM04"),
      S("FuchsiaCity_WardensHouse", talk=["Warden"]), needs=item("GOLD_TEETH")),
    # --- Saffron ------------------------------------------------------------------------------------
    O("silph_co", "Free Silph Co. (Card Key on 5F, Giovanni on 11F)", flag("HIDE_SAFFRON_ROCKETS"),
      S("SilphCo_11F", step=["GiovanniTrigger"], when=item("CARD_KEY")),
      S("SilphCo_5F", talk=["ItemCardKey"]), needs=flag("GOT_TEA")),
    O("badge6", "Beat Sabrina (Marsh Badge)", badge(6), S("SaffronCity_Gym", talk=["Sabrina"]),
      needs=flag("HIDE_SAFFRON_ROCKETS")),
    # --- Cinnabar, Viridian, the League --------------------------------------------------------------
    O("secret_key", "Find the Secret Key in the Pokémon Mansion", flag("HIDE_POKEMON_MANSION_B1F_SECRET_KEY"),
      S("PokemonMansion_B1F", talk=["ItemSecretKey", "Statue"]), needs=CAN_SURF),
    O("badge7", "Beat Blaine (Volcano Badge)", badge(7),
      S("CinnabarIsland_Gym", talk=["Quiz", "Blaine"]), needs=flag("HIDE_POKEMON_MANSION_B1F_SECRET_KEY")),
    O("badge8", "Beat Giovanni at the Viridian Gym (Earth Badge)", badge(8),
      S("ViridianCity_Gym", talk=["Giovanni"]), needs=all_of(*(badge(n) for n in range(2, 8)))),
    O("reach_league", "Cross Route 23 and Victory Road to the Indigo Plateau",
      flag("WORLD_MAP_INDIGO_PLATEAU_EXTERIOR"), S("IndigoPlateau_Exterior"),
      needs=all_of(badge(8), CAN_STRENGTH, CAN_SURF)),
    O("elite_four", "Beat the Elite Four and the Champion", flag("SYS_GAME_CLEAR"),
      S("PokemonLeague_ChampionsRoom", when=flag("DEFEATED_LANCE")),
      S("PokemonLeague_LancesRoom", talk=["Lance"], when=flag("DEFEATED_AGATHA")),
      S("PokemonLeague_AgathasRoom", talk=["Agatha"], when=flag("DEFEATED_BRUNO")),
      S("PokemonLeague_BrunosRoom", talk=["Bruno"], when=flag("DEFEATED_LORELEI")),
      S("PokemonLeague_LoreleisRoom", talk=["Lorelei"]),
      needs=flag("WORLD_MAP_INDIGO_PLATEAU_EXTERIOR")),
    # --- after the Hall of Fame -----------------------------------------------------------------------
    O("national_dex", "Get the National Pokédex from Oak", flag("SYS_NATIONAL_DEX"),
      S("PalletTown_ProfessorOaksLab", talk=["ProfOak"]), needs=flag("SYS_GAME_CLEAR"), post_game=True),
    O("one_island", "Go with Bill to One Island (Sevii Islands 1-3)", flag("WORLD_MAP_ONE_ISLAND"),
      S("CinnabarIsland_PokemonCenter_1F", talk=["Bill"]), needs=badge(7), post_game=True),
    O("sevii_123", "Help Celio at One Island (the Tri-Pass, Sevii Islands 1-3)", flag("SYS_SEVII_MAP_123"),
      S("OneIsland_PokemonCenter_1F", talk=["Celio", "Bill"]), needs=flag("WORLD_MAP_ONE_ISLAND"),
      post_game=True),
    O("lostelle", "Rescue Lostelle in Three Island's Berry Forest", flag("RESCUED_LOSTELLE"),
      S("ThreeIsland_BerryForest", talk=["Lostelle"]), needs=flag("WORLD_MAP_ONE_ISLAND"), post_game=True),
    O("ruby", "Find the Ruby at the bottom of Mt. Ember", flag("GOT_RUBY"),
      S("MtEmber_RubyPath_B5F", talk=["Ruby"]), needs=all_of(flag("SYS_GAME_CLEAR"), CAN_STRENGTH,
                                                           CAN_ROCK_SMASH), post_game=True),
    O("rainbow_pass", "Give Celio the Ruby (the Rainbow Pass, Sevii Islands 4-7)", flag("SYS_SEVII_MAP_4567"),
      S("OneIsland_PokemonCenter_1F", talk=["Celio"]), needs=flag("GOT_RUBY"), post_game=True),
    O("rocket_warehouse", "Clear the Rocket Warehouse on Five Island", flag("DEFEATED_ROCKETS_IN_WAREHOUSE"),
      S("FiveIsland_RocketWarehouse", talk=["Gideon", "Admin1", "Admin2"]), needs=flag("SYS_SEVII_MAP_4567"),
      post_game=True),
    O("sapphire", "Recover the Sapphire from Dotted Hole on Six Island", flag("RECOVERED_SAPPHIRE"),
      S("SixIsland_DottedHole_SapphireRoom", talk=["Sapphire"]), needs=flag("SYS_SEVII_MAP_4567"),
      post_game=True),
]

BY_KEY = {o.key: o for o in STORY}


def current(s, game, skip=frozenset()) -> Objective | None:
    """The first objective not yet done whose needs hold (skipping `skip`)."""
    for o in STORY:
        if o.key in skip:
            continue
        if not o.done(s, game) and o.needs(s, game):
            return o
    return None


def progress(s, game) -> tuple[int, list[str]]:
    """How many main-story objectives are done, and which, in order."""
    done = [o.key for o in STORY if not o.post_game and o.done(s, game)]
    return len(done), done


def next_step(o: Objective, s, game) -> Step | None:
    for st in o.steps:
        if st.when(s, game):
            return st
    return None
