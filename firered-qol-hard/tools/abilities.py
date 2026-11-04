#!/usr/bin/env python3
"""Modern abilities for FireRed QoL+Hard.

* Every Pokemon gets up to three ability slots (two regular + hidden), as in
  modern games. The hidden slot is stored in a spare ribbon bit, so saves are
  unaffected.
* Adds the 75 abilities later generations gave Gen 1-3 Pokemon (names and
  descriptions). Their battle effects live in the C code.
* Pokemon only get a modern ability once its effect is implemented (the
  IMPLEMENTED list below grows batch by batch); until then the slot keeps the
  Gen 3 ability.

    python3 tools/hack/abilities.py <pokemon-showdown>/data            first run
    python3 tools/hack/abilities.py <pokemon-showdown>/data --species  re-assign species only
Showdown's data files are read as text, never run.
"""
import re
import subprocess
import sys

SD = sys.argv[1]
SPECIES_ONLY = "--species" in sys.argv

# name in game (max 12 chars), description (one short line, Gen 3 style)
NEW = [
    ("Sheer Force", "SHEER FORCE", "Drops added effects for power."),
    ("Unnerve", "UNNERVE", "Foes can't eat BERRIES."),
    ("Gluttony", "GLUTTONY", "Eats pinch BERRIES early."),
    ("Sniper", "SNIPER", "Powers up critical hits."),
    ("Hydration", "HYDRATION", "Heals status in rain."),
    ("Frisk", "FRISK", "Checks the foe's item."),
    ("Rattled", "RATTLED", "Bug, Ghost, Dark hits up SPEED."),
    ("Quick Feet", "QUICK FEET", "Ups SPEED if suffering."),
    ("Infiltrator", "INFILTRATOR", "Passes through barriers."),
    ("Technician", "TECHNICIAN", "Powers up weak moves."),
    ("Ice Body", "ICE BODY", "Slight HP recovery in hail."),
    ("Weak Armor", "WEAK ARMOR", "Hits lower DEF, raise SPEED."),
    ("Leaf Guard", "LEAF GUARD", "Prevents status in sunlight."),
    ("Rivalry", "RIVALRY", "Strong vs. the same gender."),
    ("Telepathy", "TELEPATHY", "Dodges allies' attacks."),
    ("Solar Power", "SOLAR POWER", "Ups SP. ATK in sun, hurts."),
    ("Tinted Lens", "TINTED LENS", "Ups not very effective hits."),
    ("Tangled Feet", "TANGLED FEET", "Ups evasion if confused."),
    ("Magic Guard", "MAGIC GUARD", "Only hurt by attacks."),
    ("Steadfast", "STEADFAST", "Flinching raises SPEED."),
    ("Regenerator", "REGENERATOR", "Heals when switched out."),
    ("Analytic", "ANALYTIC", "Ups power when moving last."),
    ("Scrappy", "SCRAPPY", "Hits GHOST-type POKéMON."),
    ("Sap Sipper", "SAP SIPPER", "GRASS moves raise ATTACK."),
    ("Overcoat", "OVERCOAT", "Blocks weather and powder."),
    ("Moxie", "MOXIE", "KOs raise ATTACK."),
    ("Light Metal", "LIGHT METAL", "Halves its weight."),
    ("Moody", "MOODY", "Stats change every turn."),
    ("Friend Guard", "FRIEND GUARD", "Reduces damage to allies."),
    ("Competitive", "COMPETITIVE", "Stat drops sharply up SP. ATK."),
    ("Anger Point", "ANGER POINT", "Critical hits max ATTACK."),
    ("Forewarn", "FOREWARN", "Senses the foe's best move."),
    ("Unburden", "UNBURDEN", "Using an item ups SPEED."),
    ("Adaptability", "ADAPTABILITY", "Powers up same-type moves."),
    ("Super Luck", "SUPER LUCK", "Ups critical-hit ratio."),
    ("Prankster", "PRANKSTER", "Status moves go first."),
    ("Pickpocket", "PICKPOCKET", "Steals items on contact."),
    ("Big Pecks", "BIG PECKS", "Prevents DEFENSE loss."),
    ("Unaware", "UNAWARE", "Ignores stat changes."),
    ("Dry Skin", "DRY SKIN", "Water heals, fire and sun hurt."),
    ("Wonder Skin", "WONDER SKIN", "Evades status moves."),
    ("Sand Force", "SAND FORCE", "Powers up moves in sand."),
    ("Defiant", "DEFIANT", "Stat drops sharply up ATTACK."),
    ("Justified", "JUSTIFIED", "DARK hits raise ATTACK."),
    ("No Guard", "NO GUARD", "All moves always hit."),
    ("Skill Link", "SKILL LINK", "Multi-hit moves hit 5 times."),
    ("Cursed Body", "CURSED BODY", "May disable a move."),
    ("Harvest", "HARVEST", "May restore a used BERRY."),
    ("Reckless", "RECKLESS", "Powers up recoil moves."),
    ("Healer", "HEALER", "May heal an ally's status."),
    ("Anticipation", "ANTICIPATION", "Senses dangerous moves."),
    ("Snow Cloak", "SNOW CLOAK", "Ups evasion in hail."),
    ("Magic Bounce", "MAGIC BOUNCE", "Reflects status moves."),
    ("Heavy Metal", "HEAVY METAL", "Doubles its weight."),
    ("Sand Rush", "SAND RUSH", "Ups SPEED in a sandstorm."),
    ("Poison Touch", "POISON TOUCH", "May poison on contact."),
    ("Aftermath", "AFTERMATH", "Hurts the foe when fainting."),
    ("Iron Fist", "IRON FIST", "Powers up punches."),
    ("Neutralizing Gas", "NEUTRAL. GAS", "Neutralizes abilities."),
    ("Download", "DOWNLOAD", "Adjusts power to the foe."),
    ("Multiscale", "MULTISCALE", "Halves damage at full HP."),
    ("Contrary", "CONTRARY", "Inverts stat changes."),
    ("Poison Heal", "POISON HEAL", "Poison restores HP."),
    ("Normalize", "NORMALIZE", "All moves become NORMAL."),
    ("Storm Drain", "STORM DRAIN", "WATER moves raise SP. ATK."),
    ("Filter", "FILTER", "Weakens super effective hits."),
    ("Mold Breaker", "MOLD BREAKER", "Ignores the foe's ability."),
    ("Imposter", "IMPOSTER", "Transforms into the foe."),
    ("Honey Gather", "HONEY GATHER", "May gather HONEY."),
    ("Wind Rider", "WIND RIDER", "Wind moves raise ATTACK."),
    ("Stall", "STALL", "Moves after the foe."),
    ("Simple", "SIMPLE", "Doubles stat changes."),
    ("Solid Rock", "SOLID ROCK", "Weakens super effective hits."),
    ("Toxic Boost", "TOXIC BOOST", "Ups ATTACK when poisoned."),
    ("Protean", "PROTEAN", "Changes type to its move."),
]

# Abilities whose battle effects exist.
IMPLEMENTED = {
    "Adaptability", "Technician", "Iron Fist", "Reckless", "Sheer Force", "Toxic Boost", "Solar Power",
    "Rivalry", "Sand Force", "Analytic", "Normalize", "Heavy Metal", "Light Metal", "Unaware", "Multiscale",
    "Filter", "Solid Rock", "Tinted Lens", "Scrappy", "Sniper", "Super Luck", "Skill Link", "No Guard",
    "Wonder Skin", "Tangled Feet", "Snow Cloak", "Sand Rush", "Quick Feet", "Stall", "Big Pecks", "Simple",
    "Contrary", "Overcoat", "Ice Body", "Hydration", "Poison Heal", "Dry Skin", "Magic Guard", "Gluttony",
    "Friend Guard", "Telepathy",
    # batch 2
    "Moxie", "Defiant", "Competitive", "Justified", "Rattled", "Steadfast", "Weak Armor", "Anger Point",
    "Sap Sipper", "Storm Drain", "Wind Rider", "Cursed Body", "Poison Touch", "Aftermath", "Regenerator",
    "Download", "Frisk", "Unnerve", "Moody", "Healer",
}


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


def edit(p, old, new):
    s = read(p)
    assert old in s, (p, old)
    write(p, s.replace(old, new, 1))


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def const(name):
    return "ABILITY_" + re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def ts_entries(path):
    key, body = None, []
    for line in open(path, encoding="utf-8"):
        m = re.match(r'^\t"?(\w+)"?: \{$', line.rstrip("\n"))
        if m:
            key, body = m.group(1), []
        elif line.startswith("\t},") and key:
            yield key, "\n".join(body)
            key = None
        elif key:
            body.append(line.rstrip("\n"))


# ---------------------------------------------------------------- definitions
if not SPECIES_ONLY:
    p = "include/constants/abilities.h"
    s = read(p)
    m = re.search(r"#define ABILITIES_COUNT (\d+)", s)
    first = int(m.group(1))
    defs = "".join(f"#define {const(n):<26} {first + i}\n" for i, (n, *_) in enumerate(NEW))
    s = s.replace(m.group(0), "// FireRed QoL+Hard: modern abilities (tools/hack/abilities.py)\n" + defs
                  + "\n#define ABILITIES_COUNT %d" % (first + len(NEW)))
    write(p, s)

    p = "src/data/text/abilities.h"
    s = read(p)
    descs = "".join(f'static const u8 sHack{const(n)[8:].title().replace("_", "")}Description[] = _("{d}");\n'
                    for n, _, d in NEW)
    s = s.replace("const u8 *const gAbilityDescriptionPointers[ABILITIES_COUNT] =", descs + "\nconst u8 *const gAbilityDescriptionPointers[ABILITIES_COUNT] =", 1)
    ptr_end = s.index("};", s.index("gAbilityDescriptionPointers"))
    s = s[:ptr_end].rstrip().rstrip(",") + ",\n" + "".join(
        f'    [{const(n)}] = sHack{const(n)[8:].title().replace("_", "")}Description,\n' for n, *_ in NEW) + s[ptr_end:]
    name_end = s.index("};", s.index("gAbilityNames"))
    s = s[:name_end].rstrip().rstrip(",") + ",\n" + "".join(f'    [{const(n)}] = _("{g}"),\n' for n, g, _ in NEW) + s[name_end:]
    write(p, s)
    assert all(len(g) <= 12 for _, g, _ in NEW)

    # Three ability slots per species; the hidden one is flagged in a spare ribbon bit.
    edit("include/pokemon.h", "u8 abilities[2];", "u8 abilities[3]; // regular, regular, hidden")
    edit("include/pokemon.h", "u32 unusedRibbons:4;            // Discarded in Gen 4.",
         "u32 unusedRibbons:3;            // Discarded in Gen 4.\n /* 0x0B */ u32 hiddenAbility:1;            // FireRed QoL+Hard: uses the hidden ability slot")

# ---------------------------------------------------------------- species
known = {norm(c[8:]): c for c in re.findall(r"#define (ABILITY_\w+)\s+\d+", read("include/constants/abilities.h"))}
new_names = {norm(n): n for n, *_ in NEW}


def usable(name):
    k = norm(name)
    if k not in known:
        return None
    if k in new_names and new_names[k] not in IMPLEMENTED:
        return None
    return known[k]


modern = {}
for key, t in ts_entries(SD + "/pokedex.ts"):
    m = re.search(r"num: (\d+)", t)
    if not m or not 1 <= int(m.group(1)) <= 386:
        continue
    if "forme:" in t and not key.startswith("deoxys"):
        continue
    modern[key] = dict(re.findall(r'(0|1|H): "(.*?)"', re.search(r"abilities: \{(.*?)\}", t).group(1)))

vanilla = subprocess.run(["git", "show", "ce6406d:src/data/pokemon/species_info.h"], capture_output=True, text=True).stdout
old = {sp: re.findall(r"ABILITY_\w+", b) for sp, b in re.findall(r"\[(SPECIES_\w+)\] =\n    \{.*?\.abilities = \{(.*?)\}", vanilla, re.S)}

p = "src/data/pokemon/species_info.h"
s = read(p)
changed = 0
for sp in re.findall(r"\[(SPECIES_\w+)\] =\n    \{", s):
    key = norm(sp[8:])
    if key not in modern:
        continue
    ab = modern[key]
    regular = [c for c in (usable(ab.get("0", "")), usable(ab.get("1", ""))) if c]
    if not regular:
        regular = [a for a in old.get(sp, []) if a != "ABILITY_NONE"][:2] or ["ABILITY_NONE"]
    regular = list(dict.fromkeys(regular))
    hidden = usable(ab.get("H", "")) or "ABILITY_NONE"
    if hidden in regular:
        hidden = "ABILITY_NONE"
    slots = (regular + ["ABILITY_NONE"])[:2] + [hidden]
    new_line = "{%s}" % ", ".join(slots)
    s2, n = re.subn(r"(\[%s\] =\n    \{.*?\.abilities = )\{[^}]*\}" % sp, r"\g<1>" + new_line, s, count=1, flags=re.S)
    if s2 != s:
        changed += 1
    s = s2
write(p, s)
print(f"{len(NEW)} abilities defined; {changed} species updated ({len(IMPLEMENTED)} new abilities in use)")
