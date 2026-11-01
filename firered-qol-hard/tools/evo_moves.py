#!/usr/bin/env python3
"""Let evolved Pokemon keep learning moves by level-up.

Modern games give most stone evolutions (Ninetales, Starmie, Vileplume, ...)
nothing but level-1 moves. For every species that evolves by item and has at
most two moves above level 1, the pre-evolution's later moves are learned again
by level-up, a little later to offset the evolved form's higher stats:
    new level = old level + max(3, round(old level * 0.15))
The species keeps its own level-1 moves, except ones the pre-evolution learns
later (those move to their delayed level instead).

Run once from the repo root after modernize.py:
    python3 tools/hack/evo_moves.py
"""
import re

LEARNSETS = "src/data/pokemon/level_up_learnsets.h"


def delay(level):
    return min(100, level + max(3, round(level * 0.15)))


def main():
    text = open(LEARNSETS).read()
    ptrs = dict(re.findall(r"\[(SPECIES_\w+)\] = (s\w+LevelUpLearnset)",
                           open("src/data/pokemon/level_up_learnset_pointers.h").read()))
    pre = {}
    for a, body in re.findall(r"\[(SPECIES_\w+)\]\s*=\s*\{(.*?)\}\},", open("src/data/pokemon/evolution.h").read(), re.S):
        for method, target in re.findall(r"\{(EVO_\w+), [^,]+, (SPECIES_\w+)", body):
            if method == "EVO_ITEM":
                pre[target] = a

    def moves(arr):
        body = re.search(r"static const u16 %s\[\] = \{(.*?)\};" % arr, text, re.S).group(1)
        return [(int(l), m) for l, m in re.findall(r"LEVEL_UP_MOVE\(\s*(\d+), (MOVE_\w+)\)", body)]

    changed = []
    for species, prevo in pre.items():
        arr, prev_arr = ptrs.get(species), ptrs.get(prevo)
        if not arr or not prev_arr:
            continue
        own = moves(arr)
        if len([1 for l, _ in own if l > 1]) > 2:
            continue
        later = {}
        for l, m in moves(prev_arr):
            if l > 1:
                later[m] = min(later.get(m, 100), delay(l))
        own_kept = {(l, m) for l, m in own if l > 1 or m not in later}
        own_later = {m for l, m in own if l > 1}
        extra = {(l, m) for m, l in later.items() if m not in own_later}
        if not extra:
            continue
        merged = sorted(own_kept | extra)
        lines = [f"static const u16 {arr}[] = {{"]
        lines += [f"    LEVEL_UP_MOVE({l}, {m})," for l, m in merged]
        lines += ["    LEVEL_UP_END", "};"]
        text = re.sub(r"static const u16 %s\[\] = \{.*?\n\};" % arr, "\n".join(lines), text, flags=re.S)
        changed.append(species[8:])
    open(LEARNSETS, "w").write(text)
    print(f"{len(changed)} species now inherit later moves: {' '.join(changed)}")


if __name__ == "__main__":
    main()
