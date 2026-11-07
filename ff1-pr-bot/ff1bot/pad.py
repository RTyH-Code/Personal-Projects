"""A virtual Xbox 360 controller (Windows, needs the ViGEmBus driver)."""

from __future__ import annotations

import time

BUTTONS = ["a", "b", "x", "y", "start", "back", "lb", "rb", "lt", "rt",
           "up", "down", "left", "right", "l3", "r3"]


class Pad:
    def __init__(self, window_title: str | None = "FINAL FANTASY"):
        import vgamepad as vg  # noqa: PLC0415 - Windows-only

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
        self.window_title = window_title
        time.sleep(1.0)  # let Windows register the controller before the game polls it

    def focus(self) -> None:
        """Bring the game to the front; some games ignore controllers while unfocused."""
        if not self.window_title:
            return
        try:
            import pygetwindow  # noqa: PLC0415

            wins = [w for w in pygetwindow.getWindowsWithTitle(self.window_title) if w.width > 100]
            if wins and not wins[0].isActive:
                if wins[0].isMinimized:
                    wins[0].restore()
                wins[0].activate()
        except Exception:
            pass

    def hold(self, button: str) -> None:
        if button in ("lt", "rt"):
            (self.pad.left_trigger if button == "lt" else self.pad.right_trigger)(value=255)
        else:
            self.pad.press_button(button=self._buttons[button])
        self.pad.update()

    def release(self, button: str) -> None:
        if button in ("lt", "rt"):
            (self.pad.left_trigger if button == "lt" else self.pad.right_trigger)(value=0)
        else:
            self.pad.release_button(button=self._buttons[button])
        self.pad.update()

    def press(self, button: str, hold_ms: int = 80, after_ms: int = 80) -> None:
        self.focus()
        self.hold(button)
        time.sleep(hold_ms / 1000)
        self.release(button)
        time.sleep(after_ms / 1000)

    def release_all(self) -> None:
        self.pad.reset()
        self.pad.update()


if __name__ == "__main__":
    # Quick check that the game sees the controller:  python -m ff1bot.pad down 3
    import sys

    button = sys.argv[1] if len(sys.argv) > 1 else "down"
    times = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    if button not in BUTTONS:
        sys.exit(f"Unknown button {button!r}. Choose from: {', '.join(BUTTONS)}")
    pad = Pad()
    for _ in range(times):
        pad.press(button, hold_ms=120, after_ms=300)
    pad.release_all()
    print(f"Pressed {button} {times} time(s).")
