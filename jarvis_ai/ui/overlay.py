from __future__ import annotations

import argparse
import queue
import subprocess
import threading
import tkinter as tk
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import sys

# Ensure the project root (containing the jarvis_ai package) is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import keyboard  # type: ignore
except Exception:  # pragma: no cover
    keyboard = None


@dataclass
class OverlayConfig:
    hotkey: str = "right ctrl"
    size: int = 260
    bg_color: str = "#111111"
    text_color: str = "#00e5ff"
    label: str = "JARVIS"
    opacity: float = 0.6
    greeting: str = "hello sir how can i help"


class BubbleOverlay:
    def __init__(self, root: tk.Tk, config: OverlayConfig) -> None:
        self.root = root
        self.config = config
        self._visible = False
        self._events: queue.Queue[bool] = queue.Queue()
        self._status_events: queue.Queue[str] = queue.Queue()
        self._last_greeting_at: float = 0.0

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.config.opacity)

        # Fullscreen overlay to dim background
        width = self.root.winfo_screenwidth()
        height = self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}+0+0")

        canvas = tk.Canvas(self.root, width=width, height=height, highlightthickness=0, bg="#000000")
        canvas.pack(fill="both", expand=True)

        # Centered "3D"-style orb animation
        cx, cy = width // 2, height // 2
        r = self.config.size // 2
        self._orb_id = canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            fill=self.config.bg_color,
            outline="",
        )
        inner_r = int(r * 0.7)
        self._inner_orb_id = canvas.create_oval(
            cx - inner_r,
            cy - inner_r,
            cx + inner_r,
            cy + inner_r,
            outline=self.config.text_color,
            width=3,
        )
        # Rotating ring
        ring_r = int(r * 1.2)
        self._ring_id = canvas.create_oval(
            cx - ring_r,
            cy - ring_r,
            cx + ring_r,
            cy + ring_r,
            outline=self.config.text_color,
            width=2,
        )

        self._text_id = canvas.create_text(
            cx,
            cy + r + 30,
            text=self.config.label,
            fill=self.config.text_color,
            font=("Segoe UI", 16, "bold"),
        )

        self._canvas = canvas
        self._angle = 0.0

        self.root.withdraw()
        self.root.after(16, self._poll_events)
        self.root.after(30, self._animate)

    def show(self) -> None:
        if not self._visible:
            self.root.deiconify()
            self._visible = True
            self._say_greeting()

    def hide(self) -> None:
        if self._visible:
            self.root.withdraw()
            self._visible = False

    def enqueue_visibility(self, visible: bool) -> None:
        self._events.put(visible)

    def enqueue_status(self, text: str) -> None:
        self._status_events.put(text)

    def _poll_events(self) -> None:
        while not self._events.empty():
            visible = self._events.get_nowait()
            if visible:
                self.show()
            else:
                self.hide()
        while not self._status_events.empty():
            text = self._status_events.get_nowait()
            self._canvas.itemconfig(self._text_id, text=text)
        self.root.after(16, self._poll_events)

    def _animate(self) -> None:
        # Simple rotating highlight on the ring to give a "moving AI" feel
        if self._visible:
            cx = self._canvas.winfo_width() // 2
            cy = self._canvas.winfo_height() // 2
            ring_r = int(self.config.size // 2 * 1.2)
            self._angle = (self._angle + 5) % 360
            # Compute small dot position on ring
            import math

            rad = math.radians(self._angle)
            dx = ring_r * math.cos(rad)
            dy = ring_r * math.sin(rad)
            dot_r = 6
            if hasattr(self, "_dot_id"):
                self._canvas.coords(
                    self._dot_id,
                    cx + dx - dot_r,
                    cy + dy - dot_r,
                    cx + dx + dot_r,
                    cy + dy + dot_r,
                )
            else:
                self._dot_id = self._canvas.create_oval(
                    cx + dx - dot_r,
                    cy + dy - dot_r,
                    cx + dx + dot_r,
                    cy + dy + dot_r,
                    fill=self.config.text_color,
                    outline="",
                )
        self.root.after(30, self._animate)

    def _say_greeting(self) -> None:
        # Log so you can see in the console that the greeting fired
        print("[JARVIS][OVERLAY] Greeting triggered.", flush=True)
        try:
            from jarvis_ai.voice.tts import speak

            speak(self.config.greeting)
        except Exception as exc:
            print(f"[JARVIS][OVERLAY] Greeting error: {exc}", flush=True)


def _read_agent_stdout(process: subprocess.Popen[str], overlay: BubbleOverlay) -> None:
    for raw in process.stdout or []:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("STATUS:"):
            overlay.enqueue_status(line.replace("STATUS:", "").strip())
        elif line.startswith("JARVIS>"):
            overlay.enqueue_status(line.replace("JARVIS>", "").strip())


def run_overlay(config: Optional[OverlayConfig] = None, agent_cmd: Optional[str] = None) -> None:
    if keyboard is None:
        raise RuntimeError("keyboard package is not installed")
    cfg = config or OverlayConfig()

    root = tk.Tk()
    overlay = BubbleOverlay(root, cfg)

    if agent_cmd:
        process = subprocess.Popen(
            agent_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            shell=True,
        )
        threading.Thread(target=_read_agent_stdout, args=(process, overlay), daemon=True).start()

    def on_press(_: object) -> None:
        overlay.enqueue_visibility(True)

    def on_release(_: object) -> None:
        overlay.enqueue_visibility(False)

    keyboard.on_press_key(cfg.hotkey, on_press)
    keyboard.on_release_key(cfg.hotkey, on_release)

    root.mainloop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JARVIS overlay")
    parser.add_argument(
        "--agent-cmd",
        default="",
        help="Command to launch JARVIS agent and read its stdout",
    )
    args = parser.parse_args()
    run_overlay(agent_cmd=args.agent_cmd or None)
