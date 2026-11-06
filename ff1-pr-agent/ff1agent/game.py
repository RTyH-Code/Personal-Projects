"""The agent's hands and eyes: a virtual Xbox controller and window screenshots.

Windows only for the real game. `FakeGame` stands in for tests and dry runs.
"""

from __future__ import annotations

import io
import time
from typing import Protocol

from PIL import Image

BUTTONS = [
    "a", "b", "x", "y", "start", "back", "lb", "rb", "lt", "rt",
    "up", "down", "left", "right", "l3", "r3",
]
DIRECTIONS = {"up", "down", "left", "right"}


class Game(Protocol):
    def screenshot(self) -> Image.Image: ...
    def press(self, button: str, hold_ms: int) -> None: ...
    def release_all(self) -> None: ...


def to_jpeg(image: Image.Image, max_width: int, quality: int = 80) -> bytes:
    """Shrink a screenshot so it costs fewer tokens, and encode it as JPEG."""
    if image.width > max_width:
        image = image.resize((max_width, round(image.height * max_width / image.width)), Image.LANCZOS)
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


class WindowsGame:
    """Drives FINAL FANTASY (Pixel Remaster) through a ViGEm virtual Xbox 360 pad."""

    def __init__(self, window_title: str = "FINAL FANTASY"):
        import mss  # noqa: PLC0415 - Windows-only dependencies
        import pygetwindow
        import vgamepad as vg

        self._vg = vg
        self._mss = mss.mss()
        self._gw = pygetwindow
        self.window_title = window_title
        self.pad = vg.VX360Gamepad()
        b = vg.XUSB_BUTTON
        self._buttons = {
            "a": b.XUSB_GAMEPAD_A, "b": b.XUSB_GAMEPAD_B, "x": b.XUSB_GAMEPAD_X, "y": b.XUSB_GAMEPAD_Y,
            "start": b.XUSB_GAMEPAD_START, "back": b.XUSB_GAMEPAD_BACK,
            "lb": b.XUSB_GAMEPAD_LEFT_SHOULDER, "rb": b.XUSB_GAMEPAD_RIGHT_SHOULDER,
            "up": b.XUSB_GAMEPAD_DPAD_UP, "down": b.XUSB_GAMEPAD_DPAD_DOWN,
            "left": b.XUSB_GAMEPAD_DPAD_LEFT, "right": b.XUSB_GAMEPAD_DPAD_RIGHT,
            "l3": b.XUSB_GAMEPAD_LEFT_THUMB, "r3": b.XUSB_GAMEPAD_RIGHT_THUMB,
        }
        # Give Windows a moment to register the new controller before the game polls it.
        time.sleep(1.0)

    def _window(self):
        matches = [w for w in self._gw.getWindowsWithTitle(self.window_title) if w.width > 100]
        if not matches:
            raise RuntimeError(f"No window titled {self.window_title!r}. Is the game running (windowed)?")
        return matches[0]

    def focus(self) -> None:
        win = self._window()
        if win.isMinimized:
            win.restore()
        if not win.isActive:
            try:
                win.activate()
            except Exception:  # Windows sometimes refuses focus changes; input usually still lands.
                pass

    def screenshot(self) -> Image.Image:
        win = self._window()
        shot = self._mss.grab({"left": win.left, "top": win.top, "width": win.width, "height": win.height})
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def press(self, button: str, hold_ms: int) -> None:
        self.focus()
        if button in ("lt", "rt"):
            setter = self.pad.left_trigger if button == "lt" else self.pad.right_trigger
            setter(value=255)
            self.pad.update()
            time.sleep(hold_ms / 1000)
            setter(value=0)
        else:
            self.pad.press_button(button=self._buttons[button])
            self.pad.update()
            time.sleep(hold_ms / 1000)
            self.pad.release_button(button=self._buttons[button])
        self.pad.update()

    def release_all(self) -> None:
        self.pad.reset()
        self.pad.update()


class FakeGame:
    """A stand-in game for tests: records presses, returns a plain image."""

    def __init__(self, size=(1280, 720)):
        self.size = size
        self.presses: list[tuple[str, int]] = []

    def screenshot(self) -> Image.Image:
        return Image.new("RGB", self.size, (20, 20, 80))

    def press(self, button: str, hold_ms: int) -> None:
        self.presses.append((button, hold_ms))

    def release_all(self) -> None:
        pass
