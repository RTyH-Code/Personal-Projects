#!/usr/bin/env python3
"""guide/BOSSES.md from the boss team report.

    python3 tools/hack/boss_teams.py --report > report.txt     (from the hack's hg-engine root)
    python3 tools/boss_guide.py report.txt guide/BOSSES.md
"""
import re, sys
lines = open(sys.argv[1]).read().split("\n")
out = ["# Boss teams", "",
       "Spoilers: every hand-built boss team, from Falkner to Red.",
       "Generated from `tools/hack/boss_teams.py --report`.", "",
       "All boss Pokémon have perfect IVs. From Chuck onward they also have a nature and a full EV spread.", ""]
section = None
def head(label):
    global section
    kanto = ("Lt. Surge", "Sabrina", "Erika", "Janine", "Misty", "Brock", "Blaine", "Blue")
    group = ("Rival" if label.startswith("Rival") else "Kimono Girls" if label.startswith("Kimono") else
             "Team Rocket" if re.match(r"(Proton|Petrel|Ariana|Archer)", label) else
             "Post-game: Gym Leader rematches" if label.endswith(", rematch") else
             "Post-game: the Elite Four's second round" if label.endswith(", second round") else
             "Post-game: Kanto Gym Leaders" if label in kanto else
             "Post-game: Red" if label == "Red" else
             "Elite Four and Champion" if label in ("Will", "Koga", "Bruno", "Karen", "Lance") else "Gym Leaders")
    if group != section:
        section = group
        out.extend(["## " + group, ""])
for line in lines:
    if line.startswith("== "):
        label = line[3:]
        head(label)
        label = label.replace("azalea", "Azalea Town").replace("burned tower", "Burned Tower").replace("goldenrod tunnel", "Goldenrod Tunnel").replace("victory road", "Victory Road").replace("mt. moon", "Mt. Moon").replace("indigo plateau", "Indigo Plateau").replace("tag battle", "tag battle with Lance and Clair")
        label = re.sub(r"\(vs (\w+)\)", lambda m: "(you chose %s)" % m.group(1).title(), label)
        out.extend(["### " + label, "", "| Pokémon | Lv. | Item | Moves | Ability, nature |", "|---|---|---|---|---|"])
    elif line.startswith("   note:"):
        out.append(""); out.append("*" + line.strip()[6:].strip() + ".*"); out.append("")
    elif line.strip():
        m = re.match(r"\s+(\S+)\s+Lv\. (\d+)\s+@ (.+?)\s{2,}(.*?)(?:  \[(.*)\])?$", line)
        if not m:
            m = re.match(r"\s+(\S+)\s+Lv\. (\d+)\s+@ (\S+(?: \S+)*?) {1,}((?:[A-Z][\w' ]*, )*[A-Z][\w' ]*)(?:  \[(.*)\])?$", line)
        name, lv, item, moves, extra = m.groups()
        out.append("| %s | %s | %s | %s | %s |" % (name.replace("_", " "), lv, item if item != "None" else "—", moves, extra or "—"))
    else:
        if out[-1] != "": out.append("")
open(sys.argv[2], "w").write("\n".join(out).rstrip("\n") + "\n")
