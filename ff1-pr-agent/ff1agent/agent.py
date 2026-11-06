"""Claude plays FINAL FANTASY (Pixel Remaster) toward a checklist of objectives.

Claude sees screenshots and presses buttons through tools. The run is split into
segments of a few dozen turns. Each segment is one conversation; at its end Claude
writes a handoff into its notes, and the next segment starts fresh from the notes,
the objective checklist and a new screenshot. The notes and checklist live in
`state.json`, so stopping and restarting picks up where it left off.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from .game import BUTTONS, DIRECTIONS, Game, to_jpeg

OBJECTIVES_FILE = Path(__file__).with_name("objectives.json")
MAX_NOTES_CHARS = 12_000

# USD per million tokens, for the running cost estimate.
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_write": 5.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_write": 2.50, "cache_read": 0.20},
}


@dataclass
class Config:
    model: str = "claude-opus-5-5"
    effort: str = "medium"
    segment_turns: int = 40
    max_turns: int | None = None
    budget_usd: float = 20.0
    tile_ms: int = 270
    screenshot_width: int = 960
    allow_boosts: bool = False
    user_notes: str = ""
    save_frames: bool = False


@dataclass
class State:
    notes: str = ""
    done: dict[str, str] = field(default_factory=dict)  # objective id -> evidence
    turns: int = 0
    segments: int = 0
    spent_usd: float = 0.0

    @classmethod
    def load(cls, path: Path) -> "State":
        if path.exists():
            return cls(**json.loads(path.read_text(encoding="utf-8")))
        return cls()

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")
        tmp.replace(path)


def load_objectives(path: Path = OBJECTIVES_FILE) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["objectives"]


TOOLS = [
    {
        "name": "press_buttons",
        "description": (
            "Press controller buttons one after another, then return a screenshot. "
            "Batch several presses when you're confident (menu navigation, dialogue), "
            "and press one at a time when you need to see the result. "
            f"Buttons: {', '.join(BUTTONS)}. up/down/left/right are the D-pad."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "buttons": {"type": "array", "items": {"type": "string", "enum": BUTTONS}, "minItems": 1, "maxItems": 30},
                "hold_ms": {"type": "integer", "minimum": 30, "maximum": 3000, "description": "How long each press is held. Default 100."},
                "gap_ms": {"type": "integer", "minimum": 0, "maximum": 3000, "description": "Pause between presses. Default 250."},
            },
            "required": ["buttons"],
        },
    },
    {
        "name": "walk",
        "description": (
            "Hold a D-pad direction for about the time it takes to walk the given number of tiles, "
            "then return a screenshot. Movement can be cut short by walls, people or battles; check the screenshot."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": sorted(DIRECTIONS)},
                "tiles": {"type": "integer", "minimum": 1, "maximum": 30},
            },
            "required": ["direction", "tiles"],
        },
    },
    {
        "name": "wait",
        "description": "Wait without pressing anything (cutscenes, battle animations), then return a screenshot.",
        "input_schema": {
            "type": "object",
            "properties": {"seconds": {"type": "number", "minimum": 0.2, "maximum": 30}},
            "required": ["seconds"],
        },
    },
    {
        "name": "update_notes",
        "description": (
            "Replace your notes with this text. The notes are your only memory between segments: "
            "keep them a complete, current picture (where you are, party and equipment, gil, key items, "
            "the plan, what's left per area, controls and interface quirks you've learned). "
            f"At most {MAX_NOTES_CHARS} characters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"notes": {"type": "string"}},
            "required": ["notes"],
        },
    },
    {
        "name": "complete_objective",
        "description": "Mark an objective done once the screen confirms it. Give the evidence you saw.",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "evidence": {"type": "string"}},
            "required": ["id", "evidence"],
        },
    },
]


def system_prompt(cfg: Config) -> str:
    boosts = (
        "You may use the game's Boost options (encounter toggle, EXP and gil multipliers) when they help."
        if cfg.allow_boosts
        else "Leave the game's Boost options (encounter toggle, EXP and gil multipliers) at their defaults."
    )
    extra = f"\n\nNotes from the person running you:\n{cfg.user_notes.strip()}" if cfg.user_notes.strip() else ""
    return f"""You are playing FINAL FANTASY (the Pixel Remaster of the first game) on a Windows PC, through a virtual Xbox controller. Your goal is to complete the game 100%, working through the objective checklist you're given. Use everything you know about the game: the world, the story order, dungeons, shops, spells, equipment and monsters. Plan the route and the party's growth yourself.

Each action returns a screenshot of the game afterwards; that screenshot is the truth about the game state, so trust it over your memory of the game when they disagree. Things in the remaster can differ from the NES and GBA versions.

The run is split into segments. At the start of each one you get the checklist, your notes and a screenshot. Nothing else carries over, so keep your notes up to date with update_notes whenever something important changes, and always before a segment ends.

Save often, especially before bosses and long dungeons. If the party is wiped out, load the latest save and change the plan rather than repeating it. Grind when the party is underleveled for the next area; it is cheaper than losing fights. Use auto-battle for easy fights if you know how to toggle it.

{boosts}

Only mark an objective complete when the screen shows it happened.{extra}"""


def checklist_text(objectives: list[dict], done: dict[str, str]) -> str:
    lines = []
    for o in objectives:
        mark = "x" if o["id"] in done else " "
        hint = f" (hint: {o['hint']})" if o.get("hint") and o["id"] not in done else ""
        lines.append(f"- [{mark}] {o['id']} [{o['group']}]: {o['title']}{hint}")
    return "\n".join(lines)


def image_block(jpeg: bytes) -> dict:
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}}


class Agent:
    def __init__(self, game: Game, cfg: Config, save_dir: Path, client: anthropic.Anthropic | None = None,
                 objectives: list[dict] | None = None, log=print):
        self.game = game
        self.cfg = cfg
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.save_dir / "state.json"
        self.state = State.load(self.state_path)
        self.objectives = objectives if objectives is not None else load_objectives()
        self.client = client or anthropic.Anthropic()
        self.log = log
        self.system = system_prompt(cfg)
        self.log_file = (self.save_dir / "log.jsonl").open("a", encoding="utf-8")
        self.frames = self.save_dir / "frames"
        if cfg.save_frames:
            self.frames.mkdir(exist_ok=True)

    # ---------- tools ----------

    def _observe(self, note: str) -> list[dict]:
        jpeg = to_jpeg(self.game.screenshot(), self.cfg.screenshot_width)
        if self.cfg.save_frames:
            (self.frames / f"{self.state.turns:06d}.jpg").write_bytes(jpeg)
        return [{"type": "text", "text": note}, image_block(jpeg)]

    def run_tool(self, name: str, args: dict) -> tuple[list[dict] | str, bool]:
        """Run one tool call. Returns (result content, is_error)."""
        try:
            if name == "press_buttons":
                buttons = args["buttons"]
                if not isinstance(buttons, list) or not buttons or any(b not in BUTTONS for b in buttons):
                    return f"buttons must be a non-empty list from: {', '.join(BUTTONS)}", True
                hold, gap = int(args.get("hold_ms", 100)), int(args.get("gap_ms", 250))
                for b in buttons[:30]:
                    self.game.press(b, hold)
                    time.sleep(gap / 1000)
                time.sleep(0.3)
                return self._observe(f"Pressed {' '.join(buttons[:30])}."), False
            if name == "walk":
                direction, tiles = args["direction"], int(args["tiles"])
                if direction not in DIRECTIONS or not 1 <= tiles <= 30:
                    return "direction must be up/down/left/right and tiles 1-30", True
                self.game.press(direction, tiles * self.cfg.tile_ms)
                time.sleep(0.3)
                return self._observe(f"Walked {direction} for about {tiles} tiles."), False
            if name == "wait":
                seconds = min(max(float(args["seconds"]), 0.2), 30.0)
                time.sleep(seconds)
                return self._observe(f"Waited {seconds:g}s."), False
            if name == "update_notes":
                notes = str(args["notes"])
                if len(notes) > MAX_NOTES_CHARS:
                    return f"Notes are {len(notes)} characters; the limit is {MAX_NOTES_CHARS}. Shorten them and try again.", True
                self.state.notes = notes
                self.state.save(self.state_path)
                return "Notes saved.", False
            if name == "complete_objective":
                oid = str(args["id"])
                if oid not in {o["id"] for o in self.objectives}:
                    return f"Unknown objective id {oid!r}.", True
                self.state.done[oid] = str(args.get("evidence", ""))
                self.state.save(self.state_path)
                self.log(f"*** Objective complete: {oid}")
                left = [o["id"] for o in self.objectives if o["id"] not in self.state.done]
                return f"Marked {oid} complete. {len(left)} objectives left.", False
            return f"Unknown tool {name!r}.", True
        except (KeyError, TypeError, ValueError) as e:
            return f"Bad arguments for {name}: {e}", True

    # ---------- the loop ----------

    def _record_usage(self, usage) -> None:
        price = PRICES.get(self.cfg.model, PRICES["claude-opus-5-5"])
        cost = (
            (usage.input_tokens or 0) * price["input"]
            + (usage.output_tokens or 0) * price["output"]
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0) * price["cache_write"]
            + (getattr(usage, "cache_read_input_tokens", 0) or 0) * price["cache_read"]
        ) / 1_000_000
        self.state.spent_usd += cost

    def _call(self, messages: list) -> object:
        return self.client.beta.messages.create(
            model=self.cfg.model,
            max_tokens=16000,
            system=self.system,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": self.cfg.effort},
            cache_control={"type": "ephemeral"},
            # If a safety classifier declines a turn, the API retries it on its recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    def finished(self) -> bool:
        return all(o["id"] in self.state.done for o in self.objectives)

    def out_of_budget(self) -> str | None:
        if self.state.spent_usd >= self.cfg.budget_usd:
            return f"Budget of ${self.cfg.budget_usd:.2f} reached (spent ${self.state.spent_usd:.2f})."
        if self.cfg.max_turns is not None and self.state.turns >= self.cfg.max_turns:
            return f"Turn limit of {self.cfg.max_turns} reached."
        return None

    def run(self) -> str:
        try:
            while not self.finished():
                if reason := self.out_of_budget():
                    return reason
                self.run_segment()
            return "Every objective is complete."
        finally:
            self.game.release_all()
            self.state.save(self.state_path)
            self.log_file.close()

    def _wait_if_paused(self) -> None:
        pause = self.save_dir / "PAUSE"
        if pause.exists():
            self.log(f"Paused: delete {pause} to continue.")
            self.game.release_all()
            while pause.exists():
                time.sleep(2)

    def run_segment(self) -> None:
        self.state.segments += 1
        seg = self.state.segments
        self.log(f"=== Segment {seg} (turn {self.state.turns}, ${self.state.spent_usd:.2f} spent) ===")
        intro = (
            f"Segment {seg}.\n\nObjectives:\n{checklist_text(self.objectives, self.state.done)}\n\n"
            f"Your notes:\n{self.state.notes or '(none yet: this is the first segment)'}\n\n"
            "Here is the current screen. Carry on."
        )
        messages: list = [{"role": "user", "content": self._observe(intro)}]

        for i in range(self.cfg.segment_turns + 1):
            last = i == self.cfg.segment_turns
            if last:
                messages[-1]["content"].append({"type": "text", "text": (
                    "This segment ends after this turn. Call update_notes now with a complete handoff "
                    "for your next segment, which won't see this conversation.")})
            self._wait_if_paused()
            response = self._call(messages)
            self._record_usage(response.usage)
            self.state.turns += 1

            if response.stop_reason == "refusal":
                self.log(f"Turn declined ({getattr(response.stop_details, 'category', None)}); starting a new segment.")
                break

            texts = [b.text for b in response.content if b.type == "text" and b.text.strip()]
            calls = [b for b in response.content if b.type == "tool_use"]
            for t in texts:
                self.log(f"Claude: {t}")
            messages.append({"role": "assistant", "content": response.content})

            results = []
            for call in calls:
                self.log(f"  -> {call.name} {json.dumps(call.input)[:200]}")
                content, is_error = self.run_tool(call.name, call.input)
                results.append({"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": is_error})
            self.log_file.write(json.dumps({
                "segment": seg, "turn": self.state.turns, "stop_reason": response.stop_reason, "text": texts,
                "calls": [{"name": c.name, "input": c.input} for c in calls], "spent_usd": round(self.state.spent_usd, 4),
            }) + "\n")
            self.log_file.flush()
            self.state.save(self.state_path)

            if last or self.finished() or self.out_of_budget():
                break
            if not results:
                messages.append({"role": "user", "content": self._observe("Keep playing: act with a tool. Here is the screen.")})
            else:
                messages.append({"role": "user", "content": results})
