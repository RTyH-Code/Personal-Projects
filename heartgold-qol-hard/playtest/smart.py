"""The story bot's own turn choices (STORY_SMART=1): fight, switch, or heal, as a player would.

The game's trainer AI still picks the move once Fight is chosen, who comes in after a switch, and which item is
used from the bag (story_bot.py puts the items in the player's trainer item slots). What this module decides is
the one thing that AI leaves to chance for the player's side: whether to stay in.

    choose(me, foe, bench, state) -> "fight" | "switch" | "heal"

me and foe: dict(types=[...], moves=[type, ...] of damaging moves, hp=, max_hp=). bench: the player's other
Pokemon still standing, as dict(types=[...], hp=, max_hp=). state: what the bot has done so far this battle
(switches, heals, and whether the last turn was a switch), which keeps it from switching back and forth.

The rules, in order:
- heal: HP at or under 40%, an item left, and at most two heals on this Pokemon
- switch: the foe's types hit this Pokemon super effectively, none of this Pokemon's moves hit the foe super
  effectively, and someone on the bench takes the foe's types for half or less (at most three switches a battle,
  never two turns running)
- otherwise fight
"""

TYPES = ["NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK", "BUG", "GHOST", "STEEL", "FAIRY", "FIRE",
         "WATER", "GRASS", "ELECTRIC", "PSYCHIC", "ICE", "DRAGON", "DARK"]
# attacking type -> {defending type: multiplier}; anything missing is 1
_CHART = {
    "NORMAL": {"ROCK": .5, "GHOST": 0, "STEEL": .5},
    "FIGHTING": {"NORMAL": 2, "FLYING": .5, "POISON": .5, "ROCK": 2, "BUG": .5, "GHOST": 0, "STEEL": 2, "FAIRY": .5,
                 "PSYCHIC": .5, "ICE": 2, "DARK": 2},
    "FLYING": {"FIGHTING": 2, "ROCK": .5, "BUG": 2, "STEEL": .5, "GRASS": 2, "ELECTRIC": .5},
    "POISON": {"POISON": .5, "GROUND": .5, "ROCK": .5, "GHOST": .5, "STEEL": 0, "FAIRY": 2, "GRASS": 2},
    "GROUND": {"FLYING": 0, "POISON": 2, "ROCK": 2, "BUG": .5, "STEEL": 2, "FIRE": 2, "GRASS": .5, "ELECTRIC": 2},
    "ROCK": {"FIGHTING": .5, "FLYING": 2, "GROUND": .5, "BUG": 2, "STEEL": .5, "FIRE": 2, "ICE": 2},
    "BUG": {"FIGHTING": .5, "FLYING": .5, "POISON": .5, "GHOST": .5, "STEEL": .5, "FAIRY": .5, "FIRE": .5,
            "GRASS": 2, "PSYCHIC": 2, "DARK": 2},
    "GHOST": {"NORMAL": 0, "GHOST": 2, "PSYCHIC": 2, "DARK": .5},
    "STEEL": {"ROCK": 2, "STEEL": .5, "FAIRY": 2, "FIRE": .5, "WATER": .5, "ELECTRIC": .5, "ICE": 2},
    "FAIRY": {"FIGHTING": 2, "POISON": .5, "STEEL": .5, "FIRE": .5, "DRAGON": 2, "DARK": 2},
    "FIRE": {"ROCK": .5, "BUG": 2, "STEEL": 2, "FIRE": .5, "WATER": .5, "GRASS": 2, "ICE": 2, "DRAGON": .5},
    "WATER": {"GROUND": 2, "ROCK": 2, "FIRE": 2, "WATER": .5, "GRASS": .5, "DRAGON": .5},
    "GRASS": {"FLYING": .5, "POISON": .5, "GROUND": 2, "ROCK": 2, "BUG": .5, "STEEL": .5, "FIRE": .5, "WATER": 2,
              "GRASS": .5, "DRAGON": .5},
    "ELECTRIC": {"FLYING": 2, "GROUND": 0, "WATER": 2, "GRASS": .5, "ELECTRIC": .5, "DRAGON": .5},
    "PSYCHIC": {"FIGHTING": 2, "POISON": 2, "STEEL": .5, "PSYCHIC": .5, "DARK": 0},
    "ICE": {"FLYING": 2, "GROUND": 2, "STEEL": .5, "FIRE": .5, "WATER": .5, "GRASS": 2, "ICE": .5, "DRAGON": 2},
    "DRAGON": {"STEEL": .5, "DRAGON": 2, "FAIRY": 0},
    "DARK": {"FIGHTING": .5, "GHOST": 2, "FAIRY": .5, "PSYCHIC": 2, "DARK": .5},
}
HEAL_AT = 0.40
MAX_HEALS_EACH, MAX_SWITCHES = 2, 3


def hit(attack, defender):
    """The multiplier of an attacking type against a list of defending types."""
    m = 1.0
    for t in dict.fromkeys(defender):
        m *= _CHART.get(attack, {}).get(t, 1)
    return m


def threat(foe_types, defender):
    """The worst the foe's own types (its likely attacks) do to the defender."""
    return max(hit(t, defender) for t in foe_types)


def choose(me, foe, bench, state):
    heals = state.setdefault("heals", {})
    if me["hp"] * 1.0 <= HEAL_AT * me["max_hp"] and state.get("items", 0) > 0 \
            and heals.get(me["key"], 0) < MAX_HEALS_EACH and me["hp"] > 0:
        heals[me["key"]] = heals.get(me["key"], 0) + 1
        state["items"] -= 1
        state["last"] = "heal"
        return "heal"
    danger = threat(foe["types"], me["types"]) >= 2
    answer = any(hit(t, foe["types"]) >= 2 for t in me["moves"])
    safe = [b for b in bench if b["hp"] > 0 and threat(foe["types"], b["types"]) <= 0.5]
    if danger and not answer and safe and state.get("switches", 0) < MAX_SWITCHES and state.get("last") != "switch":
        state["switches"] = state.get("switches", 0) + 1
        state["last"] = "switch"
        return "switch"
    state["last"] = "fight"
    return "fight"


def pick(foe, bench):
    """Who to send in against the foe: the one its types hurt least, then the one with a super effective move,
    then the one with the most HP left. bench holds only Pokemon still standing; returns its index, or None."""
    if not bench:
        return None
    def score(b):
        return (threat(foe["types"], b["types"]), -max([hit(t, foe["types"]) for t in b.get("moves", [])] or [1]),
                -b["hp"] / max(b["max_hp"], 1))
    return min(range(len(bench)), key=lambda i: score(bench[i]))


if __name__ == "__main__":
    # a few checks: Gardevoir (Psychic/Fairy) against Hitmontop (Fighting) stays in, its moves hit back
    gard = dict(key=1, types=["PSYCHIC", "FAIRY"], moves=["PSYCHIC", "FAIRY", "FIRE"], hp=148, max_hp=148)
    top = dict(types=["FIGHTING"])
    assert choose(gard, top, [], {}) == "fight"
    # Snorlax against Hitmonlee (Fighting) with Slowbro on the bench: no answer, so switch
    lax = dict(key=2, types=["NORMAL"], moves=["NORMAL", "GROUND"], hp=200, max_hp=220)
    lee = dict(types=["FIGHTING"])
    bro = dict(types=["WATER", "PSYCHIC"], hp=180, max_hp=180)
    s = {}
    assert choose(lax, lee, [bro], s) == "switch"
    assert choose(lax, lee, [bro], s) == "fight"          # never two turns running
    # against Annihilape (Fighting/Ghost) Slowbro is no refuge (Ghost hits it), so Snorlax stays in
    assert choose(lax, dict(types=["FIGHTING", "GHOST"]), [bro], {}) == "fight"
    # low on HP with an item: heal, at most twice
    s = dict(items=3)
    low = dict(lax, hp=60)
    assert [choose(low, top, [], s) for _ in range(3)] == ["heal", "heal", "fight"]
    assert hit("GROUND", ["FLYING", "STEEL"]) == 0 and hit("FIGHTING", ["NORMAL", "ROCK"]) == 4
    # against Hitmonlee, send in Slowbro (resists Fighting) over Tyranitar (four times weak)
    tyr = dict(types=["ROCK", "DARK"], moves=["ROCK", "DARK"], hp=186, max_hp=186)
    assert pick(lee, [tyr, bro]) == 1 and pick(lee, []) is None
    print("smart.py checks pass")
