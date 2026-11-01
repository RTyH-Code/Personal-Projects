"""Train an agent to play Pokémon FireRed with PPO.

    python train.py path/to/firered.gba --state states/start.state

Runs several emulators in parallel. Progress is saved to runs/<name>/:
checkpoints, TensorBoard logs, the progress pool (save states later
episodes start from) and a save state each time an agent earns a new badge.
Stop with Ctrl+C at any time and continue with --resume.

By default the goal is all 8 badges, becoming Champion and a complete
Pokédex for your ROM (see --goals and --pokedex).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback, CheckpointCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecMonitor

from firered_ai.cli import add_goal_args, goals_from_args
from firered_ai.env import FireRedEnv
from firered_ai.ram import load_addresses


class ProgressLogger(BaseCallback):
    """Log how far the agents got (badges, levels, maps) at the end of each episode."""

    KEYS = ["badges", "level_sum", "dex_owned", "tiles_explored", "maps_explored",
            "goal_progress", "start_score", "score"]

    def _on_step(self) -> bool:
        for info, done in zip(self.locals["infos"], self.locals["dones"]):
            if not done:
                continue
            for k in self.KEYS:
                self.logger.record_mean(f"game/{k}", info[k])
            for k, v in info.items():
                if k.startswith(("reward/", "goal/")):
                    self.logger.record_mean(k, v)
            self.logger.record_mean("game/completed", float(info["complete"]))
            if info["complete"]:
                print(f"An agent met every goal after {self.num_timesteps} steps!")
        return True


def make_env(args, rank: int):
    def init():
        return FireRedEnv(
            rom_path=args.rom,
            start_state=args.state,
            max_steps=args.episode_steps,
            allow_start=args.allow_start,
            reward_weights=json.loads(Path(args.rewards).read_text()) if args.rewards else None,
            addresses=load_addresses(args.addresses),
            milestone_dir=str(Path(args.run_dir) / "milestones"),
            goals=args.goal_set,
            progress_dir=None if args.no_progress_pool else str(Path(args.run_dir) / "progress"),
            progress_prob=args.progress_prob,
        )

    return init


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom", help="your FireRed .gba file")
    p.add_argument("--state", default="states/start.state", help="save state to start each episode from")
    p.add_argument("--name", default="firered", help="run name, used for runs/<name>/")
    p.add_argument("--envs", type=int, default=os.cpu_count(), help="emulators to run in parallel")
    p.add_argument("--timesteps", type=float, default=10_000_000, help="total button presses to train for")
    p.add_argument("--episode-steps", type=int, default=8192, help="button presses per episode")
    p.add_argument("--allow-start", action="store_true", help="let the agent press START (opens the menu)")
    p.add_argument("--rewards", help="JSON file overriding reward weights (see firered_ai/rewards.py)")
    p.add_argument("--addresses", help="JSON file of RAM addresses (see tools/symbols_from_map.py)")
    add_goal_args(p)
    p.add_argument("--no-progress-pool", action="store_true",
                   help="always start episodes from --state instead of from the best progress so far")
    p.add_argument("--progress-prob", type=float, default=0.8,
                   help="chance an episode starts from the progress pool rather than --state")
    p.add_argument("--resume", help="checkpoint .zip to continue from")
    p.add_argument("--device", default="auto", help="cpu, cuda or auto")
    args = p.parse_args()

    try:
        args.goal_set = goals_from_args(args)
    except ValueError as e:
        p.error(str(e))
    if not Path(args.state).exists():
        p.error(f"{args.state} not found. Create it with: python make_start_state.py {args.rom} {args.state}")
    args.run_dir = str(Path("runs") / args.name)
    print(f"Goals: {args.goal_set.describe()}")

    fns = [make_env(args, i) for i in range(args.envs)]
    env = VecMonitor(SubprocVecEnv(fns) if args.envs > 1 else DummyVecEnv(fns))

    # Each env collects n_steps presses before every update.
    n_steps = 2048
    if args.resume:
        model = PPO.load(args.resume, env=env, device=args.device)
        print(f"Resumed from {args.resume} at {model.num_timesteps} steps")
    else:
        model = PPO(
            "MultiInputPolicy",
            env,
            n_steps=n_steps,
            batch_size=512,
            n_epochs=3,
            gamma=0.998,  # long horizon: badges are many thousands of presses away
            gae_lambda=0.95,
            ent_coef=0.01,
            learning_rate=2.5e-4,
            tensorboard_log=str(Path(args.run_dir) / "tb"),
            device=args.device,
            verbose=1,
        )

    callbacks = [
        CheckpointCallback(
            save_freq=max(n_steps * 4, 1),  # counted per env
            save_path=str(Path(args.run_dir) / "checkpoints"),
            name_prefix="ppo",
        ),
        ProgressLogger(),
    ]
    try:
        model.learn(
            total_timesteps=int(args.timesteps),
            callback=callbacks,
            reset_num_timesteps=not args.resume,
            tb_log_name="ppo",
        )
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        path = Path(args.run_dir) / "latest.zip"
        model.save(path)
        print(f"Saved {path}")
        env.close()


if __name__ == "__main__":
    main()
