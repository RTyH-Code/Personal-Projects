#!/usr/bin/env python3
"""Write the spoiler guide for HeartGold QoL + Hard from the hack's own data.

    python3 tools/spoiler_guide.py TREE DUMP [OUT]

TREE is an hg-engine tree with the hack's patches applied, DUMP a vanilla
`make dump_scripts` tree (for the maps' events) and OUT the guide folder
(default: guide/ next to tools/). BOSSES.md in that folder comes from
boss_teams.py and is left alone.

Everything is read from the data the game is built from, so the guide matches
the game. What the data does not hold is not in the guide: Pokemon and items
handed over by people in the story, the Safari Zone, the Bug-Catching Contest
and the Pokewalker.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LAND_ODDS = [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1]
WATER_ODDS = [60, 30, 5, 4, 1]
ROD_ODDS = [40, 30, 15, 10, 5]
SMASH_ODDS = [90, 10]
STATS = [("hp", "HP"), ("attack", "Atk"), ("defense", "Def"), ("spAttack", "SpA"), ("spDefense", "SpD"), ("speed", "Spe")]
SMALL = {"Of", "The", "To", "And", "On", "In", "At"}
NAME_FIXES = {"Farfetchd": "Farfetch'd", "Mr Mime": "Mr. Mime", "Mime Jr": "Mime Jr.", "Ho Oh": "Ho-Oh",
              "Porygon Z": "Porygon-Z", "Nidoran F": "Nidoran♀", "Nidoran M": "Nidoran♂", "Kings Rock": "King's Rock",
              "Up Grade": "Up-Grade", "Tinymushroom": "TinyMushroom", "Hp Up": "HP Up", "Pp Up": "PP Up",
              "Pp Max": "PP Max", "X Sp Atk": "X Sp. Atk", "X Sp Def": "X Sp. Def", "Guard Spec": "Guard Spec.",
              "Energy Powder": "EnergyPowder", "Silver Powder": "SilverPowder", "Bright Powder": "BrightPowder",
              "Never Melt Ice": "NeverMeltIce", "Twisted Spoon": "TwistedSpoon", "Black Glasses": "BlackGlasses",
              "Deep Sea Tooth": "DeepSeaTooth", "Deep Sea Scale": "DeepSeaScale", "Thunder Stone": "Thunder Stone",
              "U Turn": "U-turn", "X Scissor": "X-Scissor", "Will O Wisp": "Will-O-Wisp", "Double Edge": "Double-Edge",
              "Self Destruct": "Self-Destruct", "Soft Boiled": "Soft-Boiled", "Mud Slap": "Mud-Slap",
              "Lock On": "Lock-On", "Wake Up Slap": "Wake-Up Slap", "Poke Ball": "Poké Ball", "Poke Doll": "Poké Doll"}


def title(text):
    words = []
    for i, w in enumerate(text.split("_")):
        if re.fullmatch(r"B?\d+F|[NSEW]{1,2}|PC|TM\d*|HM\d*", w):
            words.append(w)
        elif w == "MT":
            words.append("Mt.")
        else:
            t = w.capitalize()
            words.append(t.lower() if i and t in SMALL else t)
    out = " ".join(words)
    return NAME_FIXES.get(out, out)


class Data:
    def __init__(self, tree, dump):
        self.tree, self.dump = tree, dump
        read = self.read
        sys.path.insert(0, os.path.join(tree, "tools", "hack"))
        cwd = os.getcwd()
        os.chdir(tree)                 # the hack's tools read the data relative to the tree
        import boss_teams
        import legendaries
        os.chdir(cwd)
        self.bt, self.legend_tool = boss_teams, legendaries
        self.species_ids = {n: int(v) for n, v in re.findall(r"#define SPECIES_(\w+)\s+\(?(\d+)\)?\s*$",
                                                             read("include/constants/species.h"), re.M)}
        self.map_names = json.load(open(os.path.join(HERE, "data", "map_names.json"), encoding="utf-8"))
        self.species = self.load_species()
        self.evolutions = self.load_evolutions()
        self.hidden_abilities = dict(re.findall(r"\[SPECIES_(\w+)\s*\] = ABILITY_(\w+)", read("data/HiddenAbilityTable.c")))
        self.machines = self.load_machines()
        self.encounters = self.load_encounters()
        self.headbutt = self.load_headbutt()
        self.trainers = self.load_trainers()
        self.events = self.load_events()

    def read(self, path):
        return open(os.path.join(self.tree, path), encoding="utf-8").read()

    def load_species(self):
        out = {}
        for m in re.finditer(r"^    \[SPECIES_(\w+)\] = \{\n(.*?)^    \},\n", self.read("data/Species.c"), re.S | re.M):
            body = m.group(2)
            stats = re.search(r"\.baseStats = \{(.*?)\}", body, re.S)
            if not stats:
                continue
            name = re.search(r'\.name = "(.*?)"', body)
            abilities = re.search(r"\.abilities = \{(.*?)\}", body)
            out[m.group(1)] = dict(
                name=name.group(1) if name else title(m.group(1)),
                stats={k: int(v) for k, v in re.findall(r"\.(\w+) = (\d+)", stats.group(1))},
                types=list(dict.fromkeys(re.findall(r"TYPE_(\w+)", re.search(r"\.types = \{(.*?)\}", body).group(1)))),
                abilities=[a for a in re.findall(r"ABILITY_(\w+)", abilities.group(1)) if a != "NONE"] if abilities else [],
                catch=int(re.search(r"\.catchRate = (\d+)", body).group(1)))
        return out

    def load_evolutions(self):
        out = {}
        for m in re.finditer(r"^    \[SPECIES_(\w+)\] = \{(.*?)^    \},", self.read("data/Evolutions.c"), re.S | re.M):
            rows = re.findall(r"\{ (EVO_\w+), (\w+), SPECIES_(\w+) \}", m.group(2))
            rows = [(method, param, target) for method, param, target in rows if method != "EVO_NONE"]
            if rows:
                out[m.group(1)] = rows
        return out

    def load_machines(self):
        out = {}
        for move, kind, number in re.findall(r"MOVE_(\w+), // (TM|HM)(\d+)", self.read("data/MachineMoves.c")):
            if kind == "HM" or int(number) <= 92:       # the game has TM01 to TM92 and the eight HMs
                out["%s%03d" % (kind, int(number))] = move
        return out

    def load_encounters(self):
        tables = []
        triples = lambda text: [(int(a), int(b), s) for a, b, s in re.findall(r"\{ (\d+), (\d+), SPECIES_(\w+) \}", text)]
        for m in re.finditer(r"^    \[ENCDATA_(\w+)\] = \{\n(.*?)^    \},\n", self.read("data/Encounters.c"), re.S | re.M):
            body = m.group(2)
            block = lambda key: re.search(r"\.%s = \{(.*?)\n        \}" % key, body, re.S).group(1)
            levels = [int(x) for x in re.search(r"\.levels = \{(.*?)\}", body, re.S).group(1).replace("\n", " ").split(",") if x.strip()]
            land = {part: re.findall(r"SPECIES_(\w+)", re.search(r"\.species%s = \{(.*?)\}" % part, body, re.S).group(1))
                    for part in ("Morning", "Day", "Night")}
            rate = lambda key: int(re.search(r"\.rate%s = (\d+)" % key, body).group(1))
            one = lambda key: re.search(r"\.%s = SPECIES_(\w+)" % key, body).group(1)
            code = m.group(1).split("_")[0]
            tables.append(dict(
                key=m.group(1), code=code, levels=levels, land=land if rate("Walk") else None,
                hoenn=re.findall(r"SPECIES_(\w+)", block("hoennSoundSpecies")),
                sinnoh=re.findall(r"SPECIES_(\w+)", block("sinnohSoundSpecies")),
                surf=triples(block("surfSlots")) if rate("Surf") else [],
                smash=triples(block("rockSmashSlots")) if rate("RockSmash") else [],
                old=triples(block("oldRodSlots")) if rate("OldRod") else [],
                good=triples(block("goodRodSlots")) if rate("GoodRod") else [],
                super=triples(block("superRodSlots")) if rate("SuperRod") else [],
                land_swarm=one("landSwarm"), surf_swarm=one("surfSwarm"), night_fish=one("nightFish"),
                fish_swarm=one("fishSwarm")))
        return tables

    def load_headbutt(self):
        out = []
        text = self.read("data/Headbutt.c")
        for m in re.finditer(r"^    \.(\w+) = \{\n(.*?)^    \},\n", text, re.S | re.M):
            body = m.group(2)
            def slots(key):
                block = re.search(r"\.%s =\s*\{(.*?)\n        \}" % key, body, re.S)
                return [(s, int(a), int(b)) for s, a, b in
                        re.findall(r"\{ SPECIES_(\w+), (\d+), (\d+) \}", block.group(1)) if s != "NONE"] if block else []
            normal, special = slots("normalSlots"), slots("specialSlots")
            if normal or special:
                out.append(dict(name=m.group(1), normal=normal, special=special))
        return out

    def load_trainers(self):
        ids = {n: int(v) for n, v in re.findall(r"^\.equ TRAINER_(\w+), (\d+)", self.read("asm/include/trainers.inc"), re.M)}
        out = {}
        for m in re.finditer(r"^    \[(\d+)\] = \{\n        \.name = \"(.*?)\",(.*?)^    \},\n", self.read("data/Trainers.c"), re.S | re.M):
            party = []
            for mon in re.finditer(r"\{\n(\s+\.ivs.*?)\n\s+\},", m.group(3), re.S):
                get = lambda k: re.search(r"\.%s = (\w+)" % k, mon.group(1))
                item = get("item")
                moves = re.search(r"\.moves = \{(.*?)\}", mon.group(1))
                party.append(dict(species=get("species").group(1).replace("SPECIES_", ""), level=int(get("level").group(1)),
                                  item=item.group(1).replace("ITEM_", "") if item else "NONE",
                                  moves=[x for x in re.findall(r"MOVE_(\w+)", moves.group(1)) if x != "NONE"] if moves else []))
            if party:
                out[int(m.group(1))] = dict(name=m.group(2), party=party,
                                            cls=re.search(r"\.trainerClass = TRAINERCLASS_(\w+)", m.group(3)).group(1),
                                            double=re.search(r"\.battleType = (\w+)", m.group(3)).group(1) != "SINGLE_BATTLE")
        self.trainer_ids = ids
        return out

    def load_events(self):
        """Every map's events: the hack's own file when it has one, else the original."""
        out = {}
        for base in (self.dump, self.tree):
            for path in glob.glob(os.path.join(base, "data/eventdata/zone_event/*.json")):
                code = os.path.basename(path)[:-5].split("_", 1)[1]
                out[code] = json.load(open(path))
        return out

    def place(self, code):
        """(area, exact place) for a map code."""
        entry = self.map_names.get(code)
        if not entry:
            return title(code), title(code)
        name = entry["area"] if entry["area"].startswith(entry["name"]) else entry["name"]
        return entry["area"], name

    def mon(self, key):
        return self.species[key]["name"] if key in self.species else title(key)


# ------------------------------------------------------------ the pages

def odds_table(slots, odds):
    """[(min, max, species)] with per-slot odds -> {species: (percent, min, max)}."""
    out = {}
    for (low, high, name), chance in zip(slots, odds):
        if name == "NONE":
            continue
        p, a, b = out.get(name, (0, low, high))
        out[name] = (p + chance, min(a, low), max(b, high))
    return out


def levels(low, high):
    return str(low) if low == high else "%d–%d" % (low, high)


def encounters_page(d, found):
    lines = ["# Wild Pokémon", "",
             "Every area's wild Pokémon, with the chance of each and its levels. Generated from the game's data.", "",
             "The Safari Zone, the Bug-Catching Contest and the Pokéwalker are as in the original game and are not listed.",
             "Swarms happen one area a day (Professor Oak's radio show says where). Hoenn Sound and Sinnoh Sound",
             "are the Wednesday and Thursday music on the Pokégear radio, after the National Pokédex, which this hack",
             "gives from the start.", ""]
    def note(species, area, how):
        found.setdefault(species, []).append((area, how))
    for t in d.encounters:
        area, place = d.place(t["code"])
        section = []
        if t["land"]:
            per = {}
            for part in ("Morning", "Day", "Night"):
                for name, level, chance in zip(t["land"][part], t["levels"], LAND_ODDS):
                    e = per.setdefault(name, dict(Morning=0, Day=0, Night=0, low=level, high=level))
                    e[part] += chance
                    e["low"], e["high"] = min(e["low"], level), max(e["high"], level)
            section += ["| Walking | Lv. | Morning | Day | Night |", "|---|---|--:|--:|--:|"]
            for name, e in sorted(per.items(), key=lambda kv: -(kv[1]["Morning"] + kv[1]["Day"] + kv[1]["Night"])):
                cell = lambda v: "%d%%" % v if v else "—"
                section.append("| %s | %s | %s | %s | %s |" % (d.mon(name), levels(e["low"], e["high"]), cell(e["Morning"]),
                                                             cell(e["Day"]), cell(e["Night"])))
                note(name, place, "walking")
            section.append("")
            extras = []
            if t["land_swarm"] != "NONE":
                extras.append("swarm: %s" % d.mon(t["land_swarm"]))
                note(t["land_swarm"], place, "swarm")
            for key, label in (("hoenn", "Hoenn Sound"), ("sinnoh", "Sinnoh Sound")):
                names = list(dict.fromkeys(n for n in t[key] if n != "NONE"))
                if names:
                    extras.append("%s: %s" % (label, ", ".join(d.mon(n) for n in names)))
                    for n in names:
                        note(n, place, label)
            if extras:
                section += ["Also, walking: " + "; ".join(extras) + ".", ""]
        for key, label, odds in (("surf", "Surfing", WATER_ODDS), ("smash", "Rock Smash", SMASH_ODDS),
                                 ("old", "Old Rod", ROD_ODDS), ("good", "Good Rod", ROD_ODDS), ("super", "Super Rod", ROD_ODDS)):
            table = odds_table(t[key], odds)
            if table:
                section += ["| %s | Lv. | Chance |" % label, "|---|---|--:|"]
                for name, (p, low, high) in sorted(table.items(), key=lambda kv: -kv[1][0]):
                    section.append("| %s | %s | %d%% |" % (d.mon(name), levels(low, high), p))
                    note(name, place, label.lower())
                section.append("")
        extras = []
        if t["surf"] and t["surf_swarm"] != "NONE":
            extras.append("surfing swarm: %s" % d.mon(t["surf_swarm"]))
            note(t["surf_swarm"], place, "swarm")
        if (t["good"] or t["super"]) and t["night_fish"] != "NONE":
            extras.append("fishing at night: %s" % d.mon(t["night_fish"]))
            note(t["night_fish"], place, "fishing at night")
        if (t["old"] or t["good"] or t["super"]) and t["fish_swarm"] != "NONE":
            extras.append("fishing swarm: %s" % d.mon(t["fish_swarm"]))
            note(t["fish_swarm"], place, "swarm")
        if extras:
            section += ["Also, on the water: " + "; ".join(extras) + ".", ""]
        if section:
            lines += ["## " + place, ""] + section
    lines += ["# Headbutt trees", "",
              "Some trees in an area are special trees with their own Pokémon; which trees depends on your Trainer ID.", ""]
    for h in d.headbutt:
        place = title(re.sub(r"(?<=[a-z])(?=[A-Z0-9])", "_", h["name"]).upper())
        lines += ["## " + place, ""]
        for label, slots in (("Ordinary trees", h["normal"]), ("Special trees", h["special"])):
            per = {}
            for name, low, high in slots:
                a, b = per.get(name, (low, high))
                per[name] = (min(a, low), max(b, high))
            if per:
                lines.append("- %s: %s." % (label, ", ".join("%s (Lv. %s)" % (d.mon(n), levels(a, b)) for n, (a, b) in per.items())))
                for n in per:
                    note(n, place, "Headbutt")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


EVO_TEXT = {
    "EVO_LEVEL": "at Lv. {p}", "EVO_FRIENDSHIP": "with high friendship", "EVO_FRIENDSHIP_DAY": "with high friendship, by day",
    "EVO_FRIENDSHIP_NIGHT": "with high friendship, at night", "EVO_TRADE": "by trade", "EVO_STONE": "with a {item}",
    "EVO_TRADE_ITEM": "by trade holding {item}", "EVO_LEVEL_ATK_GT_DEF": "at Lv. {p}, Attack above Defense",
    "EVO_LEVEL_ATK_EQ_DEF": "at Lv. {p}, Attack equal to Defense", "EVO_LEVEL_ATK_LT_DEF": "at Lv. {p}, Attack below Defense",
    "EVO_LEVEL_PID_LO": "at Lv. {p} (one of two, fixed for each Pokémon)", "EVO_LEVEL_PID_HI": "at Lv. {p} (one of two, fixed for each Pokémon)",
    "EVO_LEVEL_NINJASK": "at Lv. {p}", "EVO_LEVEL_SHEDINJA": "at Lv. {p}, with a free party slot and a Poké Ball",
    "EVO_BEAUTY": "with high Beauty", "EVO_STONE_MALE": "with a {item} (male)", "EVO_STONE_FEMALE": "with a {item} (female)",
    "EVO_ITEM_DAY": "leveling up holding {item}, by day", "EVO_ITEM_NIGHT": "leveling up holding {item}, at night",
    "EVO_HAS_MOVE": "leveling up knowing {move}", "EVO_OTHER_PARTY_MON": "leveling up with {mon} in the party",
    "EVO_LEVEL_MALE": "at Lv. {p} (male)", "EVO_LEVEL_FEMALE": "at Lv. {p} (female)",
    "EVO_CORONET": "leveling up at Mt. Coronet (not in this game)", "EVO_ETERNA": "leveling up at a Moss Rock (not in this game)",
    "EVO_ROUTE217": "leveling up at an Ice Rock (not in this game)", "EVO_HAS_MOVE_TYPE": "leveling up with high friendship, knowing a {type}-type move",
}


def evo_text(d, method, param):
    strip = lambda prefix: title(param.replace(prefix, "")) if param.startswith(prefix) else param
    text = EVO_TEXT.get(method)
    if text is None:
        return title(method.replace("EVO_", "")).lower() + (" (%s)" % title(re.sub(r"^[A-Z]+_", "", param)) if not param.isdigit() else "")
    return text.format(p=param, item=strip("ITEM_"), move=strip("MOVE_"), type=strip("TYPE_"),
                       mon=d.mon(param.replace("SPECIES_", "")))


def roster(d, found, statics):
    """Every species that can be had in the game: caught, given, then evolved or bred."""
    have = set(found) | set(statics)
    parents = {}
    for base, rows in d.evolutions.items():
        for _, _, target in rows:
            parents.setdefault(target, base)
    changed = True
    while changed:
        changed = False
        for name in list(have):
            for _, _, target in d.evolutions.get(name, []):
                if target in d.species and target not in have:
                    have.add(target)
                    changed = True
            if name in parents and parents[name] not in have:      # by breeding
                have.add(parents[name])
                changed = True
    return {n for n in have if n in d.species}, parents


# Pokemon the story hands over or that stand in the overworld in the original game: (species, how)
GIVEN = [
    ("CHIKORITA", "starter, New Bark Town"), ("CYNDAQUIL", "starter, New Bark Town"), ("TOTODILE", "starter, New Bark Town"),
    ("TOGEPI", "Egg from Professor Elm's aide, Violet City"), ("EEVEE", "from Bill, Goldenrod City"),
    ("SPEAROW", "Kenya, from the guard on Route 35"), ("SHUCKLE", "lent in Cianwood City"),
    ("TYROGUE", "from the Karate King, Mt. Mortar"), ("DRATINI", "from the Dragon's Den elder"),
    ("SCYTHER", "Bug-Catching Contest, National Park"), ("PINSIR", "Bug-Catching Contest, National Park"),
    ("SUDOWOODO", "Route 36"), ("LAPRAS", "Union Cave B2F, Fridays"), ("GYARADOS", "the red Gyarados, Lake of Rage"),
    ("ELECTRODE", "Team Rocket HQ"), ("SNORLAX", "Vermilion City gate, Route 11"),
    ("BULBASAUR", "from Professor Oak after beating Red (one of three)"), ("CHARMANDER", "from Professor Oak after beating Red (one of three)"),
    ("SQUIRTLE", "from Professor Oak after beating Red (one of three)"),
    ("TREECKO", "from Steven after beating Red (one of three)"), ("TORCHIC", "from Steven after beating Red (one of three)"),
    ("MUDKIP", "from Steven after beating Red (one of three)"),
    ("RAIKOU", "roaming Johto"), ("ENTEI", "roaming Johto"), ("SUICUNE", "Route 25"), ("HO_OH", "Bell Tower"),
    ("LUGIA", "Whirl Islands"), ("ARTICUNO", "Seafoam Islands"), ("ZAPDOS", "Route 10"), ("MOLTRES", "Mt. Silver Cave"),
    ("MEWTWO", "Cerulean Cave"), ("LATIAS", "roaming Kanto"), ("LATIOS", "roaming Kanto"), ("KYOGRE", "Embedded Tower"),
    ("RAYQUAZA", "Embedded Tower, with Groudon and Kyogre"),
    ("OMANYTE", "Helix Fossil"), ("KABUTO", "Dome Fossil"), ("AERODACTYL", "Old Amber"), ("LILEEP", "Root Fossil"),
    ("ANORITH", "Claw Fossil"), ("CRANIDOS", "Skull Fossil"), ("SHIELDON", "Armor Fossil"),
]


def pokemon_page(d, found, statics, have, parents):
    lines = ["# Where to find every Pokémon", "",
             "One line per Pokémon that can be had in the game, in Pokédex order. Evolutions and babies are listed",
             "by how you get them from a Pokémon you can find. Wild places are from the game's data; people who give",
             "you a Pokémon are from the original game. See [Wild Pokémon](ENCOUNTERS.md) for chances and levels, and",
             "the [Pokédex](POKEDEX.md) for each Pokémon's page.", "",
             "| No. | Pokémon | How to get it |", "|--:|---|---|"]
    for name in sorted(have, key=lambda n: d.species_ids[n]):
        ways = []
        if name in statics:
            ways += statics[name]
        if name in found:
            places = list(dict.fromkeys(place for place, _ in found[name]))
            shown = ", ".join(places[:6]) + (" and %d more" % (len(places) - 6) if len(places) > 6 else "")
            ways.append("wild: " + shown)
        if not ways:
            if name in parents:
                base = parents[name]
                how = "; ".join(evo_text(d, m, p) for m, p, t in d.evolutions[base] if t == name)
                ways.append("evolve %s %s" % (d.mon(base), how))
            else:
                kids = [t for _, _, t in d.evolutions.get(name, [])]
                ways.append("breed %s" % d.mon(kids[0]) if kids else "?")
        lines.append("| %d | [%s](pokedex/%s) | %s |" % (d.species_ids[name], d.mon(name), dex_file(d, name), "; ".join(ways)))
    return "\n".join(lines) + "\n"


def dex_file(d, name):
    return "%04d-%s.md" % (d.species_ids[name], re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"))


def dex_pages(d, found, statics, have, parents, out):
    os.makedirs(os.path.join(out, "pokedex"), exist_ok=True)
    for old in glob.glob(os.path.join(out, "pokedex", "*.md")):
        os.remove(old)
    usable = set(d.machines.values())
    by_move = {}
    for label, move in d.machines.items():
        by_move.setdefault(move, label)
    index = ["# Pokédex", "",
             "Every Pokémon that can be had in the game: %d of them. Click a name for its page, with abilities, evolutions," % len(have),
             "where to find it and its moves.", "",
             "| No. | Pokémon | Type | HP | Atk | Def | SpA | SpD | Spe | Total |", "|--:|---|---|--:|--:|--:|--:|--:|--:|--:|"]
    for name in sorted(have, key=lambda n: d.species_ids[n]):
        s = d.species[name]
        stats = [s["stats"][k] for k, _ in STATS]
        types = " / ".join(title(t) for t in s["types"])
        index.append("| %d | [%s](pokedex/%s) | %s | %s | %d |" % (d.species_ids[name], s["name"], dex_file(d, name), types,
                                                                 " | ".join(map(str, stats)), sum(stats)))
        page = ["# %s" % s["name"], "", "No. %d · %s · catch rate %d" % (d.species_ids[name], types, s["catch"]), "",
                "| " + " | ".join(label for _, label in STATS) + " | Total |", "|" + "--:|" * 7,
                "| " + " | ".join(map(str, stats)) + " | %d |" % sum(stats), ""]
        abilities = [title(a) for a in s["abilities"]]
        hidden = d.hidden_abilities.get(name)
        page.append("**Abilities:** " + ", ".join(abilities) + (" · hidden: %s" % title(hidden) if hidden and hidden != "NONE" else ""))
        page.append("")
        evo = []
        if name in parents:
            base = parents[name]
            how = "; ".join(evo_text(d, m, p) for m, p, t in d.evolutions[base] if t == name)
            evo.append("- From [%s](%s) %s." % (d.mon(base), dex_file(d, base), how))
        for method, param, target in d.evolutions.get(name, []):
            if target in have:
                evo.append("- Into [%s](%s) %s." % (d.mon(target), dex_file(d, target), evo_text(d, method, param)))
        if evo:
            page += ["## Evolution", ""] + evo + [""]
        where = list(statics.get(name, []))
        for place, how in found.get(name, []):
            where.append("%s (%s)" % (place, how))
        if where:
            page += ["## Where", ""] + ["- %s" % w for w in dict.fromkeys(where)] + [""]
        learn = d.bt.LEARNSETS.get("SPECIES_" + name, {})
        level_moves = [(m["Level"], m["Move"].replace("MOVE_", "")) for m in learn.get("LevelMoves", [])]
        if level_moves:
            page += ["## Moves by level", "", "| Lv. | Move |", "|--:|---|"]
            page += ["| %s | %s |" % (lv if lv > 0 else "Evo.", title(mv)) for lv, mv in sorted(level_moves, key=lambda x: x[0])]
            page.append("")
        machine = sorted((by_move[m.replace("MOVE_", "")], m.replace("MOVE_", "")) for m in learn.get("MachineMoves", [])
                         if m.replace("MOVE_", "") in usable)
        if machine:
            short = lambda label: "%s%02d" % (label[:2], int(label[2:]))
            page += ["## TMs and HMs", "", ", ".join("%s %s" % (short(label), title(mv)) for label, mv in machine) + ".", ""]
        eggs = [title(m.replace("MOVE_", "")) for m in learn.get("EggMoves", [])]
        if eggs:
            page += ["## Egg moves", "", ", ".join(eggs) + ".", ""]
        open(os.path.join(out, "pokedex", dex_file(d, name)), "w", encoding="utf-8").write("\n".join(page).rstrip("\n") + "\n")
    return "\n".join(index) + "\n"


BOSS = re.compile(r"LEADER_|ELITE_FOUR_|CHAMPION|RIVAL|PKMN_TRAINER_RED|EXECUTIVE|KIMONO_GIRL")


def trainers_page(d):
    placed = {}
    for code, events in d.events.items():
        for e in events.get("object_events", []):
            m = re.match(r"TRAINER_(\w+) - 1 \+ _std_(\w+)", str(e.get("script", "")))
            if m and m.group(1) in d.trainer_ids:
                placed.setdefault(d.place(code), []).append(d.trainer_ids[m.group(1)])
    lines = ["# Trainers", "",
             "Every trainer standing on a map, by place, with their Pokémon. Gym Leaders, the Elite Four, the Champion,",
             "your rival, Red, the Team Rocket executives and the Kimono Girls have their full teams, with moves and",
             "items, in [Boss teams](BOSSES.md). Trainers who only fight through a story scene or a phone rematch are",
             "not on a map and are not listed here.", ""]
    area_order = {}
    for (area, place), ids in placed.items():
        area_order.setdefault(area, {})[place] = ids
    def low(ids):
        return min(min(p["level"] for p in d.trainers[i]["party"]) for i in ids if i in d.trainers)
    count = 0
    for area in sorted(area_order, key=lambda a: min(low(ids) for ids in area_order[a].values() if any(i in d.trainers for i in ids))
                       if any(i in d.trainers for ids in area_order[a].values() for i in ids) else 999):
        lines += ["## " + area, ""]
        for place, ids in sorted(area_order[area].items()):
            if place != area:
                lines += ["**%s**" % place, ""]
            for i in dict.fromkeys(ids):
                t = d.trainers.get(i)
                if not t:
                    continue
                count += 1
                team = ", ".join("%s Lv. %d" % (d.mon(p["species"]), p["level"]) + (" @ %s" % title(p["item"]) if p["item"] != "NONE" else "")
                                 for p in t["party"])
                boss = " ([boss team](BOSSES.md))" if BOSS.search(t["cls"]) else ""
                lines.append("- %s %s%s: %s%s" % (title(re.sub(r"_(M|F|GS|2|3)$", "", t["cls"])), t["name"],
                                                  " (double battle)" if t["double"] else "", team, boss))
            lines.append("")
    lines.insert(6, "%d trainers, in the order their weakest Pokémon would put them." % count)
    return "\n".join(lines).rstrip("\n") + "\n"


def item_name(d, key):
    key = key.upper()
    m = re.fullmatch(r"(TM|HM)0*(\d+)", key)
    if m:
        label = "%s%02d" % (m.group(1), int(m.group(2)))
        move = d.machines.get("%s%03d" % (m.group(1), int(m.group(2))))
        return "%s %s" % (label, title(move)) if move else label
    return title(key)


def items_page(d):
    lines = ["# Items", "",
             "Item balls and hidden items on every map, what the shops sell, and the fossils from Rock Smash. Items that",
             "people give you in the story are not listed.", ""]
    by_area = {}
    for code, events in d.events.items():
        low = code.lower()
        balls, hidden = [], []
        for e in events.get("object_events", []):
            m = re.match(r"std_itemball_%s_(\w+?)(?:_\d+)?$" % low, str(e.get("script", "")))
            if m:
                balls.append(item_name(d, m.group(1)))
        for e in events.get("bg_events", []):
            m = re.match(r"std_hiddenitem_%s_(\w+?)(?:_\d+)?$" % low, str(e.get("script", "")))
            if m:
                hidden.append(item_name(d, m.group(1)))
        if balls or hidden:
            area, place = d.place(code)
            by_area.setdefault(area, []).append((place, balls, hidden))
    lines += ["## On the ground", ""]
    for area in sorted(by_area):
        lines += ["### " + area, ""]
        for place, balls, hidden in sorted(by_area[area]):
            parts = (["item balls: " + ", ".join(balls)] if balls else []) + (["hidden: " + ", ".join(hidden)] if hidden else [])
            text = "; ".join(parts)
            lines.append("- %s." % (text[0].upper() + text[1:] if place == area else "%s: %s" % (place, text)))
        lines.append("")
    mart = d.read("src/field/mart.c")
    lines += ["## Shops", "", "### Every Poké Mart", "",
              "The ordinary counter sells more as you earn badges:", "", "| Item | Badges needed |", "|---|--:|"]
    block = re.search(r"sBadgeMart\[\] = \{(.*?)\};", mart, re.S).group(1)
    for item, badges in re.findall(r"\{ ITEM_(\w+), (\d+) \}", block):
        lines.append("| %s | %s |" % (title(item), badges))
    locked = dict(re.findall(r"\{ ITEM_(\w+), (\d+) \}", re.search(r"sBadgeLockedMartItems\[\] = \{(.*?)\};", mart, re.S).group(1)))
    specific = re.findall(r"\{ ITEM_(\w+), MART_BADGE_(\w+) \}", re.search(r"sSpecificBadgeLockedMartItems\[\] = \{(.*?)\};", mart, re.S).group(1))
    lines += ["", "### Other counters", ""]
    for name, body in re.findall(r"^u16 s(\w+)\[\] = \{(.*?)\};", mart, re.S | re.M):
        items = re.findall(r"ITEM_(\w+)", body)
        label = title(re.sub(r"(?<=[a-z])(?=[A-Z0-9])", "_", name).upper())
        shown = []
        for item in items:
            text = item_name(d, item)
            if name == "GoldenrodDepartment4F" and item in locked:
                text += " (%s badges)" % locked[item]
            for locked_item, badge in specific:
                if name == "GoldenrodDepartment4F" and item == locked_item:
                    text += " (after the %s Badge)" % title(badge)
            shown.append(text)
        lines.append("- **%s:** %s." % (label, ", ".join(shown)))
    smash = d.read("src/field/rock_smash_item.c")
    fossils = list(dict.fromkeys(re.findall(r"ITEM_(\w*(?:FOSSIL|AMBER))", smash)))
    lines += ["", "## Fossils", "",
              "Smashing rocks can turn up: %s. The scientist in the Ruins of Alph Research Center revives them at once;" % ", ".join(title(f) for f in fossils),
              "the Pewter Museum still does after the Elite Four.", ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def legendary_statics(d):
    statics = {}
    for name, how in GIVEN:
        statics.setdefault(name, []).append(how)
    when = lambda conditions: ("after beating Red" if any("4131" in c for c in conditions) else
                               "with 16 badges" if any("MT_SILVER" in c for c in conditions) else "after the Champion")
    for entry in d.legend_tool.NEW:
        name, level, code, conditions = entry[0], entry[1], entry[2], entry[7]
        statics.setdefault(name, []).append("%s, Lv. %d, %s" % (d.place(code)[1], level, when(conditions)))
    statics.setdefault("PHIONE", []).append("breed Manaphy")
    return statics


def readme_page(d, have):
    return "\n".join([
        "# HeartGold QoL + Hard: spoiler guide", "",
        "**Spoilers ahead.** Generated from the game's data by `tools/spoiler_guide.py`, so it matches the game.", "",
        "1. [Pokédex](POKEDEX.md): all %d Pokémon you can have, with stats; each has a page with abilities," % len(have),
        "   evolutions, where to find it and its moves.",
        "2. [Where to find every Pokémon](POKEMON.md): one line each.",
        "3. [Wild Pokémon](ENCOUNTERS.md): every area by walking, surfing, fishing, Rock Smash and Headbutt, with",
        "   chances and levels.",
        "4. [Boss teams](BOSSES.md): Gym Leaders, the Elite Four, the Champion, your rival, Team Rocket, Red and the",
        "   rematches, with moves, items, abilities and natures.",
        "5. [Trainers](TRAINERS.md): every other trainer, by place.",
        "6. [Items](ITEMS.md): item balls, hidden items, shop stock and fossils.", "",
        "Not covered, because the game's data files don't hold them in a form the generator reads: items and Pokémon",
        "given by people in the story (the well-known ones are listed by hand in the Pokémon pages), the Safari Zone,",
        "the Bug-Catching Contest and the Pokéwalker. Those are unchanged from the original game.", ""])


def main():
    tree, dump = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(HERE), "guide")
    os.makedirs(out, exist_ok=True)
    d = Data(os.path.abspath(tree), os.path.abspath(dump))
    found = {}
    pages = {"ENCOUNTERS.md": encounters_page(d, found)}
    found = {k: v for k, v in found.items() if k in d.species}
    statics = legendary_statics(d)
    have, parents = roster(d, found, statics)
    pages["POKEMON.md"] = pokemon_page(d, found, statics, have, parents)
    pages["POKEDEX.md"] = dex_pages(d, found, statics, have, parents, out)
    pages["TRAINERS.md"] = trainers_page(d)
    pages["ITEMS.md"] = items_page(d)
    pages["README.md"] = readme_page(d, have)
    for name, text in pages.items():
        open(os.path.join(out, name), "w", encoding="utf-8").write(text)
        print("wrote %s (%d lines)" % (name, text.count("\n")))
    print("%d Pokemon in the roster, %d Pokedex pages" % (len(have), len(glob.glob(os.path.join(out, "pokedex", "*.md")))))


if __name__ == "__main__":
    main()
