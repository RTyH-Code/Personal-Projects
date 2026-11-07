"""Talks to the FF1 Bridge mod running inside the game (one JSON request per line)."""

from __future__ import annotations

import json
import socket
from pathlib import Path

DEFAULT_PORT = 52323
PATHS_FILE = Path(__file__).with_name("paths.json")


class BridgeError(Exception):
    """The mod answered with an error (bad path, missing member, null object...)."""


def load_paths(path: Path = PATHS_FILE) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


class Bridge:
    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 15.0):
        self.host, self.port, self.timeout = host, port, timeout
        self._sock: socket.socket | None = None
        self._file = None

    def _connect(self) -> None:
        try:
            self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        except OSError as e:
            raise ConnectionError(
                f"Can't reach the FF1 Bridge on {self.host}:{self.port}. Is the game running with the mod installed?"
            ) from e
        self._file = self._sock.makefile("rwb")

    def close(self) -> None:
        if self._sock:
            self._sock.close()
        self._sock = self._file = None

    def call(self, cmd: str, **kwargs):
        request = (json.dumps({"cmd": cmd, **kwargs}) + "\n").encode()
        for attempt in (1, 2):
            if self._file is None:
                self._connect()
            try:
                self._file.write(request)
                self._file.flush()
                line = self._file.readline()
                if not line:
                    raise ConnectionError("The bridge closed the connection.")
                break
            except (OSError, ConnectionError):
                self.close()
                if attempt == 2:
                    raise
        reply = json.loads(line)
        if not reply.get("ok"):
            raise BridgeError(reply.get("error", "unknown error"))
        return reply["result"]

    # Convenience wrappers around the mod's commands.
    def ping(self) -> dict:
        return self.call("ping")

    def find_types(self, pattern: str, limit: int = 100) -> list[str]:
        return self.call("find_types", pattern=pattern, limit=limit)

    def members(self, path: str) -> dict:
        return self.call("members", path=path)

    def get(self, path: str, depth: int = 1, max_items: int = 100):
        return self.call("get", path=path, depth=depth, max_items=max_items)

    def set(self, path: str, value) -> None:
        self.call("set", path=path, value=value)

    def state(self, paths: dict[str, str | dict], depth: int = 0) -> dict:
        """Reads many paths in one request (one game frame). Failures come back as {"$error": ...}."""
        return self.call("state", paths=paths, depth=depth)

    def read_named(self, names: list[str] | None = None, paths: dict[str, dict] | None = None) -> dict:
        """Reads entries from paths.json by name."""
        table = paths if paths is not None else load_paths()
        wanted = {n: {"path": table[n]["path"], "depth": table[n].get("depth", 0)}
                  for n in (names or table) if table[n].get("path")}
        return self.state(wanted)
