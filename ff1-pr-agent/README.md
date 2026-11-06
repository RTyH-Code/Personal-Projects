# FF1 Pixel Remaster Agent

Claude plays FINAL FANTASY (the Pixel Remaster, Steam/PC) toward a 100%
checklist. Nothing is trained: Claude uses what it already knows about the game,
looks at screenshots, and presses buttons on a virtual Xbox controller.

```
 game window ──screenshot──▶ Claude ──tool calls──▶ virtual Xbox pad ──▶ game
                               ▲   │
          objectives + notes ──┘   └──▶ update_notes / complete_objective (state.json)
```

## How it works

- **Tools.** `press_buttons`, `walk`, `wait` (each returns a fresh screenshot),
  `update_notes` and `complete_objective`.
- **Objectives.** [`ff1agent/objectives.json`](ff1agent/objectives.json) is the
  checklist: the story in order, plus completionist goals (Bestiary, every
  chest, Warmech, Excalibur, achievements). Hints are nudges, not scripts. Edit
  it freely, and check the completionist part against your achievement list.
- **Memory.** Play is split into segments of 40 turns. Each segment is a fresh
  conversation that starts from the checklist, Claude's notes and a screenshot.
  At the end of a segment Claude writes a handoff into its notes. This keeps
  each request small, so a long play-through doesn't get slower or pricier per
  turn as it goes.
- **Progress is saved** in `save/state.json`, so you can stop with Ctrl+C and
  carry on later. To take the controller yourself, create an empty file
  `save/PAUSE`. The agent pauses before its next turn until you delete it.

## Cost

Every turn is one Claude API call, billed to your Anthropic API account (the
API key, not a Claude.ai subscription). With Claude Opus 5.5 at its default
settings, a turn is roughly:

| Part | Tokens | Cost |
|---|---|---|
| New screenshot (960 px wide) + tool call text | ~1,000, written to the cache | ~$0.005 |
| Earlier turns of the segment (re-read from the cache) | ~20,000 on average | ~$0.004 |
| Claude's reply and thinking | ~300–1,000 | ~$0.006–0.02 |
| **Per turn** | | **~$0.015–0.03** |

A 100% run is long: likely **10,000–30,000 turns**, so expect somewhere around
**$150–900** for the whole thing. That's a rough guess until real runs measure
it. The running estimate is printed and stored in `state.json`, and
`--budget-usd` (default $20) stops the run when it's reached. The budget counts
across runs with the same save folder.

Ways to spend less:

- `--model claude-sonnet-5-5` halves the per-token price. It's untested whether
  it plays as well.
- `--screenshot-width 640` cuts image tokens by more than half. Text gets harder
  to read.
- `--allow-boosts` lets Claude turn random encounters off while travelling and
  raise EXP/gil, which saves a lot of turns. It's still 100% by the checklist,
  but not a "pure" run.
- `--effort low` thinks less per turn. It's worth trying in easy stretches.

## Setup (Windows)

1. Install the game on Steam and set it to **windowed** mode (1280×720 is plenty).
2. Install the [ViGEmBus driver](https://github.com/nefarius/ViGEmBus/releases).
   `vgamepad` needs it to create the virtual controller.
3. Install Python 3.10+, then in this folder:

   ```bash
   python -m venv .venv
   ```

   ```bash
   .venv\Scripts\activate
   ```

   ```bash
   pip install -r requirements.txt
   ```

4. Set your API key, from the [Claude Console](https://platform.claude.com):

   ```bash
   setx ANTHROPIC_API_KEY "sk-ant-..."
   ```

   Open a new terminal afterwards so the variable is picked up.

5. Check the setup without the game. This runs 3 turns on a blank screen and
   costs a few cents:

   ```bash
   python play.py --dry-run --save-dir dry-run
   ```

## Running

Start the game, get to the title screen, then:

```bash
python play.py --budget-usd 5
```

Leave the game window visible. The agent focuses it before each press, so
don't use the PC for other things while it plays. Watch the first few minutes:
if walks overshoot or stop short, adjust `--tile-ms`. `python play.py --help`
lists every option, including `--notes-file` for extra instructions (party
wishes, which achievements you're missing) and `--save-frames` to keep every
screenshot.

## Limits and what to expect

- **Untested against the real game so far.** This was written without the game
  to hand. Expect a tuning pass: walking speed, wait times, and how well
  Claude reads the menus at the chosen screenshot size.
- **Screenshots are its only view of the game.** It reads HP, menus and the
  map from images, so it can misread things. A mod that reads the game's
  memory (BepInEx) would be more reliable, and could be added later as another
  tool.
- **It's slow.** Each turn takes a few seconds of thinking, about as fast as a
  careful human, not faster.
- **Long-horizon play is the hard part.** Getting lost, forgetting a key item
  or wandering underleveled into a dungeon are the likely failures. The notes,
  frequent saves and the checklist are there to limit them. Read
  `save/log.jsonl` and Claude's notes to see what it was thinking, and steer it
  with `--notes-file`.

## Tests

```bash
pip install pytest
```

```bash
python -m pytest tests
```

The tests run the loop against a fake game and a scripted fake Claude, so they
need no API key and no game.
