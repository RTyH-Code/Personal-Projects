"""Start (or continue) Claude's play-through of FINAL FANTASY Pixel Remaster.

    python play.py --budget-usd 10

Stop any time with Ctrl+C; run it again to carry on. Create a file named PAUSE in
the save folder to pause between turns (to take over the controller yourself),
and delete it to resume.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ff1agent.agent import PRICES, Agent, Config


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--save-dir", type=Path, default=Path("save"), help="Where notes, progress and logs are kept (default: ./save).")
    p.add_argument("--budget-usd", type=float, default=20.0, help="Stop once the estimated API spend reaches this, across all runs with this save folder (default: 20).")
    p.add_argument("--max-turns", type=int, help="Stop after this many turns in total.")
    p.add_argument("--model", default="claude-opus-5-5", choices=sorted(PRICES))
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--segment-turns", type=int, default=40, help="Turns per conversation before Claude writes a handoff and starts fresh (default: 40).")
    p.add_argument("--screenshot-width", type=int, default=960, help="Screenshots are shrunk to this width; smaller is cheaper but harder to read (default: 960).")
    p.add_argument("--tile-ms", type=int, default=270, help="How long walking one tile takes, in ms. Tune it if walks overshoot or fall short.")
    p.add_argument("--window-title", default="FINAL FANTASY")
    p.add_argument("--allow-boosts", action="store_true", help="Let Claude use the game's Boost options.")
    p.add_argument("--notes-file", type=Path, help="A text file of extra instructions for Claude (party wishes, missing achievements...).")
    p.add_argument("--save-frames", action="store_true", help="Keep every screenshot in the save folder.")
    p.add_argument("--dry-run", action="store_true", help="Use a blank fake game instead of the real one (checks your API key and setup; costs a few cents).")
    a = p.parse_args()

    cfg = Config(
        model=a.model, effort=a.effort, segment_turns=a.segment_turns, max_turns=a.max_turns,
        budget_usd=a.budget_usd, tile_ms=a.tile_ms, screenshot_width=a.screenshot_width,
        allow_boosts=a.allow_boosts, save_frames=a.save_frames,
        user_notes=a.notes_file.read_text(encoding="utf-8") if a.notes_file else "",
    )
    if a.dry_run:
        from ff1agent.game import FakeGame
        game = FakeGame()
        if a.max_turns is None:
            cfg.max_turns = 3
    else:
        from ff1agent.game import WindowsGame
        game = WindowsGame(a.window_title)

    agent = Agent(game, cfg, a.save_dir)
    try:
        reason = agent.run()
    except KeyboardInterrupt:
        reason = "Stopped with Ctrl+C."
    s = agent.state
    print(f"\n{reason}\nTurns: {s.turns}  Segments: {s.segments}  Estimated spend: ${s.spent_usd:.2f}  "
          f"Objectives done: {len(s.done)}/{len(agent.objectives)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
