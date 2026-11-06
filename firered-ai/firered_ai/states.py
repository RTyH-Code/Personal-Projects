"""Save-state files: raw, or gzip-compressed as the learning agent writes them."""

from __future__ import annotations

import gzip
import os
from pathlib import Path


def load_state_file(path: str | os.PathLike) -> bytes:
    data = Path(path).read_bytes()
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def save_state_file(path: str | os.PathLike, state: bytes) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(gzip.compress(state))
