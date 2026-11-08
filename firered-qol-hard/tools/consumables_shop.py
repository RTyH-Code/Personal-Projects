#!/usr/bin/env python3
"""Battle consumables you couldn't restock: add them to Celadon's shops.

Run after berry_shop.py. Runs once.
  Berry stand (2F)  from the start:  Energy Powder, Heal Powder
                    after Erika:     Energy Root, Revival Herb, White Herb, Mental Herb
  X items (5F)      after Erika:     Ether, Elixir
                    after Champion:  Max Ether, Max Elixir, Max Revive
White and Mental Herb now cost 2,000 (they were 100).
"""
import json, os, re, sys

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def read(p):
    return open(p, encoding="utf-8").read()


def write(p, s):
    open(p, "w", encoding="utf-8").write(s)


def add_to_mart(text, label, items):
    m = re.search(r"(%s::\n(?:\t\.2byte ITEM_\w+\n)*?)(\t\.2byte ITEM_NONE\n)" % label, text)
    assert m, label
    return text[:m.end(1)] + "".join(f"\t.2byte ITEM_{i}\n" for i in items) + text[m.end(1):]


P2 = "data/maps/CeladonCity_DepartmentStore_2F/scripts.inc"
P5 = "data/maps/CeladonCity_DepartmentStore_5F/scripts.inc"
s2, s5 = read(P2), read(P5)
if "ITEM_ENERGY_POWDER" in s2:
    sys.exit("The consumables are already on sale.")
if "CeladonCity_DepartmentStore_2F_BerriesBasic" not in s2:
    sys.exit("Run berry_shop.py first.")

# Berry stand: herbal medicine and the two held herbs
basic, mid = ["ENERGY_POWDER", "HEAL_POWDER"], ["ENERGY_ROOT", "REVIVAL_HERB", "WHITE_HERB", "MENTAL_HERB"]
s2 = add_to_mart(s2, "CeladonCity_DepartmentStore_2F_BerriesBasic", basic)
s2 = add_to_mart(s2, "CeladonCity_DepartmentStore_2F_BerriesMid", basic + mid)
s2 = add_to_mart(s2, "CeladonCity_DepartmentStore_2F_BerriesAll", basic + mid)
write(P2, s2)
t2 = "data/maps/CeladonCity_DepartmentStore_2F/text.inc"
write(t2, read(t2).replace('''    .string "Welcome to the BERRY STAND!\\n"
    .string "Fresh from the SEVII ISLANDS.$"''', '''    .string "Welcome to the BERRY STAND!\\n"
    .string "We have herbs, too.$"'''))

# 5F X-item clerk: PP restorers and Max Revive by progress
lab = "CeladonCity_DepartmentStore_5F_XItems"
xitems = re.search(r"%s::\n((?:\t\.2byte ITEM_\w+\n)*?)\t\.2byte ITEM_NONE\n" % lab, s5).group(1)
s5 = s5.replace('''	pokemart CeladonCity_DepartmentStore_5F_XItems
	msgbox Text_PleaseComeAgain''', '''	goto_if_set FLAG_SYS_GAME_CLEAR, CeladonCity_DepartmentStore_5F_EventScript_HackXItemsAll
	goto_if_set FLAG_BADGE04_GET, CeladonCity_DepartmentStore_5F_EventScript_HackXItemsMid
	pokemart CeladonCity_DepartmentStore_5F_XItems
CeladonCity_DepartmentStore_5F_EventScript_HackXItemsEnd::
	msgbox Text_PleaseComeAgain''', 1)
s5 += f"""
@ FireRed QoL+Hard: PP restorers and Max Revive (tools/hack/consumables_shop.py)
CeladonCity_DepartmentStore_5F_EventScript_HackXItemsMid::
\tpokemart CeladonCity_DepartmentStore_5F_XItemsMid
\tgoto CeladonCity_DepartmentStore_5F_EventScript_HackXItemsEnd

CeladonCity_DepartmentStore_5F_EventScript_HackXItemsAll::
\tpokemart CeladonCity_DepartmentStore_5F_XItemsAll
\tgoto CeladonCity_DepartmentStore_5F_EventScript_HackXItemsEnd

\t.align 2
CeladonCity_DepartmentStore_5F_XItemsMid::
{xitems}\t.2byte ITEM_ETHER
\t.2byte ITEM_ELIXIR
\t.2byte ITEM_NONE
\trelease
\tend

\t.align 2
CeladonCity_DepartmentStore_5F_XItemsAll::
{xitems}\t.2byte ITEM_ETHER
\t.2byte ITEM_ELIXIR
\t.2byte ITEM_MAX_ETHER
\t.2byte ITEM_MAX_ELIXIR
\t.2byte ITEM_MAX_REVIVE
\t.2byte ITEM_NONE
\trelease
\tend
"""
write(P5, s5)

# Prices
raw = read("src/data/items.json")
d = json.loads(raw)
for it in d["items"]:
    if it["itemId"] in ("ITEM_WHITE_HERB", "ITEM_MENTAL_HERB"):
        it["price"] = 2000
write("src/data/items.json", json.dumps(d, indent=2, ensure_ascii=False) + ("\n" if raw.endswith("\n") else ""))
print("Consumables added to the Celadon shops.")
