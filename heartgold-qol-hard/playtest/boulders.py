"""Plans Strength boulder puzzles: where to walk and which way to push, so that boulders drop into holes."""
from collections import deque

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def plan(floor, start, boulders, holes, goals=None, limit=3_000_000):
    """The shortest list of moves (directions) from start that drops every boulder into a hole and, with goals,
    ends on one of them. `floor` is the set of tiles the player and boulders can stand on (no holes, walls or
    people); a boulder pushed onto a hole falls through and is gone, and the player never steps on a hole.
    Pushes are searched over; the walking between them is found by a flood fill."""
    holes = frozenset(holes)

    def reach(player, bl):
        seen = {player: None}
        queue = deque([player])
        while queue:
            p = queue.popleft()
            for d, (dx, dz) in DIRS.items():
                n = (p[0] + dx, p[1] + dz)
                if n in floor and n not in bl and n not in seen:
                    seen[n] = (p, d)
                    queue.append(n)
        return seen

    def walk(seen, to):
        steps = []
        while seen[to]:
            to, d = seen[to]
            steps.append(d)
        return steps[::-1]

    # the tiles a boulder can still be pushed into a hole from, leaving the others round it out of the way:
    # pushing one anywhere else (into a corner, against a wall it can't come off) can never help
    live, grew = set(holes), True
    while grew:
        grew = False
        for t in floor:
            if t not in live and any((t[0] + dx, t[1] + dz) in live and (t[0] - dx, t[1] - dz) in floor
                                     for dx, dz in DIRS.values()):
                live.add(t)
                grew = True

    first = (start, frozenset(boulders))
    came = {first: None}
    queue = deque([first])
    known = set()                             # (the part of the floor the player can walk in, the boulders)
    while queue and len(came) < limit:
        state = queue.popleft()
        player, bl = state
        seen = reach(player, bl)
        key = (min(seen), bl)
        if key in known:
            continue
        known.add(key)
        if not bl and (goals is None or any(g in seen for g in goals)):
            moves = walk(seen, next(g for g in goals if g in seen)) if goals else []
            while came[state]:
                state, steps = came[state]
                moves = steps + moves
            return moves
        for b in bl:
            for d, (dx, dz) in DIRS.items():
                behind, ahead = (b[0] - dx, b[1] - dz), (b[0] + dx, b[1] + dz)
                if behind not in seen or ahead in bl:
                    continue
                if ahead in holes:
                    nbl = bl - {b}
                elif ahead in live:
                    nbl = (bl - {b}) | {ahead}
                else:
                    continue
                nxt = (b, nbl)                 # the player ends where the boulder was
                if nxt not in came:
                    came[nxt] = (state, walk(seen, behind) + [d])
                    queue.append(nxt)
    return None


def plan_one_by_one(floor, start, boulders, holes, goals=None):
    """Faster, for puzzles where each boulder has a hole of its own nearby: drop them one at a time, the others
    standing where they are; if that gets nowhere, the full search (plan)."""
    player, left, moves = start, set(boulders), []
    while left:
        for b in sorted(left):
            others = left - {b}
            m = plan(floor - others, player, {b}, holes)
            if m is not None:
                break
        else:
            return plan(floor, start, boulders, holes, goals)
        moves += m
        player = replay(start, boulders, holes, moves)[0]
        left = others
    if goals:
        end = plan(floor, player, set(), holes, goals)
        if end is None:
            return plan(floor, start, boulders, holes, goals)
        moves += end
    return moves


def replay(start, boulders, holes, moves):
    """Where the player and the boulders end up after the moves."""
    player, bl = start, set(boulders)
    for d in moves:
        dx, dz = DIRS[d]
        n = (player[0] + dx, player[1] + dz)
        if n in bl:
            ahead = (n[0] + dx, n[1] + dz)
            bl.discard(n)
            if ahead not in holes:
                bl.add(ahead)
        player = n
    return player, bl
