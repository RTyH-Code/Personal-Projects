from ff1bot.nav import Navigator, walk_to

MAZE = [
    "#########",
    "#S..#...#",
    "#.#.#.#.#",
    "#.#...#G#",
    "#########",
]


class GridWorld:
    def __init__(self, rows, battle_after=None):
        self.rows = rows
        self.steps = 0
        self.battle_after = battle_after
        for y, row in enumerate(rows):
            for x, c in enumerate(row):
                if c == "S":
                    self.x, self.y = x, y

    def position(self):
        return 1, self.x, self.y

    def in_battle(self):
        return self.battle_after is not None and self.steps >= self.battle_after

    def step(self, direction):
        self.steps += 1
        dx, dy = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[direction]
        if self.rows[self.y + dy][self.x + dx] != "#":
            self.x, self.y = self.x + dx, self.y + dy


def goal_of(rows):
    return next((x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == "G")


def test_learns_walls_and_arrives(tmp_path):
    nav = Navigator(tmp_path / "walls.json")
    world = GridWorld(MAZE)
    assert walk_to(world, nav, goal_of(MAZE)) == "arrived"
    first = world.steps
    # Second trip on the same map uses what it learned: no more bumping into walls.
    world2 = GridWorld(MAZE)
    assert walk_to(world2, Navigator(tmp_path / "walls.json"), goal_of(MAZE)) == "arrived"
    assert world2.steps < first


def test_unreachable_and_battle(tmp_path):
    boxed = ["#####", "#S#G#", "#####"]
    assert walk_to(GridWorld(boxed), Navigator(), goal_of(boxed)) == "unreachable"
    assert walk_to(GridWorld(MAZE, battle_after=3), Navigator(), goal_of(MAZE)) == "battle"
