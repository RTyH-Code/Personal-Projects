#!/usr/bin/env python3
"""Berry shop: a clerk at the Celadon Department Store 2F counter sells berries.

FireRed has no berry growing, so this makes battle berries reliable to get.
The stock grows with your progress:
  always             status-curing berries, Oran and Leppa
  after Erika        Sitrus, Lum and the confusion-healing berries
  after the Champion pinch berries, Lansat, Starf and the EV-lowering berries
Prices are raised from 20 (each still sells back for half). Runs once.
"""
import json, os, sys

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

TIERS = [
    ("CHERI", "CHESTO", "PECHA", "RAWST", "ASPEAR", "PERSIM", "ORAN", "LEPPA"),
    ("SITRUS", "LUM", "FIGY", "WIKI", "MAGO", "AGUAV", "IAPAPA"),
    ("LIECHI", "GANLON", "SALAC", "PETAYA", "APICOT", "LANSAT", "STARF",
     "POMEG", "KELPSY", "QUALOT", "HONDEW", "GREPA", "TAMATO"),
]
PRICES = {"CHERI": 200, "CHESTO": 200, "PECHA": 200, "RAWST": 200, "ASPEAR": 200, "PERSIM": 200,
          "ORAN": 100, "LEPPA": 400, "SITRUS": 1200, "LUM": 1500,
          "FIGY": 600, "WIKI": 600, "MAGO": 600, "AGUAV": 600, "IAPAPA": 600,
          "LIECHI": 3000, "GANLON": 3000, "SALAC": 3000, "PETAYA": 3000, "APICOT": 3000,
          "LANSAT": 5000, "STARF": 5000,
          "POMEG": 300, "KELPSY": 300, "QUALOT": 300, "HONDEW": 300, "GREPA": 300, "TAMATO": 300}
MAP = "data/maps/CeladonCity_DepartmentStore_2F"
LABEL = "CeladonCity_DepartmentStore_2F_EventScript_ClerkBerries"


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


scripts = read(MAP + "/scripts.inc")
if LABEL in scripts:
    sys.exit("The berry shop is already in place.")

# Prices
raw = read("src/data/items.json")
items = json.loads(raw)
for it in items["items"]:
    name = it["itemId"][len("ITEM_"):-len("_BERRY")] if it["itemId"].endswith("_BERRY") else None
    if name in PRICES:
        it["price"] = PRICES[name]
write("src/data/items.json", json.dumps(items, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))

# The clerk, between the two existing ones behind the left counter
m = json.loads(read(MAP + "/map.json"))
m["object_events"].append({
    "type": "object", "graphics_id": "OBJ_EVENT_GFX_CLERK", "x": 1, "y": 7, "elevation": 3,
    "movement_type": "MOVEMENT_TYPE_FACE_RIGHT", "movement_range_x": 1, "movement_range_y": 1,
    "trainer_type": "TRAINER_TYPE_NONE", "trainer_sight_or_berry_tree_id": "0", "script": LABEL, "flag": "0"})
write(MAP + "/map.json", json.dumps(m, indent=2, ensure_ascii=False) + "\n")


def mart(label, berries):
    return f"\t.align 2\n{label}::\n" + "".join(f"\t.2byte ITEM_{b}_BERRY\n" for b in berries) + "\t.2byte ITEM_NONE\n\trelease\n\tend\n"


prefix = "CeladonCity_DepartmentStore_2F_Berries"
scripts += f"""
@ FireRed QoL+Hard: berry shop (tools/hack/berry_shop.py)
{LABEL}::
\tgoto_if_questlog EventScript_ReleaseEnd
\tlock
\tfaceplayer
\tmessage CeladonCity_DepartmentStore_2F_Text_HackBerryClerk
\twaitmessage
\tgoto_if_set FLAG_SYS_GAME_CLEAR, {LABEL}All
\tgoto_if_set FLAG_BADGE04_GET, {LABEL}Mid
\tpokemart {prefix}Basic
\tgoto {LABEL}End

{LABEL}Mid::
\tpokemart {prefix}Mid
\tgoto {LABEL}End

{LABEL}All::
\tpokemart {prefix}All
{LABEL}End::
\tmsgbox Text_PleaseComeAgain
\trelease
\tend

""" + mart(prefix + "Basic", TIERS[0]) + "\n" + mart(prefix + "Mid", TIERS[0] + TIERS[1]) + "\n" + mart(prefix + "All", TIERS[0] + TIERS[1] + TIERS[2])
write(MAP + "/scripts.inc", scripts)
text = read(MAP + "/text.inc") + """
CeladonCity_DepartmentStore_2F_Text_HackBerryClerk::
    .string "Welcome to the BERRY STAND!\\n"
    .string "Fresh from the SEVII ISLANDS.$"
"""
write(MAP + "/text.inc", text)
print("Berry shop added.")
