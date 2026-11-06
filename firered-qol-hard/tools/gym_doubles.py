#!/usr/bin/env python3
"""Gym double battles.

Turns one trainer in each gym from Misty's on into a double battle (no Gym
Leaders, and not Cinnabar, whose quiz battles have no double version). Their
teams get doubles movesets: spread moves that only hit foes (never Earthquake
or Self-Destruct-style moves that would hit their own partner), plus support
like Protect, Fake Out, screens and speed control.

Runs once against the hack's data; refuses to run twice. Every move is checked
against what the species can learn in this hack.
"""
import glob, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from learnsets import learnable, move_ids, read  # noqa: E402  (also chdirs to the repo root)

TEAMS = {
    # Cerulean (Misty): rain-free water pair with Twister and Swift.
    "TRAINER_SWIMMER_MALE_LUIS": [
        ("HORSEA", 18, ["TWISTER", "WATER_GUN", "SMOKESCREEN", "PROTECT"]),
        ("SHELLDER", 18, ["WATER_GUN", "PROTECT", "SCREECH", "TACKLE"]),
        ("STARYU", 18, ["SWIFT", "WATER_GUN", "RECOVER", "PROTECT"]),
    ],
    # Vermilion (Lt. Surge): Electroweb speed control and paralysis.
    "TRAINER_ENGINEER_BAILY": [
        ("VOLTORB", 24, ["ELECTROWEB", "SWIFT", "SCREECH", "PROTECT"]),
        ("MAGNEMITE", 24, ["ELECTROWEB", "THUNDER_WAVE", "SUPERSONIC", "PROTECT"]),
        ("PIKACHU", 24, ["NUZZLE", "ELECTROWEB", "QUICK_ATTACK", "PROTECT"]),
    ],
    # Celadon (Erika): spore support and spread Acid / Razor Leaf.
    "TRAINER_BEAUTY_BRIDGET": [
        ("ODDISH", 24, ["ACID", "STUN_SPORE", "MEGA_DRAIN", "SWEET_SCENT"]),
        ("BELLSPROUT", 24, ["RAZOR_LEAF", "SLEEP_POWDER", "ACID", "PROTECT"]),
        ("GLOOM", 25, ["ACID", "SLEEP_POWDER", "MEGA_DRAIN", "PROTECT"]),
        ("WEEPINBELL", 25, ["RAZOR_LEAF", "STUN_SPORE", "ACID", "PROTECT"]),
    ],
    # Fuchsia (Koga): Glare and Snarl support for a Rock Slide Sandslash.
    "TRAINER_TAMER_EDGAR": [
        ("ARBOK", 38, ["GLARE", "SNARL", "POISON_FANG", "PROTECT"]),
        ("SANDSLASH", 38, ["ROCK_SLIDE", "SLASH", "SANDSTORM", "PROTECT"]),
        ("ARBOK", 38, ["ACID", "BITE", "SCREECH", "PROTECT"]),
    ],
    # Saffron (Sabrina): Fake Out, screens and Trick Room.
    "TRAINER_PSYCHIC_JOHAN": [
        ("MR_MIME", 36, ["FAKE_OUT", "LIGHT_SCREEN", "PSYBEAM", "ENCORE"]),
        ("KADABRA", 36, ["PSYBEAM", "DAZZLING_GLEAM", "REFLECT", "RECOVER"]),
        ("SLOWPOKE", 36, ["SURF", "CONFUSION", "TRICK_ROOM", "PROTECT"]),
        ("KADABRA", 36, ["PSYCHIC", "DAZZLING_GLEAM", "CALM_MIND", "PROTECT"]),
    ],
    # Viridian (Giovanni): Rock Slide spam with Helping Hand.
    "TRAINER_COOLTRAINER_SAMUEL": [
        ("SANDSLASH", 43, ["ROCK_SLIDE", "SLASH", "SWORDS_DANCE", "PROTECT"]),
        ("RHYHORN", 44, ["ROCK_SLIDE", "HORN_ATTACK", "SANDSTORM", "PROTECT"]),
        ("NIDORINO", 45, ["HELPING_HAND", "POISON_JAB", "HORN_ATTACK", "PROTECT"]),
        ("SANDSLASH", 43, ["ROCK_SLIDE", "CRUSH_CLAW", "SANDSTORM", "PROTECT"]),
        ("NIDOKING", 45, ["ROCK_SLIDE", "POISON_JAB", "SURF", "PROTECT"]),
    ],
}
NOT_ENOUGH = "Hack_Text_GymDoubleNotEnough"


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


tr = read("src/data/trainers.h")
if "FireRed QoL+Hard: gym double battle" in tr or "FireRed QoL+Hard: gym double battle" in read("src/data/trainer_parties.h"):
    sys.exit("Gym doubles are already in place.")
tp = read("src/data/trainer_parties.h")
bad = False
for t, team in TEAMS.items():
    entry = re.search(r"(    \[" + t + r"\] = \{\n)(.*?)(\n    \},\n)", tr, re.S)
    party = re.search(r"\.party = \w+\((sParty_\w+)\)", entry.group(2)).group(1)
    for sp, _, moves in team:
        can = learnable("SPECIES_" + sp)
        for m in moves:
            if "MOVE_" + m not in move_ids:
                sys.exit(f"{t} {sp}: unknown move {m}")
            if "MOVE_" + m not in can:
                print(f"warning: {t} {sp} can't normally learn {m}")
                bad = True
    mons = ",\n".join(
        f"    {{\n        .iv = 150,\n        .lvl = {lv},\n        .species = SPECIES_{sp},\n"
        f"        .moves = {{{', '.join('MOVE_' + m for m in moves)}}},\n    }}"
        for sp, lv, moves in team)
    tp = re.sub(r"static const struct \w+ " + party + r"\[\] = \{\n.*?\n\};\n",
                lambda _: f"// FireRed QoL+Hard: gym double battle\nstatic const struct TrainerMonNoItemCustomMoves {party}[] = {{\n{mons},\n}};\n",
                tp, count=1, flags=re.S)
    body = entry.group(2)
    body = re.sub(r"\.doubleBattle = FALSE", ".doubleBattle = TRUE", body)
    body = re.sub(r"\.party = \w+\(" + party + r"\)", f".party = NO_ITEM_CUSTOM_MOVES({party})", body)
    tr = tr[:entry.start()] + entry.group(1).replace("] = {\n", "] = { // FireRed QoL+Hard: gym double battle\n") + body + entry.group(3) + tr[entry.end():]
if bad:
    sys.exit("Fix the movesets above first.")

for f in glob.glob("data/maps/*_Gym/scripts.inc"):
    sc = read(f)
    new = sc
    for t in TEAMS:
        new = re.sub(r"trainerbattle_single " + t + r", (\w+), (\w+)\n",
                     lambda m: f"trainerbattle_double {t}, {m.group(1)}, {m.group(2)}, {NOT_ENOUGH}\n", new)
    if new != sc:
        write(f, new)
write("src/data/trainers.h", tr)
write("src/data/trainer_parties.h", tp)
print(f"{len(TEAMS)} gym trainers now fight double battles.")
