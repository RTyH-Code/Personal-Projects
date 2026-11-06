"""What each species can learn in this hack (level-up, TM/HM, tutors, egg
moves and the modern tutor, including everything its pre-evolutions learn).

    from learnsets import learnable, move_ids
"""
import os, re

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def read(p):
    return open(p, encoding="utf-8").read()


# ---------------------------------------------------------------- what each species can learn in this hack
lu_ptr = dict(re.findall(r"\[(SPECIES_\w+)\] = (s\w+LevelUpLearnset)", read("src/data/pokemon/level_up_learnset_pointers.h")))
lu = {n: set(re.findall(r"MOVE_\w+", b)) for n, b in re.findall(r"static const u16 (s\w+LevelUpLearnset)\[\] = \{(.*?)\};", read("src/data/pokemon/level_up_learnsets.h"), re.S)}
tm_moves = {}
for name in re.findall(r"#define ITEM_((?:TM|HM)\d\d_\w+)", read("include/constants/items.h")):
    tm_moves[name] = "MOVE_" + name.split("_", 1)[1]
tmhm = {sp: {tm_moves.get(t, "MOVE_" + t.split("_", 1)[1]) for t in re.findall(r"TMHM\(((?:TM|HM)\d\d_\w+)\)", b)}
        for sp, b in re.findall(r"\[(SPECIES_\w+)\]\s*= TMHM_LEARNSET\((.*?)\),\n", read("src/data/pokemon/tmhm_learnsets.h"), re.S)}
tutor = {sp: set(re.findall(r"TUTOR\((MOVE_\w+)\)", b)) for sp, b in re.findall(r"\[(SPECIES_\w+)\] = (TUTOR.*?),\n\n", read("src/data/pokemon/tutor_learnsets.h"), re.S)}
egg = {"SPECIES_" + sp: set(re.findall(r"MOVE_\w+", b)) for sp, b in re.findall(r"egg_moves\((\w+),(.*?)\)", read("src/data/pokemon/egg_moves.h"), re.S)}
move_ids = {m: int(n) for m, n in re.findall(r"#define (MOVE_\w+) (\d+)\n", read("include/constants/moves.h"))}
by_id = {v: k for k, v in move_ids.items()}
ht = read("src/data/pokemon/hack_tutor_learnsets.h")
first = move_ids[re.search(r"#define HACK_TUTOR_FIRST_MOVE (MOVE_\w+)", ht).group(1)]
modern = {}
for sp, body in re.findall(r"\[(SPECIES_\w+)\] = \{(.*?)\}", ht):
    bits = [int(b, 16) for b in body.split(",")]
    modern[sp] = {by_id[first + i] for i in range(len(bits) * 8) if bits[i // 8] & (1 << (i % 8)) and first + i in by_id}
evo = read("src/data/pokemon/evolution.h")
prevo = {}
for a, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", evo, re.S):
    for t in re.findall(r"(SPECIES_\w+)\}", body + "}"):
        prevo[t] = a


def learnable(sp):
    out, s = set(), sp
    while s:
        out |= lu.get(lu_ptr.get(s), set()) | tmhm.get(s, set()) | tutor.get(s, set()) | egg.get(s, set()) | modern.get(s, set())
        s = prevo.get(s)
    return out


