"""Runs the agent loop against a fake game and a scripted fake Claude (no API calls)."""

import json
from types import SimpleNamespace as NS

from ff1agent.agent import Agent, Config, State
from ff1agent.game import FakeGame

OBJECTIVES = [{"id": "garland", "group": "story", "title": "Beat Garland"},
              {"id": "chaos", "group": "story", "title": "Beat Chaos"}]


def usage():
    return NS(input_tokens=1000, output_tokens=200, cache_creation_input_tokens=0, cache_read_input_tokens=0)


def reply(*calls, text="ok", stop="tool_use"):
    content = [NS(type="text", text=text)]
    content += [NS(type="tool_use", id=f"t{i}", name=n, input=a) for i, (n, a) in enumerate(calls)]
    return NS(content=content, stop_reason=stop, usage=usage(), stop_details=None)


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.requests.append(json.loads(json.dumps(kw["messages"], default=lambda o: o.__dict__)))
        assert kw["fallbacks"] == "default"
        return self.replies.pop(0)


def make(tmp_path, replies, **cfg):
    game = FakeGame()
    client = FakeClient(replies)
    agent = Agent(game, Config(**cfg), tmp_path, client=client, objectives=OBJECTIVES, log=lambda *_: None)
    return agent, game, client


def test_plays_and_completes(tmp_path):
    agent, game, client = make(tmp_path, [
        reply(("press_buttons", {"buttons": ["a", "down"], "hold_ms": 50, "gap_ms": 0})),
        reply(("walk", {"direction": "up", "tiles": 2}), ("complete_objective", {"id": "garland", "evidence": "saw it"})),
        reply(("update_notes", {"notes": "Garland down."}), ("complete_objective", {"id": "chaos", "evidence": "credits"})),
    ], tile_ms=10)
    assert agent.run() == "Every objective is complete."
    assert game.presses == [("a", 50), ("down", 50), ("up", 20)]
    state = State.load(tmp_path / "state.json")
    assert set(state.done) == {"garland", "chaos"} and state.notes == "Garland down." and state.turns == 3
    # Tool results for parallel calls come back together in one user message.
    second_results = client.requests[2][-1]["content"]
    assert [r["type"] for r in second_results] == ["tool_result", "tool_result"]


def test_segment_handoff_and_resume(tmp_path):
    agent, _, client = make(tmp_path, [
        reply(("wait", {"seconds": 0.2})),
        reply(("update_notes", {"notes": "In Cornelia."})),
        reply(text="looking", stop="end_turn"),
    ], segment_turns=1, max_turns=3)
    assert "Turn limit" in agent.run()
    # The segment's last turn asks for a handoff; the next segment starts from the notes.
    assert "segment ends" in client.requests[1][-1]["content"][-1]["text"]
    assert "In Cornelia." in client.requests[2][0]["content"][0]["text"]


def test_bad_input_is_an_error_not_a_crash(tmp_path):
    agent, game, _ = make(tmp_path, [])
    content, err = agent.run_tool("press_buttons", {"buttons": ["select"]})
    assert err and not game.presses
    content, err = agent.run_tool("complete_objective", {"id": "nope", "evidence": ""})
    assert err


def test_budget_stops_run(tmp_path):
    agent, _, _ = make(tmp_path, [reply(("wait", {"seconds": 0.2}))] * 5, budget_usd=0.01)
    assert "Budget" in agent.run()
