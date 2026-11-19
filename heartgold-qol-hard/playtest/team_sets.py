#!/usr/bin/env python3
"""Boss team sets for story_bot.py: the team a player could reasonably have for each boss.

    team_sets.py TREE DUMP        check every set and print it

Before each boss the bot swaps its party for that boss's set at the
Pokemon Center, and carries the set on until the next one. Each set is
built from what a player could have by then:

- Pokemon: caught by walking in grass or caves (or with the Old Rod, or
  from Headbutt trees, once the player has them) on the maps the story has
  passed through, as in the hack's encounter tables, or the starter. Each
  is evolved by level up to the set's level. The checker below proves this
  for every Pokemon in every set.
- Moves: chosen by the hack's boss team tool (the best move of each of the
  Pokemon's types, a coverage move, a status or set-up move), but only from
  its level-up moves and the TMs the player can have picked up by then. A
  set can instead name the moves for a matchup, as a player would; the
  checker holds those to the same rule.
- Level: the boss's strongest Pokemon's level.
- EVs: what a player who battles a lot but never trains on purpose might
  have: a total that grows with the badges, half in the stat the Pokemon
  attacks with and half in Speed. IVs are all 15, the average, and the
  nature is a neutral one, so runs are repeatable.
- Items: Oran Berries early; later what the story has given.

The player's own Pokemon is the template for each one (so it is the
player's, with their trainer name and ID, and obeys); everything that
matters in battle is rewritten.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pkm

WALK = ("walking",)
ROD = ("walking", "old rod")
TREES = ("walking", "old rod", "Headbutt")

VIOLET = ["Route 29", "Route 30", "Route 31", "Violet City", "Sprout Tower 2F", "Sprout Tower 3F",
          "Dark Cave Route 31 Side", "Ruins of Alph"]
AZALEA = VIOLET + ["Route 32", "Union Cave 1F", "Route 33", "Slowpoke Well B1F"]
GOLDENROD = AZALEA + ["Ilex Forest", "Route 34", "Route 35", "Route 36", "National Park"]
ECRUTEAK = GOLDENROD + ["Route 37", "Ecruteak City", "Burned Tower 1F", "Burned Tower B1F"]
CIANWOOD = ECRUTEAK + ["Route 38", "Route 39", "Olivine City", "Route 40", "Route 41", "Cianwood City"]
MAHOGANY = CIANWOOD + ["Whirl Islands 1F", "Route 42", "Mount Mortar 1F Entrance", "Mount Mortar 1F Back",
                       "Mount Mortar 2F", "Mount Mortar B1F", "Mahogany Town", "Route 43", "Lake of Rage"]
WATER = ("walking", "old rod", "Headbutt", "surfing", "good rod")

SETS = {
    # Falkner's birds (Lv. 11-14): Rock, Electric and a Ghost from the caves and routes before Violet City
    "falkner": dict(level=14, badges=0, places=VIOLET, ways=WALK, tms=["FLASH"], item="ORAN_BERRY",
                    team=["CHIKORITA", "GEODUDE", "PACHIRISU", "SABLEYE", "PIDGEY"]),
    # Proton (Lv. 13-16) and Bugsy's bugs (Lv. 16-19): Rock, Electric, Flying and Psychic. The Mystery Egg goes
    # to the box with the old team
    "bugsy": dict(level=19, badges=1, places=AZALEA, ways=ROD, tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB"],
                  item="ORAN_BERRY", team=["BAYLEEF", "GEODUDE", "ONIX", "FLAAFFY", "SPEAROW", "NATU"]),
    # Whitney's team in the hack answers the usual picks: Furret has Brick Break and Shadow Claw, Stantler
    # Intimidate, and Miltank Scrappy (her Normal moves hit Ghosts), Rollout and Attract. So: Steel types that
    # take Normal and Rock moves (Bronzor; Mawile, with Intimidate of its own), Fighting (Heracross, Meditite),
    # Rock and Ground (Geodude) and a special attacker past Intimidate (Kadabra). All female where the species
    # can be (Miltank is female, and Attract only works on the other gender); Bronzor has no gender
    "whitney": dict(level=24, badges=2, places=GOLDENROD, ways=TREES,
                    tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB", "U_TURN", "DIG", "PAYBACK", "EMBARGO",
                         "PROTECT", "LIGHT_SCREEN", "REFLECT"],
                    item="ORAN_BERRY", female=True,
                    team=["BRONZOR", "MAWILE", "HERACROSS", "MEDITITE", "GEODUDE", "KADABRA"],
                    # chosen for the matchup, as a player would; the check holds them to what can be learned
                    moves=dict(BRONZOR=["GYRO_BALL", "CONFUSION", "HYPNOSIS", "REFLECT"],
                               MAWILE=["SUCKER_PUNCH", "BITE", "ROCK_TOMB", "IRON_DEFENSE"],
                               HERACROSS=["DIG", "HORN_ATTACK", "ROCK_TOMB", "ARM_THRUST"],
                               MEDITITE=["FORCE_PALM", "PSYBEAM", "ROCK_TOMB", "CALM_MIND"],
                               GEODUDE=["ROCK_TOMB", "DIG", "SMACK_DOWN", "PROTECT"],
                               KADABRA=["PSYBEAM", "DISABLE", "REFLECT", "PROTECT"])),
    # used from the Burned Tower's rival on. Morty's five Ghosts (Lv. 26-29: Duskull, Haunter, Drifblim, Gengar, Mismagius) hit hard with coverage
    # (Icy Wind, Giga Drain, Air Cutter, Shock Wave, Sludge Bomb, Power Gem, Mystical Fire): Dark types that
    # resist Ghost, a Normal type that Ghost moves pass through, and Dark moves all round; three Intimidates
    "morty": dict(level=29, badges=3, places=ECRUTEAK, ways=TREES,
                  tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB", "U_TURN", "DIG", "PAYBACK", "EMBARGO",
                       "PROTECT", "LIGHT_SCREEN", "REFLECT", "ATTRACT"],
                  item="ORAN_BERRY",
                  team=["HOUNDOOM", "MIGHTYENA", "RATICATE", "GYARADOS", "SABLEYE", "MAWILE"],
                  moves=dict(MIGHTYENA=["CRUNCH", "BITE", "ICE_FANG", "FIRE_FANG"],
                             RATICATE=["CRUNCH", "SUCKER_PUNCH", "SWORDS_DANCE", "U_TURN"],
                             MAWILE=["CRUNCH", "SUCKER_PUNCH", "IRON_DEFENSE", "ROCK_TOMB"])),
    # Chuck's Fighting types (Lv. 31-34: Primeape, Hitmontop, Machoke, Poliwrath, Heracross) carry Poison Jab,
    # Night Slash, Shadow Claw, Rock Slide and Aerial Ace: Psychic, Flying and Fairy, a Ghost that Fighting moves
    # miss, a Steel type for the Poison moves, and Intimidate on Gyarados
    "chuck": dict(level=34, badges=4, places=CIANWOOD, ways=WATER,
                  tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB", "U_TURN", "DIG", "PAYBACK", "EMBARGO",
                       "PROTECT", "LIGHT_SCREEN", "REFLECT", "ATTRACT"],
                  item="ORAN_BERRY",
                  team=["GARDEVOIR", "XATU", "DRIFBLIM", "GYARADOS", "BRONZONG", "HYPNO"]),
    # Jasmine's six Steel types (Lv. 35-38: Mawile, Magneton, Forretress, Skarmory, Scizor, Steelix): Fire for
    # most of them (Scizor and Forretress four times over), Ground for Magneton and Steelix, and Levitate on
    # Claydol against Steelix's Earthquake
    "jasmine": dict(level=38, badges=5, places=CIANWOOD + ["Whirl Islands 1F"], ways=WATER,
                    tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB", "U_TURN", "DIG", "PAYBACK", "EMBARGO",
                         "PROTECT", "LIGHT_SCREEN", "REFLECT", "ATTRACT", "FOCUS_PUNCH"],
                    item="ORAN_BERRY",
                    team=["MAGMAR", "TORKOAL", "HOUNDOOM", "CLAYDOL", "GASTRODON", "QUAGSIRE"]),
    # Pryce's Ice types (Lv. 38-42: Delibird, Sneasel, Jynx, Dewgong, Lapras, Mamoswine): Fighting for all of
    # them (Sneasel four times over), Fire for Jynx, Delibird and Mamoswine, Electric for Lapras and Dewgong
    "pryce": dict(level=42, badges=6, places=MAHOGANY, ways=WATER,
                  tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB", "U_TURN", "DIG", "PAYBACK", "EMBARGO",
                       "PROTECT", "LIGHT_SCREEN", "REFLECT", "ATTRACT", "FOCUS_PUNCH", "CALM_MIND"],
                  item="ORAN_BERRY",
                  team=["MACHAMP", "HERACROSS", "TOXICROAK", "MAGMAR", "LUXRAY", "HOUNDOOM"],
                  # Low Kick hits harder the heavier the target: Lapras and Mamoswine are very heavy
                  moves=dict(TOXICROAK=["LOW_KICK", "POISON_JAB", "SUCKER_PUNCH", "DIG"])),
    # the Radio Tower and the Goldenrod Underground (Lv. 41-46): Proton, Petrel, Ariana and Archer, mostly
    # Poison types (Koffing and Weezing with Levitate, so Ground moves miss them), Golbat and Crobat, Houndoom,
    # Honchkrow and Sneasel, and the rival (Ampharos, Golbat, Sneasel, Mismagius, Pupitar, Typhlosion).
    # Psychic for the Poison types, a Steel type with Levitate that their moves can't touch, Electric for the
    # birds, Water for the Fire types, and Dark moves for Mismagius
    "radio_tower": dict(level=46, badges=7, places=MAHOGANY, ways=WATER,
                        tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB", "U_TURN", "DIG", "PAYBACK", "EMBARGO",
                             "PROTECT", "LIGHT_SCREEN", "REFLECT", "ATTRACT", "FOCUS_PUNCH", "CALM_MIND", "HAIL"],
                        item="ORAN_BERRY",
                        team=["ALAKAZAM", "BRONZONG", "CLAYDOL", "LUXRAY", "GYARADOS", "HOUNDOOM"]),
    # Clair's six Dragon types (Lv. 44-47: Dragonair, Altaria, Gabite, Gyarados, Flygon, Kingdra), with Outrage
    # and Earthquake all round: Ice for all but Gyarados and Kingdra (Altaria, Gabite and Flygon four times
    # over), Fairy types that Outrage can't touch, a Steel type with Levitate that takes neither, and Electric
    "clair": dict(level=47, badges=7, places=MAHOGANY + ["Route 44", "Ice Path 1F", "Ice Path B1F", "Ice Path B2F",
                                                        "Ice Path B3F"], ways=WATER,
                  tms=["FLASH", "ROOST", "BULLET_SEED", "ROCK_TOMB", "U_TURN", "DIG", "PAYBACK", "EMBARGO",
                       "PROTECT", "LIGHT_SCREEN", "REFLECT", "ATTRACT", "FOCUS_PUNCH", "CALM_MIND", "HAIL",
                       "AVALANCHE"],
                  item="ORAN_BERRY",
                  # Piloswine was first: it fainted to the gym's Seadra every time before Clair, and her Gyarados
                  # (Intimidate, Dragon Dance) took 9 of her KOs in five losses. Luxray: Electric for Gyarados and
                  # Kingdra, and Intimidate of its own against her physical Dragons
                  team=["LUXRAY", "DEWGONG", "JYNX", "GARDEVOIR", "GRANBULL", "BRONZONG"],
                  moves=dict(JYNX=["ICE_PUNCH", "PSYCHIC", "LOVELY_KISS", "AVALANCHE"],
                             LUXRAY=["DISCHARGE", "SPARK", "CRUNCH", "THUNDER_WAVE"])),
}
STARTERS = {"CHIKORITA", "CYNDAQUIL", "TOTODILE"}
EV_TOTAL = {0: 128, 1: 192, 2: 256, 3: 320, 4: 384, 5: 448}       # by badges held; 510 from 6 badges on
NEUTRAL = 12            # Serious: no stat raised or lowered
GROWTH = ["MEDIUM_FAST", "ERRATIC", "FLUCTUATING", "MEDIUM_SLOW", "FAST", "SLOW"]
STAT_ORDER = ["hp", "attack", "defense", "speed", "spAttack", "spDefense"]      # the order EVs and IVs are kept in


def experience(growth, n):
    """Experience for level n."""
    if n <= 1:
        return 0
    if growth == "MEDIUM_FAST":
        return n ** 3
    if growth == "FAST":
        return 4 * n ** 3 // 5
    if growth == "SLOW":
        return 5 * n ** 3 // 4
    if growth == "MEDIUM_SLOW":
        return 6 * n ** 3 // 5 - 15 * n ** 2 + 100 * n - 140
    if growth == "ERRATIC":
        if n <= 50:
            return n ** 3 * (100 - n) // 50
        if n <= 68:
            return n ** 3 * (150 - n) // 100
        if n <= 98:
            return n ** 3 * ((1911 - 10 * n) // 3) // 500
        return n ** 3 * (160 - n) // 100
    if growth == "FLUCTUATING":
        if n <= 15:
            return n ** 3 * ((n + 1) // 3 + 24) // 50
        if n <= 36:
            return n ** 3 * (n + 14) // 50
        return n ** 3 * (n // 2 + 32) // 50
    raise ValueError(growth)


class Data:
    """What the sets need from the hack's tree, the dumped tree and the boss team tool."""

    def __init__(self, tree, dump):
        read = lambda p: open(os.path.join(tree, p), encoding="utf-8").read()
        ids = lambda text, prefix: {n: int(v) for n, v in re.findall(r"#define %s_(\w+)\s+\(?(\d+)\)?\s*$" % prefix,
                                                                       text, re.M)}
        self.species_ids = ids(read("include/constants/species.h"), "SPECIES")
        self.item_ids = ids(read("include/constants/item.h"), "ITEM")
        self.ability_ids = ids(read("include/constants/ability.h"), "ABILITY")
        self.move_ids = ids(read("include/constants/moves.h"), "MOVE")
        self.species = {}
        for m in re.finditer(r"^    \[SPECIES_(\w+)\] = \{\n(.*?)^    \},\n", read("data/Species.c"), re.S | re.M):
            body = m.group(2)
            stats = re.search(r"\.baseStats = \{(.*?)\}", body, re.S)
            if not stats:
                continue
            get = lambda k: re.search(r"\.%s = ([^,\n]+)" % k, body).group(1).strip()
            self.species[m.group(1)] = dict(
                name=re.search(r'\.name = "(.*?)"', body).group(1),
                stats={k: int(v) for k, v in re.findall(r"\.(\w+) = (\d+)", stats.group(1))},
                gender=int(get("genderRatio")), friendship=int(get("baseFriendship")),
                growth=get("expRate").replace("GROWTH_", ""),
                abilities=re.findall(r"ABILITY_(\w+)", re.search(r"\.abilities = \{(.*?)\}", body).group(1)))
        self.pp = {}
        for m in re.finditer(r"^    \[MOVE_(\w+)\] = \{\n(.*?)^    \},\n", read("data/Moves.c"), re.S | re.M):
            pp = re.search(r"\.pp = (\d+)", m.group(2))
            if pp:
                self.pp[m.group(1)] = int(pp.group(1))
        self.parents, self.evolutions = {}, {}
        for m in re.finditer(r"^    \[SPECIES_(\w+)\] = \{(.*?)^    \},", read("data/Evolutions.c"), re.S | re.M):
            for method, param, target in re.findall(r"\{ (EVO_\w+), ([^,]+), SPECIES_(\w+) \}", m.group(2)):
                if method != "EVO_NONE" and target != m.group(1):
                    self.parents.setdefault(target, (m.group(1), method, param.strip()))
        self.chars = {}
        for line in open(os.path.join(tree, "charmap.txt"), encoding="utf-8"):
            m = re.match(r"\s*([0-9A-Fa-f]{4})=(.)$", line.rstrip("\n"))
            if m and m.group(2) not in self.chars:
                self.chars[m.group(2)] = int(m.group(1), 16)
        # where each Pokemon can be found, from the spoiler guide's reading of the encounter tables
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
        import spoiler_guide
        guide = spoiler_guide.Data(os.path.abspath(tree), os.path.abspath(dump))
        self.found = {}
        spoiler_guide.encounters_page(guide, self.found)
        # the boss team tool picks moves; it reads the hack's data relative to the tree
        sys.path.insert(0, os.path.join(tree, "tools", "hack"))
        cwd = os.getcwd()
        os.chdir(tree)
        import boss_teams
        os.chdir(cwd)
        self.bt = boss_teams

    # ------------------------------------------------------------- checks

    def line(self, name):
        """The species and its earlier stages, newest first, with how each evolved: [(name, method, param)]."""
        out = [(name, None, None)]
        while name in self.parents:
            parent, method, param = self.parents[name]
            out[-1] = (out[-1][0], method, param)
            out.append((parent, None, None))
            name = parent
        return out

    def check(self, set_name, spec):
        """Why a set is not one a player could have, as a list of problems (empty when it is fine)."""
        problems = []
        for name in spec["team"]:
            line = self.line(name)
            for stage, method, param in line[:-1]:
                if method != "EVO_LEVEL":
                    problems.append("%s evolves by %s, not by level" % (stage, method))
                elif int(param) > spec["level"]:
                    problems.append("%s evolves at Lv. %s, above the set's %d" % (stage, param, spec["level"]))
            ways = [(place, how) for stage, _, _ in line for place, how in self.found.get(stage, [])
                    if place in spec["places"] and how in spec["ways"]]
            if not ways and not any(stage in STARTERS for stage, _, _ in line):
                problems.append("%s: no member of its line is caught on the way (%s)" % (
                    name, ", ".join(sorted({"%s %s" % (p, h) for stage, _, _ in line
                                           for p, h in self.found.get(stage, [])}))[:200] or "nowhere"))
            if name in spec.get("moves", {}):
                saved = self.bt.MACHINES
                self.bt.MACHINES = set(spec["tms"])
                try:
                    legal = self.bt.legal_moves(name, spec["level"], False)
                finally:
                    self.bt.MACHINES = saved
                for move in spec["moves"][name]:
                    if move not in legal:
                        problems.append("%s cannot have %s by Lv. %d with the set's TMs" % (name, move, spec["level"]))
        return problems

    def moves(self, name, spec):
        """The set's moves for a Pokemon: the boss team tool's choice from its level-up moves and the set's TMs."""
        bt = self.bt
        if name in spec.get("moves", {}):
            return list(spec["moves"][name])
        saved = bt.MACHINES
        bt.MACHINES = set(spec["tms"])
        try:
            return bt.pick_moves(name, spec["level"], False)
        finally:
            bt.MACHINES = saved

    def evs(self, name, moves, badges):
        total = EV_TOTAL.get(badges, 510)
        physical = sum(1 for m in moves if self.bt.MOVES[m]["split"] == "PHYSICAL")
        special = sum(1 for m in moves if self.bt.MOVES[m]["split"] == "SPECIAL")
        main = "attack" if physical >= special else "spAttack"
        evs = dict.fromkeys(STAT_ORDER, 0)
        evs[main] = min(252, total // 2)
        evs["speed"] = min(252, total - evs[main])
        return evs

    # ------------------------------------------------------------- building

    def nickname(self, name):
        text = self.species[name]["name"]
        codes = [self.chars[c] for c in text][:10] + [0xFFFF]
        return codes + [0xFFFF] * (11 - len(codes))

    def build(self, template, name, spec, item=None):
        """A party Pokemon of the set, from a decoded Pokemon of the player's (pkm.Mon) used as the template."""
        sp = self.species[name]
        level = spec["level"]
        moves = self.moves(name, spec)
        evs = self.evs(name, moves, spec["badges"])
        mon = pkm.Mon(template.encode())
        tid, sid = mon.u16(0x04), mon.u16(0x06)
        # a personality value with a neutral nature that is not shiny; it also sets gender and ability slot
        pid = (self.species_ids[name] * 2654435761) & 0xFFFFFFFF
        ratio = sp["gender"]
        want_female = spec.get("female") and ratio not in (0, 255)
        while (pid % 25 != NEUTRAL or ((pid >> 16) ^ (pid & 0xFFFF) ^ tid ^ sid) < 8
               or (want_female and ratio != 254 and (pid & 0xFF) >= ratio)):
            pid = (pid + 1) & 0xFFFFFFFF
        mon.pid = pid
        mon.set_u16(0x00, self.species_ids[name])
        mon.set_u16(0x02, self.item_ids[item or spec["item"]])
        mon.set_u32(0x08, experience(sp["growth"], level))
        mon.blocks[0x0C] = sp["friendship"]
        abilities = [a for a in sp["abilities"] if a != "NONE"] or ["NONE"]
        mon.blocks[0x0D] = self.ability_ids[abilities[pid & 1] if len(abilities) > 1 else abilities[0]]
        for i, stat in enumerate(STAT_ORDER):
            mon.blocks[0x10 + i] = evs[stat]
        for i in range(4):
            move = moves[i] if i < len(moves) else None
            mon.set_u16(0x20 + 2 * i, self.move_ids[move] if move else 0)
            mon.blocks[0x28 + i] = self.pp.get(move, 0) if move else 0
            mon.blocks[0x2C + i] = 0
        ivs = sum(15 << (5 * i) for i in range(6))            # all 15; not an egg, not nicknamed
        mon.set_u32(0x30, ivs)
        female = ratio == 254 or (ratio not in (0, 255) and (pid & 0xFF) < ratio)
        mon.blocks[0x38] = (mon.blocks[0x38] & 1) | (2 if female else 0) | (4 if ratio == 255 else 0)  # form 0
        for i, code in enumerate(self.nickname(name)):
            mon.set_u16(0x40 + 2 * i, code)
        # battle stats
        stats = {}
        for i, stat in enumerate(STAT_ORDER):
            base, ev = sp["stats"][stat], evs[stat]
            core = (2 * base + 15 + ev // 4) * level // 100
            stats[stat] = core + level + 10 if stat == "hp" else core + 5
        mon.stats[:] = bytes(100)
        struct.pack_into("<IBBHHHHHHH", mon.stats, 0, 0, level, 0, stats["hp"], stats["hp"], stats["attack"],
                         stats["defense"], stats["speed"], stats["spAttack"], stats["spDefense"])
        return mon, moves, evs


def main():
    tree, dump = sys.argv[1], sys.argv[2]
    d = Data(tree, dump)
    bad = 0
    for set_name, spec in SETS.items():
        print("%s (Lv. %d, %d badges, EVs %d)" % (set_name, spec["level"], spec["badges"], EV_TOTAL.get(spec["badges"], 510)))
        for name in spec["team"]:
            moves = d.moves(name, spec)
            print("  %-11s %s" % (name, ", ".join(moves)))
        for p in d.check(set_name, spec):
            print("  PROBLEM:", p)
            bad += 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
