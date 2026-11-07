"""The playtester's checklist: finish the game, and try what the hack changed.

The checklist is the story's objectives (story.py) with checks of the hack's
own features slotted in where they become possible. Workers work through it
in order: the first item not yet done whose needs hold. Free exploring is
only for when nothing on the list can be reached.

A check says where to go and what to do there (steps, as in story.py), and
how to tell it worked (`verify`):
- "done":   its `done` condition holds afterwards (a flag, an item, a beaten trainer)
- "battle": a battle starts (a legendary's marker, a Gym Leader's rematch)
- "double": a double battle starts (the gyms' double battle trainers)
- "toggle": talking flips `flag` (it talks again to flip it back)
- "visit":  the conversation or menu opens and closes without trouble

After each try it waits VERIFY_WITHIN presses. If a check still hasn't
worked after TRIES tries, that's reported as a problem: the hack's feature
may be broken (or the playtester couldn't drive its menu; the report says so).

Watches don't need the playtester to do anything: once `after` becomes true
during play, `expect` must follow within `within` presses (Koga's Lucky Egg
after his badge, the Hall of Fame tickets after the credits).
"""

from __future__ import annotations

from dataclasses import dataclass

from . import story
from .story import TRUE, S, all_of, any_of, badge, flag, item, not_, trainer

TRIES = 3
VERIFY_WITHIN = 60  # presses to wait for a try to show its result


@dataclass(frozen=True)
class Check:
    key: str
    title: str
    done: story.Cond
    steps: tuple
    needs: story.Cond = TRUE
    post_game: bool = False
    part: str = "hack"  # story or hack
    verify: str = "done"  # done, battle, double, toggle, visit
    flag: str = ""  # for toggle checks
    macro: tuple = ("A", "A", "A", "A")  # presses after facing them
    why: str = ""  # what in the hack it tests


@dataclass(frozen=True)
class Watch:
    key: str
    title: str
    after: story.Cond
    expect: story.Cond
    within: int
    why: str = ""
    post_game: bool = False


def C(key, title, done, *steps, needs=TRUE, verify="done", flag_name="", macro=("A", "A", "A", "A"), why="",
      post_game=False):
    return Check(key, title, done, tuple(steps), needs, post_game, "hack", verify, flag_name, macro, why)


def from_story(o: story.Objective) -> Check:
    return Check(o.key, o.title, o.done, o.steps, o.needs, o.post_game, "story")


TWO_ABLE = story.Cond("party", value=2)  # gym double battles need two Pokémon

def doubles(city, who, trainer_id, gym, script, *needs):
    """A gym's double battle trainer: talking to them must start a double battle (done once beaten)."""
    return C(f"doubles_{city}", f"Fight {who}, {gym.split('City')[0]}'s gym double battle", trainer(trainer_id),
             S(gym, talk=[script]), verify="double", needs=all_of(TWO_ABLE, *needs), why="Gym double battles")


# Hack checks, each placed before the story objective it should come before.
HACK_BEFORE = {
    "viridian_old_man": [
        C("level_cap_toggle", "Switch level caps with the Viridian Pokémon Center scientist (and back)", TRUE,
          S("ViridianCity_PokemonCenter_1F", talk=["EventScript_LevelCap"]), needs=flag("SYS_POKEDEX_GET"),
          verify="toggle", flag_name="HACK_LEVEL_CAP", why="Challenge settings: level caps can be switched any time"),
        C("exp_share_toggle", "Switch Party Exp. Share with the same scientist (and back)", TRUE,
          S("ViridianCity_PokemonCenter_1F", talk=["EventScript_LevelCap"]), needs=flag("SYS_POKEDEX_GET"),
          verify="toggle", flag_name="HACK_PARTY_EXP_SHARE", macro=("A", "A", "DOWN", "A", "A", "A"),
          why="Party Exp. Share option"),
        C("modern_tutor", "Talk to the modern move tutor in the Viridian Pokémon Center", TRUE,
          S("ViridianCity_PokemonCenter_1F", talk=["ModernTutor"]), needs=flag("SYS_POKEDEX_GET"), verify="visit",
          macro=("A", "A", "A", "A", "B", "B", "B", "B", "B"), why="Later moves: the modern tutor"),
    ],
    "reach_cerulean": [
        C("both_fossils", "Take the second fossil at Mt. Moon (the hack lets you have both)",
          all_of(flag("GOT_DOME_FOSSIL"), flag("GOT_HELIX_FOSSIL")),
          S("MtMoon_B2F", talk=["DomeFossil", "HelixFossil"]), needs=flag("GOT_FOSSIL_FROM_MT_MOON"),
          why="Fossils: both Mt. Moon fossils"),
    ],
    "badge2": [doubles("cerulean", "Swimmer Luis", "SWIMMER_MALE_LUIS", "CeruleanCity_Gym", "Luis")],
    "badge3": [doubles("vermilion", "Engineer Baily", "ENGINEER_BAILY", "VermilionCity_Gym", "Baily",
                       story.CAN_CUT)],
    "badge4": [
        doubles("celadon", "Beauty Bridget", "BEAUTY_BRIDGET", "CeladonCity_Gym", "Bridget", story.CAN_CUT),
        C("evolution_shop", "Look at the evolution items on Celadon Dept. Store 4F", TRUE,
          S("CeladonCity_DepartmentStore_4F", talk=["DepartmentStore_4F_EventScript_Clerk"]),
          needs=flag("WORLD_MAP_CELADON_CITY"), verify="visit",
          macro=("A", "A", "A", "DOWN", "DOWN", "DOWN", "B", "B", "B", "B", "B"),
          why="Celadon 4F sells every evolution item"),
    ],
    "badge5": [doubles("fuchsia", "Tamer Edgar", "TAMER_EDGAR", "FuchsiaCity_Gym", "Edgar")],
    "badge6": [doubles("saffron", "Psychic Johan", "PSYCHIC_JOHAN", "SaffronCity_Gym", "Johan",
                       flag("HIDE_SAFFRON_ROCKETS"))],
    "badge8": [doubles("viridian", "Cool Trainer Samuel", "COOLTRAINER_SAMUEL", "ViridianCity_Gym", "Samuel",
                       *(badge(n) for n in range(2, 8)))],
    "national_dex": [
        C("shiny_charm", "Get the Shiny Charm from Oak's aide", flag("HACK_GOT_SHINY_CHARM"),
          S("PalletTown_ProfessorOaksLab", talk=["Aide1"]), needs=flag("SYS_GAME_CLEAR"), post_game=True,
          why="Shiny Charm after becoming Champion"),
        C("nature_coach", "Talk to the nature and ability coach at Indigo Plateau", TRUE,
          S("IndigoPlateau_PokemonCenter_1F", talk=["NatureCoach"]), needs=flag("SYS_GAME_CLEAR"), verify="visit",
          macro=("A", "A", "A", "B", "B", "B", "B", "B"), post_game=True, why="Nature and ability coach"),
    ],
}

GYM_LEADERS = [("PewterCity_Gym", "Brock"), ("CeruleanCity_Gym", "Misty"), ("VermilionCity_Gym", "LtSurge"),
               ("CeladonCity_Gym", "Erika"), ("FuchsiaCity_Gym", "Koga"), ("SaffronCity_Gym", "Sabrina"),
               ("CinnabarIsland_Gym", "Blaine"), ("ViridianCity_Gym", "Giovanni")]

LEGENDARIES = [
    ("Mew", "PokemonMansion_B1F"), ("Celebi", "ViridianForest"), ("Raikou", "PowerPlant"),
    ("Entei", "MtEmber_Exterior"), ("Suicune", "TwoIsland_CapeBrink"),
    ("Regirock", "SevenIsland_TanobyRuins_LiptooChamber"), ("Regice", "SevenIsland_TanobyRuins_WeepthChamber"),
    ("Registeel", "SevenIsland_TanobyRuins_DilfordChamber"), ("Kyogre", "SeafoamIslands_B3F"),
    ("Groudon", "MtEmber_RubyPath_B3F"), ("Rayquaza", "SevenIsland_SevaultCanyon"),
    ("Latias", "SixIsland_OutcastIsland"), ("Latios", "FiveIsland_MemorialPillar"), ("Jirachi", "MtMoon_B2F"),
]

# After the story's post-game objectives: the post-game content the hack adds.
HACK_AFTER = [
    C(f"rematch_{leader.lower()}", f"Start a peak rematch with {leader} (six Lv. 100 Pokémon)", TRUE,
      S(gym, talk=[f"EventScript_{leader}"]), needs=flag("SYS_GAME_CLEAR"), verify="battle", post_game=True,
      why="Post-game Gym Leader rematches")
    for gym, leader in GYM_LEADERS
] + [
    C("move_relearner", "Talk to the Move Maniac on Two Island (the free full relearner)", TRUE,
      S("TwoIsland_House", talk=["MoveManiac"]), needs=all_of(flag("SYS_GAME_CLEAR"), flag("WORLD_MAP_TWO_ISLAND")),
      verify="visit", macro=("A", "A", "A", "B", "B", "B", "B", "B"), post_game=True, why="Full move relearner"),
] + [
    C(f"legend_{name.lower()}", f"Meet {name} ({map_name.replace('_', ' ')})", TRUE,
      S(map_name, talk=[f"Hack_EventScript_Legend_{name}"]),
      needs=all_of(flag("SYS_GAME_CLEAR"), not_(flag(f"HACK_CAUGHT_{name.upper()}"))),
      verify="battle", post_game=True, why="One-time legendary encounters")
    for name, map_name in LEGENDARIES
]

WATCHES = [
    Watch("lucky_egg", "Koga gives a Lucky Egg after his gym", after=badge(5),
          expect=any_of(item("LUCKY_EGG"), flag("HACK_GOT_LUCKY_EGG")), within=400,
          why="Lucky Egg from Koga"),
    Watch("hof_tickets", "The Hall of Fame gives the Mystic and Aurora Tickets", after=flag("SYS_GAME_CLEAR"),
          expect=all_of(item("MYSTIC_TICKET"), item("AURORA_TICKET")), within=3000, post_game=True,
          why="Legendaries: Navel Rock and Birth Island tickets"),
]

# Field moves straight from the overworld (the HM in the bag and its badge). The
# navigator presses A at these on the way; each is checked when it first works.
FIELD_MOVES = {
    "EventScript_CutTree": ("field_cut", "Cut a tree with HM01 in the bag (no Pokémon needs to know it)"),
    "EventScript_RockSmash": ("field_rock_smash", "Smash a rock with HM06 in the bag"),
    "EventScript_StrengthBoulder": ("field_strength", "Push a boulder with HM04 in the bag"),
    "water": ("field_surf", "Surf with HM03 in the bag"),
}


def _build() -> list[Check]:
    out = []
    for o in story.STORY:
        out += HACK_BEFORE.get(o.key, [])
        out.append(from_story(o))
    return out + HACK_AFTER


CHECKS: list[Check] = _build()
BY_KEY = {c.key: c for c in CHECKS}
ALL_TITLES = {**{c.key: c.title for c in CHECKS}, **{w.key: w.title for w in WATCHES},
              **{k: t for k, t in FIELD_MOVES.values()}}


def done(c: Check, s, game, checked) -> bool:
    """Done: its condition holds, or this worker already settled it (tried it and saw it work,
    or gave up on it)."""
    return c.key in checked or (c.done is not TRUE and c.done(s, game))


def is_hack(game) -> bool:
    """The hack's own checks only make sense on the hack (vanilla FireRed has the story only)."""
    return "HACK_LEVEL_CAP" in game.flags


def current(s, game, skip=frozenset(), checked=frozenset(), post_game=True) -> Check | None:
    """The first item on the checklist not done whose needs hold (skipping `skip`)."""
    hack = is_hack(game)
    for c in CHECKS:
        if c.key in skip or (c.post_game and not post_game) or (c.part == "hack" and not hack):
            continue
        if not done(c, s, game, checked) and c.needs(s, game):
            return c
    return None
