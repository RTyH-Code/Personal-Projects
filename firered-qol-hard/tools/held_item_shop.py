#!/usr/bin/env python3
"""Post-game held items: the Trainer Tower lobby shop (Seven Island, which you
can only reach after the Elite Four) also sells the held items competitive
teams use, so you can build teams for the Trainer Tower and the peak trainers.
Prices are set to match (most were placeholder values). Runs once.
"""
import json, os, sys

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

PRICES = {
    "LEFTOVERS": 10000, "CHOICE_BAND": 10000, "LUCKY_EGG": 10000,
    "SHELL_BELL": 8000, "FOCUS_BAND": 8000,
    "QUICK_CLAW": 6000, "SCOPE_LENS": 6000, "BRIGHT_POWDER": 6000,
    "KINGS_ROCK": 3000, "METAL_COAT": 3000,
    "CHARCOAL": 3000, "MYSTIC_WATER": 3000, "MAGNET": 3000, "MIRACLE_SEED": 3000, "NEVER_MELT_ICE": 3000,
    "BLACK_BELT": 3000, "POISON_BARB": 3000, "SOFT_SAND": 3000, "SHARP_BEAK": 3000, "TWISTED_SPOON": 3000,
    "SILVER_POWDER": 3000, "HARD_STONE": 3000, "SPELL_TAG": 3000, "DRAGON_FANG": 3000, "BLACK_GLASSES": 3000,
    "SILK_SCARF": 3000,
}
ORDER = ["LEFTOVERS", "CHOICE_BAND", "SHELL_BELL", "FOCUS_BAND", "QUICK_CLAW", "SCOPE_LENS", "BRIGHT_POWDER",
         "KINGS_ROCK", "LUCKY_EGG", "SILK_SCARF", "CHARCOAL", "MYSTIC_WATER", "MAGNET", "MIRACLE_SEED",
         "NEVER_MELT_ICE", "BLACK_BELT", "POISON_BARB", "SOFT_SAND", "SHARP_BEAK", "TWISTED_SPOON",
         "SILVER_POWDER", "HARD_STONE", "SPELL_TAG", "DRAGON_FANG", "BLACK_GLASSES", "METAL_COAT"]
P = "data/maps/TrainerTower_Lobby/scripts.inc"
s = open(P, encoding="utf-8").read()
if "ITEM_LEFTOVERS" in s:
    sys.exit("The held items are already on sale.")
old = "\t.2byte ITEM_MAX_REPEL\n\t.2byte ITEM_NONE\n"
assert old in s
s = s.replace(old, "\t.2byte ITEM_MAX_REPEL\n" + "".join(f"\t.2byte ITEM_{i}\n" for i in ORDER) + "\t.2byte ITEM_NONE\n", 1)
open(P, "w", encoding="utf-8").write(s)

raw = open("src/data/items.json", encoding="utf-8").read()
d = json.loads(raw)
for it in d["items"]:
    name = it["itemId"][len("ITEM_"):]
    if name in PRICES:
        it["price"] = PRICES[name]
open("src/data/items.json", "w", encoding="utf-8").write(json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
print(f"{len(ORDER)} held items added to the Trainer Tower lobby shop.")
