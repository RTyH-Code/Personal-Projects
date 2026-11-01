#!/usr/bin/env python3
"""Generate the FireRed QoL+Hard spoiler guide (Markdown) from the game data.

Everything is read from the source, FireRed only (LeafGreen variants are
skipped), so the guide always matches the built ROM. New additions are marked
by comparing against vanilla pret/pokefirered (commit ce6406d).

Usage (from the repo root):
    python3 tools/hack/spoiler_guide.py OUTPUT_DIR
"""
import glob
import json
import os
import re
import subprocess
import sys

VANILLA = "ce6406d"
OUT = sys.argv[1]

# ---------------------------------------------------------------- helpers

def read(path):
    return open(path, encoding="utf-8").read()


def vanilla(path):
    return subprocess.run(["git", "show", f"{VANILLA}:{path}"], capture_output=True, text=True).stdout


def firered_only(text):
    """Drop LeafGreen-only blocks (.ifdef FIRERED/LEAFGREEN in scripts, #if in C)."""
    out, stack = [], []
    for line in text.split("\n"):
        s = line.strip()
        m = re.match(r"(?:\.ifdef|#ifdef|#if defined\(|#if)\s*\(?\s*(FIRERED|LEAFGREEN)", s)
        if m:
            stack.append(m.group(1) == "FIRERED")
            continue
        if re.match(r"#elif\s+defined\(\s*LEAFGREEN|#elif\s+LEAFGREEN", s):
            stack[-1] = False
            continue
        if re.match(r"#elif\s+defined\(\s*FIRERED|#elif\s+FIRERED", s):
            stack[-1] = True
            continue
        if s in (".else", "#else") and stack:
            stack[-1] = not stack[-1]
            continue
        if s in (".endif", "#endif") and stack:
            stack.pop()
            continue
        if all(stack):
            out.append(line)
    return "\n".join(out)


SPECIAL_NAMES = {"NIDORAN_F": "Nidoran♀", "NIDORAN_M": "Nidoran♂", "MR_MIME": "Mr. Mime",
                 "FARFETCHD": "Farfetch'd", "HO_OH": "Ho-Oh", "PORYGON2": "Porygon2",
                 "DEOXYS_ATTACK": "Deoxys (Attack)", "DEOXYS_DEFENSE": "Deoxys (Defense)",
                 "DEOXYS_SPEED": "Deoxys (Speed)"}


def mon(const):
    c = const.replace("SPECIES_", "")
    return SPECIAL_NAMES.get(c, c.replace("_", " ").title())


def move(const):
    c = const.replace("MOVE_", "")
    return {"SOFTBOILED": "Soft-Boiled", "WILL_O_WISP": "Will-O-Wisp", "U_TURN": "U-turn",
            "DOUBLE_EDGE": "Double-Edge", "SELF_DESTRUCT": "Self-Destruct", "X_SCISSOR": "X-Scissor",
            "LOCK_ON": "Lock-On", "MUD_SLAP": "Mud-Slap"}.get(c, c.replace("_", " ").title())


def map_name(const):
    c = const.replace("MAP_", "")
    words = []
    for w in c.split("_"):
        if re.fullmatch(r"B?\d+F|\d+R", w):
            words.append(w)
        elif w == "SSANNE":
            words.append("S.S. Anne")
        elif w == "MT":
            words.append("Mt.")
        elif w == "POKEMON":
            words.append("Pokémon")
        elif re.fullmatch(r"ROUTE\d+", w):
            words.append("Route " + w[5:])
        else:
            words.append(w.title())
    return " ".join(words)


SEVII = ["ONE_ISLAND", "TWO_ISLAND", "THREE_ISLAND", "FOUR_ISLAND", "FIVE_ISLAND", "SIX_ISLAND",
         "SEVEN_ISLAND", "NAVEL_ROCK", "BIRTH_ISLAND"]
TOWNS = ["PALLET_TOWN", "VIRIDIAN_CITY", "PEWTER_CITY", "CERULEAN_CITY", "VERMILION_CITY", "LAVENDER_TOWN",
         "CELADON_CITY", "FUCHSIA_CITY", "SAFFRON_CITY", "CINNABAR_ISLAND", "INDIGO_PLATEAU"]


def map_order(const):
    c = const.replace("MAP_", "")
    m = re.match(r"ROUTE(\d+)", c)
    if m:
        return (1, int(m.group(1)), c)
    for i, t in enumerate(TOWNS):
        if c.startswith(t):
            return (0, i, c)
    for i, s in enumerate(SEVII):
        if c.startswith(s):
            return (3, i, c)
    return (2, 0, c)


def anchor(title):
    return re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-")


# ---------------------------------------------------------------- shared data

items_json = json.loads(read("src/data/items.json"))["items"]
item_ids = {}
for name, val in re.findall(r"#define (ITEM_\w+)\s+(\w+)", read("include/constants/items.h")):
    item_ids[name] = val
def item_index(const):
    v = const
    for _ in range(4):
        if v.isdigit():
            return int(v)
        v = item_ids.get(v, v)
    return None
tm_moves = {}
for name, base in re.findall(r"#define (ITEM_(?:TM|HM)\d\d_\w+)\s+(ITEM_(?:TM|HM)\d\d)\b", read("include/constants/items.h")):
    tm_moves[base] = name[len(base) + 1:]


ITEM_WORDS = {"DEEPSEATOOTH": "Deep Sea Tooth", "DEEPSEASCALE": "Deep Sea Scale", "NEVERMELTICE": "Never-Melt Ice",
              "TWISTEDSPOON": "Twisted Spoon", "SILVERPOWDER": "Silver Powder", "BLACKGLASSES": "Black Glasses",
              "BRIGHTPOWDER": "Bright Powder", "MYSTICTICKET": "Mystic Ticket", "AURORATICKET": "Aurora Ticket",
              "BLACKBELT": "Black Belt", "SILKSCARF": "Silk Scarf", "SHARPBEAK": "Sharp Beak",
              "DRAGONFANG": "Dragon Fang", "SPELLTAG": "Spell Tag", "THUNDERSTONE": "Thunder Stone",
              "TV": "TV", "PP": "PP", "HP": "HP", "TM": "TM", "HM": "HM", "SS": "S.S.", "EXP.": "Exp.",
              "POKéDEX": "Pokédex", "POKé": "Poké", "POKéBLOCK": "Pokéblock", "POKéFLUTE": "Poké Flute"}


def nice_item_name(raw):
    words = []
    for w in raw.split(" "):
        if w in ITEM_WORDS:
            words.append(ITEM_WORDS[w])
        elif re.fullmatch(r"(TM|HM)\d\d", w):
            words.append(w)
        else:
            words.append("-".join(p[:1] + p[1:].lower() for p in w.split("-")))
    return " ".join(words)


def item(const):
    idx = item_index(const)
    raw = items_json[idx]["english"] if idx is not None and idx < len(items_json) else const[5:]
    name = nice_item_name(raw)
    base = re.match(r"ITEM_(?:TM|HM)\d\d", const)
    if base and base.group(0) in tm_moves:
        name = f"{raw} {move('MOVE_' + tm_moves[base.group(0)])}"
    return name


maps = {}  # map const -> (dir, json)
for f in glob.glob("data/maps/*/map.json"):
    m = json.loads(read(f))
    maps[m["id"]] = (f.split("/")[2], m)
dir_to_map = {d: k for k, (d, _) in maps.items()}

script_text = {}
for f in glob.glob("data/maps/*/scripts.inc") + glob.glob("data/scripts/*.inc") + ["data/event_scripts.s"]:
    script_text[f] = firered_only(read(f))
all_scripts = "\n".join(script_text.values())

# label -> map const, from any event in map.json that runs it
label_map = {}
for k, (d, m) in maps.items():
    for ev in (m.get("object_events") or []) + (m.get("bg_events") or []) + (m.get("coord_events") or []):
        if ev.get("script"):
            label_map.setdefault(ev["script"], k)


def labels_in(text):
    """Yield (label, body) for each script label in a file."""
    parts = re.split(r"^(\w+)::\s*$", text, flags=re.M)
    for i in range(1, len(parts) - 1, 2):
        yield parts[i], parts[i + 1]


def reached_from(label, file_map, seen=None):
    """Which map runs this label (directly, or via goto/call from another label)."""
    if label in label_map:
        return label_map[label]
    return file_map


label_body = {}
label_file_map = {}
for f, text in script_text.items():
    fmap = dir_to_map.get(f.split("/")[2]) if f.startswith("data/maps/") else None
    for lab, body in labels_in(text):
        label_body[lab] = body
        label_file_map[lab] = fmap
callers = {}
for lab, body in label_body.items():
    for tgt in re.findall(r"\b(?:goto|call|goto_if_\w+|call_if_\w+)\b[^\n]*?\b(\w+_EventScript_\w+|EventScript_\w+)", body):
        callers.setdefault(tgt, set()).add(lab)


def label_location(lab, depth=0):
    if lab in label_map:
        return label_map[lab]
    if label_file_map.get(lab):
        return label_file_map[lab]
    if depth < 4:
        for c in sorted(callers.get(lab, ())):
            loc = label_location(c, depth + 1)
            if loc:
                return loc
    return None

# ---------------------------------------------------------------- encounters

RATES = {"land_mons": [20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1], "water_mons": [60, 30, 5, 4, 1],
         "rock_smash_mons": [60, 30, 5, 4, 1]}
ROD_SLOTS = {"Old Rod": (0, 2, [70, 30]), "Good Rod": (2, 5, [60, 20, 20]), "Super Rod": (5, 10, [40, 40, 15, 4, 1])}
KIND_NAME = {"land_mons": "Grass / cave", "water_mons": "Surfing", "rock_smash_mons": "Rock Smash"}


def fr_tables(data):
    out = {}
    for e in data["wild_encounter_groups"][0]["encounters"]:
        if e["base_label"].endswith("FireRed") and e["map"] not in out:
            out[e["map"]] = e
    return out


def summarize(mons, rates):
    agg = {}
    for r, m in zip(rates, mons):
        a = agg.setdefault(m["species"], [0, 100, 0])
        a[0] += r
        a[1] = min(a[1], m["min_level"])
        a[2] = max(a[2], m["max_level"])
    return sorted(agg.items(), key=lambda kv: -kv[1][0])


def encounter_rows(e):
    rows = []
    for kind in ("land_mons", "water_mons", "rock_smash_mons"):
        if kind in e:
            rows.append((KIND_NAME[kind], summarize(e[kind]["mons"], RATES[kind])))
    if "fishing_mons" in e:
        for rod, (a, b, rates) in ROD_SLOTS.items():
            rows.append((rod, summarize(e["fishing_mons"]["mons"][a:b], rates)))
    return rows


def write_encounters():
    cur = fr_tables(json.loads(read("src/data/wild_encounters.json")))
    old = fr_tables(json.loads(vanilla("src/data/wild_encounters.json")))
    order = sorted(cur, key=map_order)
    out = ["# Wild encounters", "",
           "Every FireRed encounter table. Percentages are the chance per encounter; "
           "**★** marks a Pokémon that wasn't in that spot in the original FireRed.", "",
           "Altering Cave uses one mixed table (the Mystery Gift tables aren't used). "
           "Tanoby Chambers only have Unown.", ""]
    out += ["## Contents", ""] + [f"- [{map_name(k)}](#{anchor(map_name(k))})" for k in order] + [""]
    for k in order:
        out += [f"## {map_name(k)}", "", "| Method | Pokémon | Levels | Chance |", "|---|---|---|---|"]
        oldset = set()
        if k in old:
            for _, rows in encounter_rows(old[k]):
                oldset |= {s for s, _ in rows}
        for method, rows in encounter_rows(cur[k]):
            for i, (sp, (pct, lo, hi)) in enumerate(rows):
                star = " ★" if sp not in oldset else ""
                lv = f"{lo}" if lo == hi else f"{lo}–{hi}"
                out.append(f"| {method if i == 0 else ''} | {mon(sp)}{star} | {lv} | {pct}% |")
        out.append("")
    open(os.path.join(OUT, "ENCOUNTERS.md"), "w").write("\n".join(out))

# ---------------------------------------------------------------- items

def write_items():
    ball_items = {lab: (re.search(r"finditem (ITEM_\w+)(?:, (\d+))?", body)) for lab, body in label_body.items()}
    per_map = {}
    for k, (d, m) in maps.items():
        for o in m.get("object_events") or []:
            if o.get("graphics_id") == "OBJ_EVENT_GFX_ITEM_BALL":
                f = ball_items.get(o.get("script"))
                if f:
                    q = f" ×{f.group(2)}" if f.group(2) else ""
                    per_map.setdefault(k, []).append(("Item ball", item(f.group(1)) + q, (o["x"], o["y"])))
        for b in m.get("bg_events") or []:
            if b.get("type") == "hidden_item":
                q = f" ×{b['quantity']}" if b.get("quantity", 1) > 1 else ""
                per_map.setdefault(k, []).append(("Hidden", item(b["item"]) + q, (b["x"], b["y"])))
    gifts = {}
    for lab, body in label_body.items():
        for it in re.findall(r"^\s*(?:giveitem|giveitem_msg [^,]+,|msgreceiveditem [^,]+,)\s*(ITEM_\w+)", body, re.M):
            loc = label_location(lab)
            if loc:
                gifts.setdefault(loc, set()).add(item(it))
    marts = {}
    for f, text in script_text.items():
        for lab in re.findall(r"pokemart (\w+)", text):
            m = re.search(r"^%s::\s*\n((?:\s*\.2byte ITEM_\w+\n)+)" % lab, all_scripts, re.M)
            if not m:
                continue
            its = [i for i in re.findall(r"(ITEM_\w+)", m.group(1)) if i != "ITEM_NONE"]
            loc = label_location(lab) or (dir_to_map.get(f.split("/")[2]) if f.startswith("data/maps/") else None)
            if loc:
                marts.setdefault(loc, []).append(its)

    out = ["# Items", "",
           "Item balls, hidden items (use the Itemfinder), NPC gifts and shop stock, by location. "
           "Coordinates are map tiles (x, y), counted from the top-left corner.", "",
           "**Changed from the original game:**",
           "- TMs are reusable.",
           "- Celadon Dept. Store 4F sells every evolution item.",
           "- After beating the round 2 Champion, vitamins (HP Up, Protein, Iron, Calcium, Zinc, Carbos) cost ₽0.",
           "- Sevault Canyon has a Root Fossil and a Claw Fossil.", ""]
    order = sorted(set(per_map) | set(gifts) | set(marts), key=map_order)
    for k in order:
        out += [f"## {map_name(k)}", ""]
        if k in per_map:
            out += ["| Type | Item | At |", "|---|---|---|"]
            for t, it, (x, y) in sorted(per_map[k], key=lambda r: (r[0], r[1])):
                out.append(f"| {t} | {it} | {x}, {y} |")
            out.append("")
        if k in gifts:
            out += ["Gifts / events: " + ", ".join(sorted(gifts[k])), ""]
        if k in marts:
            for its in marts[k]:
                prices = []
                for i in its:
                    idx = item_index(i)
                    p = items_json[idx]["price"] if idx is not None else 0
                    prices.append(f"{item(i)} (₽{p})")
                out += ["Shop: " + ", ".join(prices), ""]
    open(os.path.join(OUT, "ITEMS.md"), "w").write("\n".join(out))

# ---------------------------------------------------------------- trainers

def parse_parties():
    text = firered_only(read("src/data/trainer_parties.h"))
    parties = {}
    for name, body in re.findall(r"static const struct \w+ (sParty_\w+)\[\] = \{\n(.*?)\n\};", text, re.S):
        mons = []
        for blk in re.findall(r"\{(.*?)\n    \}", body, re.S):
            sp = re.search(r"\.species = (SPECIES_\w+)", blk)
            if not sp:
                continue
            lv = re.search(r"\.lvl = (\d+)", blk).group(1)
            held = re.search(r"\.heldItem = (ITEM_\w+)", blk)
            mv = re.search(r"\.moves = \{(.*?)\}", blk)
            mons.append({"species": sp.group(1), "lvl": int(lv),
                         "item": held.group(1) if held and held.group(1) != "ITEM_NONE" else None,
                         "moves": [x.strip() for x in mv.group(1).split(",") if x.strip() not in ("", "MOVE_NONE")] if mv else []})
        parties[name] = mons
    return parties


def parse_trainers():
    text = firered_only(read("src/data/trainers.h"))
    out = {}
    for tid, body in re.findall(r"\[(TRAINER_\w+)\] = \{(.*?)\n    \},", text, re.S):
        cls = re.search(r"\.trainerClass = TRAINER_CLASS_(\w+)", body)
        nm = re.search(r'\.trainerName = _\("(.*?)"\)', body)
        party = re.search(r"\((sParty_\w+)\)", body)
        double = "doubleBattle = TRUE" in body
        if cls and nm and party:
            out[tid] = {"class": cls.group(1), "name": nm.group(1), "party": party.group(1), "double": double}
    aliases = dict(re.findall(r"#define (TRAINER_PEAK_\w+)\s+(TRAINER_\w+)", read("include/constants/opponents.h")))
    return out, aliases


CLASS_NAMES = {"RIVAL_EARLY": "Rival", "RIVAL_LATE": "Rival", "CHAMPION": "Champion", "LEADER": "Leader",
               "ELITE_FOUR": "Elite Four", "TEAM_ROCKET": "Team Rocket", "BOSS": "Boss",
               "PKMN_PROF": "Prof.", "COOLTRAINER": "Cool Trainer", "SUPER_NERD": "Super Nerd",
               "PSYCHIC": "Psychic", "CRUSH_KIN": "Crush Kin", "SIS_AND_BRO": "Sis and Bro"}


def trainer_title(t):
    cls = CLASS_NAMES.get(t["class"], t["class"].replace("_", " ").title())
    name = t["name"].replace("TERRY", "(your rival)") if t["class"] in ("RIVAL_EARLY", "RIVAL_LATE", "CHAMPION") else t["name"].title()
    return f"{cls} {name}".strip()


def party_line(mons):
    return ", ".join(f"{mon(m['species'])} Lv{m['lvl']}" for m in mons)


def party_detail(mons):
    rows = ["| Pokémon | Lv | Item | Moves |", "|---|---|---|---|"]
    for m in mons:
        rows.append(f"| {mon(m['species'])} | {m['lvl']} | {item(m['item']) if m['item'] else '—'} | "
                    f"{', '.join(move(x) for x in m['moves']) or 'level-up moves'} |")
    return rows


def write_trainers():
    parties = parse_parties()
    trainers, aliases = parse_trainers()
    rev_alias = {v: k for k, v in aliases.items()}
    where = {}
    for lab, body in label_body.items():
        for tid in re.findall(r"trainerbattle\w*\s+(TRAINER_\w+)", body):
            loc = label_location(lab)
            if loc:
                where.setdefault(tid, set()).add(loc)
    # resolve peak aliases used in scripts
    resolved = {}
    for tid, locs in where.items():
        resolved.setdefault(aliases.get(tid, tid), set()).update(locs)

    def block(title, tid):
        t = trainers[tid]
        out = [f"### {title}", ""]
        if t["double"]:
            out += ["*Double battle.*", ""]
        return out + party_detail(parties[t["party"]]) + [""]

    out = ["# Trainers", "",
           "Gym Leaders, the Elite Four, the Champion and post-game peak trainers are listed in full first. "
           "Then every other trainer, by location.", "",
           "Regular trainers use their normal level-up moves unless moves are listed. "
           "Peak trainers' Pokémon have perfect IVs, a nature that boosts their main attacking stat, "
           "and 252/252 EVs (attack stat and Speed, or HP for slow Pokémon).", ""]
    gyms = [("Brock", "LEADER_BROCK"), ("Misty", "LEADER_MISTY"), ("Lt. Surge", "LEADER_LT_SURGE"),
            ("Erika", "LEADER_ERIKA"), ("Koga", "LEADER_KOGA"), ("Sabrina", "LEADER_SABRINA"),
            ("Blaine", "LEADER_BLAINE"), ("Giovanni", "LEADER_GIOVANNI")]
    out += ["## Gym Leaders", ""]
    for n, t in gyms:
        out += block(n, "TRAINER_" + t)
    out += ["## Elite Four and Champion", ""]
    e4 = [("Lorelei", "ELITE_FOUR_LORELEI"), ("Bruno", "ELITE_FOUR_BRUNO"), ("Agatha", "ELITE_FOUR_AGATHA"),
          ("Lance", "ELITE_FOUR_LANCE")]
    for rnd, suffix in [("round 1", ""), ("round 2 (after the Sevii Islands story)", "_2")]:
        for n, t in e4:
            out += block(f"{n}, {rnd}", f"TRAINER_{t}{suffix}")
        for starter, rival in [("Bulbasaur", "CHARMANDER"), ("Charmander", "SQUIRTLE"), ("Squirtle", "BULBASAUR")]:
            kind = "FIRST" if not suffix else "REMATCH"
            out += block(f"Champion, {rnd} (you chose {starter})", f"TRAINER_CHAMPION_{kind}_{rival}")
    out += ["## Post-game peak trainers (Lv. 100)", "",
            "Gym Leaders offer these rematches any number of times after you become Champion. "
            "The Elite Four and Champion use them when the PEAK challenge is on "
            "(League official in the Indigo Plateau Pokémon Center).", ""]
    for alias, slot in aliases.items():
        n = alias.replace("TRAINER_PEAK_", "")
        title = n.replace("CHAMPION_", "Champion (rival's ") .replace("_", " ").title()
        if n.startswith("CHAMPION_"):
            rival = n.split("_")[1].title()
            chose = {"Charmander": "Bulbasaur", "Squirtle": "Charmander", "Bulbasaur": "Squirtle"}[rival]
            title = f"Champion, peak (you chose {chose})"
        out += block(f"Peak {title}" if not n.startswith("CHAMPION_") else title, slot)
    shown = {"TRAINER_" + t for _, t in gyms} | {f"TRAINER_{t}{s}" for _, t in e4 for s in ("", "_2")} | set(aliases.values())
    shown |= {f"TRAINER_CHAMPION_{k}_{r}" for k in ("FIRST", "REMATCH") for r in ("SQUIRTLE", "BULBASAUR", "CHARMANDER")}
    by_map = {}
    for tid, locs in resolved.items():
        if tid in shown or tid not in trainers:
            continue
        for loc in locs:
            by_map.setdefault(loc, []).append(tid)
    out += ["## All other trainers, by location", "",
            "Includes the rival's earlier battles; which team you face depends on your starter.", ""]
    for k in sorted(by_map, key=map_order):
        out += [f"### {map_name(k)}", "", "| Trainer | Pokémon |", "|---|---|"]
        for tid in sorted(by_map[k], key=lambda t: trainers[t]["name"]):
            t = trainers[tid]
            mons = parties[t["party"]]
            line = party_line(mons)
            extra = []
            if any(m["item"] for m in mons):
                extra.append("items: " + ", ".join(f"{mon(m['species'])} @ {item(m['item'])}" for m in mons if m["item"]))
            dbl = " *(double)*" if t["double"] else ""
            out.append(f"| {trainer_title(t)}{dbl} | {line}{' — ' + '; '.join(extra) if extra else ''} |")
        out.append("")
    open(os.path.join(OUT, "TRAINERS.md"), "w").write("\n".join(out))

# ---------------------------------------------------------------- Pokemon: gifts, statics, trades, changes

def special_encounters():
    """(map const, species const, level, how) for gifts, eggs, statics, prizes."""
    rows = []
    for lab, body in label_body.items():
        for cmd, sp, lv in re.findall(r"^\s*(givemon|giveegg|setwildbattle|seteventmon)\s+(SPECIES_\w+)(?:,\s*(\d+))?", body, re.M):
            loc = label_location(lab)
            if not loc:
                continue
            kind = {"givemon": "Gift", "giveegg": "Egg", "setwildbattle": "Battle", "seteventmon": "Battle"}[cmd]
            rows.append((loc, sp, lv or "egg", kind))
    for lab, body in label_body.items():
        if "PrizeRoom" in lab or "Dojo" in lab:
            for sp in re.findall(r"setvar VAR_TEMP_1, (SPECIES_\w+)", body):
                loc = label_location(lab)
                coins = re.search(r"setvar VAR_TEMP_2, (\d+)", body)
                kind = (f"Game Corner prize ({coins.group(1)} coins)" if coins else "Game Corner prize") \
                    if "PrizeRoom" in lab else "Gift (choose one)"
                lvl = re.search(r"case %s,\s*(\w+)" % sp, all_scripts)
                lv = "?"
                if lvl and lvl.group(1) in label_body:
                    m = re.search(r"givemon VAR_TEMP_1, (\d+)", label_body[lvl.group(1)])
                    lv = m.group(1) if m else "?"
                elif "Dojo" in lab:
                    m = re.search(r"givemon VAR_TEMP_1, (\d+)", all_scripts[all_scripts.find("SaffronCity_Dojo"):])
                    lv = m.group(1) if m else "?"
                rows.append((loc, sp, lv, kind))
    return sorted(set(rows), key=lambda r: (map_order(r[0]), r[1]))


def ingame_trades():
    """(map const or None, species you give, species you get, nickname)."""
    trades = firered_only(read("src/data/ingame_trades.h"))
    out = []
    for tid, body in re.findall(r"\[(INGAME_TRADE_\w+)\] =\s*\{(.*?)\n    \}", trades, re.S):
        get = re.search(r"\.species = (SPECIES_\w+)", body).group(1)
        give = re.search(r"\.requestedSpecies = (SPECIES_\w+)", body).group(1)
        nick = re.search(r'\.nickname = _\("(.*?)"\)', body).group(1)
        loc = next((label_location(l) for l, b in label_body.items() if re.search(r"\b%s\b" % tid, b)), None)
        out.append((loc, give, get, nick))
    return out


def evos(text):
    res = {}
    for a, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", text, re.S):
        for meth, param, t in re.findall(r"\{(EVO_\w+), ([^,]+), (SPECIES_\w+)", body):
            res[(a, t)] = (meth, param.strip())
    return res


def evo_text(meth, param):
    if meth == "EVO_ITEM":
        return f"use {item(param)}"
    if meth == "EVO_LEVEL":
        return f"level {param}"
    if meth == "EVO_TRADE":
        return "trade"
    if meth == "EVO_TRADE_ITEM":
        return f"trade holding {item(param)}"
    return meth.replace("EVO_", "").replace("_", " ").lower()


def write_pokemon():
    out = ["# Pokémon", "", "Gift and one-time Pokémon, in-game trades, and every change to evolutions, "
           "base stats and moves.", ""]
    rows = [(map_order(l), map_name(l), mon(sp), lv, kind) for l, sp, lv, kind in special_encounters()]
    rows = sorted(set(rows))
    out += ["## Gift, static and legendary Pokémon", "",
            "Legendaries added by this hack appear after your first Hall of Fame entry (see the main README "
            "for exact spots). Starters other than yours are wild; see ENCOUNTERS.md.", "",
            "| Location | Pokémon | Lv | How |", "|---|---|---|---|"]
    out += [f"| {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in rows] + [""]

    out += ["## In-game trades", "", "| Location | You give | You get | Nickname |", "|---|---|---|---|"]
    for loc, give, get, nick in ingame_trades():
        out.append(f"| {map_name(loc) if loc else '?'} | {mon(give)} | {mon(get)} | {nick} |")
    out.append("")

    new, old = evos(read("src/data/pokemon/evolution.h")), evos(vanilla("src/data/pokemon/evolution.h"))
    out += ["## Changed evolutions", "", "| Evolution | Original | Now |", "|---|---|---|"]
    for k in sorted(new, key=lambda k: k[0]):
        if old.get(k) != new[k]:
            o = evo_text(*old[k]) if k in old else "—"
            out.append(f"| {mon(k[0])} → {mon(k[1])} | {o} | {evo_text(*new[k])} |")
    out.append("")
    out += ["Deoxys changes Forme with the **Meteorite** (key item, given when you catch it on Birth Island).", ""]

    changes = read("tools/hack/modernize_changes.txt").strip().split("\n") if os.path.exists("tools/hack/modernize_changes.txt") else []
    stat = [c for c in changes if c.startswith("SPECIES_")]
    mv = [c for c in changes if c.startswith("MOVE_")]
    out += ["## Base stat changes (modern values)", "", "| Pokémon | Stat | Original | Now |", "|---|---|---|---|"]
    for c in stat:
        m = re.match(r"(SPECIES_\w+): base(\w+) (\d+) -> (\d+)", c)
        out.append(f"| {mon(m.group(1))} | {m.group(2).replace('SpAttack','Sp. Atk').replace('SpDefense','Sp. Def')} | {m.group(3)} | {m.group(4)} |")
    out += ["", "## Move changes (modern values)", "",
            "Power and accuracy changes below; many PP values also match modern games. "
            "Every move uses the physical/special split.", "",
            "| Move | Change |", "|---|---|"]
    for c in mv:
        m = re.match(r"(MOVE_\w+): (\w+) (\d+) -> (\d+)", c)
        out.append(f"| {move(m.group(1))} | {m.group(2)} {m.group(3)} → {m.group(4)} |")
    out.append("")
    open(os.path.join(OUT, "POKEMON.md"), "w").write("\n".join(out))


# ---------------------------------------------------------------- Pokédex

TYPES = ["NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK", "BUG", "GHOST", "STEEL",
         "FIRE", "WATER", "GRASS", "ELECTRIC", "PSYCHIC", "ICE", "DRAGON", "DARK"]
GROWTH = {"GROWTH_MEDIUM_FAST": ("Medium Fast", 1000000), "GROWTH_ERRATIC": ("Erratic", 600000),
          "GROWTH_FLUCTUATING": ("Fluctuating", 1640000), "GROWTH_MEDIUM_SLOW": ("Medium Slow", 1059860),
          "GROWTH_FAST": ("Fast", 800000), "GROWTH_SLOW": ("Slow", 1250000)}
EGG_GROUPS = {"MONSTER": "Monster", "WATER_1": "Water 1", "BUG": "Bug", "FLYING": "Flying", "FIELD": "Field",
              "FAIRY": "Fairy", "GRASS": "Grass", "HUMAN_LIKE": "Human-Like", "WATER_3": "Water 3",
              "MINERAL": "Mineral", "AMORPHOUS": "Amorphous", "WATER_2": "Water 2", "DITTO": "Ditto",
              "DRAGON": "Dragon", "UNDISCOVERED": "Undiscovered (can't breed)"}
STATS = [("HP", "baseHP"), ("Attack", "baseAttack"), ("Defense", "baseDefense"),
         ("Sp. Atk", "baseSpAttack"), ("Sp. Def", "baseSpDefense"), ("Speed", "baseSpeed")]
EV_FIELDS = [("HP", "evYield_HP"), ("Attack", "evYield_Attack"), ("Defense", "evYield_Defense"),
             ("Sp. Atk", "evYield_SpAttack"), ("Sp. Def", "evYield_SpDefense"), ("Speed", "evYield_Speed")]
DEOXYS_FORMES = [("SPECIES_DEOXYS", "Normal Forme"), ("SPECIES_DEOXYS_ATTACK", "Attack Forme"),
                 ("SPECIES_DEOXYS_DEFENSE", "Defense Forme"), ("SPECIES_DEOXYS_SPEED", "Speed Forme")]


def tname(t):
    return "???" if t == "TYPE_MYSTERY" else t.replace("TYPE_", "").title()


def c_blocks(text, key_re=r"SPECIES_\w+"):
    """[KEY] = { ... } blocks of a designated-initializer table."""
    out = {}
    for k, body in re.findall(r"\[(%s)\]\s*=\s*\{\n(.*?)\n    \}," % key_re, text, re.S):
        out[k] = body
    return out


def fields(body):
    return {k: v.strip() for k, v in re.findall(r"\.(\w+)\s*=\s*([^\n]*?),?\s*(?:\n|$)", body)}


def species_info(text):
    return {k: fields(v) for k, v in c_blocks(text).items()}


def levelup_learnsets(text):
    text = firered_only(text)
    arrays = {n: [(int(l), m) for l, m in re.findall(r"LEVEL_UP_MOVE\(\s*(\d+),\s*(MOVE_\w+)\)", b)]
              for n, b in re.findall(r"static const u16 (s\w+LevelUpLearnset)\[\] = \{(.*?)\};", text, re.S)}
    return arrays


def learnset_pointers(text):
    return dict(re.findall(r"\[(SPECIES_\w+)\]\s*=\s*(s\w+LevelUpLearnset)", text))


def stat_range(base, level, hp=False):
    def calc(iv, ev, nat):
        core = (2 * base + iv + ev // 4) * level // 100
        if hp:
            return core + level + 10
        return int((core + 5) * nat)
    if hp:
        return calc(0, 0, 1), calc(31, 252, 1)
    return calc(0, 0, 0.9), calc(31, 252, 1.1)


def bar(v):
    n = max(1, round(v / 10))
    return "█" * n


def write_pokedex():
    info = species_info(read("src/data/pokemon/species_info.h"))
    old_info = species_info(vanilla("src/data/pokemon/species_info.h"))
    dex_order = re.findall(r"NATIONAL_DEX_(\w+),", read("include/constants/pokedex.h").split("HOENN_DEX_NONE")[0])
    dex_order = [d for d in dex_order if d != "NONE"]
    dex_order = dex_order[:dex_order.index("DEOXYS") + 1]
    species = ["SPECIES_" + d for d in dex_order]
    dexno = {sp: i + 1 for i, sp in enumerate(species)}
    for f, _ in DEOXYS_FORMES:
        dexno.setdefault(f, dexno["SPECIES_DEOXYS"])

    # moves
    mv = {}
    for k, body in c_blocks(read("src/data/battle_moves.h"), r"MOVE_\w+").items():
        f = fields(body)
        mv[k] = f
    def move_cells(m):
        f = mv.get(m, {})
        split = {"SPLIT_PHYSICAL": "Physical", "SPLIT_SPECIAL": "Special", "SPLIT_STATUS": "Status"}.get(f.get("split"), "?")
        pw = f.get("power", "0")
        acc = f.get("accuracy", "0")
        pw = "—" if pw in ("0", "1") and split == "Status" else ("varies" if pw == "1" else ("—" if pw == "0" else pw))
        acc = "—" if acc == "0" else acc + "%"
        return f"{move(m)} | {tname(f.get('type', 'TYPE_NORMAL'))} | {split} | {pw} | {acc} | {f.get('pp', '?')}"

    # learnsets
    lu_arrays = levelup_learnsets(read("src/data/pokemon/level_up_learnsets.h"))
    lu_ptr = learnset_pointers(read("src/data/pokemon/level_up_learnset_pointers.h"))
    old_arrays = levelup_learnsets(vanilla("src/data/pokemon/level_up_learnsets.h"))
    old_ptr = learnset_pointers(vanilla("src/data/pokemon/level_up_learnset_pointers.h"))
    def levelup(sp, arrays=lu_arrays, ptr=lu_ptr):
        return arrays.get(ptr.get(sp), [])

    tmhm = {}
    for sp, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*TMHM_LEARNSET\((.*?)\)\s*,", read("src/data/pokemon/tmhm_learnsets.h"), re.S):
        tmhm[sp] = re.findall(r"TMHM\(((?:TM|HM)\d\d)_\w+\)", body)
    tutor = {}
    for sp, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*((?:\s*\|?\s*TUTOR\(MOVE_\w+\))+)", read("src/data/pokemon/tutor_learnsets.h")):
        tutor[sp] = re.findall(r"TUTOR\((MOVE_\w+)\)", body)
    for sp, m in (("SPECIES_VENUSAUR", "MOVE_FRENZY_PLANT"), ("SPECIES_CHARIZARD", "MOVE_BLAST_BURN"),
                  ("SPECIES_BLASTOISE", "MOVE_HYDRO_CANNON")):
        tutor.setdefault(sp, []).append(m)
    starter_tutor = label_location("TwoIsland_CapeBrink_House_EventScript_StarterTutor")
    tutor_loc = {m: starter_tutor for m in ("MOVE_FRENZY_PLANT", "MOVE_BLAST_BURN", "MOVE_HYDRO_CANNON")}
    for lab, body in labels_in(script_text["data/scripts/move_tutors.inc"]):
        t = re.search(r"setvar VAR_0x8005, MOVETUTOR_(\w+)", body)
        loc = label_location(lab)
        if t and loc:
            tutor_loc.setdefault("MOVE_" + t.group(1), loc)
    egg = {}
    for sp, body in re.findall(r"egg_moves\((\w+),(.*?)\)", read("src/data/pokemon/egg_moves.h"), re.S):
        egg["SPECIES_" + sp] = re.findall(r"MOVE_\w+", body)

    # evolutions
    ev = evos(read("src/data/pokemon/evolution.h"))
    old_ev = evos(vanilla("src/data/pokemon/evolution.h"))
    pre = {t: a for (a, t) in ev}
    def root(sp):
        while sp in pre:
            sp = pre[sp]
        return sp
    def evo_desc(meth, param):
        lv = param
        return {
            "EVO_LEVEL": f"Level {lv}",
            "EVO_ITEM": f"Use a {item(param)}",
            "EVO_TRADE": "Trade",
            "EVO_TRADE_ITEM": f"Trade holding {item(param)}",
            "EVO_FRIENDSHIP": "Level up with high friendship (220+)",
            "EVO_FRIENDSHIP_DAY": "Level up with high friendship during the day",
            "EVO_FRIENDSHIP_NIGHT": "Level up with high friendship at night",
            "EVO_LEVEL_ATK_GT_DEF": f"Level {lv} with Attack > Defense",
            "EVO_LEVEL_ATK_EQ_DEF": f"Level {lv} with Attack = Defense",
            "EVO_LEVEL_ATK_LT_DEF": f"Level {lv} with Attack < Defense",
            "EVO_LEVEL_SILCOON": f"Level {lv} (50% chance, set by personality)",
            "EVO_LEVEL_CASCOON": f"Level {lv} (50% chance, set by personality)",
            "EVO_LEVEL_NINJASK": f"Level {lv}",
            "EVO_LEVEL_SHEDINJA": f"Level {lv} as Nincada evolves, with an empty party slot and a spare Poké Ball",
            "EVO_BEAUTY": "Level up with high Beauty",
        }.get(meth, meth)

    # text data
    abil_names = {k: v for k, v in re.findall(r"\[(ABILITY_\w+)\] = _\(\"(.*?)\"\)", read("src/data/text/abilities.h"))}
    abil_desc_vars = dict(re.findall(r"static const u8 (s\w+Description)\[\] = _\(\"(.*?)\"\);", read("src/data/text/abilities.h")))
    abil_desc = {k: abil_desc_vars.get(v, "") for k, v in re.findall(r"\[(ABILITY_\w+)\] = (s\w+Description)", read("src/data/text/abilities.h"))}
    dex_entries = c_blocks(read("src/data/pokemon/pokedex_entries.h"), r"NATIONAL_DEX_\w+")
    dex_text = {n: " ".join(re.findall(r'"(.*?)"', b)).replace("\\n", " ").replace("  ", " ")
                for n, b in re.findall(r"const u8 (g\w+PokedexText)\[\] = (_\(.*?\));", firered_only(read("src/data/pokemon/pokedex_text_fr.h")), re.S)}
    def gametext(t):
        t = t.replace("POKéMON", "Pokémon").replace("POKé", "Poké")
        keep = {"DNA", "PP", "HP", "KO", "TV", "UFO"}
        return re.sub(r"\b([A-Z][A-Z'.-]+)\b",
                      lambda m: m.group(1) if len(m.group(1)) < 2 or m.group(1) in keep else m.group(1).title(), t)

    # type chart
    chart = {}
    for a, d, mul in re.findall(r"TYPE_(\w+), TYPE_(\w+), TYPE_MUL_(\w+)", read("src/battle_main.c").split("gTypeEffectiveness")[1].split("};")[0]):
        if a in ("FORESIGHT", "ENDTABLE"):
            continue
        chart[(a, d)] = {"NO_EFFECT": 0, "NOT_EFFECTIVE": 0.5, "SUPER_EFFECTIVE": 2, "NORMAL": 1}[mul]

    # where to find
    where = {}
    cur = fr_tables(json.loads(read("src/data/wild_encounters.json")))
    for k in sorted(cur, key=map_order):
        per = {}
        for method, rows in encounter_rows(cur[k]):
            for sp, (pct, lo, hi) in rows:
                lv = f"{lo}" if lo == hi else f"{lo}–{hi}"
                per.setdefault(sp, []).append(f"{method} Lv {lv} ({pct}%)")
        for sp, bits in per.items():
            where.setdefault(sp, []).append(f"**{map_name(k)}**: " + "; ".join(bits))
    hack_legends = set(re.findall(r"setwildbattle (SPECIES_\w+)", read("data/scripts/hack_legendaries.inc")))
    for loc, sp, lv, kind in special_encounters():
        lvs = "" if lv == "egg" else f", Lv {lv}"
        if kind == "Battle":
            kind = "one-time encounter"
            if sp in hack_legends:
                kind += " (appears after your first Hall of Fame entry)"
            elif loc.startswith("MAP_NAVEL_ROCK"):
                kind += " (Mystic Ticket, given at your first Hall of Fame entry)"
            elif loc.startswith("MAP_BIRTH_ISLAND"):
                kind += " (Aurora Ticket, given at your first Hall of Fame entry)"
        where.setdefault(sp, []).append(f"**{map_name(loc)}**: {kind}{lvs}")
    for loc, give, get, nick in ingame_trades():
        where.setdefault(get, []).append(f"**{map_name(loc) if loc else '?'}**: in-game trade for {mon(give)} (\"{nick}\")")

    changes = read("tools/hack/modernize_changes.txt").strip().split("\n") if os.path.exists("tools/hack/modernize_changes.txt") else []

    def slug(sp):
        return f"{dexno[sp]:03d}-" + sp.replace("SPECIES_", "").lower().replace("_", "-")
    def link(sp, here=True):
        return f"[{mon(sp)}]({slug(sp)}.md)" if here else f"[{mon(sp)}](pokedex/{slug(sp)}.md)"
    def types_of(i):
        t = re.findall(r"TYPE_\w+", i["types"])
        return list(dict.fromkeys(t))

    def stat_section(sp, title=None):
        i = info[sp]
        o = old_info.get(sp, {})
        out = []
        if title:
            out += [f"### {title}", ""]
        out += ["| Stat | Base | | Lv 50 | Lv 100 |", "|---|--:|---|--:|--:|"]
        total = 0
        for name, f in STATS:
            b = int(i[f])
            total += b
            hp = name == "HP"
            changed = f" *(was {o[f]})*" if o.get(f) and o[f] != i[f] else ""
            if sp == "SPECIES_SHEDINJA" and hp:
                r50 = r100 = "1"
            else:
                a, z = stat_range(b, 50, hp)
                r50 = f"{a}–{z}"
                a, z = stat_range(b, 100, hp)
                r100 = f"{a}–{z}"
            out.append(f"| {name} | **{b}**{changed} | `{bar(b)}` | {r50} | {r100} |")
        out += [f"| **Total** | **{total}** | | | |", "",
                ]
        return out, total

    def type_defense(ts):
        groups = {}
        for atk in TYPES:
            mul = 1
            for d in ts:
                mul *= chart.get((atk, d.replace("TYPE_", "")), 1)
            groups.setdefault(mul, []).append(atk.title())
        out = ["| Damage taken | Types |", "|---|---|"]
        for mul, label in ((4, "4×"), (2, "2×"), (0.5, "½×"), (0.25, "¼×"), (0, "0× (immune)")):
            if groups.get(mul):
                out.append(f"| {label} | {', '.join(groups[mul])} |")
        return out

    def family_lines(sp):
        r = root(sp)
        lines = []
        def walk(a, depth):
            kids = [(t, ev[(x, t)]) for (x, t) in ev if x == a]
            for t, (meth, param) in kids:
                was = ""
                if (a, t) in old_ev and old_ev[(a, t)] != (meth, param):
                    was = f" *(originally: {evo_desc(*old_ev[(a, t)])})*"
                elif (a, t) not in old_ev:
                    was = " *(new in this hack)*"
                cur_a = f"**{mon(a)}**" if a == sp else link(a)
                cur_t = f"**{mon(t)}**" if t == sp else link(t)
                lines.append(f"{'  ' * depth}- {cur_a} → {cur_t}: {evo_desc(meth, param)}{was}")
                walk(t, depth + 1)
        walk(r, 0)
        return lines or [f"{mon(sp)} does not evolve."]

    def gender(g):
        if g == "MON_GENDERLESS":
            return "Genderless"
        if g == "MON_MALE":
            return "100% male"
        if g == "MON_FEMALE":
            return "100% female"
        m = re.search(r"PERCENT_FEMALE\(([\d.]+)\)", g)
        f = float(m.group(1))
        return f"{100 - f:g}% male, {f:g}% female"

    os.makedirs(os.path.join(OUT, "pokedex"), exist_ok=True)
    index_rows = []
    for n, sp in enumerate(species):
        i = info[sp]
        ts = types_of(i)
        nav = []
        if n > 0:
            nav.append(f"← #{n:03d} {link(species[n - 1])}")
        nav.append("[Index](../POKEDEX.md)")
        if n + 1 < len(species):
            nav.append(f"{link(species[n + 1])} #{n + 2:03d} →")
        de = fields(dex_entries.get("NATIONAL_DEX_" + sp[8:], ""))
        cat = gametext(re.sub(r'_\("(.*)"\)', r"\1", de.get("categoryName", '_("?")')))
        h, w = int(de.get("height", 0)), int(de.get("weight", 0))
        inches = round(h * 3.937)
        out = [" · ".join(nav), "", f"# #{n + 1:03d} {mon(sp)}", "",
               f"*The {cat} Pokémon* — **{' / '.join(tname(t) for t in ts)}**", ""]
        txt = dex_text.get(de.get("description", ""), "")
        if txt:
            out += [f"> {gametext(txt)}", ""]
        out += [f"Height {h / 10:g} m ({inches // 12}′{inches % 12:02d}″) · Weight {w / 10:g} kg ({w * 0.220462:.1f} lbs)", ""]

        # abilities
        abil = [a for a in re.findall(r"ABILITY_\w+", i["abilities"]) if a != "ABILITY_NONE"]
        abil = list(dict.fromkeys(abil))
        out += ["## Abilities", ""]
        for a in abil:
            out.append(f"- **{gametext(abil_names.get(a, a[8:]))}**: {gametext(abil_desc.get(a, ''))}")
        if len(abil) == 2:
            out.append("")
            out.append("*Each individual has one of the two, set by its personality value.*")
        out.append("")

        # stats
        out += ["## Base stats", ""]
        if sp == "SPECIES_DEOXYS":
            for f, title in DEOXYS_FORMES:
                sec, total = stat_section(f, title)
                out += sec
            out += ["Use the **Meteorite** (key item) on Deoxys to cycle Normal → Attack → Defense → Speed.", ""]
        else:
            sec, total = stat_section(sp)
            out += sec
        out += ["*Ranges: the minimum uses 0 IVs, 0 EVs and a hindering nature; the maximum uses 31 IVs, "
                "252 EVs and a helpful nature. HP is not affected by nature.*", ""]
        index_rows.append((n + 1, sp, ts, [int(i[f]) for _, f in STATS], total))

        # type defenses
        out += ["## Type defenses", ""] + type_defense(ts) + [""]
        notes = {"ABILITY_LEVITATE": "immune to Ground moves", "ABILITY_FLASH_FIRE": "immune to Fire moves",
                 "ABILITY_VOLT_ABSORB": "Electric moves heal it instead", "ABILITY_WATER_ABSORB": "Water moves heal it instead",
                 "ABILITY_THICK_FAT": "Fire and Ice moves do half damage",
                 "ABILITY_WONDER_GUARD": "only super-effective moves can hit it"}
        for a in abil:
            if a in notes:
                who = "With" if len(abil) > 1 else "Its ability"
                out += [f"*{who} {gametext(abil_names[a])}: {notes[a]}.*", ""]

        # training / breeding
        evy = ", ".join(f"{i[f]} {name}" for name, f in EV_FIELDS if i.get(f, "0") != "0") or "None"
        held = []
        if i.get("itemCommon", "ITEM_NONE") != "ITEM_NONE":
            held.append(f"{item(i['itemCommon'])} (50%)")
        if i.get("itemRare", "ITEM_NONE") != "ITEM_NONE":
            held.append(f"{item(i['itemRare'])} (5%)")
        if held and i.get("itemCommon") == i.get("itemRare"):
            held = [f"{item(i['itemCommon'])} (100%)"]
        gname, gexp = GROWTH.get(i["growthRate"], (i["growthRate"], 0))
        eggs = list(dict.fromkeys(EGG_GROUPS.get(g, g) for g in re.findall(r"EGG_GROUP_(\w+)", i["eggGroups"])))
        cyc = int(i["eggCycles"])
        out += ["## Training and breeding", "", "| | |", "|---|---|",
                f"| Catch rate | {i['catchRate']} |",
                f"| Base Exp. yield | {i['expYield']} |",
                f"| EV yield | {evy} |",
                f"| Held items (wild) | {', '.join(held) if held else 'None'} |",
                f"| Base friendship | {i['friendship']} |",
                f"| Growth rate | {gname} ({gexp:,} Exp. to Lv 100) |",
                f"| Gender | {gender(i['genderRatio'])} |",
                f"| Egg groups | {', '.join(eggs)} |",
                f"| Hatch time | {cyc} egg cycles ({cyc * 256:,} steps) |", ""]

        # evolution
        out += ["## Evolution", ""] + family_lines(sp) + [""]

        # where
        out += ["## Where to find it", ""]
        places = where.get(sp, [])
        if sp in pre:
            places = places + [f"Evolve {link(pre[sp])}"]
        if root(sp) == sp and "UNDISCOVERED" not in info[sp]["eggGroups"] and sp != "SPECIES_DITTO":
            fam = [sp] + [t for (x, t) in ev if root(x) == sp]
            fam = [f for f in dict.fromkeys(fam) if "UNDISCOVERED" not in info[f]["eggGroups"]]
            parents = " or ".join(mon(f) for f in fam)
            places.append(f"Breeding: hatches from an Egg left by a {parents} at the Four Island Day Care")
        babies = {"SPECIES_PICHU", "SPECIES_CLEFFA", "SPECIES_IGGLYBUFF", "SPECIES_TOGEPI", "SPECIES_TYROGUE",
                  "SPECIES_SMOOCHUM", "SPECIES_ELEKID", "SPECIES_MAGBY", "SPECIES_AZURILL", "SPECIES_WYNAUT"}
        if sp in babies:
            kids = [t for (x, t) in ev if x == sp]
            need = {"SPECIES_AZURILL": " holding a Sea Incense", "SPECIES_WYNAUT": " holding a Lax Incense"}.get(sp, "")
            places = [p for p in places if not p.startswith("Breeding")]
            places.append(f"Breeding: hatches from an Egg left by a {' or '.join(link(k) for k in kids)}{need} "
                          "at the Four Island Day Care")
        lines = [f"- {p}" for p in places]
        if len(lines) > 12:
            out += [f"<details><summary>{len(lines)} places (click to expand)</summary>", ""] + lines + ["", "</details>"]
        else:
            out += lines
        out.append("")

        # moves
        def lu_rows(s):
            rows = levelup(s)
            oldmoves = {m for _, m in levelup(s, old_arrays, old_ptr)}
            res = ["| Lv | Move | Type | Cat. | Power | Acc. | PP |", "|--:|---|---|---|--:|--:|--:|"]
            for lv, m in rows:
                star = " ★" if m not in oldmoves else ""
                res.append(f"| {lv if lv > 1 else '1'} | " + move_cells(m).replace(" | ", star + " | ", 1) + " |")
            return res
        out += ["## Moves", "", "★ = not learned this way in the original FireRed. After you become Champion, the "
                "Move Maniac on Two Island can teach every move on this page (any level, egg, TM/HM, tutor).", "",
                "### By level up", ""]
        out += lu_rows(sp) + [""]
        if sp == "SPECIES_DEOXYS":
            out += ["All four formes share this learnset.", ""]

        tms = tmhm.get(sp, [])
        if tms:
            out += ["### By TM/HM", "", "| TM | Move | Type | Cat. | Power | Acc. | PP |", "|---|---|---|---|--:|--:|--:|"]
            for t in sorted(tms, key=lambda t: (t[:2] == "HM", t)):
                mname = "MOVE_" + tm_moves.get("ITEM_" + t, "?")
                out.append(f"| {t} | {move_cells(mname)} |")
            out.append("")
        tut = tutor.get(sp, [])
        if tut:
            out += ["### By move tutor", "", "| Move | Type | Cat. | Power | Acc. | PP | Tutor |", "|---|---|---|--:|--:|--:|---|"]
            for m in tut:
                loc = tutor_loc.get(m)
                out.append(f"| {move_cells(m)} | {map_name(loc) if loc else '?'} |")
            out.append("")
        eb = root(sp)
        em = egg.get(eb, [])
        if em:
            via = "" if eb == sp else f" (passed down to {mon(eb)}, which then evolves)"
            out += ["### By breeding (egg moves)", "",
                    f"Breed a {mon(eb)}{via} with a father that knows the move.", "",
                    "| Move | Type | Cat. | Power | Acc. | PP |", "|---|---|---|--:|--:|--:|"]
            out += [f"| {move_cells(m)} |" for m in em] + [""]

        out += ["---", "", " · ".join(nav), ""]
        open(os.path.join(OUT, "pokedex", slug(sp) + ".md"), "w").write("\n".join(out))

    idx = ["# Pokédex", "", "All 386 Pokémon in National Dex order, with this hack's stats. Click a name for its full "
           "page: stat ranges, abilities, type defenses, evolution, where to find it and every learnset.", "",
           "| # | Pokémon | Type | HP | Atk | Def | SpA | SpD | Spe | Total |",
           "|--:|---|---|--:|--:|--:|--:|--:|--:|--:|"]
    for no, sp, ts, st, total in index_rows:
        idx.append(f"| {no:03d} | {link(sp, here=False)} | {' / '.join(tname(t) for t in ts)} | "
                   + " | ".join(str(x) for x in st) + f" | {total} |")
    idx.append("")
    open(os.path.join(OUT, "POKEDEX.md"), "w").write("\n".join(idx))


def write_index():
    open(os.path.join(OUT, "README.md"), "w").write("""# FireRed QoL + Hard: spoiler guide

**Spoilers ahead.** Generated from the game's data, so it matches the patched ROM.

- [Wild encounters](ENCOUNTERS.md): every map's grass, cave, surf, Rock Smash and fishing tables, with rates and levels. ★ marks additions.
- [Items](ITEMS.md): item balls, hidden items, NPC gifts and shop stock, by location.
- [Trainers](TRAINERS.md): Gym Leaders, Elite Four and Champion (rounds 1–2 and peak) in full, then every other trainer by location.
- [Pokédex](POKEDEX.md): all 386 Pokémon with stat ranges, abilities, type defenses, evolutions, locations and full learnsets.
- [Pokémon](POKEMON.md): gift, static and legendary Pokémon, in-game trades, changed evolutions, base stat and move changes.

Regenerate with `python3 tools/hack/spoiler_guide.py <output dir>` from the source tree.
""")


os.makedirs(OUT, exist_ok=True)
write_encounters()
write_items()
write_trainers()
write_pokemon()
write_pokedex()
write_index()
print("guide written to", OUT)
