from __future__ import annotations

from typing import Optional

try:
    import keyboard  # type: ignore
except Exception:  # pragma: no cover
    keyboard = None

try:
    import pyautogui  # type: ignore
except Exception:  # pragma: no cover
    pyautogui = None

from jarvis_ai.memory.logs import Logger
from jarvis_ai.tools.safety import require_confirmation


def send_keys(text: str, require_confirm: bool = True, logger: Optional[Logger] = None) -> None:
    if keyboard is None:
        raise RuntimeError("keyboard package is not installed")
    if require_confirm and not require_confirmation(f"send keys: {text}"):
        raise PermissionError("User denied keyboard input")
    try:
        keyboard.write(text)
        if logger:
            logger.log(task=f"send_keys {text}", decision="send_keys", outcome="success")
    except Exception as exc:
        if logger:
            logger.log(task=f"send_keys {text}", decision="send_keys", outcome="failed", error=str(exc))
        raise


def hotkey(*keys: str, require_confirm: bool = True, logger: Optional[Logger] = None) -> None:
    if pyautogui is None:
        raise RuntimeError("pyautogui package is not installed")
    if require_confirm and not require_confirmation(f"hotkey: {'+'.join(keys)}"):
        raise PermissionError("User denied hotkey")
    try:
        pyautogui.hotkey(*keys)
        if logger:
            logger.log(task=f"hotkey {'+'.join(keys)}", decision="hotkey", outcome="success")
    except Exception as exc:
        if logger:
            logger.log(task=f"hotkey {'+'.join(keys)}", decision="hotkey", outcome="failed", error=str(exc))
        raise


def move_mouse(x: int, y: int, duration: float = 0.2, require_confirm: bool = True, logger: Optional[Logger] = None) -> None:
    if pyautogui is None:
        raise RuntimeError("pyautogui package is not installed")
    if require_confirm and not require_confirmation(f"move mouse to {x},{y}"):
        raise PermissionError("User denied mouse move")
    try:
        pyautogui.moveTo(x, y, duration=duration)
        if logger:
            logger.log(task=f"move_mouse {x},{y}", decision="move_mouse", outcome="success")
    except Exception as exc:
        if logger:
            logger.log(task=f"move_mouse {x},{y}", decision="move_mouse", outcome="failed", error=str(exc))
        raise


def click_mouse(button: str = "left", require_confirm: bool = True, logger: Optional[Logger] = None) -> None:
    if pyautogui is None:
        raise RuntimeError("pyautogui package is not installed")
    if require_confirm and not require_confirmation(f"click mouse {button}"):
        raise PermissionError("User denied mouse click")
    try:
        pyautogui.click(button=button)
        if logger:
            logger.log(task=f"click_mouse {button}", decision="click_mouse", outcome="success")
    except Exception as exc:
        if logger:
            logger.log(task=f"click_mouse {button}", decision="click_mouse", outcome="failed", error=str(exc))
        raise
