# FF1 Pixel Remaster Bot

A bot that plays FINAL FANTASY (the Pixel Remaster, Steam/PC) locally, with the
game knowledge written in, like the [FireRed playtester](../firered-ai/README.md).
No AI service and no running costs.

```
 ┌──────────── the game ─────────────┐        ┌────────── Python bot ──────────┐
 │  FF1 Bridge mod (BepInEx plugin)  │  JSON  │  reads state, plans, decides   │
 │  reads party, map, position,      │ ◀────▶ │  (route, battles, shopping)    │
 │  battle state from live objects   │ :52323 │                                │
 └───────────────────────────────────┘        └───────────────┬────────────────┘
                 ▲                                            │
                 └─────────── virtual Xbox controller ◀───────┘
```

The game isn't an emulator, so there's no fixed RAM map to read like FireRed's.
Instead, a small mod runs inside the game and answers questions like
"what is `Last.Management.UserDataManager.Instance().OwendGil`?" by walking the
game's own objects. The bot then presses buttons on a virtual controller, just
like a player would. It doesn't edit the game's data.

## Status: milestone 1 of 5

| # | Milestone | State |
|---|---|---|
| 1 | **Bridge.** The mod, the Python client, the explorer for finding the game's data, the controller, and a pathfinder that learns walls by bumping into them | Built and tested here against a fake game, **not yet run in the real game** |
| 2 | **Reading the game.** Confirm where the map, position, party, inventory and battle state live; walk to a tile on command | Needs your help (see below) |
| 3 | **Battles.** Menu navigation and rules: attack, heal, cast, run | |
| 4 | **The story.** The route through every story objective, as data the bot follows: where to go, who to talk to, what to buy, when to grind and save | |
| 5 | **100%.** Bestiary, every chest, Warmech, Excalibur, achievements | |

Names in the game's code come partly from two open-source Pixel Remaster mods,
[FFPR-Fix](https://github.com/d3xMachina/FFPR-Fix) and
[Memoria.FFPR](https://github.com/Albeoris/Memoria.FFPR). The rest have to be
found in the running game with the explorer, which is what milestone 2 is.

## Setup (Windows)

1. **BepInEx.** Download a BepInEx 6 bleeding-edge build for **IL2CPP, Windows x64**
   (`BepInEx-Unity.IL2CPP-win-x64-6.0.0-be.*`) from
   [builds.bepinex.dev](https://builds.bepinex.dev/projects/bepinex_be).
   Memoria.FFPR uses be.735; that's a safe choice. Extract it into the game
   folder (Steam: right-click FINAL FANTASY → Manage → Browse local files), so
   that `BepInEx` sits next to `FINAL FANTASY.exe`.
2. **Run the game once** and wait at the title screen. The first start takes a
   few minutes while BepInEx generates `BepInEx\interop`. Then close the game.
3. **Build the mod.** Install the [.NET SDK](https://dotnet.microsoft.com/download)
   (8 or newer), then from this folder:

   ```bash
   dotnet build mod/FF1Bridge -c Release
   ```

   It finds the game through Steam and copies `FF1Bridge.dll` into
   `BepInEx\plugins`. If the game is somewhere unusual, add
   `-p:GamePath="D:\path\to\FINAL FANTASY PR"`.
4. **Controller driver.** Install [ViGEmBus](https://github.com/nefarius/ViGEmBus/releases).
5. **Python** 3.10 or newer, in this folder:

   ```bash
   python -m venv .venv
   ```

   ```bash
   .venv\Scripts\activate
   ```

   ```bash
   pip install -r requirements.txt
   ```

Start the game. The BepInEx console window should show
`FF1 Bridge 0.1.0 listening on 127.0.0.1:52323`.

## Milestone 2: finding the game's data

These steps confirm the bridge works, then find what's still missing. Load a
save, or start a new game and get to Cornelia, then run each step and paste the
output back to me. I'll fill in `ff1bot/paths.json` from it.

1. **Is the mod reachable?**

   ```bash
   python -m ff1bot.explore ping
   ```

2. **Which known and guessed paths work?**

   ```bash
   python -m ff1bot.explore state
   ```

3. **Does the game see the controller?** With the game in front, this should
   move the cursor or the character down three times:

   ```bash
   python -m ff1bot.pad down 3
   ```

4. **What's in the player's save data?**

   ```bash
   python -m ff1bot.explore get "Last.Management.UserDataManager.Instance()" --depth 1
   ```

5. **What are the map and field types called?**

   ```bash
   python -m ff1bot.explore find Last.Map
   ```

   ```bash
   python -m ff1bot.explore find FieldPlayer
   ```

6. **Where is the player's position?** This takes a snapshot, waits while you
   walk exactly one step in the game, then prints what changed. Look for a
   number that changed by 1.

   ```bash
   python -m ff1bot.explore diff "Last.Management.UserDataManager.Instance()" --depth 3
   ```

   If nothing useful changes, try the objects from step 5 instead of
   `UserDataManager`. Use `members` to see what an object offers.

The explorer has more commands: `search` finds a value such as your gil amount
inside an object, `watch` prints a value as it changes, and `members` lists
properties and methods. `python -m ff1bot.explore --help` shows them all, with
the path syntax.

**Speeding the game up.** Unity's time scale works for most animations:

```bash
python -m ff1bot.explore set UnityEngine.Time.timeScale 3
```

## How the pieces work

- **`mod/FF1Bridge`** is the BepInEx plugin. Requests arrive on a background
  thread and run on the game's main thread, a few milliseconds per frame. The
  logic lives in `mod/FF1Bridge/Core` and is plain .NET reflection, so it can
  be tested without the game.
- **`mod/TestHost`** runs that core over fake game objects for the tests. It's
  not part of the mod.
- **`ff1bot/bridge.py`** is the client. `ff1bot/paths.json` maps names
  (`gil`, `party`, `player_x`...) to paths, each marked known, guess or todo.
- **`ff1bot/nav.py`** plans routes assuming unknown ground is walkable. When a
  step doesn't move the player, it marks that step blocked, re-plans, and
  remembers the wall for next time.
- **`ff1bot/pad.py`** is the virtual Xbox controller.

## Tests

The tests build the test host and talk to it over the same protocol the real
mod uses, so they need the .NET SDK (they're skipped without it):

```bash
python -m pytest tests
```

## Limits

- A game update can rename the game's internals. Then the explorer is how to
  find the new names, and only `paths.json` needs changing.
- `set` can change any value in the game, so it can also break a save. The bot
  only uses it for the time scale.
- People standing in the way get remembered as walls for now. Milestone 2
  should fix that by reading where NPCs are.
