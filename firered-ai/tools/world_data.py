"""Extract the whole world map from pret source, so the playtester can find its way.

    python tools/world_data.py <pokefirered checkout> > firered_ai/data/games/<name>.world.json
    gzip -9 firered_ai/data/games/<name>.world.json

For every map: its size, a grid of what each tile is (wall, water, grass,
ledge), its warps (doors, stairs) and connections (walking off an edge into
the next route), and its people, signs and trigger tiles. Reads the source
as text; builds nothing.

Each grid cell is one byte:
    bit 0  wall (the map's collision bits)
    bit 1  surfable water
    bit 2  wild encounters on land (tall grass, caves)
    bit 3  wild encounters on water
    bits 4-6  ledge: 1 east, 2 west, 3 north, 4 south (you can jump that way only)
"""

from __future__ import annotations

import base64
import glob
import json
import os
import re
import struct
import sys

LEDGES = {"MB_JUMP_EAST": 1, "MB_JUMP_WEST": 2, "MB_JUMP_NORTH": 3, "MB_JUMP_SOUTH": 4}
NUM_METATILES_IN_PRIMARY = 640


def read(root, path):
    with open(os.path.join(root, path), encoding="utf-8") as f:
        return f.read()


def behaviors(root):
    names = dict((n, int(v, 0)) for n, v in re.findall(r"#define (MB_\w+) (0x[0-9A-Fa-f]+|\d+)",
                                                       read(root, "include/constants/metatile_behaviors.h")))
    code = read(root, "src/metatile_behavior.c")
    table = re.search(r"sBehaviorSurfable\[[^\]]*\]\s*=\s*\{(.*?)\};", code, re.S).group(1)
    surfable = {names[n] for n in re.findall(r"\[(MB_\w+)\]\s*=\s*TRUE", table)}
    ledges = {names[n]: v for n, v in LEDGES.items()}
    return surfable, ledges


def tileset_attributes(root):
    """Tileset symbol (gTileset_X) -> list of u32 metatile attributes."""
    paths = dict(re.findall(r"(gMetatileAttributes_\w+)\[\]\s*=\s*INCBIN_U32\(\"([^\"]+)\"\)",
                            read(root, "src/data/tilesets/metatiles.h")))
    headers = read(root, "src/data/tilesets/headers.h")
    out = {}
    for name, body in re.findall(r"const struct Tileset (gTileset_\w+)\s*=\s*\{(.*?)\};", headers, re.S):
        m = re.search(r"\.metatileAttributes\s*=\s*(gMetatileAttributes_\w+)", body)
        if m and m.group(1) in paths:
            data = open(os.path.join(root, paths[m.group(1)]), "rb").read()
            out[name] = list(struct.unpack(f"<{len(data) // 4}I", data))
    return out


def grid(root, layout, attrs, surfable, ledges):
    w, h = layout["width"], layout["height"]
    data = open(os.path.join(root, layout["blockdata_filepath"]), "rb").read()
    blocks = struct.unpack(f"<{w * h}H", data[: 2 * w * h])
    primary = attrs.get(layout["primary_tileset"], [])
    secondary = attrs.get(layout["secondary_tileset"], [])
    cells = bytearray(w * h)
    for i, b in enumerate(blocks):
        metatile, collision = b & 0x3FF, (b >> 10) & 3
        if metatile < NUM_METATILES_IN_PRIMARY:
            a = primary[metatile] if metatile < len(primary) else 0
        else:
            j = metatile - NUM_METATILES_IN_PRIMARY
            a = secondary[j] if j < len(secondary) else 0
        behavior, encounter = a & 0x1FF, (a >> 24) & 7
        c = 0
        if collision:
            c |= 1
        if behavior in surfable:
            c |= 2
        if encounter == 1:
            c |= 4
        if encounter == 2:
            c |= 8
        c |= ledges.get(behavior, 0) << 4
        cells[i] = c
    return w, h, base64.b64encode(bytes(cells)).decode()


def gate_scripts(root):
    """Trigger scripts that turn the player back ("You can't go through yet"): story gates."""
    scripts = {}
    for f in glob.glob(os.path.join(root, "data", "maps", "*", "scripts.inc")) + \
            glob.glob(os.path.join(root, "data", "scripts", "*.inc")):
        text = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^(\w+)::\n(.*?)(?=^\w+::|\Z)", text, re.S | re.M):
            scripts[m.group(1)] = m.group(2)

    def body(name, depth=0, seen=None):
        seen = seen if seen is not None else set()
        if name in seen:
            return ""
        seen.add(name)
        out = scripts.get(name, "")
        if depth < 3:
            for callee in re.findall(r"\b(?:call|goto)(?:_if_\w+\s+[\w,\s]+?,)?\s*(\w*EventScript_\w+)", out):
                out += "\n" + body(callee, depth + 1, seen)
        return out

    gates = set()
    for name in scripts:
        b = body(name)
        if re.search(r"applymovement (?:LOCALID_PLAYER|OBJ_EVENT_ID_PLAYER), \w*(?:Walk|Step|Push|Back)\w*", b) \
                and "trainerbattle" not in b:
            gates.add(name)
    return gates


def warp_id(v):
    try:
        return int(str(v), 0)
    except ValueError:
        return -1


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    surfable, ledges = behaviors(root)
    gates = gate_scripts(root)
    attrs = tileset_attributes(root)
    layouts = {l["id"]: l for l in json.loads(read(root, "data/layouts/layouts.json"))["layouts"] if "id" in l}
    maps = {}
    id_to_name = {}
    files = sorted(glob.glob(os.path.join(root, "data", "maps", "*", "map.json")))
    raw = [json.load(open(f, encoding="utf-8")) for f in files]
    for d in raw:
        id_to_name[d["id"]] = d["name"]
    for d in raw:
        layout = layouts.get(d["layout"])
        if layout is None or "blockdata_filepath" not in layout:
            continue
        w, h, cells = grid(root, layout, attrs, surfable, ledges)
        maps[d["name"]] = {
            "w": w, "h": h, "grid": cells,
            # dest_warp -1: a dynamic warp (back to wherever you came from: elevators, some exits)
            "warps": [[e["x"], e["y"], id_to_name.get(e["dest_map"], e["dest_map"]), warp_id(e["dest_warp_id"])]
                      for e in d.get("warp_events") or []],
            "connections": [[c["direction"], c["offset"], id_to_name.get(c["map"], c["map"])]
                            for c in d.get("connections") or []],
            "objects": [[o.get("local_id", ""), o["x"], o["y"], o.get("script", ""), o.get("flag", "0")]
                        for o in d.get("object_events") or [] if "x" in o],
            "signs": [[b["x"], b["y"], b.get("type", ""), b.get("script", "")]
                      for b in d.get("bg_events") or []],
            # [x, y, var, value, script, gate]: the script runs when var == value; a gate turns you back
            "triggers": [[c["x"], c["y"], c.get("var", ""), str(c.get("var_value", "")), c.get("script", ""),
                          c.get("script", "") in gates]
                         for c in d.get("coord_events") or [] if c.get("type") != "weather"],
        }
    json.dump({"maps": maps}, sys.stdout, separators=(",", ":"))
    print(f"{len(maps)} maps", file=sys.stderr)


if __name__ == "__main__":
    main()
