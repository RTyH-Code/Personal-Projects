"""A playtester (and optional learning agent) for Pokémon FireRed and FireRed QoL + Hard."""

from .ram import GameState, read_state

__all__ = ["FireRedEnv", "GameState", "read_state"]


def __getattr__(name):
    # The learning environment needs gymnasium; the playtester doesn't.
    if name == "FireRedEnv":
        from .env import FireRedEnv

        return FireRedEnv
    raise AttributeError(name)
