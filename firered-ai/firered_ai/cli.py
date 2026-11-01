"""Command-line options shared by train.py and play.py."""

from __future__ import annotations

import sys

from .goals import GOAL_NAMES, Goals, PokedexTarget, detect_game


def add_goal_args(p) -> None:
    p.add_argument("--goals", default=",".join(GOAL_NAMES),
                   help="what counts as finishing the game: any of badges,champion,pokedex, or none "
                        "(default: all three)")
    p.add_argument("--pokedex", default="auto",
                   help="which Pokémon count for a complete Pokédex: auto (detect from the ROM), "
                        "firered, firered-qol-hard, or a JSON file from tools/pokedex_targets.py")


def goals_from_args(args) -> Goals:
    pokedex = None
    if "pokedex" in args.goals:
        name = args.pokedex
        if name == "auto":
            name = detect_game(args.rom)
            if name is None:
                print("warning: unknown ROM, using the vanilla FireRed Pokédex list. "
                      "Pass --pokedex to choose another.", file=sys.stderr)
                name = "firered"
        pokedex = PokedexTarget.load(name)
    return Goals.parse(args.goals, pokedex)
