"""The story guide and world navigation, against the real game data (no ROM needed)."""

import os
import random
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from world_emulator import WorldEmulator  # noqa: E402

from firered_ai import checklist, story  # noqa: E402
from firered_ai.explorer import Explorer  # noqa: E402
from firered_ai.game import Game  # noqa: E402
from firered_ai.navigate import Navigator  # noqa: E402
from firered_ai.ram import GameState  # noqa: E402
from firered_ai.world import World  # noqa: E402

GAMES = ["firered_qol_hard", "firered"]


@pytest.fixture(scope="module", params=GAMES)
def game_world(request):
    return Game.load(request.param), World.load(request.param)


def test_every_name_in_the_story_is_real(game_world):
    """Every map, person, sign, trigger, flag, var and item the story guide names exists."""
    g, w = game_world
    bad = []

    def check(c, where):
        for kind, name in c.names():
            ok = {"flag": name in g.flags, "var": name in g.vars, "item": g.item(name) is not None,
                  "trainer": name in g.trainer_ids}[kind]
            if not ok:
                bad.append((where, kind, name))

    hack = g.name == "firered_qol_hard"
    items = list(story.STORY) + (checklist.CHECKS if hack else [])
    for w_ in checklist.WATCHES if hack else []:
        check(w_.after, w_.key)
        check(w_.expect, w_.key)
    for c in checklist.CHECKS if hack else []:
        if c.verify == "toggle":
            check(story.flag(c.flag), c.key)
    for o in items:
        check(o.done, o.key)
        check(o.needs, o.key)
        for st in o.steps:
            check(st.when, o.key)
            m = w.maps.get(st.map)
            if m is None:
                bad.append((o.key, "map", st.map))
                continue
            scripts = [ob[3] for ob in m.objects] + [sg[3] for sg in m.signs]
            bad += [(o.key, "talk", st.map, t) for t in st.talk if not any(t in sc for sc in scripts)]
            bad += [(o.key, "step", st.map, t) for t in st.step if not any(t in tr[4] for tr in m.triggers)]
    for key, c in story.GATE_PASS.items():
        check(c, key)
        if not any(key in tr[4] for m in w.maps.values() for tr in m.triggers):
            bad.append(("gate", key))
    for (map_name, local_id), places in story.MOVED.items():
        for c, _x, _y in places:
            check(c, local_id)
        if not any(o[0] == local_id for o in w.maps[map_name].objects):
            bad.append(("moved", map_name, local_id))
    assert not bad


def test_every_gate_is_known_or_avoided(game_world):
    """Gate triggers the guide has no pass rule for are ones the planner should keep away from."""
    _g, w = game_world
    unknown = {t[4] for m in w.maps.values() for t in m.triggers
               if t[5] and not any(k in t[4] for k in story.GATE_PASS)}
    assert unknown <= {
        "OneIsland_PokemonCenter_1F_EventScript_LeaveOneIslandTriggerTop",
        "OneIsland_PokemonCenter_1F_EventScript_LeaveOneIslandTriggerMidTop",
        "OneIsland_PokemonCenter_1F_EventScript_LeaveOneIslandTriggerMidBottom",
        "OneIsland_PokemonCenter_1F_EventScript_LeaveOneIslandTriggerBottom",
        "SeafoamIslands_B4F_EventScript_UpwardCurrent",
        "ViridianCity_EventScript_RoadBlocked",  # the old man, until you have the Pokédex
    }


class Save:
    """A game state built up objective by objective, as if each had been done."""

    def __init__(self, g):
        self.g = g
        self.flags = bytearray(0x120)
        self.vars = bytearray(0x200)
        self.items = set()

    def flag(self, name):
        n = self.g.flags[name]
        self.flags[n // 8] |= 1 << (n % 8)

    def var(self, name, v):
        n = self.g.vars[name] - 0x4000
        self.vars[2 * n: 2 * n + 2] = v.to_bytes(2, "little")

    def satisfy(self, c):
        if c.kind == "flag":
            self.flag(c.name)
        elif c.kind == "var":
            self.var(c.name, c.value)
        elif c.kind == "item":
            self.items.add(c.name)
        elif c.kind == "all":
            for p in c.parts:
                self.satisfy(p)
        elif c.kind == "any":
            self.satisfy(c.parts[0])

    def state(self, nav, pos):
        group, num = nav.id_by_name[pos[0]]
        bag = {"key_items": [(self.g.item(i), 1) for i in self.items]}
        return GameState(True, group, num, pos[1], pos[2], flags=bytes(self.flags), vars=bytes(self.vars), bag=bag)


# What finishing an objective does besides its own check: the cutscenes' other
# flags and vars, and the HMs (the guide checks the flag you get them with).
SIDE_EFFECTS = {
    "starter": [("var", "MAP_SCENE_PALLET_TOWN_OAK", 3), ("var", "MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB", 4)],
    "pokedex": [("var", "MAP_SCENE_VIRIDIAN_CITY_OLD_MAN", 1)],
    # Taking the Dome Fossil. In vanilla, Miguel takes the other; in the hack it stays for you.
    "mt_moon_fossil": [("flag", "GOT_DOME_FOSSIL"), ("flag", "HIDE_DOME_FOSSIL"), ("vanilla", "HIDE_HELIX_FOSSIL")],
    "ss_anne": [("item", "HM01")],
    "bike_voucher": [("item", "BIKE_VOUCHER")],
    "surf": [("item", "HM03")],
    "strength": [("item", "HM04")],
}
# Reached through a cutscene, not on foot: the Mansion's switches change its walls
# as you play; Bill takes you to One Island on his boat; the Elite Four's doors
# walk you in. (The planner is told only where the objective ends up.)
NOT_ON_FOOT = {"secret_key": ("CinnabarIsland", 14, 11), "elite_four": None, "one_island": ("OneIsland", 12, 10)}


def test_the_whole_story_has_a_way_through(game_world):
    """Walk the main story objective by objective, from the bedroom: each one's place
    must be reachable from where the last one ended, given what's been done so far."""
    g, w = game_world
    nav = Navigator(w, g)
    save = Save(g)
    pos = ("PalletTown_PlayersHouse_2F", 5, 5)
    stuck = []
    hack = g.name == "firered_qol_hard"
    for o in [o for o in (checklist.CHECKS if hack else story.STORY) if not o.post_game]:
        s = save.state(nav, pos)
        if getattr(o, "part", "story") == "hack":
            # A hack check on the way: its place must be reachable from here. (It doesn't move us on.)
            if not o.needs(s, g):
                continue  # e.g. no second Pokémon for a double battle
            st = story.next_step(o, s, g)
            spots = {(st.map, x, y) for sp in nav.talk_spots(s, st.map, st.talk) for x, y, _d in sp}
            nav.plan_key = None
            nav._make_plan(s, o.key, lambda m, x, y: (m, x, y) in spots, set())
            if nav.plan is None:
                stuck.append((o.key, pos[0], st.map))
            continue
        assert o.needs(s, g), f"{o.key}: its needs don't hold after the objectives before it"
        st = story.next_step(o, s, g)
        if st.talk:
            goal_set = {(st.map, x, y) for spots in nav.talk_spots(s, st.map, st.talk) for x, y, _d in spots}
        elif st.step:
            goal_set = {(st.map, x, y) for x, y in nav.trigger_tiles(st.map, st.step)}
        else:
            goal_set = None
        if o.key in NOT_ON_FOOT:
            pos = NOT_ON_FOOT[o.key] or pos
        else:
            goal = (lambda m, x, y: m == st.map) if goal_set is None else (lambda m, x, y: (m, x, y) in goal_set)
            nav.plan_key = None
            nav._make_plan(s, o.key, goal, set())
            if nav.plan is None:
                stuck.append((o.key, pos[0], st.map))
            else:
                for p in nav.plan:  # arriving in a town marks it on the map
                    f = "WORLD_MAP_" + re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])", "_", p[0]).upper()
                    if f in g.flags:
                        save.flag(f)
                last = nav.plan[-1] if nav.plan else None
                if last:
                    m = w.maps[last[0]]
                    pos = w._step(m, *last[1:3], last[3], story.CAN_SURF(s, g)) or \
                        w._exit_from_warp(m, *last[1:3], last[3]) or pos
        save.satisfy(o.done)
        for kind, *args in SIDE_EFFECTS.get(o.key, []):
            if kind == "vanilla":
                if not hack:
                    save.flag(*args)
                continue
            {"flag": save.flag, "var": save.var, "item": save.items.add}[kind](*args)
    assert not stuck


def test_gates_block_until_the_story_opens_them():
    g, w = Game.load("firered_qol_hard"), World.load("firered_qol_hard")
    nav = Navigator(w, g)
    save = Save(g)
    save.var("MAP_SCENE_PALLET_TOWN_OAK", 3)
    save.flag("SYS_POKEMON_GET")
    # Before the Pokédex, the old man lies across the road north of Viridian.
    s = save.state(nav, ("ViridianCity", 20, 20))
    nav._make_plan(s, "north", lambda m, x, y: m == "Route2", set())
    assert nav.plan is None
    save.flag("SYS_POKEDEX_GET")
    save.var("MAP_SCENE_VIRIDIAN_CITY_OLD_MAN", 2)
    nav._make_plan(save.state(nav, ("ViridianCity", 20, 20)), "north", lambda m, x, y: m == "Route2", set())
    assert nav.plan
    # Saffron's gate guards want a drink.
    inside = ("Route5_SouthEntrance", 4, 2)  # just in from Route 5
    nav._make_plan(save.state(nav, inside), "saffron", lambda m, x, y: m == "SaffronCity", set())
    assert nav.plan is None
    save.flag("GOT_TEA")
    nav._make_plan(save.state(nav, inside), "saffron", lambda m, x, y: m == "SaffronCity", set())
    assert nav.plan


def test_cut_trees_are_walls_until_cut_works_then_pressed():
    g, w = Game.load("firered_qol_hard"), World.load("firered_qol_hard")
    save = Save(g)
    trees = [(o[1], o[2]) for o in w.maps["VermilionCity"].objects if o[3] == "EventScript_CutTree"]
    nav = Navigator(w, g)
    blocked, obstacles = nav.obstacles(save.state(nav, ("VermilionCity", 20, 20)))
    assert ("VermilionCity", *trees[0]) in blocked and not obstacles
    save.items.add("HM01")
    save.flag("BADGE02_GET")
    nav = Navigator(w, g)
    blocked, obstacles = nav.obstacles(save.state(nav, ("VermilionCity", 20, 20)))
    assert ("VermilionCity", *trees[0]) in obstacles and ("VermilionCity", *trees[0]) not in blocked


def test_a_tester_walks_from_the_bedroom_to_the_mart_for_oaks_parcel():
    """With a starter and nothing else, the next objective is Oak's Parcel: it should head
    straight for the Viridian Mart and talk to the clerk across the counter."""
    g = Game.load("firered_qol_hard")
    emu = WorldEmulator(g)
    emu.set_party([dict(level=60, hp=200, max_hp=200)])
    emu.set_flag(g.flags["SYS_POKEMON_GET"])
    emu.set_var("MAP_SCENE_PALLET_TOWN_OAK", 3)
    emu.set_var("MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB", 4)
    clerk = next(o for o in emu.world.maps["ViridianCity_Mart"].objects if "Clerk" in o[3])
    got = []
    emu.on_talk = lambda e, name, x, y: got.append(1) if (name, x, y) == ("ViridianCity_Mart", clerk[1], clerk[2] + 1) \
        or (name, x, y) == ("ViridianCity_Mart", clerk[1] + 1, clerk[2]) or (name, x, y) == ("ViridianCity_Mart", *clerk[1:3]) else None
    ex = Explorer(random.Random(3), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    from firered_ai.ram import read_state, DEFAULT_ADDRESSES
    maps = []
    for _ in range(1500):
        s = read_state(emu.read, DEFAULT_ADDRESSES, g.layout)
        a = ex.next(s)
        emu.press(a.buttons, a.hold)
        maps.append(emu.where()[0])
        if got:
            break
    assert ex.objective == "parcel"
    assert got, f"never talked to the clerk; ended on {emu.where()}, visited {sorted(set(maps))}"
    assert len(maps) < 600


def run(emu, ex, g, presses, until):
    from firered_ai.ram import DEFAULT_ADDRESSES, read_state
    for i in range(presses):
        s = read_state(emu.read, DEFAULT_ADDRESSES, g.layout)
        a = ex.next(s)
        emu.press(a.buttons, a.hold)
        if until():
            return i + 1
    return None


def test_takes_the_parcel_back_to_oak():
    g = Game.load("firered_qol_hard")
    emu = WorldEmulator(g, start=("ViridianCity_Mart", 4, 6))
    emu.set_party([dict(level=60, hp=200, max_hp=200)])
    emu.set_flag(g.flags["SYS_POKEMON_GET"])
    emu.set_var("MAP_SCENE_PALLET_TOWN_OAK", 3)
    emu.set_var("MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB", 4)
    emu.set_bag_item("key_items", g.item("OAKS_PARCEL"), 1, g.layout)
    oak = next(o for o in emu.world.maps["PalletTown_ProfessorOaksLab"].objects if "ProfOak" in o[3])
    talked = []
    emu.on_talk = lambda e, name, x, y: talked.append(1) if (name, x, y) == (
        "PalletTown_ProfessorOaksLab", oak[1], oak[2]) else None
    ex = Explorer(random.Random(5), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    n = run(emu, ex, g, 1500, lambda: bool(talked))
    assert ex.objective == "pokedex"
    assert n is not None and n < 600, f"ended on {emu.where()}"


def test_goes_to_the_nearest_pokemon_center_when_hurt():
    g = Game.load("firered_qol_hard")
    emu = WorldEmulator(g, start=("ViridianCity", 20, 20))
    emu.set_party([dict(level=60, hp=20, max_hp=200)])
    emu.set_flag(g.flags["SYS_POKEMON_GET"])
    nurse = next(o for o in emu.world.maps["ViridianCity_PokemonCenter_1F"].objects if o[3].endswith("Nurse"))
    talked = []
    emu.on_talk = lambda e, name, x, y: talked.append(1) if (name, x, y) == (
        "ViridianCity_PokemonCenter_1F", nurse[1], nurse[2] + 1) else None
    ex = Explorer(random.Random(6), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    n = run(emu, ex, g, 800, lambda: bool(talked))
    assert n is not None and n < 200, f"ended on {emu.where()}"


def test_a_stuck_objective_is_put_aside_for_a_while(monkeypatch):
    import firered_ai.explorer as explorer
    monkeypatch.setattr(explorer, "STORY_BUDGET", 50)
    g = Game.load("firered_qol_hard")
    emu = WorldEmulator(g)
    emu.set_party([dict(level=60, hp=200, max_hp=200)])
    emu.set_flag(g.flags["SYS_POKEMON_GET"])
    emu.set_var("MAP_SCENE_PALLET_TOWN_OAK", 3)
    # A wall where the house's stairs are: there's no way out of the bedroom.
    emu.world.maps["PalletTown_PlayersHouse_2F"].warps.clear()
    emu.world.maps["PalletTown_PlayersHouse_2F"].warp_at.clear()
    ex = Explorer(random.Random(7), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    run(emu, ex, g, 200, lambda: False)
    assert ex.story_stalls.get("parcel")


def test_report_shows_where_the_story_stalls():
    from firered_ai.report import progress_html
    page = progress_html({"furthest": [], "story_stalls": [("parcel", 2)],
                          "session_ends": {"sessions": 1, "badges": {0: 1}, "common_maps": [], "average_badges": 0,
                                           "average_top_level": 5, "objectives": [("parcel", 1)]}})
    assert "Collect Oak&#x27;s Parcel" in page and "(2&times;)" in page and "they were on" in page



def viridian_pc_emulator(g, flips=True):
    """In the Viridian Pokémon Center with the Pokédex: the checklist's first hack item is the
    level-cap scientist. With `flips`, talking to him switches the flag as the hack does: the
    first A starts the conversation, and the YES that switches it comes a different number of
    A presses later depending on the setting (its message is longer when caps are on). B, or an
    A after that, ends the conversation."""
    emu = WorldEmulator(g, start=("ViridianCity_PokemonCenter_1F", 7, 8))
    emu.set_party([dict(level=60, hp=200, max_hp=200)])
    for f in ("SYS_POKEMON_GET", "SYS_POKEDEX_GET"):
        emu.set_flag(g.flags[f])
    emu.set_var("MAP_SCENE_PALLET_TOWN_OAK", 3)
    sci = next(o for o in emu.world.maps["ViridianCity_PokemonCenter_1F"].objects if o[3].endswith("LevelCap"))
    conv = {"a": 0}  # A presses in the conversation; 0: not talking

    def talk(e, name, x, y):
        if conv["a"] == 0 and (x, y) != (sci[1], sci[2]):
            return
        conv["a"] += 1
        on = e.flag_on("HACK_LEVEL_CAP")
        need = 4 if on else 3
        if flips and conv["a"] == need:
            e.set_flag(g.flags["HACK_LEVEL_CAP"], not on)
        elif conv["a"] > need:
            conv["a"] = 0

    def press(e, b):
        if b == "B":
            conv["a"] = 0
    emu.on_talk = talk
    emu.on_press = press
    return emu


@pytest.mark.parametrize("caps_on", [False, True])
def test_switches_level_caps_and_back(caps_on):
    """Off -> on and on -> off take different numbers of A presses; either way it
    switches the setting and puts it back."""
    g = Game.load("firered_qol_hard")
    emu = viridian_pc_emulator(g)
    if caps_on:
        emu.set_flag(g.flags["HACK_LEVEL_CAP"])
    ex = Explorer(random.Random(8), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    run(emu, ex, g, 800, lambda: "level_cap_toggle" in ex.checked)
    assert {"key": "level_cap_toggle", "result": "pass", "detail": ""} in ex.events
    assert emu.flag_on("HACK_LEVEL_CAP") == caps_on  # put back as it was


def test_a_feature_that_does_nothing_is_reported():
    g = Game.load("firered_qol_hard")
    emu = viridian_pc_emulator(g, flips=False)
    ex = Explorer(random.Random(9), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    run(emu, ex, g, 1500, lambda: "level_cap_toggle" in ex.checked)
    fails = [e for e in ex.events if e["result"] == "fail"]
    assert fails and fails[0]["key"] == "level_cap_toggle" and "HACK_LEVEL_CAP didn't change" in fails[0]["detail"]
    # It moves on down the list instead of trying forever.
    from firered_ai.ram import DEFAULT_ADDRESSES, read_state
    s = read_state(emu.read, DEFAULT_ADDRESSES, g.layout)
    assert checklist.current(s, g, checked=ex.checked).key != "level_cap_toggle"


@pytest.mark.parametrize("gets_egg", [True, False])
def test_koga_must_give_the_lucky_egg(gets_egg):
    g = Game.load("firered_qol_hard")
    emu = viridian_pc_emulator(g)
    ex = Explorer(random.Random(10), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    from firered_ai.ram import DEFAULT_ADDRESSES, read_state
    for i in range(700):
        if i == 50:
            emu.set_flag(g.flags["BADGE05_GET"])
            if gets_egg:
                emu.set_bag_item("items", g.item("LUCKY_EGG"), 1, g.layout)
        ex.next(read_state(emu.read, DEFAULT_ADDRESSES, g.layout))
    results = [e["result"] for e in ex.events if e["key"] == "lucky_egg"]
    assert results == (["pass"] if gets_egg else ["fail"])


def test_report_lists_the_checklist():
    from firered_ai.report import checklist_html, checklist_rows
    rows = checklist_rows({"parcel": {"pass": 2, "fail": 0, "unreached": 0},
                           "level_cap_toggle": {"pass": 0, "fail": 1, "unreached": 0}})
    page = checklist_html({"checklist": rows})
    assert "Done (2&times;)" in page and "Didn&#x27;t work" not in page and "Didn't work (1&times;)" in page
    assert "Not reached yet" in page and "Gym double battles" in page


def test_trains_in_the_last_grass_before_the_next_gym():
    """Before Brock: Viridian Forest, not Route 1 next door."""
    g = Game.load("firered_qol_hard")
    emu = WorldEmulator(g, start=("ViridianCity", 20, 20))
    emu.set_party([dict(level=5, hp=20, max_hp=20)])
    for f in ("SYS_POKEMON_GET", "SYS_POKEDEX_GET"):
        emu.set_flag(g.flags[f])
    emu.set_var("MAP_SCENE_PALLET_TOWN_OAK", 3)
    emu.set_var("MAP_SCENE_VIRIDIAN_CITY_OLD_MAN", 2)
    ex = Explorer(random.Random(11), interact_prob=0, menu_prob=0, game=g, world=emu.world)
    ex.checked |= {"level_cap_toggle", "exp_share_toggle", "modern_tutor"}
    from firered_ai.ram import DEFAULT_ADDRESSES, read_state
    assert ex._training_map(read_state(emu.read, DEFAULT_ADDRESSES, g.layout)) == "ViridianForest"
    n = run(emu, ex, g, 2000, lambda: emu.where()[0] == "ViridianForest")
    assert n is not None
