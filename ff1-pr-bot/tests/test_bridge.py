"""Runs the mod's core (the TestHost build, over fake game objects) and talks to it from Python."""

import shutil
import subprocess
from pathlib import Path

import pytest

from ff1bot import explore
from ff1bot.bridge import Bridge, BridgeError

HOST_DIR = Path(__file__).resolve().parents[1] / "mod" / "TestHost"
UDM = "Last.Management.UserDataManager.Instance()"


@pytest.fixture(scope="module")
def bridge(tmp_path_factory):
    if not shutil.which("dotnet"):
        pytest.skip("needs the .NET SDK")
    out = tmp_path_factory.mktemp("host")
    subprocess.run(["dotnet", "build", str(HOST_DIR), "-o", str(out), "-nologo", "-v", "q"], check=True, capture_output=True)
    proc = subprocess.Popen(["dotnet", str(out / "TestHost.dll"), "0"], stdout=subprocess.PIPE, text=True)
    port = None
    for line in proc.stdout:
        if line.startswith("PORT "):
            port = int(line.split()[1])
            break
    b = Bridge(port=port)
    yield b
    b.close()
    proc.kill()


def test_ping_and_find(bridge):
    assert bridge.ping()["version"]
    assert "Last.Management.UserDataManager" in bridge.find_types("userdatamanager")


def test_get_paths(bridge):
    assert bridge.get(f"{UDM}.OwendGil", 0) == 500
    assert bridge.get(f"{UDM}.Party[1].Name", 0) == "Mage"
    assert bridge.get(f"{UDM}.GetCharacter(0).Level", 0) == 3
    assert bridge.get(f"{UDM}.Flags[1]", 0) == "bridge"
    assert bridge.get(f"{UDM}.State", 0) == "Walk"
    assert bridge.get(f"{UDM}.Party[0].as(Last.Management.OwnedCharacterData).Hp", 0) == 50
    assert bridge.get(f"{UDM}.Party[0].as(Last.Management.ConfigData)", 0) is None


def test_objects_and_errors(bridge):
    hero = bridge.get(f"{UDM}.Party[0]", 1)
    assert hero["Name"] == "Warrior" and hero["Throws"].startswith("!error")
    pos = bridge.get(f"{UDM}.Position", 1)
    assert set(pos) == {"$type", "x", "y", "z"}  # struct: fields only, no derived properties
    with pytest.raises(BridgeError, match="No member 'Nope'"):
        bridge.get(f"{UDM}.Nope")
    with pytest.raises(BridgeError, match="No type"):
        bridge.get("Not.A.Type")


def test_state_members_and_set(bridge):
    s = bridge.state({"gil": f"{UDM}.OwendGil", "bad": f"{UDM}.Missing", "party": {"path": f"{UDM}.Party", "depth": 1}})
    assert s["gil"] == 500 and "$error" in s["bad"] and s["party"][1]["MaxHp"] == 25
    m = bridge.members(UDM)
    assert any(p.startswith("OwendGil") for p in m["properties"])
    assert any(x.startswith("GetCharacter(System.Int32 i)") for x in m["methods"])
    assert "Instance() -> Last.Management.UserDataManager" in bridge.members("Last.Management.UserDataManager")["methods"]
    bridge.set(f"{UDM}.OwendGil", 1234)
    bridge.set(f"{UDM}.State", "Dush")
    assert bridge.get(f"{UDM}.OwendGil", 0) == 1234 and bridge.get(f"{UDM}.State", 0) == "Dush"


def test_explore_search_and_diff(bridge, capsys, monkeypatch):
    port = ["--port", str(bridge.port)]
    assert explore.main(port + ["search", UDM, "Warrior"]) == 0
    assert f"{UDM}.Party[0].Name" in capsys.readouterr().out
    monkeypatch.setattr("builtins.input", lambda *_: __import__("time").sleep(0.2))
    assert explore.main(port + ["diff", UDM]) == 0
    out = capsys.readouterr().out
    assert f"{UDM}.Steps:" in out
