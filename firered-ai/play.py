"""Watch a trained agent play, and save it as a video.

    python play.py path/to/firered.gba runs/firered/latest.zip --out play.mp4

Without a model, it plays random buttons (handy as a baseline).
Saves .mp4 if imageio-ffmpeg is installed, otherwise use --out play.gif.
"""

from __future__ import annotations

import argparse

from firered_ai.cli import add_goal_args, goals_from_args
from firered_ai.env import FireRedEnv
from firered_ai.ram import load_addresses


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("rom")
    p.add_argument("model", nargs="?", help="checkpoint .zip (omit for random play)")
    p.add_argument("--state", default="states/start.state")
    p.add_argument("--steps", type=int, default=2000, help="button presses to play")
    p.add_argument("--out", default="play.mp4", help="video file (.mp4 or .gif)")
    p.add_argument("--every", type=int, default=1, help="record one frame per N presses")
    p.add_argument("--deterministic", action="store_true", help="always pick the most likely button")
    p.add_argument("--allow-start", action="store_true")
    p.add_argument("--addresses")
    add_goal_args(p)
    args = p.parse_args()
    goals = goals_from_args(args)

    env = FireRedEnv(
        rom_path=args.rom,
        start_state=args.state,
        max_steps=args.steps,
        allow_start=args.allow_start,
        addresses=load_addresses(args.addresses),
        goals=goals,
    )
    model = None
    if args.model:
        from stable_baselines3 import PPO

        model = PPO.load(args.model, device="cpu")

    obs, info = env.reset()
    frames, total = [], 0.0
    for t in range(args.steps):
        if model is not None:
            action, _ = model.predict(obs, deterministic=args.deterministic)
        else:
            action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total += reward
        if t % args.every == 0:
            frames.append(env.render())
        if t % 250 == 0:
            print(f"step {t:5d}  reward {total:7.2f}  {info['map']} ({info['x']},{info['y']})  "
                  f"badges {info['badges']}  levels {info['level_sum']}  goals {info['goal_progress']:.0%}")
        if terminated or truncated:
            break

    print(f"Done: reward {total:.2f}, {info['maps_explored']} maps, {info['tiles_explored']} tiles, "
          f"{info['badges']} badges, goals {info['goal_progress']:.0%}"
          + (" (all goals met!)" if info["complete"] else ""))
    if goals.pokedex is not None:
        missing = goals.pokedex.missing(env.state.owned)
        names = [goals.pokedex.names.get(n, str(n)) for n in missing[:20]]
        print(f"Pokédex: {len(missing)} still to catch, e.g. {', '.join(names)}")
    save_video(frames, args.out)
    env.close()


def save_video(frames, out: str) -> None:
    if out.endswith(".gif"):
        from PIL import Image

        imgs = [Image.fromarray(f) for f in frames]
        imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=1000 // 30, loop=0)
    else:
        import imageio.v2 as imageio

        imageio.mimsave(out, frames, fps=30)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
