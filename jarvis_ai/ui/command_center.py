from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

INSTRUCTIONS = """
JARVIS COMMAND CENTER
=====================

How to use:
- Type and Send (Enter) or toggle the mic to speak (hold your push-to-talk key, defaults to Right Ctrl).
- JARVIS plans and acts across browser/HTTP/files/system; cloud falls back to local automatically.

Common commands:
- "remember that my name is <name>"
- "open chrome" / "go to https://example.com"
- Natural missions (e.g., "download my transcript from ..."); JARVIS plans actions.
- Quick actions: "search cats", "play lo-fi", "system stats".

Safety:
- Confirmations may be required for actions (kill process, write files, etc.).
- Respect site terms; do not attempt to bypass security.

Tip: Be specific. Include URLs, selectors, and expected files when you can.
"""


class CommandCenter:
    def __init__(self) -> None:
        self.proc: subprocess.Popen[str] | None = None
        self.reader_thread: threading.Thread | None = None
        self.stdout_queue: "queue.Queue[str]" = queue.Queue()
        self.voice_enabled: bool = False
        self.theme_bg = "#05080F"
        self.theme_panel = "#0C1424"
        self.theme_accent = "#4DD0E1"
        self.theme_accent_2 = "#7C3AED"
        self.theme_text = "#E8F1FF"
        self.theme_muted = "#94A3B8"
        self.font_sans = ("Segoe UI", 11)
        self.font_sans_bold = ("Segoe UI Semibold", 11)
        self.font_mono = ("Cascadia Code", 10)

        self.root = tk.Tk()
        self.root.title("JARVIS Command Center")
        self.root.geometry("960x640")
        self.root.configure(bg=self.theme_bg)

        # Header with pulsing ring
        self.header = tk.Canvas(self.root, height=90, bg=self.theme_bg, highlightthickness=0)
        self.header.pack(fill=tk.X, padx=8, pady=4)
        self._ring_phase = 0
        self._ring_id = None
        self._orb_id = None
        self._ring_center = (0, 0)
        self._draw_header()
        self.header.bind("<Configure>", lambda _: self._draw_header())

        # Layout
        self.instructions = scrolledtext.ScrolledText(
            self.root,
            height=10,
            wrap=tk.WORD,
            state="disabled",
            bg=self.theme_panel,
            fg=self.theme_text,
            insertbackground=self.theme_accent,
            relief=tk.FLAT,
            borderwidth=0,
            font=self.font_sans,
        )
        self.instructions.pack(fill=tk.X, padx=8, pady=4)
        self._set_instructions(INSTRUCTIONS)

        self.log = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            state="disabled",
            bg=self.theme_panel,
            fg=self.theme_text,
            insertbackground=self.theme_accent,
            relief=tk.FLAT,
            borderwidth=0,
            font=self.font_mono,
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        entry_frame = tk.Frame(self.root)
        entry_frame.configure(bg=self.theme_bg)
        entry_frame.pack(fill=tk.X, padx=8, pady=8)

        self.voice_var = tk.BooleanVar(value=False)
        self.mic_btn = tk.Button(
            entry_frame,
            text="🎙 OFF",
            command=self._on_toggle_voice,
            bg=self.theme_panel,
            fg=self.theme_text,
            activebackground="#1f2937",
            activeforeground=self.theme_accent,
            relief=tk.FLAT,
            padx=10,
            pady=4,
            font=self.font_sans_bold,
        )
        self.mic_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.entry = tk.Entry(entry_frame)
        self.entry.configure(
            bg="#0b1220",
            fg=self.theme_text,
            insertbackground=self.theme_accent,
            relief=tk.FLAT,
            borderwidth=2,
            highlightthickness=1,
            highlightcolor=self.theme_accent_2,
            highlightbackground="#0f172a",
            font=self.font_sans,
        )
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", self._on_send)

        send_btn = tk.Button(
            entry_frame,
            text="Send",
            command=self._on_send,
            bg=self.theme_panel,
            fg=self.theme_text,
            activebackground="#1f2937",
            activeforeground=self.theme_accent,
            relief=tk.FLAT,
            padx=12,
            pady=4,
            font=self.font_sans_bold,
        )
        send_btn.pack(side=tk.RIGHT)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._start_agent(voice=False)
        self._poll_stdout()
        self._animate_header()

    def _set_instructions(self, text: str) -> None:
        self.instructions.configure(state="normal")
        self.instructions.delete("1.0", tk.END)
        self.instructions.insert(tk.END, text)
        self.instructions.configure(state="disabled")

    def _start_agent(self, voice: bool) -> None:
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        if not voice:
            env["JARVIS_TEXT_ONLY"] = "1"
        else:
            env.pop("JARVIS_TEXT_ONLY", None)
        self.voice_enabled = voice
        mode = "Voice" if voice else "Text"
        self._append_log(f"[JARVIS] Starting agent in {mode} mode...")
        cmd = ["python", "-m", "jarvis_ai.main"]
        self.proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        self.reader_thread = threading.Thread(target=self._reader, daemon=True)
        self.reader_thread.start()

    def _restart_agent(self, voice: bool) -> None:
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass
        self.proc = None
        self.reader_thread = None
        self._start_agent(voice=voice)

    def _reader(self) -> None:
        assert self.proc is not None
        for line in self.proc.stdout or []:
            self.stdout_queue.put(line.rstrip())
        self.stdout_queue.put("[JARVIS] Agent exited.")

    def _poll_stdout(self) -> None:
        while not self.stdout_queue.empty():
            line = self.stdout_queue.get_nowait()
            self._append_log(line)
        self.root.after(100, self._poll_stdout)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _on_send(self, event: object | None = None) -> None:
        msg = self.entry.get().strip()
        if not msg or self.proc is None or self.proc.stdin is None:
            return
        self.proc.stdin.write(msg + "\n")
        self.proc.stdin.flush()
        self._append_log(f"You> {msg}")
        self.entry.delete(0, tk.END)

    def _on_toggle_voice(self) -> None:
        desired = bool(self.voice_var.get())
        # Toggle state manually since we're using a button
        desired = not self.voice_enabled
        self.voice_var.set(desired)
        label = "🎙 ON" if desired else "🎙 OFF"
        self.mic_btn.configure(text=label, fg=self.theme_accent if desired else self.theme_text)
        self._append_log(f"[JARVIS] Switching agent to {'Voice' if desired else 'Text'} mode...")
        self._restart_agent(voice=desired)

    def _draw_header(self) -> None:
        w = max(int(self.header.winfo_width()), 960)
        h = max(int(self.header.winfo_height()), 90)
        self.header.configure(height=h)
        left_cx, cy = 70, h // 2
        base_r = 22
        self.header.delete("all")
        grad_inner = self.header.create_oval(
            left_cx - base_r,
            cy - base_r,
            left_cx + base_r,
            cy + base_r,
            fill=self.theme_accent,
            outline="",
        )
        grad_outer = self.header.create_oval(
            left_cx - base_r * 1.3,
            cy - base_r * 1.3,
            left_cx + base_r * 1.3,
            cy + base_r * 1.3,
            outline=self.theme_accent_2,
            width=3,
        )
        self._orb_id = grad_inner
        self._ring_id = grad_outer
        self.header.create_text(
            left_cx + 60,
            cy - 10,
            text="JARVIS Command Center",
            fill=self.theme_text,
            font=("Segoe UI Semibold", 17),
            anchor="w",
        )
        self.header.create_text(
            left_cx + 60,
            cy + 14,
            text="Operate as agent + assistant",
            fill=self.theme_muted,
            font=("Segoe UI", 11),
            anchor="w",
        )

        # Right-side animated ring
        ring_cx = w - 140
        ring_r = 26
        self._ring_center = (ring_cx, cy)
        self._ring_id = self.header.create_oval(
            ring_cx - ring_r,
            cy - ring_r,
            ring_cx + ring_r,
            cy + ring_r,
            outline=self.theme_accent_2,
            width=3,
        )

    def _animate_header(self) -> None:
        if self._ring_id:
            self._ring_phase = (self._ring_phase + 1) % 40
            scale = 1.1 + 0.08 * (self._ring_phase % 20)
            ring_cx, cy = self._ring_center
            base_r = 26
            ring_r = base_r * scale
            self.header.coords(
                self._ring_id,
                ring_cx - ring_r,
                cy - ring_r,
                ring_cx + ring_r,
                cy + ring_r,
            )
        self.header.after(50, self._animate_header)

    def _on_close(self) -> None:
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    CommandCenter().run()


if __name__ == "__main__":
    main()
