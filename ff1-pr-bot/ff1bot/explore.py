"""Look around inside the running game to find where its data lives.

    python -m ff1bot.explore ping
    python -m ff1bot.explore state                       # check every entry in paths.json
    python -m ff1bot.explore find UserData               # search type names
    python -m ff1bot.explore members "Last.Management.UserDataManager.Instance()"
    python -m ff1bot.explore get "Last.Management.UserDataManager.Instance()" --depth 2
    python -m ff1bot.explore search "Last.Management.UserDataManager.Instance()" 500
    python -m ff1bot.explore diff "Last.Management.UserDataManager.Instance()" --depth 3
    python -m ff1bot.explore watch "UnityEngine.Time.timeScale"
    python -m ff1bot.explore set "UnityEngine.Time.timeScale" 2

Paths start with a full type name, then members: properties, fields, methods
with arguments like GetX(0), list indexes like Party[0], and casts like
as(Last.Map.FieldPlayer).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

from .bridge import Bridge, BridgeError, load_paths


def flatten(value, prefix: str = "") -> dict[str, object]:
    """Turns nested JSON into {"a.b[0].c": leaf} pairs."""
    out: dict[str, object] = {}
    if isinstance(value, dict):
        for k, v in value.items():
            if k == "$type":
                continue
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = value
    return out


def diff(before, after) -> list[tuple[str, object, object]]:
    a, b = flatten(before), flatten(after)
    return [(k, a.get(k, "<missing>"), b.get(k, "<missing>"))
            for k in sorted(set(a) | set(b)) if a.get(k, "<missing>") != b.get(k, "<missing>")]


def matches(leaf, target: str) -> bool:
    if isinstance(leaf, bool) or leaf is None:
        return str(leaf).lower() == target.lower()
    if isinstance(leaf, (int, float)):
        try:
            return abs(float(leaf) - float(target)) < 1e-6
        except ValueError:
            return False
    return isinstance(leaf, str) and target.lower() in leaf.lower()


def parse_value(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def show(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m ff1bot.explore", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=52323)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ping", help="Check the mod is reachable.")
    sub.add_parser("state", help="Read every entry in paths.json and say which work.")
    s = sub.add_parser("find", help="Search type names.")
    s.add_argument("pattern")
    s.add_argument("--limit", type=int, default=100)
    s = sub.add_parser("members", help="List an object's (or a type's static) properties and methods.")
    s.add_argument("path")
    s = sub.add_parser("get", help="Print an object as JSON.")
    s.add_argument("path")
    s.add_argument("--depth", type=int, default=1)
    s.add_argument("--max-items", type=int, default=100)
    s = sub.add_parser("search", help="Find fields under an object whose value matches (numbers exactly, text by substring).")
    s.add_argument("path")
    s.add_argument("value")
    s.add_argument("--depth", type=int, default=4)
    s = sub.add_parser("diff", help="Snapshot an object, let you do something in the game, then show what changed.")
    s.add_argument("path")
    s.add_argument("--depth", type=int, default=3)
    s.add_argument("--max-items", type=int, default=100)
    s = sub.add_parser("watch", help="Print a value whenever it changes (Ctrl+C to stop).")
    s.add_argument("path")
    s.add_argument("--depth", type=int, default=0)
    s.add_argument("--interval", type=float, default=0.25)
    s = sub.add_parser("set", help="Change a field or property (value is JSON, or plain text).")
    s.add_argument("path")
    s.add_argument("value")
    a = p.parse_args(argv)

    bridge = Bridge(port=a.port)
    try:
        if a.cmd == "ping":
            print(f"Connected: FF1 Bridge {bridge.ping()['version']}")
        elif a.cmd == "state":
            table = load_paths()
            values = bridge.read_named(paths=table)
            for name, entry in table.items():
                if not entry.get("path"):
                    print(f"  TODO   {name}: not found yet")
                    continue
                v = values[name]
                if isinstance(v, dict) and "$error" in v:
                    print(f"  FAIL   {name} ({entry.get('status')}): {v['$error']}")
                else:
                    text = json.dumps(v, ensure_ascii=False)
                    print(f"  ok     {name} ({entry.get('status')}): {text[:150]}{'...' if len(text) > 150 else ''}")
        elif a.cmd == "find":
            for name in bridge.find_types(a.pattern, a.limit):
                print(name)
        elif a.cmd == "members":
            show(bridge.members(a.path))
        elif a.cmd == "get":
            show(bridge.get(a.path, a.depth, a.max_items))
        elif a.cmd == "search":
            found = [(k, v) for k, v in flatten(bridge.get(a.path, a.depth)).items() if matches(v, a.value)]
            for k, v in found:
                print(f"{a.path}.{k} = {json.dumps(v, ensure_ascii=False)}")
            if not found:
                print("No matches. Try a larger --depth, or a different starting object.")
        elif a.cmd == "diff":
            before = bridge.get(a.path, a.depth, a.max_items)
            input("Snapshot taken. Do the thing in the game (walk a step, open a chest...), then press Enter. ")
            after = bridge.get(a.path, a.depth, a.max_items)
            changes = diff(before, after)
            for k, old, new in changes:
                print(f"{a.path}.{k}: {json.dumps(old, ensure_ascii=False)} -> {json.dumps(new, ensure_ascii=False)}")
            print(f"{len(changes)} change(s).")
        elif a.cmd == "watch":
            last = object()
            while True:
                v = bridge.get(a.path, a.depth)
                if v != last:
                    print(f"{time.strftime('%H:%M:%S')} {json.dumps(v, ensure_ascii=False)}")
                    last = v
                time.sleep(a.interval)
        elif a.cmd == "set":
            bridge.set(a.path, parse_value(a.value))
            print("Done.")
    except BridgeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ConnectionError as e:
        print(e, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
